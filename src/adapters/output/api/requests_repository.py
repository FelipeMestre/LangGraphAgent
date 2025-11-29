"""Requests-based API repository implementation."""
from __future__ import annotations

import re
from typing import Any, Dict, List, Optional
from urllib.parse import urljoin, urlparse

import requests

from src.ports.output.api_repository import ApiRepository


class RequestsApiRepository(ApiRepository):
  """Performs HTTP calls using the requests library."""

  def discover_endpoints_from_swagger(
    self, swagger_url: str, headers: Optional[Dict[str, str]] = None
  ) -> List[Dict[str, Any]]:
    """
    Discover endpoints by parsing a Swagger/OpenAPI specification.

    Supports:
    - Direct JSON spec URL (e.g., /swagger.json, /openapi.json, /v3/api-docs)
    - HTML Swagger UI page (extracts spec URL automatically)
    """
    spec = self._fetch_swagger_spec(swagger_url, headers)
    return self._parse_openapi_spec(spec, swagger_url)

  def _fetch_swagger_spec(
    self, swagger_url: str, headers: Optional[Dict[str, str]] = None
  ) -> Dict[str, Any]:
    """Fetch the OpenAPI/Swagger spec, handling HTML pages if needed."""
    response = requests.get(swagger_url, headers=headers or {}, timeout=30)
    response.raise_for_status()

    content_type = response.headers.get('Content-Type', '')

    # If JSON, parse directly
    if 'application/json' in content_type:
      return response.json()

    # Try parsing as JSON anyway (some servers don't set content-type correctly)
    try:
      return response.json()
    except ValueError:
      pass

    # If HTML, try to extract the spec URL from Swagger UI
    if 'text/html' in content_type or response.text.strip().startswith('<!'):
      spec_url = self._extract_spec_url_from_html(response.text, swagger_url)
      if spec_url:
        spec_response = requests.get(spec_url, headers=headers or {}, timeout=30)
        spec_response.raise_for_status()
        return spec_response.json()

    # Try common spec paths as fallback
    return self._try_common_spec_paths(swagger_url, headers)

  def _extract_spec_url_from_html(self, html: str, base_url: str) -> Optional[str]:
    """Extract OpenAPI spec URL from Swagger UI HTML page."""
    patterns = [
      r'url\s*[=:]\s*["\']([^"\']+\.json)["\']',
      r'url\s*[=:]\s*["\']([^"\']+/api-docs[^"\']*)["\']',
      r'url\s*[=:]\s*["\']([^"\']+openapi[^"\']*)["\']',
      r'url\s*[=:]\s*["\']([^"\']+swagger[^"\']*)["\']',
      r'spec-url\s*=\s*["\']([^"\']+)["\']',
      r'configUrl\s*[=:]\s*["\']([^"\']+)["\']',
    ]

    for pattern in patterns:
      match = re.search(pattern, html, re.IGNORECASE)
      if match:
        spec_path = match.group(1)
        return urljoin(base_url, spec_path)

    return None

  def _try_common_spec_paths(
    self, base_url: str, headers: Optional[Dict[str, str]] = None
  ) -> Dict[str, Any]:
    """Try common OpenAPI spec paths."""
    parsed = urlparse(base_url)
    base = f'{parsed.scheme}://{parsed.netloc}'

    common_paths = [
      '/swagger.json',
      '/openapi.json',
      '/v3/api-docs',
      '/v2/api-docs',
      '/api-docs',
      '/swagger/v1/swagger.json',
      '/api/swagger.json',
    ]

    for path in common_paths:
      try:
        url = urljoin(base, path)
        response = requests.get(url, headers=headers or {}, timeout=10)
        if response.status_code == 200:
          return response.json()
      except (requests.RequestException, ValueError):
        continue

    raise ValueError(
      f'No se pudo encontrar el spec OpenAPI/Swagger en {base_url}. '
      'Intenta proporcionar la URL directa al archivo .json del spec.'
    )

  def _parse_openapi_spec(self, spec: Dict[str, Any], base_url: str) -> List[Dict[str, Any]]:
    """Parse OpenAPI 2.0 (Swagger) or 3.x spec into endpoint list."""
    endpoints: List[Dict[str, Any]] = []

    # Determine base URL from spec
    api_base = self._get_api_base_url(spec, base_url)

    # Get security schemes for reference
    security_schemes = self._extract_security_schemes(spec)

    paths = spec.get('paths', {})
    for path, methods in paths.items():
      if not isinstance(methods, dict):
        continue

      for method, details in methods.items():
        if method.lower() in ('get', 'post', 'put', 'patch', 'delete', 'head', 'options'):
          endpoint = self._parse_endpoint(
            path=path,
            method=method.upper(),
            details=details if isinstance(details, dict) else {},
            api_base=api_base,
            security_schemes=security_schemes,
          )
          endpoints.append(endpoint)

    return endpoints

  def _get_api_base_url(self, spec: Dict[str, Any], fallback_url: str) -> str:
    """Extract base URL from OpenAPI spec."""
    # OpenAPI 3.x
    servers = spec.get('servers', [])
    if servers and isinstance(servers[0], dict):
      return servers[0].get('url', fallback_url)

    # Swagger 2.0
    host = spec.get('host')
    if host:
      scheme = (spec.get('schemes') or ['https'])[0]
      base_path = spec.get('basePath', '')
      return f'{scheme}://{host}{base_path}'

    # Fallback: use the URL we fetched from
    parsed = urlparse(fallback_url)
    return f'{parsed.scheme}://{parsed.netloc}'

  def _extract_security_schemes(self, spec: Dict[str, Any]) -> Dict[str, Any]:
    """Extract security schemes from spec."""
    # OpenAPI 3.x
    components = spec.get('components', {})
    if 'securitySchemes' in components:
      return components['securitySchemes']

    # Swagger 2.0
    return spec.get('securityDefinitions', {})

  def _parse_endpoint(
    self,
    path: str,
    method: str,
    details: Dict[str, Any],
    api_base: str,
    security_schemes: Dict[str, Any],
  ) -> Dict[str, Any]:
    """Parse a single endpoint from the spec."""
    # Build full URL
    full_url = urljoin(api_base.rstrip('/') + '/', path.lstrip('/'))

    # Extract parameters
    parameters = self._extract_parameters(details.get('parameters', []))

    # Extract request body schema (OpenAPI 3.x)
    request_body = details.get('requestBody', {})
    body_schema = None
    if request_body:
      content = request_body.get('content', {})
      json_content = content.get('application/json', {})
      body_schema = json_content.get('schema')

    # Determine if auth is required
    security = details.get('security', [])
    requires_auth = bool(security) or bool(security_schemes)

    return {
      'path': path,
      'url': full_url,
      'method': method,
      'summary': details.get('summary', ''),
      'description': details.get('description', ''),
      'operation_id': details.get('operationId', ''),
      'tags': details.get('tags', []),
      'parameters': parameters,
      'request_body_schema': body_schema,
      'requires_auth': requires_auth,
      'security': security,
      'responses': list(details.get('responses', {}).keys()),
    }

  def _extract_parameters(self, params: List[Dict[str, Any]]) -> Dict[str, List[Dict[str, Any]]]:
    """Group parameters by location (query, path, header, cookie)."""
    grouped: Dict[str, List[Dict[str, Any]]] = {
      'path': [],
      'query': [],
      'header': [],
      'cookie': [],
    }

    for param in params:
      if not isinstance(param, dict):
        continue
      location = param.get('in', 'query')
      if location in grouped:
        grouped[location].append({
          'name': param.get('name'),
          'required': param.get('required', False),
          'type': param.get('schema', {}).get('type') if 'schema' in param else param.get('type'),
          'description': param.get('description', ''),
        })

    return grouped

  def execute_request(self, request: Dict[str, Any]) -> Dict[str, Any]:
    """Execute an HTTP request and return the response."""
    method = request.get('method', 'GET').upper()
    url = request['url']
    headers = request.get('headers') or {}
    params = request.get('params') or {}
    json_payload = request.get('json')
    path_params = request.get('path_params') or {}

    # Substitute path parameters in URL
    for key, value in path_params.items():
      url = url.replace(f'{{{key}}}', str(value))

    try:
      response = requests.request(
        method, url, headers=headers, params=params, json=json_payload, timeout=30
      )
      response.raise_for_status()
    except requests.HTTPError as e:
      return {
        'status_code': e.response.status_code if e.response else 500,
        'error': str(e),
        'data': None,
      }
    except requests.RequestException as e:
      return {
        'status_code': 0,
        'error': str(e),
        'data': None,
      }

    try:
      data = response.json()
    except ValueError:
      data = {'raw_text': response.text}

    return {
      'status_code': response.status_code,
      'headers': dict(response.headers),
      'data': data,
    }
