"""Command object representing a database query request."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Optional


@dataclass(frozen=True)
class DatabaseQueryCommand:
  database_url: str
  user_query: str
  max_tables: int = 10
  query_timeout: Optional[int] = None

  def __post_init__(self) -> None:
    if not self.database_url:
      raise ValueError('database_url is required')
    if not self.user_query:
      raise ValueError('user_query is required')
    if not 1 <= self.max_tables <= 10:
      raise ValueError('max_tables must be between 1 and 10')
    if self.query_timeout is not None and self.query_timeout <= 0:
      raise ValueError('query_timeout must be positive when provided')
