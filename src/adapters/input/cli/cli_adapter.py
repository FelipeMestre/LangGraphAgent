"""CLI adapter for interacting with the query service."""
from __future__ import annotations

import asyncio
from typing import List, Optional

import click

from src.application.commands.api_query_command import ApiQueryCommand, AuthConfig, AuthType
from src.application.commands.database_query_command import DatabaseQueryCommand
from src.domain.value_objects.oauth2_credentials import OAuth2Config, OAuth2GrantType
from src.ports.input.query_service import QueryService
from src.ports.input.result_presenter import ResultPresenter


class CLIAdapter:
  def __init__(self, query_service: QueryService, presenter: ResultPresenter):
    self._query_service = query_service
    self._presenter = presenter

  def run(self) -> None:
    cli = click.Group()

    @cli.command('database')
    @click.option('--database-url', required=True, help='SQLAlchemy connection URL')
    @click.option('--query', required=True, help='Natural language query')
    @click.option('--max-tables', default=10, type=click.IntRange(1, 20), help='Max tables to analyze')
    def database(database_url: str, query: str, max_tables: int) -> None:
      """Query a database using natural language."""
      command = DatabaseQueryCommand(database_url=database_url, user_query=query, max_tables=max_tables)
      result = asyncio.run(self._query_service.execute_database_query(command))
      click.echo(self._presenter.present(result))

    @cli.command('api')
    @click.option('--swagger-url', required=True, help='URL to Swagger UI or OpenAPI spec')
    @click.option('--query', required=True, help='Natural language query')
    @click.option('--max-endpoints', default=5, type=click.IntRange(1, 20), help='Max endpoints to query')
    @click.option('--auth-type', type=click.Choice(['none', 'bearer', 'api_key', 'basic', 'oauth2']), default='none')
    @click.option('--token', default=None, help='Bearer token (for bearer auth)')
    @click.option('--api-key', default=None, help='API key value')
    @click.option('--api-key-header', default='X-API-Key', help='Header name for API key')
    @click.option('--username', default=None, help='Username (for basic or oauth2 password grant)')
    @click.option('--password', default=None, help='Password (for basic or oauth2 password grant)')
    # OAuth2 specific options
    @click.option('--oauth2-token-url', default=None, help='OAuth2 token endpoint URL')
    @click.option('--oauth2-client-id', default=None, help='OAuth2 client ID')
    @click.option('--oauth2-client-secret', default=None, help='OAuth2 client secret')
    @click.option('--oauth2-grant-type', type=click.Choice(['client_credentials', 'password']), 
                  default='client_credentials', help='OAuth2 grant type')
    @click.option('--oauth2-scopes', default=None, help='OAuth2 scopes (comma-separated)')
    def api(
      swagger_url: str,
      query: str,
      max_endpoints: int,
      auth_type: str,
      token: Optional[str],
      api_key: Optional[str],
      api_key_header: str,
      username: Optional[str],
      password: Optional[str],
      oauth2_token_url: Optional[str],
      oauth2_client_id: Optional[str],
      oauth2_client_secret: Optional[str],
      oauth2_grant_type: str,
      oauth2_scopes: Optional[str],
    ) -> None:
      """Query an API using its Swagger/OpenAPI spec.
      
      Supports multiple authentication methods including OAuth2.
      
      Examples:
      
        # No auth
        cli api --swagger-url https://api.example.com/swagger --query "List users"
        
        # Bearer token
        cli api --swagger-url ... --auth-type bearer --token "eyJ..."
        
        # OAuth2 client credentials
        cli api --swagger-url ... --auth-type oauth2 \\
          --oauth2-token-url https://auth.example.com/token \\
          --oauth2-client-id myapp --oauth2-client-secret secret123
          
        # OAuth2 password grant
        cli api --swagger-url ... --auth-type oauth2 \\
          --oauth2-token-url https://auth.example.com/token \\
          --oauth2-grant-type password \\
          --username user@example.com --password mypassword
      """
      auth_config = _build_auth_config(
        auth_type=auth_type,
        token=token,
        api_key=api_key,
        api_key_header=api_key_header,
        username=username,
        password=password,
        oauth2_token_url=oauth2_token_url,
        oauth2_client_id=oauth2_client_id,
        oauth2_client_secret=oauth2_client_secret,
        oauth2_grant_type=oauth2_grant_type,
        oauth2_scopes=oauth2_scopes,
      )
      command = ApiQueryCommand(
        swagger_url=swagger_url,
        user_query=query,
        auth_config=auth_config,
        max_endpoints=max_endpoints,
      )
      result = asyncio.run(self._query_service.execute_api_query(command))
      click.echo(self._presenter.present(result))

    cli()


def _build_auth_config(
  auth_type: str,
  token: Optional[str],
  api_key: Optional[str],
  api_key_header: str,
  username: Optional[str],
  password: Optional[str],
  oauth2_token_url: Optional[str] = None,
  oauth2_client_id: Optional[str] = None,
  oauth2_client_secret: Optional[str] = None,
  oauth2_grant_type: str = 'client_credentials',
  oauth2_scopes: Optional[str] = None,
) -> AuthConfig:
  """Build AuthConfig from CLI options."""
  if auth_type == 'bearer':
    return AuthConfig(auth_type=AuthType.BEARER, token=token)
  
  elif auth_type == 'api_key':
    return AuthConfig(auth_type=AuthType.API_KEY, api_key=api_key, api_key_header=api_key_header)
  
  elif auth_type == 'basic':
    return AuthConfig(auth_type=AuthType.BASIC, username=username, password=password)
  
  elif auth_type == 'oauth2':
    if not oauth2_token_url:
      raise click.ClickException('--oauth2-token-url is required for OAuth2 authentication')
    
    grant_type = OAuth2GrantType(oauth2_grant_type)
    scopes: List[str] = oauth2_scopes.split(',') if oauth2_scopes else []
    
    oauth2_config = OAuth2Config(
      token_url=oauth2_token_url,
      grant_type=grant_type,
      client_id=oauth2_client_id,
      client_secret=oauth2_client_secret,
      username=username if grant_type == OAuth2GrantType.PASSWORD else None,
      password=password if grant_type == OAuth2GrantType.PASSWORD else None,
      scopes=scopes,
    )
    return AuthConfig(auth_type=AuthType.OAUTH2, oauth2_config=oauth2_config)
  
  return AuthConfig(auth_type=AuthType.NONE)
