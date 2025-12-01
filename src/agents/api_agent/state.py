"""State definition for the API LangGraph agent."""
from __future__ import annotations

from typing import Dict, List, Optional, TypedDict


class ApiAgentState(TypedDict, total=False):
  # Input fields
  swagger_url: str
  user_query: str
  auth_headers: Dict[str, str]
  max_endpoints: int

  # Discovery results
  discovered_endpoints: List[dict]
  api_base_url: str
  total_endpoints: int

  # Processing results
  selected_endpoints: List[dict]
  api_data: List[dict]

  # Analysis results
  analysis: Optional[str]
  final_response: Optional[str]

  # Status tracking
  error: Optional[str]
  step: str
