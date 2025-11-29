"""Command object representing an API query request."""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, Optional


class AuthType(str, Enum):
  """Supported authentication types."""
  NONE = 'none'
  BEARER = 'bearer'
  API_KEY = 'api_key'
  BASIC = 'basic'


@dataclass(frozen=True)
class AuthConfig:
  """Authentication configuration."""
  auth_type: AuthType = AuthType.NONE
  token: Optional[str] = None
  api_key: Optional[str] = None
  api_key_header: str = 'X-API-Key'
  username: Optional[str] = None
  password: Optional[str] = None

  def to_headers(self) -> Dict[str, str]:
    """Convert auth config to HTTP headers."""
    headers: Dict[str, str] = {}

    if self.auth_type == AuthType.BEARER and self.token:
      headers['Authorization'] = f'Bearer {self.token}'
    elif self.auth_type == AuthType.API_KEY and self.api_key:
      headers[self.api_key_header] = self.api_key
    elif self.auth_type == AuthType.BASIC and self.username and self.password:
      import base64
      credentials = base64.b64encode(f'{self.username}:{self.password}'.encode()).decode()
      headers['Authorization'] = f'Basic {credentials}'

    return headers


@dataclass(frozen=True)
class ApiQueryCommand:
  """Command for querying an API with natural language."""
  swagger_url: str
  user_query: str
  auth_config: AuthConfig = field(default_factory=AuthConfig)
  max_endpoints: int = 5
  extra_headers: Optional[Dict[str, str]] = None

  def __post_init__(self) -> None:
    if not self.swagger_url:
      raise ValueError('swagger_url is required')
    if not self.user_query:
      raise ValueError('user_query is required')
    if not 1 <= self.max_endpoints <= 20:
      raise ValueError('max_endpoints must be between 1 and 20')

  def get_headers(self) -> Dict[str, str]:
    """Get combined headers from auth and extra headers."""
    headers = self.auth_config.to_headers()
    if self.extra_headers:
      headers.update(self.extra_headers)
    return headers
