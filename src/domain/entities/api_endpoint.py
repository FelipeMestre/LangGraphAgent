"""Domain entities for API crawling and execution."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Optional


@dataclass(frozen=True)
class ApiParameter:
  """Represents an API parameter."""

  name: str
  required: bool
  param_in: str  # query, path, header, body
  schema: Optional[str] = None
  description: Optional[str] = None


@dataclass(frozen=True)
class ApiEndpoint:
  """Represents a discovered API endpoint."""

  path: str
  method: str
  description: Optional[str]
  requires_auth: bool
  parameters: Dict[str, ApiParameter]
  response_schema: Optional[Dict]

  def identifier(self) -> str:
    return f'{self.method.upper()} {self.path}'
