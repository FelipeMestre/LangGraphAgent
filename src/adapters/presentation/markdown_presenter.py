"""Markdown presenter for report-style outputs."""
from __future__ import annotations

from typing import Any

from src.application.queries.query_result import QueryResult
from src.ports.input.result_presenter import ResultPresenter


class MarkdownPresenter(ResultPresenter):
  def present(self, result: QueryResult) -> str:
    lines = [
      '# Reporte de Consulta',
      '',
      f'**Estado:** {result.status.value}',
      f'**Tiempo de ejecución:** {result.execution_time:.2f}s',
      '',
      '## Respuesta',
      result.response_text or '(sin respuesta)',
      '',
    ]

    if result.analysis:
      lines.extend(['## Análisis', result.analysis, ''])

    if result.data:
      lines.append('## Datos')
      for entry in result.data:
        source = entry.get('source', 'desconocido')
        lines.append(f'### Fuente: {source}')
        preview = entry.get('records', [])[:5]
        if preview:
          lines.append('| Clave | Valor |')
          lines.append('| --- | --- |')
          for row in preview:
            for key, value in row.items():
              lines.append(f'| {key} | {value} |')
          lines.append('')
    if result.metadata:
      lines.append('## Metadata')
      for key, value in result.metadata.items():
        lines.append(f'- **{key}**: {value}')

    if result.error:
      lines.extend(['', f'**Error:** {result.error}'])

    return '\n'.join(lines)

  def present_error(self, error: Exception) -> str:
    return f'# Error\n\n{error}'
