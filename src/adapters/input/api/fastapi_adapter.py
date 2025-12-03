"""FastAPI adapter exposing HTTP endpoints."""
from __future__ import annotations

from enum import Enum
from typing import Optional

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

from src.application.commands.api_query_command import ApiQueryCommand, AuthConfig, AuthType
from src.application.commands.database_query_command import DatabaseQueryCommand
from src.ports.input.query_service import QueryService
from src.ports.input.result_presenter import ResultPresenter


class DatabaseQueryPayload(BaseModel):
  database_url: str = Field(..., description='SQLAlchemy connection URL')
  query: str = Field(..., description='Natural language query')
  max_tables: int = Field(default=10, ge=1, le=20, description='Maximum tables to analyze')


class AuthTypeEnum(str, Enum):
  none = 'none'
  bearer = 'bearer'
  api_key = 'api_key'
  basic = 'basic'


class AuthPayload(BaseModel):
  auth_type: AuthTypeEnum = Field(default=AuthTypeEnum.none, description='Authentication type')
  token: Optional[str] = Field(default=None, description='Bearer token (for bearer auth)')
  api_key: Optional[str] = Field(default=None, description='API key value')
  api_key_header: str = Field(default='X-API-Key', description='Header name for API key')
  username: Optional[str] = Field(default=None, description='Username (for basic auth)')
  password: Optional[str] = Field(default=None, description='Password (for basic auth)')


class ApiQueryPayload(BaseModel):
  swagger_url: str = Field(..., description='URL to Swagger UI or OpenAPI spec JSON')
  query: str = Field(..., description='Natural language query')
  auth: Optional[AuthPayload] = Field(default=None, description='Authentication configuration')
  max_endpoints: int = Field(default=5, ge=1, le=20, description='Maximum endpoints to query')


class FastAPIAdapter:
  def __init__(self, query_service: QueryService, presenter: ResultPresenter):
    self._query_service = query_service
    self._presenter = presenter
    self.app = FastAPI(
      title='LangGraph Agent API',
      version='0.1.0',
      description='API para consultas en lenguaje natural a bases de datos y APIs REST',
    )
    self._configure_routes()

  def _configure_routes(self) -> None:
    @self.app.post('/api/v1/database/query', tags=['Database'])
    async def query_database(payload: DatabaseQueryPayload):
      """Execute a natural language query against a database."""
      command = DatabaseQueryCommand(
        database_url=payload.database_url,
        user_query=payload.query,
        max_tables=payload.max_tables,
      )
      try:
        result = await self._query_service.execute_database_query(command)
        return self._presenter.present(result)
      except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=500, detail=str(exc))

    @self.app.post('/api/v1/api/query', tags=['API'])
    async def query_api(payload: ApiQueryPayload):
      """
      Query an API using its Swagger/OpenAPI spec.

      The agent will:
      1. Discover endpoints from the Swagger spec
      2. Select relevant endpoints based on your query
      3. Execute GET requests to those endpoints
      4. Analyze the responses and provide an answer
      """
      auth_config = self._build_auth_config(payload.auth)
      command = ApiQueryCommand(
        swagger_url=payload.swagger_url,
        user_query=payload.query,
        auth_config=auth_config,
        max_endpoints=payload.max_endpoints,
      )
      try:
        result = await self._query_service.execute_api_query(command)
        return self._presenter.present(result)
      except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=500, detail=str(exc))

    @self.app.get('/health', tags=['Health'])
    async def health():
      """Health check endpoint."""
      return {'status': 'healthy'}

  @staticmethod
  def _build_auth_config(auth: Optional[AuthPayload]) -> AuthConfig:
    """Convert API payload auth to AuthConfig."""
    if not auth or auth.auth_type == AuthTypeEnum.none:
      return AuthConfig(auth_type=AuthType.NONE)

    if auth.auth_type == AuthTypeEnum.bearer:
      return AuthConfig(auth_type=AuthType.BEARER, token=auth.token)

    if auth.auth_type == AuthTypeEnum.api_key:
      return AuthConfig(
        auth_type=AuthType.API_KEY,
        api_key=auth.api_key,
        api_key_header=auth.api_key_header,
      )

    if auth.auth_type == AuthTypeEnum.basic:
      return AuthConfig(
        auth_type=AuthType.BASIC,
        username=auth.username,
        password=auth.password,
      )

    return AuthConfig(auth_type=AuthType.NONE)
