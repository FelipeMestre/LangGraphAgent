"""FastAPI adapter exposing HTTP endpoints."""
from __future__ import annotations

from enum import Enum
from typing import List, Optional

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field, field_validator

from src.application.commands.api_query_command import ApiQueryCommand, AuthConfig, AuthType
from src.application.commands.database_query_command import DatabaseQueryCommand
from src.domain.value_objects.oauth2_credentials import OAuth2Config, OAuth2GrantType
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
  oauth2 = 'oauth2'


class OAuth2GrantTypeEnum(str, Enum):
  client_credentials = 'client_credentials'
  password = 'password'


class OAuth2Payload(BaseModel):
  """OAuth2 configuration for API authentication."""
  token_url: str = Field(..., description='OAuth2 token endpoint URL')
  grant_type: OAuth2GrantTypeEnum = Field(
    default=OAuth2GrantTypeEnum.client_credentials,
    description='OAuth2 grant type'
  )
  client_id: Optional[str] = Field(default=None, description='OAuth2 client ID')
  client_secret: Optional[str] = Field(default=None, description='OAuth2 client secret')
  username: Optional[str] = Field(default=None, description='Username (for password grant)')
  password: Optional[str] = Field(default=None, description='Password (for password grant)')
  scopes: List[str] = Field(default_factory=list, description='OAuth2 scopes')
  audience: Optional[str] = Field(default=None, description='OAuth2 audience (optional)')


class AuthPayload(BaseModel):
  """Authentication configuration supporting multiple methods including OAuth2."""
  auth_type: AuthTypeEnum = Field(default=AuthTypeEnum.none, description='Authentication type')
  # Static auth options
  token: Optional[str] = Field(default=None, description='Bearer token (for bearer auth)')
  api_key: Optional[str] = Field(default=None, description='API key value')
  api_key_header: str = Field(default='X-API-Key', description='Header name for API key')
  username: Optional[str] = Field(default=None, description='Username (for basic auth)')
  password: Optional[str] = Field(default=None, description='Password (for basic auth)')
  # OAuth2 options
  oauth2: Optional[OAuth2Payload] = Field(default=None, description='OAuth2 configuration')

  @field_validator('oauth2')
  @classmethod
  def validate_oauth2(cls, v, info):
    """Validate OAuth2 config is provided when auth_type is oauth2."""
    if info.data.get('auth_type') == AuthTypeEnum.oauth2 and v is None:
      raise ValueError('oauth2 configuration is required when auth_type is oauth2')
    return v


class ApiQueryPayload(BaseModel):
  """Payload for API queries with support for various authentication methods."""
  swagger_url: str = Field(..., description='URL to Swagger UI or OpenAPI spec JSON')
  query: str = Field(..., description='Natural language query')
  auth: Optional[AuthPayload] = Field(default=None, description='Authentication configuration')
  max_endpoints: int = Field(default=5, ge=1, le=20, description='Maximum endpoints to query')

  model_config = {
    'json_schema_extra': {
      'examples': [
        {
          'swagger_url': 'https://api.example.com/swagger.json',
          'query': 'List all available products',
          'auth': {
            'auth_type': 'oauth2',
            'oauth2': {
              'token_url': 'https://auth.example.com/oauth/token',
              'grant_type': 'client_credentials',
              'client_id': 'my-app',
              'client_secret': 'secret123',
              'scopes': ['read:products']
            }
          },
          'max_endpoints': 5
        }
      ]
    }
  }


class FastAPIAdapter:
  def __init__(self, query_service: QueryService, presenter: ResultPresenter):
    self._query_service = query_service
    self._presenter = presenter
    self.app = FastAPI(
      title='LangGraph Agent API',
      version='0.1.0',
      description='API para consultas en lenguaje natural a bases de datos y APIs REST. '
                  'Soporta autenticación OAuth2 para integración con APIs protegidas.',
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

      Supports multiple authentication methods:
      - **none**: No authentication
      - **bearer**: Static bearer token
      - **api_key**: API key in header
      - **basic**: Basic HTTP authentication
      - **oauth2**: OAuth2 with automatic token management (client_credentials or password grant)

      The agent will:
      1. Authenticate using the provided credentials (handles OAuth2 token exchange automatically)
      2. Discover endpoints from the Swagger spec
      3. Select relevant endpoints based on your query
      4. Execute GET requests to those endpoints
      5. Analyze the responses and provide an answer
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

    if auth.auth_type == AuthTypeEnum.oauth2 and auth.oauth2:
      oauth2_config = OAuth2Config(
        token_url=auth.oauth2.token_url,
        grant_type=OAuth2GrantType(auth.oauth2.grant_type.value),
        client_id=auth.oauth2.client_id,
        client_secret=auth.oauth2.client_secret,
        username=auth.oauth2.username,
        password=auth.oauth2.password,
        scopes=auth.oauth2.scopes,
        audience=auth.oauth2.audience,
      )
      return AuthConfig(auth_type=AuthType.OAUTH2, oauth2_config=oauth2_config)

    return AuthConfig(auth_type=AuthType.NONE)
