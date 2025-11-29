"""Plain text presenter using Rich-like formatting."""
from __future__ import annotations

from typing import Any

from src.application.queries.query_result import QueryResult
from src.ports.input.result_presenter import ResultPresenter


class TextPresenter(ResultPresenter):
  def present(self, result: QueryResult) -> str:
    lines = [
      '=' * 60,
      'RESULTADO',
      '=' * 60,
      result.response_text or '(sin respuesta)',
      '',
    ]

    if result.analysis:
      lines.extend([
        '=' * 60,
        'ANÁLISIS',
        '=' * 60,
        result.analysis,
        '',
      ])

    if result.metadata:
      lines.extend([
        '=' * 60,
        'METADATA',
        '=' * 60,
      ])
      for key, value in result.metadata.items():
        lines.append(f'- {key}: {value}')
      lines.append('')

    lines.append(f'Tiempo de ejecución: {result.execution_time:.2f}s')
    if result.error:
      lines.append(f'ERROR: {result.error}')
    return '\n'.join(lines)

  def present_error(self, error: Exception) -> str:
    return f'ERROR: {error}'
