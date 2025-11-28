"""Output port for API interactions."""
from __future__ import annotations

from typing import Any, Dict, List, Optional, Protocol


class ApiRepository(Protocol):
  def discover_endpoints_from_swagger(
    self, swagger_url: str, headers: Optional[Dict[str, str]] = None
  ) -> List[Dict[str, Any]]:
    """Discover endpoints by parsing a Swagger/OpenAPI specification."""
    ...

  def execute_request(self, request: Dict[str, Any]) -> Dict[str, Any]:
    """Execute an HTTP request and return the response."""
    ...
