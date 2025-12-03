"""Implementation of the query service port."""
from __future__ import annotations

from src.application.commands.api_query_command import ApiQueryCommand
from src.application.commands.database_query_command import DatabaseQueryCommand
from src.application.handlers.api_query_handler import ApiQueryHandler
from src.application.handlers.database_query_handler import DatabaseQueryHandler
from src.application.queries.query_result import QueryResult
from src.ports.input.query_service import QueryService


class QueryServiceImpl(QueryService):
  """Concrete implementation that delegates to the appropriate handler."""

  def __init__(
    self,
    database_handler: DatabaseQueryHandler,
    api_handler: ApiQueryHandler,
  ) -> None:
    self._database_handler = database_handler
    self._api_handler = api_handler

  async def execute_database_query(self, command: DatabaseQueryCommand) -> QueryResult:
    return await self._database_handler.handle(command)

  async def execute_api_query(self, command: ApiQueryCommand) -> QueryResult:
    return await self._api_handler.handle(command)
