"""Input port for formatting query results."""
from __future__ import annotations

from typing import Any, Protocol

from src.application.queries.query_result import QueryResult


class ResultPresenter(Protocol):
  def present(self, result: QueryResult) -> Any:
    ...

  def present_error(self, error: Exception) -> Any:
    ...
