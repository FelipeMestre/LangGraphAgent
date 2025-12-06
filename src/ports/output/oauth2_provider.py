"""Output port for OAuth2 token management."""
from __future__ import annotations

from typing import Optional, Protocol

from src.domain.value_objects.oauth2_credentials import OAuth2Config, OAuth2Token


class OAuth2TokenProvider(Protocol):
  """Interface for obtaining and refreshing OAuth2 tokens.
  
  This port abstracts the OAuth2 token exchange mechanism,
  allowing different implementations (requests, httpx, etc.)
  while keeping the core application agnostic.
  """

  def obtain_token(self, config: OAuth2Config) -> OAuth2Token:
    """Exchange credentials for an access token.
    
    Args:
      config: OAuth2 configuration with credentials and token URL
      
    Returns:
      OAuth2Token with access token and optional refresh token
      
    Raises:
      OAuth2Error: If token exchange fails
    """
    ...

  def refresh_token(
    self, config: OAuth2Config, current_token: OAuth2Token
  ) -> OAuth2Token:
    """Refresh an expired token using the refresh token.
    
    Args:
      config: OAuth2 configuration with token URL
      current_token: Token containing the refresh_token
      
    Returns:
      New OAuth2Token with fresh access token
      
    Raises:
      OAuth2Error: If refresh fails or no refresh token available
    """
    ...

  def get_valid_token(
    self, config: OAuth2Config, current_token: Optional[OAuth2Token] = None
  ) -> OAuth2Token:
    """Get a valid token, refreshing if necessary.
    
    This is the main method to use - it handles the logic of checking
    if the current token is valid, refreshing if needed, or obtaining
    a new token if no current token exists.
    
    Args:
      config: OAuth2 configuration
      current_token: Optional existing token to check/refresh
      
    Returns:
      Valid OAuth2Token ready for use
    """
    ...


class OAuth2Error(Exception):
  """Base exception for OAuth2-related errors."""
  
  def __init__(self, message: str, error_code: Optional[str] = None):
    super().__init__(message)
    self.error_code = error_code

