"""Output port for database operations."""
from __future__ import annotations

from typing import Iterable, Mapping, Protocol, Sequence


class DatabaseRepository(Protocol):
  """Defines how the application interacts with a database provider."""

  def describe_schema(self, database_url: str) -> Iterable[Mapping]:
    """Return iterable of table metadata dictionaries."""
    ...

  def fetch_rows(self, database_url: str, query: str, limit: int = 1000) -> Sequence[Mapping]:
    """Execute a read-only query and return rows."""
    ...
