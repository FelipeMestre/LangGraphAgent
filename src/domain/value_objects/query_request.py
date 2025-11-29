"""Value object for user queries in natural language."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Optional


@dataclass(frozen=True)
class QueryRequest:
  """Represents a natural language query with optional context."""

  content: str
  locale: str = 'es'
  max_items: Optional[int] = 10
  context: Optional[str] = None

  def __post_init__(self) -> None:
    if not self.content:
      raise ValueError('Query content is required')
    if self.max_items is not None and self.max_items <= 0:
      raise ValueError('max_items must be positive when provided')
