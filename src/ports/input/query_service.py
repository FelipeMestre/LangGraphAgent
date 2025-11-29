"""Input port defining the query service contract."""
from __future__ import annotations

from typing import Protocol

from src.application.commands.api_query_command import ApiQueryCommand
from src.application.commands.database_query_command import DatabaseQueryCommand
from src.application.queries.query_result import QueryResult


class QueryService(Protocol):
  async def execute_database_query(self, command: DatabaseQueryCommand) -> QueryResult:
    ...

  async def execute_api_query(self, command: ApiQueryCommand) -> QueryResult:
    ...
