"""Node implementations for the database agent workflow."""
from __future__ import annotations

from typing import Any, Dict, List

from langchain_core.output_parsers import JsonOutputParser, StrOutputParser
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.runnables import RunnableLambda
from langchain_openai import ChatOpenAI

from src.domain.services.data_analyzer import DataAnalyzer
from src.domain.services.schema_analyzer import SchemaAnalyzer
from src.ports.output.database_repository import DatabaseRepository


class DatabaseAgentActions:
  def __init__(
    self,
    repository: DatabaseRepository,
    schema_analyzer: SchemaAnalyzer,
    data_analyzer: DataAnalyzer,
    llm: ChatOpenAI,
  ) -> None:
    self._repository = repository
    self._schema_analyzer = schema_analyzer
    self._data_analyzer = data_analyzer
    self._llm = llm
    self._planner = self._build_planner()
    self._summarizer = self._build_summarizer()

  def load_schema(self, state: Dict[str, Any]) -> Dict[str, Any]:
    metadata = list(self._repository.describe_schema(state['database_url']))
    schema = self._schema_analyzer.build_schema(database_name=state['database_url'], tables_metadata=metadata)
    state['schema_summary'] = schema.summary()
    state['schema_tables'] = [table.name for table in schema.tables]
    state['step'] = 'schema_loaded'
    return state

  def select_tables(self, state: Dict[str, Any]) -> Dict[str, Any]:
    user_query = state['user_query'].lower()
    available_tables = state.get('schema_tables', [])
    selected = [table for table in available_tables if table.lower() in user_query]
    if not selected:
      selected = available_tables[: state.get('max_tables', 10)]
    state['selected_tables'] = selected[: state.get('max_tables', 10)]
    state['step'] = 'tables_selected'
    return state

  def plan_queries(self, state: Dict[str, Any]) -> Dict[str, Any]:
    if not state.get('selected_tables'):
      state['error'] = 'No se encontraron tablas para consultar'
      return state

    plan = self._planner.invoke({
      'schema_summary': state['schema_summary'],
      'tables': state['selected_tables'],
      'question': state['user_query'],
    })

    planned_queries: List[dict] = plan if isinstance(plan, list) else plan.get('queries', [])
    state['planned_queries'] = planned_queries[: state.get('max_tables', 10)]
    state['step'] = 'queries_planned'
    return state

  def execute_queries(self, state: Dict[str, Any]) -> Dict[str, Any]:
    results: List[dict] = []
    for query in state.get('planned_queries', []):
      sql = query.get('sql')
      if not sql:
        continue
      rows = self._repository.fetch_rows(state['database_url'], sql, limit=500)
      results.append({
        'table': query.get('table'),
        'source': query.get('table'),
        'sql': sql,
        'data': rows,
      })
    state['query_results'] = results
    state['step'] = 'queries_executed'
    return state

  def analyze(self, state: Dict[str, Any]) -> Dict[str, Any]:
    prompt = self._data_analyzer.build_analysis_prompt(state['user_query'], state.get('query_results', []))
    analysis = self._summarizer.invoke({'analysis_prompt': prompt})
    state['analysis'] = analysis
    state['step'] = 'analysis_complete'
    return state

  def finalize(self, state: Dict[str, Any]) -> Dict[str, Any]:
    state['final_response'] = state.get('analysis')
    state['step'] = 'complete'
    return state

  def _build_planner(self) -> RunnableLambda:
    prompt = ChatPromptTemplate.from_messages([
      (
        'system',
        'Eres un asistente experto en SQL. Genera consultas seguras basadas en el esquema.',
      ),
      (
        'human',
        'Esquema disponible:\n{schema_summary}\n\nTablas relevantes: {tables}\n\nPregunta: {question}\n'
        'Devuelve un JSON con una lista "queries" donde cada elemento tiene "table" y "sql".',
      ),
    ])
    parser = JsonOutputParser()
    return prompt | self._llm | parser

  def _build_summarizer(self) -> RunnableLambda:
    prompt = ChatPromptTemplate.from_messages([
      (
        'system',
        'Eres un analista de datos. Resume la información de manera clara.',
      ),
      ('human', '{analysis_prompt}')
    ])
    parser = StrOutputParser()
    return prompt | self._llm | parser
