"""Application handler that orchestrates database queries."""
from __future__ import annotations

import time
from typing import Mapping

from src.application.commands.database_query_command import DatabaseQueryCommand
from src.application.handlers.protocols import AgentRunner
from src.application.queries.query_result import QueryResult, QueryStatus


class DatabaseQueryHandler:
  """Coordinates the execution of database queries via the agent runner."""

  def __init__(self, agent_runner: AgentRunner):
    self._agent_runner = agent_runner

  async def handle(self, command: DatabaseQueryCommand) -> QueryResult:
    start = time.perf_counter()
    try:
      agent_response: Mapping[str, object] = await self._agent_runner.run({
        'database_url': command.database_url,
        'user_query': command.user_query,
        'max_tables': command.max_tables,
        'query_timeout': command.query_timeout,
      })

      execution_time = time.perf_counter() - start
      error = agent_response.get('error')
      status = QueryStatus.ERROR if error else QueryStatus.SUCCESS

      return QueryResult(
        status=status,
        response_text=str(agent_response.get('final_response', '')),
        analysis=str(agent_response.get('analysis', '')) if agent_response.get('analysis') else None,
        data=self._normalize_data(agent_response.get('query_results')),
        metadata={
          'tables_analyzed': agent_response.get('selected_tables', []),
          'step': agent_response.get('step'),
          'schema_summary': agent_response.get('schema_summary'),
        },
        execution_time=execution_time,
        error=str(error) if error else None,
      )
    except Exception as exc:  # noqa: BLE001
      execution_time = time.perf_counter() - start
      return QueryResult(
        status=QueryStatus.ERROR,
        response_text='',
        execution_time=execution_time,
        error=str(exc),
      )

  @staticmethod
  def _normalize_data(results: object) -> list:
    if not isinstance(results, list):
      return []
    normalized = []
    for item in results:
      if isinstance(item, Mapping):
        normalized.append(dict(item))
    return normalized
