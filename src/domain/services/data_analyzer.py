"""Domain service to generate analysis instructions for LLMs."""
from __future__ import annotations

from typing import Iterable, Mapping


class DataAnalyzer:
  """Provides utilities to craft analysis prompts for structured data."""

  @staticmethod
  def build_analysis_prompt(user_query: str, data_samples: Iterable[Mapping]) -> str:
    """Create a prompt that summarizes the data for an LLM."""
    lines = [
      'Analiza los siguientes datos para responder la pregunta del usuario.',
      f'Pregunta del usuario: {user_query}',
      '',
      'Datos disponibles:',
    ]

    for sample in data_samples:
      source = sample.get('source', 'desconocido')
      records = sample.get('records') or sample.get('data') or sample.get('response')
      if isinstance(records, dict):
        records = [records]
      records = records or []
      lines.append(f'- Fuente: {source} (total filas: {len(records)})')
      preview = records[:3]
      if preview:
        lines.append('  Ejemplos:')
        for row in preview:
          lines.append(f'    • {row}')
      lines.append('')

    lines.append('Proporciona un resumen claro, insights y respuestas concretas.')
    return '\n'.join(lines)
