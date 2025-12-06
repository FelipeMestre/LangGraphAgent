"""Application handler for API queries."""
from __future__ import annotations

import time
from typing import Dict, Mapping, Optional

from src.application.commands.api_query_command import ApiQueryCommand
from src.application.handlers.protocols import AgentRunner
from src.application.queries.query_result import QueryResult, QueryStatus
from src.domain.value_objects.oauth2_credentials import OAuth2Token
from src.ports.output.oauth2_provider import OAuth2TokenProvider


class ApiQueryHandler:
  """Coordinates API queries executed by the LangGraph API agent.
  
  Handles OAuth2 authentication transparently - if the command requires
  OAuth2, the handler obtains/refreshes tokens before executing the query.
  """

  def __init__(
    self,
    agent_runner: AgentRunner,
    oauth2_provider: Optional[OAuth2TokenProvider] = None,
  ):
    self._agent_runner = agent_runner
    self._oauth2_provider = oauth2_provider
    self._oauth2_tokens: Dict[str, OAuth2Token] = {}

  async def handle(self, command: ApiQueryCommand) -> QueryResult:
    start = time.perf_counter()
    try:
      # Get auth headers, handling OAuth2 if needed
      auth_headers = await self._get_auth_headers(command)

      agent_response: Mapping[str, object] = await self._agent_runner.run({
        'swagger_url': command.swagger_url,
        'user_query': command.user_query,
        'auth_headers': auth_headers,
        'max_endpoints': command.max_endpoints,
      })

      execution_time = time.perf_counter() - start
      error = agent_response.get('error')
      status = QueryStatus.ERROR if error else QueryStatus.SUCCESS

      metadata = {
        'endpoints_discovered': agent_response.get('total_endpoints', 0),
        'endpoints_used': self._extract_endpoint_paths(agent_response.get('selected_endpoints', [])),
        'step': agent_response.get('step'),
      }
      
      # Add OAuth2 info to metadata if used
      if command.requires_oauth2:
        metadata['auth_type'] = 'oauth2'

      return QueryResult(
        status=status,
        response_text=str(agent_response.get('final_response', '')),
        analysis=str(agent_response.get('analysis', '')) if agent_response.get('analysis') else None,
        data=self._normalize_data(agent_response.get('api_data')),
        metadata=metadata,
        execution_time=execution_time,
        error=str(error) if error else None,
      )
    except Exception as exc:  # noqa: BLE001
      execution_time = time.perf_counter() - start
      return QueryResult(
        status=QueryStatus.ERROR,
        response_text='',
        execution_time=execution_time,
        error=str(exc),
      )

  async def _get_auth_headers(self, command: ApiQueryCommand) -> Dict[str, str]:
    """Get authentication headers, handling OAuth2 token exchange if needed."""
    if command.requires_oauth2 and command.auth_config.oauth2_config:
      return self._get_oauth2_headers(command)
    return command.get_headers()

  def _get_oauth2_headers(self, command: ApiQueryCommand) -> Dict[str, str]:
    """Obtain OAuth2 token and return auth headers."""
    if not self._oauth2_provider:
      raise ValueError(
        "OAuth2 authentication requested but no OAuth2TokenProvider configured. "
        "Ensure the application container includes an OAuth2TokenProvider."
      )

    oauth2_config = command.auth_config.oauth2_config
    if not oauth2_config:
      raise ValueError("OAuth2 config is required for OAuth2 authentication")

    # Get cached token if available
    cache_key = f"{oauth2_config.token_url}:{oauth2_config.client_id}"
    current_token = self._oauth2_tokens.get(cache_key)

    # Get valid token (handles refresh/obtain automatically)
    token = self._oauth2_provider.get_valid_token(oauth2_config, current_token)
    
    # Cache the token
    self._oauth2_tokens[cache_key] = token

    # Merge OAuth2 headers with any extra headers
    headers = token.as_header()
    if command.extra_headers:
      headers.update(command.extra_headers)
    
    return headers

  @staticmethod
  def _normalize_data(results: object) -> list:
    if not isinstance(results, list):
      return []
    normalized = []
    for item in results:
      if isinstance(item, Mapping):
        normalized.append(dict(item))
    return normalized

  @staticmethod
  def _extract_endpoint_paths(endpoints: list) -> list:
    """Extract just path and method from endpoints for metadata."""
    paths = []
    for ep in endpoints:
      if isinstance(ep, dict):
        paths.append(f"{ep.get('method', 'GET')} {ep.get('path', '')}")
    return paths
