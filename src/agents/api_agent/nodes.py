"""Node implementations for API agent."""
from __future__ import annotations

import json
from typing import Any, Dict, List

from langchain_core.output_parsers import JsonOutputParser, StrOutputParser
from langchain_core.prompts import ChatPromptTemplate
from langchain_openai import ChatOpenAI

from src.domain.services.data_analyzer import DataAnalyzer
from src.ports.output.api_repository import ApiRepository


class ApiAgentActions:
  def __init__(self, repository: ApiRepository, data_analyzer: DataAnalyzer, llm: ChatOpenAI) -> None:
    self._repository = repository
    self._data_analyzer = data_analyzer
    self._llm = llm
    self._planner = self._build_planner()
    self._summarizer = self._build_summarizer()

  def discover(self, state: Dict[str, Any]) -> Dict[str, Any]:
    """Discover endpoints from Swagger/OpenAPI spec."""
    try:
      auth_headers = state.get('auth_headers') or {}
      endpoints = self._repository.discover_endpoints_from_swagger(
        swagger_url=state['swagger_url'],
        headers=auth_headers if auth_headers else None,
      )
      state['discovered_endpoints'] = endpoints
      state['total_endpoints'] = len(endpoints)
      state['step'] = 'endpoints_discovered'
    except Exception as e:
      state['error'] = f'Error descubriendo endpoints: {str(e)}'
      state['step'] = 'error'
    return state

  def select_endpoints(self, state: Dict[str, Any]) -> Dict[str, Any]:
    """Use LLM to select relevant endpoints for the user query."""
    if state.get('error'):
      return state

    endpoints = state.get('discovered_endpoints', [])
    if not endpoints:
      state['error'] = 'No se encontraron endpoints en el spec'
      state['step'] = 'error'
      return state

    # Build a summary of endpoints for the LLM
    endpoints_summary = self._build_endpoints_summary(endpoints)

    try:
      plan = self._planner.invoke({
        'endpoints_summary': endpoints_summary,
        'question': state['user_query'],
        'max_endpoints': state.get('max_endpoints', 5),
      })

      # Extract selected endpoint paths/operation_ids
      selected_ids = plan.get('endpoints', []) if isinstance(plan, dict) else []

      # Match selected IDs back to full endpoint objects
      selected_endpoints = self._match_selected_endpoints(selected_ids, endpoints)
      state['selected_endpoints'] = selected_endpoints[: state.get('max_endpoints', 5)]
      state['step'] = 'endpoints_selected'
    except Exception as e:
      state['error'] = f'Error seleccionando endpoints: {str(e)}'
      state['step'] = 'error'

    return state

  def _build_endpoints_summary(self, endpoints: List[dict]) -> str:
    """Build a concise summary of endpoints for the LLM."""
    lines = []
    for ep in endpoints:
      method = ep.get('method', 'GET')
      path = ep.get('path', '')
      summary = ep.get('summary', '') or ep.get('description', '')[:100]
      op_id = ep.get('operation_id', '')
      tags = ', '.join(ep.get('tags', []))

      line = f"- {method} {path}"
      if op_id:
        line += f" (id: {op_id})"
      if summary:
        line += f" - {summary}"
      if tags:
        line += f" [tags: {tags}]"
      lines.append(line)

    return '\n'.join(lines)

  def _match_selected_endpoints(
    self, selected_ids: List[Any], all_endpoints: List[dict]
  ) -> List[dict]:
    """Match selected endpoint identifiers back to full endpoint objects."""
    matched = []

    for selection in selected_ids:
      # Selection can be a string (path or operation_id) or dict with details
      if isinstance(selection, dict):
        path = selection.get('path', '')
        method = selection.get('method', '').upper()
        op_id = selection.get('operation_id', '')
      else:
        path = str(selection)
        method = ''
        op_id = str(selection)

      # Find matching endpoint
      for ep in all_endpoints:
        if ep.get('operation_id') == op_id:
          matched.append(ep)
          break
        if ep.get('path') == path and (not method or ep.get('method') == method):
          matched.append(ep)
          break

    return matched

  def fetch_data(self, state: Dict[str, Any]) -> Dict[str, Any]:
    """Execute HTTP requests to selected endpoints."""
    if state.get('error'):
      return state

    results: List[dict] = []
    auth_headers = state.get('auth_headers') or {}

    for endpoint in state.get('selected_endpoints', []):
      # Only execute GET endpoints automatically (safe operation)
      method = endpoint.get('method', 'GET').upper()
      if method != 'GET':
        results.append({
          'endpoint': endpoint,
          'source': endpoint.get('path'),
          'response': {
            'skipped': True,
            'reason': f'Método {method} omitido por seguridad (solo GET automático)',
          },
        })
        continue

      request_payload = {
        'method': method,
        'url': endpoint.get('url'),
        'params': endpoint.get('default_params'),
        'headers': auth_headers,
      }

      try:
        response = self._repository.execute_request(request_payload)
        results.append({
          'endpoint': endpoint,
          'source': endpoint.get('path'),
          'response': response,
        })
      except Exception as e:
        results.append({
          'endpoint': endpoint,
          'source': endpoint.get('path'),
          'response': {'error': str(e)},
        })

    state['api_data'] = results
    state['step'] = 'data_fetched'
    return state

  def analyze(self, state: Dict[str, Any]) -> Dict[str, Any]:
    """Analyze fetched data using LLM."""
    if state.get('error'):
      return state

    api_data = state.get('api_data', [])
    if not api_data:
      state['analysis'] = 'No se obtuvieron datos de la API.'
      state['step'] = 'analysis_complete'
      return state

    prompt = self._data_analyzer.build_analysis_prompt(state['user_query'], api_data)
    try:
      analysis = self._summarizer.invoke({'analysis_prompt': prompt})
      state['analysis'] = analysis
      state['step'] = 'analysis_complete'
    except Exception as e:
      state['error'] = f'Error analizando datos: {str(e)}'
      state['step'] = 'error'

    return state

  def finalize(self, state: Dict[str, Any]) -> Dict[str, Any]:
    """Prepare final response."""
    if state.get('error'):
      state['final_response'] = None
    else:
      state['final_response'] = state.get('analysis')
    state['step'] = 'complete'
    return state

  def _build_planner(self):
    prompt = ChatPromptTemplate.from_messages([
      (
        'system',
        '''Eres un asistente experto en APIs REST. Tu tarea es seleccionar los endpoints más relevantes 
para responder la pregunta del usuario.

Reglas:
1. Selecciona solo endpoints que sean útiles para la pregunta
2. Prefiere endpoints GET cuando sea posible
3. Considera los tags y descripciones para entender el propósito
4. Devuelve un JSON con la clave "endpoints" conteniendo una lista de objetos con "path" y "method"''',
      ),
      (
        'human',
        '''Endpoints disponibles en la API:
{endpoints_summary}

Pregunta del usuario: {question}

Selecciona hasta {max_endpoints} endpoints relevantes.
Responde SOLO con JSON válido en este formato:
{{"endpoints": [{{"path": "/example", "method": "GET"}}, ...]}}''',
      ),
    ])
    return prompt | self._llm | JsonOutputParser()

  def _build_summarizer(self):
    prompt = ChatPromptTemplate.from_messages([
      (
        'system',
        '''Eres un analista experto que interpreta respuestas de APIs REST.
Tu tarea es analizar los datos obtenidos y responder la pregunta del usuario de forma clara y concisa.
Si hay errores en las respuestas, menciónalos brevemente.''',
      ),
      ('human', '{analysis_prompt}'),
    ])
    return prompt | self._llm | StrOutputParser()
