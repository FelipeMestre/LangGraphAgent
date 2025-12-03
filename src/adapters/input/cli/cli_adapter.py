"""CLI adapter for interacting with the query service."""
from __future__ import annotations

import asyncio
from typing import Optional

import click

from src.application.commands.api_query_command import ApiQueryCommand, AuthConfig, AuthType
from src.application.commands.database_query_command import DatabaseQueryCommand
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
    @click.option('--auth-type', type=click.Choice(['none', 'bearer', 'api_key', 'basic']), default='none')
    @click.option('--token', default=None, help='Bearer token (for bearer auth)')
    @click.option('--api-key', default=None, help='API key value')
    @click.option('--api-key-header', default='X-API-Key', help='Header name for API key')
    @click.option('--username', default=None, help='Username (for basic auth)')
    @click.option('--password', default=None, help='Password (for basic auth)')
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
    ) -> None:
      """Query an API using its Swagger/OpenAPI spec."""
      auth_config = _build_auth_config(auth_type, token, api_key, api_key_header, username, password)
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
) -> AuthConfig:
  """Build AuthConfig from CLI options."""
  if auth_type == 'bearer':
    return AuthConfig(auth_type=AuthType.BEARER, token=token)
  elif auth_type == 'api_key':
    return AuthConfig(auth_type=AuthType.API_KEY, api_key=api_key, api_key_header=api_key_header)
  elif auth_type == 'basic':
    return AuthConfig(auth_type=AuthType.BASIC, username=username, password=password)
  return AuthConfig(auth_type=AuthType.NONE)
