"""State definition for the database LangGraph agent."""
from __future__ import annotations

from typing import List, Optional, TypedDict


class DatabaseAgentState(TypedDict, total=False):
  database_url: str
  user_query: str
  max_tables: int
  query_timeout: Optional[int]

  schema_summary: Optional[str]
  schema_tables: List[str]
  selected_tables: List[str]
  planned_queries: List[dict]
  query_results: List[dict]
  analysis: Optional[str]
  final_response: Optional[str]
  error: Optional[str]
  step: str
