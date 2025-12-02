"""Application handler for API queries."""
from __future__ import annotations

import time
from typing import Mapping

from src.application.commands.api_query_command import ApiQueryCommand
from src.application.handlers.protocols import AgentRunner
from src.application.queries.query_result import QueryResult, QueryStatus


class ApiQueryHandler:
  """Coordinates API queries executed by the LangGraph API agent."""

  def __init__(self, agent_runner: AgentRunner):
    self._agent_runner = agent_runner

  async def handle(self, command: ApiQueryCommand) -> QueryResult:
    start = time.perf_counter()
    try:
      agent_response: Mapping[str, object] = await self._agent_runner.run({
        'swagger_url': command.swagger_url,
        'user_query': command.user_query,
        'auth_headers': command.get_headers(),
        'max_endpoints': command.max_endpoints,
      })

      execution_time = time.perf_counter() - start
      error = agent_response.get('error')
      status = QueryStatus.ERROR if error else QueryStatus.SUCCESS

      return QueryResult(
        status=status,
        response_text=str(agent_response.get('final_response', '')),
        analysis=str(agent_response.get('analysis', '')) if agent_response.get('analysis') else None,
        data=self._normalize_data(agent_response.get('api_data')),
        metadata={
          'endpoints_discovered': agent_response.get('total_endpoints', 0),
          'endpoints_used': self._extract_endpoint_paths(agent_response.get('selected_endpoints', [])),
          'step': agent_response.get('step'),
        },
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
