"""Simple dependency wiring helpers."""
from __future__ import annotations

from functools import lru_cache

from src.adapters.output.api.requests_repository import RequestsApiRepository
from src.adapters.output.database.sqlalchemy_repository import SqlAlchemyDatabaseRepository
from src.agents.api_agent.graph import ApiAgentRunner
from src.agents.common.llm_factory import build_default_llm
from src.agents.database_agent.graph import DatabaseAgentRunner
from src.application.handlers.api_query_handler import ApiQueryHandler
from src.application.handlers.database_query_handler import DatabaseQueryHandler
from src.application.services.query_service_impl import QueryServiceImpl
from src.domain.services.data_analyzer import DataAnalyzer
from src.domain.services.schema_analyzer import SchemaAnalyzer


@lru_cache(maxsize=1)
def create_query_service():
  llm = build_default_llm()
  database_repository = SqlAlchemyDatabaseRepository()
  api_repository = RequestsApiRepository()
  schema_analyzer = SchemaAnalyzer()
  data_analyzer = DataAnalyzer()

  database_runner = DatabaseAgentRunner(
    repository=database_repository,
    schema_analyzer=schema_analyzer,
    data_analyzer=data_analyzer,
    planner_llm=llm,
  )
  api_runner = ApiAgentRunner(
    repository=api_repository,
    data_analyzer=data_analyzer,
    llm=llm,
  )

  database_handler = DatabaseQueryHandler(database_runner)
  api_handler = ApiQueryHandler(api_runner)

  return QueryServiceImpl(database_handler, api_handler)
