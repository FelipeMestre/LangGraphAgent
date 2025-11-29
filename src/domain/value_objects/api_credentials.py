"""Value objects for API authentication."""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Dict, Optional


class AuthType(str, Enum):
  NONE = 'none'
  API_KEY = 'api_key'
  BEARER = 'bearer'
  BASIC = 'basic'
  OAUTH2 = 'oauth2'


@dataclass(frozen=True)
class ApiCredentials:
  """Represents API authentication credentials."""

  auth_type: AuthType
  token: Optional[str] = None
  username: Optional[str] = None
  password: Optional[str] = None
  headers: Optional[Dict[str, str]] = None

  def as_headers(self) -> Dict[str, str]:
    """Return HTTP headers representing the credentials."""
    headers: Dict[str, str] = {}
    if self.headers:
      headers.update(self.headers)

    if self.auth_type == AuthType.API_KEY and self.token:
      headers['X-API-KEY'] = self.token
    elif self.auth_type == AuthType.BEARER and self.token:
      headers['Authorization'] = f'Bearer {self.token}'
    elif self.auth_type == AuthType.BASIC and self.username and self.password:
      import base64
      creds = f'{self.username}:{self.password}'.encode('utf-8')
      headers['Authorization'] = f'Basic {base64.b64encode(creds).decode("utf-8")}'

    return headers
