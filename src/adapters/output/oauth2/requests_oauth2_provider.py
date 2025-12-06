"""Requests-based OAuth2 token provider implementation."""
from __future__ import annotations

from typing import Optional

import requests

from src.domain.value_objects.oauth2_credentials import (
  OAuth2Config,
  OAuth2GrantType,
  OAuth2Token,
)
from src.ports.output.oauth2_provider import OAuth2Error, OAuth2TokenProvider


class RequestsOAuth2Provider(OAuth2TokenProvider):
  """OAuth2 token provider using the requests library."""

  def __init__(self, timeout: int = 30):
    self._timeout = timeout
    self._token_cache: dict[str, OAuth2Token] = {}

  def obtain_token(self, config: OAuth2Config) -> OAuth2Token:
    """Exchange credentials for an access token."""
    try:
      response = requests.post(
        config.token_url,
        data=config.to_token_request_data(),
        headers={'Content-Type': 'application/x-www-form-urlencoded'},
        timeout=self._timeout,
      )
      response.raise_for_status()
      token_data = response.json()
      
      if 'access_token' not in token_data:
        raise OAuth2Error(
          f"Token response missing access_token: {token_data}",
          error_code=token_data.get('error'),
        )
      
      token = OAuth2Token.from_response(token_data)
      self._cache_token(config, token)
      return token

    except requests.HTTPError as e:
      error_data = {}
      try:
        error_data = e.response.json()
      except (ValueError, AttributeError):
        pass
      
      raise OAuth2Error(
        f"Token request failed: {error_data.get('error_description', str(e))}",
        error_code=error_data.get('error'),
      ) from e

    except requests.RequestException as e:
      raise OAuth2Error(f"Network error during token request: {str(e)}") from e

  def refresh_token(
    self, config: OAuth2Config, current_token: OAuth2Token
  ) -> OAuth2Token:
    """Refresh an expired token using the refresh token."""
    if not current_token.refresh_token:
      raise OAuth2Error("No refresh token available, must re-authenticate")

    refresh_data = {
      'grant_type': OAuth2GrantType.REFRESH_TOKEN.value,
      'refresh_token': current_token.refresh_token,
    }
    
    if config.client_id:
      refresh_data['client_id'] = config.client_id
    if config.client_secret:
      refresh_data['client_secret'] = config.client_secret

    try:
      response = requests.post(
        config.token_url,
        data=refresh_data,
        headers={'Content-Type': 'application/x-www-form-urlencoded'},
        timeout=self._timeout,
      )
      response.raise_for_status()
      token_data = response.json()
      
      # Preserve refresh token if not returned in response
      if 'refresh_token' not in token_data and current_token.refresh_token:
        token_data['refresh_token'] = current_token.refresh_token
      
      token = OAuth2Token.from_response(token_data)
      self._cache_token(config, token)
      return token

    except requests.HTTPError as e:
      error_data = {}
      try:
        error_data = e.response.json()
      except (ValueError, AttributeError):
        pass
      
      raise OAuth2Error(
        f"Token refresh failed: {error_data.get('error_description', str(e))}",
        error_code=error_data.get('error'),
      ) from e

  def get_valid_token(
    self, config: OAuth2Config, current_token: Optional[OAuth2Token] = None
  ) -> OAuth2Token:
    """Get a valid token, refreshing or obtaining new one as needed."""
    # Check cache first
    cache_key = self._get_cache_key(config)
    cached = self._token_cache.get(cache_key)
    
    if cached and not cached.is_expired:
      return cached

    # Use provided token if valid
    if current_token and not current_token.is_expired:
      return current_token

    # Try to refresh if we have a refresh token
    token_to_refresh = current_token or cached
    if token_to_refresh and token_to_refresh.refresh_token:
      try:
        return self.refresh_token(config, token_to_refresh)
      except OAuth2Error:
        # Refresh failed, fall through to obtain new token
        pass

    # Obtain fresh token
    return self.obtain_token(config)

  def _get_cache_key(self, config: OAuth2Config) -> str:
    """Generate a cache key for the token based on config."""
    return f"{config.token_url}:{config.client_id}:{config.username}"

  def _cache_token(self, config: OAuth2Config, token: OAuth2Token) -> None:
    """Store token in cache."""
    self._token_cache[self._get_cache_key(config)] = token

  def clear_cache(self) -> None:
    """Clear all cached tokens."""
    self._token_cache.clear()

