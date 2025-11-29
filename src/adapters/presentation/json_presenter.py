"""JSON presenter implementation."""
from __future__ import annotations

import json
from typing import Any

from src.application.queries.query_result import QueryResult
from src.ports.input.result_presenter import ResultPresenter


class JsonPresenter(ResultPresenter):
  def present(self, result: QueryResult) -> str:
    payload = {
      'status': result.status.value,
      'response': result.response_text,
      'analysis': result.analysis,
      'data': result.data,
      'metadata': result.metadata,
      'execution_time': result.execution_time,
      'timestamp': result.timestamp.isoformat(),
      'error': result.error,
    }
    return json.dumps(payload, ensure_ascii=False, indent=2)

  def present_error(self, error: Exception) -> str:
    return json.dumps({'status': 'error', 'error': str(error)}, ensure_ascii=False, indent=2)
