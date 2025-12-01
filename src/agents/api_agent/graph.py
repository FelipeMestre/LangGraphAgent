"""API agent runner based on LangGraph."""
from __future__ import annotations

from typing import Mapping

from langgraph.graph import END, StateGraph

from src.agents.api_agent.nodes import ApiAgentActions
from src.agents.api_agent.state import ApiAgentState
from src.application.handlers.protocols import AgentRunner
from src.domain.services.data_analyzer import DataAnalyzer
from src.ports.output.api_repository import ApiRepository


class ApiAgentRunner(AgentRunner):
  def __init__(self, repository: ApiRepository, data_analyzer: DataAnalyzer, llm) -> None:
    self._actions = ApiAgentActions(repository=repository, data_analyzer=data_analyzer, llm=llm)
    self._graph = self._build_graph()

  def _build_graph(self):
    workflow = StateGraph(ApiAgentState)
    workflow.add_node('discover', self._actions.discover)
    workflow.add_node('select', self._actions.select_endpoints)
    workflow.add_node('fetch', self._actions.fetch_data)
    workflow.add_node('analyze', self._actions.analyze)
    workflow.add_node('finalize', self._actions.finalize)

    workflow.set_entry_point('discover')
    workflow.add_edge('discover', 'select')
    workflow.add_edge('select', 'fetch')
    workflow.add_edge('fetch', 'analyze')
    workflow.add_edge('analyze', 'finalize')
    workflow.add_edge('finalize', END)
    return workflow.compile()

  async def run(self, state: Mapping[str, object]) -> Mapping[str, object]:
    return await self._graph.ainvoke(state)
