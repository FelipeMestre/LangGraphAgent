"""Streamlit adapter for interactive exploration."""
from __future__ import annotations

import asyncio
import re
from urllib.parse import quote

import streamlit as st

from src.application.commands.api_query_command import ApiQueryCommand, AuthConfig, AuthType
from src.application.commands.database_query_command import DatabaseQueryCommand
from src.ports.input.query_service import QueryService
from src.ports.input.result_presenter import ResultPresenter


def _encode_database_url(url: str) -> str:
  """URL-encode the password in a database connection string."""
  pattern = r'^([^:]+://[^:]+:)([^@]+)(@.+)$'
  match = re.match(pattern, url)
  if match:
    prefix, password, suffix = match.groups()
    encoded_password = quote(password, safe='')
    return f'{prefix}{encoded_password}{suffix}'
  return url


class StreamlitAdapter:
  def __init__(self, query_service: QueryService, presenter: ResultPresenter):
    self._query_service = query_service
    self._presenter = presenter

  def render(self) -> None:
    st.set_page_config(page_title='LangGraph Agent', layout='wide')
    st.title('🤖 LangGraph Agent')

    tab_db, tab_api = st.tabs(['Base de datos', 'API (Swagger)'])

    with tab_db:
      self._render_database_tab()

    with tab_api:
      self._render_api_tab()

  def _render_database_tab(self) -> None:
    """Render database query tab."""
    st.subheader('Consulta a Base de Datos')

    database_url = st.text_input(
      'Database URL',
      key='db_url',
      placeholder='mysql+pymysql://user:password@host:port/database',
      help='URL de conexión a la base de datos (SQLAlchemy format)',
    )
    user_query = st.text_area(
      'Query en lenguaje natural',
      key='db_query',
      placeholder='Ej: ¿Cuántos usuarios hay registrados?',
    )
    max_tables = st.slider('Máximo de tablas a analizar', 1, 10, 5, key='db_max_tables')

    if st.button('Ejecutar consulta', key='db_submit', type='primary'):
      if not database_url or not user_query:
        st.error('Debes completar la URL y la query')
      else:
        encoded_url = _encode_database_url(database_url)
        command = DatabaseQueryCommand(
          database_url=encoded_url,
          user_query=user_query,
          max_tables=max_tables,
        )
        with st.spinner('Procesando...'):
          result = asyncio.run(self._query_service.execute_database_query(command))
        st.markdown(self._presenter.present(result))

  def _render_api_tab(self) -> None:
    """Render API (Swagger) query tab."""
    st.subheader('Consulta a API via Swagger/OpenAPI')

    st.info(
      '💡 Proporciona la URL del Swagger UI o del archivo JSON del spec '
      '(ej: `/swagger`, `/swagger.json`, `/v3/api-docs`)'
    )

    swagger_url = st.text_input(
      'Swagger URL',
      key='swagger_url',
      placeholder='https://api.example.com/swagger o https://api.example.com/swagger.json',
      help='URL del Swagger UI o del spec JSON/YAML',
    )

    # Authentication section
    with st.expander('🔐 Autenticación (opcional)', expanded=False):
      auth_type = st.selectbox(
        'Tipo de autenticación',
        options=['none', 'bearer', 'api_key', 'basic'],
        format_func=lambda x: {
          'none': 'Sin autenticación',
          'bearer': 'Bearer Token (JWT)',
          'api_key': 'API Key',
          'basic': 'Basic Auth (usuario/contraseña)',
        }.get(x, x),
        key='api_auth_type',
      )

      auth_config = self._build_auth_config(auth_type)

    # Query section
    api_query = st.text_area(
      'Query en lenguaje natural',
      key='api_query',
      placeholder='Ej: ¿Cuántos productos hay disponibles? ¿Cuáles son los usuarios activos?',
      help='El agente seleccionará los endpoints más relevantes para tu pregunta',
    )

    max_endpoints = st.slider(
      'Máximo de endpoints a consultar',
      min_value=1,
      max_value=10,
      value=3,
      key='api_max_endpoints',
      help='Número máximo de endpoints que el agente puede llamar',
    )

    if st.button('Consultar API', key='api_submit', type='primary'):
      if not swagger_url or not api_query:
        st.error('Debes completar la URL del Swagger y la query')
      else:
        command = ApiQueryCommand(
          swagger_url=swagger_url,
          user_query=api_query,
          auth_config=auth_config,
          max_endpoints=max_endpoints,
        )

        with st.spinner('Descubriendo endpoints y ejecutando consultas...'):
          result = asyncio.run(self._query_service.execute_api_query(command))

        st.markdown(self._presenter.present(result))

  def _build_auth_config(self, auth_type: str) -> AuthConfig:
    """Build AuthConfig based on selected auth type."""
    if auth_type == 'bearer':
      token = st.text_input(
        'Bearer Token',
        type='password',
        key='api_bearer_token',
        placeholder='eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...',
      )
      return AuthConfig(auth_type=AuthType.BEARER, token=token if token else None)

    elif auth_type == 'api_key':
      col1, col2 = st.columns(2)
      with col1:
        api_key = st.text_input(
          'API Key',
          type='password',
          key='api_key_value',
        )
      with col2:
        api_key_header = st.text_input(
          'Header name',
          value='X-API-Key',
          key='api_key_header',
          help='Nombre del header donde enviar la API key',
        )
      return AuthConfig(
        auth_type=AuthType.API_KEY,
        api_key=api_key if api_key else None,
        api_key_header=api_key_header,
      )

    elif auth_type == 'basic':
      col1, col2 = st.columns(2)
      with col1:
        username = st.text_input('Usuario', key='api_basic_user')
      with col2:
        password = st.text_input('Contraseña', type='password', key='api_basic_pass')
      return AuthConfig(
        auth_type=AuthType.BASIC,
        username=username if username else None,
        password=password if password else None,
      )

    return AuthConfig(auth_type=AuthType.NONE)
