"""Value objects for OAuth2 authentication."""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Dict, List, Optional


class OAuth2GrantType(str, Enum):
  """Supported OAuth2 grant types."""
  CLIENT_CREDENTIALS = 'client_credentials'
  PASSWORD = 'password'
  AUTHORIZATION_CODE = 'authorization_code'
  REFRESH_TOKEN = 'refresh_token'


@dataclass(frozen=True)
class OAuth2Config:
  """Configuration for OAuth2 authentication.
  
  This is interface-agnostic and can be populated from CLI, API, or web UI.
  """
  token_url: str
  grant_type: OAuth2GrantType = OAuth2GrantType.CLIENT_CREDENTIALS
  client_id: Optional[str] = None
  client_secret: Optional[str] = None
  username: Optional[str] = None
  password: Optional[str] = None
  scopes: List[str] = field(default_factory=list)
  audience: Optional[str] = None
  extra_params: Dict[str, str] = field(default_factory=dict)

  def __post_init__(self) -> None:
    if not self.token_url:
      raise ValueError('token_url is required for OAuth2')
    
    if self.grant_type == OAuth2GrantType.CLIENT_CREDENTIALS:
      if not self.client_id or not self.client_secret:
        raise ValueError('client_id and client_secret are required for client_credentials grant')
    
    elif self.grant_type == OAuth2GrantType.PASSWORD:
      if not self.username or not self.password:
        raise ValueError('username and password are required for password grant')

  def to_token_request_data(self) -> Dict[str, str]:
    """Build the token request payload."""
    data: Dict[str, str] = {'grant_type': self.grant_type.value}

    if self.client_id:
      data['client_id'] = self.client_id
    if self.client_secret:
      data['client_secret'] = self.client_secret
    if self.username:
      data['username'] = self.username
    if self.password:
      data['password'] = self.password
    if self.scopes:
      data['scope'] = ' '.join(self.scopes)
    if self.audience:
      data['audience'] = self.audience
    
    data.update(self.extra_params)
    return data


@dataclass
class OAuth2Token:
  """Represents an OAuth2 access token with optional refresh capability."""
  access_token: str
  token_type: str = 'Bearer'
  expires_in: Optional[int] = None
  refresh_token: Optional[str] = None
  scope: Optional[str] = None
  obtained_at: datetime = field(default_factory=datetime.utcnow)

  @property
  def is_expired(self) -> bool:
    """Check if the token has expired."""
    if self.expires_in is None:
      return False
    expiry = self.obtained_at + timedelta(seconds=self.expires_in)
    # Add 30 second buffer to avoid edge cases
    return datetime.utcnow() >= (expiry - timedelta(seconds=30))

  @property
  def expires_at(self) -> Optional[datetime]:
    """Return the expiration datetime if known."""
    if self.expires_in is None:
      return None
    return self.obtained_at + timedelta(seconds=self.expires_in)

  def as_header(self) -> Dict[str, str]:
    """Return the Authorization header for this token."""
    return {'Authorization': f'{self.token_type} {self.access_token}'}

  @staticmethod
  def from_response(response_data: Dict) -> 'OAuth2Token':
    """Create an OAuth2Token from a token endpoint response."""
    return OAuth2Token(
      access_token=response_data['access_token'],
      token_type=response_data.get('token_type', 'Bearer'),
      expires_in=response_data.get('expires_in'),
      refresh_token=response_data.get('refresh_token'),
      scope=response_data.get('scope'),
    )

