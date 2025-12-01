"""Database agent graph builder."""
from __future__ import annotations

from typing import Mapping

from langgraph.graph import END, StateGraph

from src.agents.database_agent.state import DatabaseAgentState
from src.application.handlers.protocols import AgentRunner
from src.domain.services.data_analyzer import DataAnalyzer
from src.domain.services.schema_analyzer import SchemaAnalyzer
from src.ports.output.database_repository import DatabaseRepository
from src.agents.database_agent.nodes import DatabaseAgentActions


class DatabaseAgentRunner(AgentRunner):
  def __init__(
    self,
    repository: DatabaseRepository,
    schema_analyzer: SchemaAnalyzer,
    data_analyzer: DataAnalyzer,
    planner_llm,
  ) -> None:
    self._actions = DatabaseAgentActions(
      repository=repository,
      schema_analyzer=schema_analyzer,
      data_analyzer=data_analyzer,
      llm=planner_llm,
    )
    self._graph = self._build_graph()

  def _build_graph(self):
    workflow = StateGraph(DatabaseAgentState)

    workflow.add_node('load_schema', self._actions.load_schema)
    workflow.add_node('select_tables', self._actions.select_tables)
    workflow.add_node('plan_queries', self._actions.plan_queries)
    workflow.add_node('execute_queries', self._actions.execute_queries)
    workflow.add_node('analyze', self._actions.analyze)
    workflow.add_node('finalize', self._actions.finalize)

    workflow.set_entry_point('load_schema')
    workflow.add_edge('load_schema', 'select_tables')
    workflow.add_edge('select_tables', 'plan_queries')
    workflow.add_edge('plan_queries', 'execute_queries')
    workflow.add_edge('execute_queries', 'analyze')
    workflow.add_edge('analyze', 'finalize')
    workflow.add_edge('finalize', END)

    return workflow.compile()

  async def run(self, state: Mapping[str, object]) -> Mapping[str, object]:
    return await self._graph.ainvoke(state)
