# LangGraphAgent

Agente inteligente construido con LangGraph + LangChain siguiendo Domain Driven Design (DDD) y arquitectura Hexagonal para consultar bases de datos o APIs desde cualquier interfaz (CLI, API REST o frontend web).

## Objetivos automatizados
- **Bases de datos**: Crawling del esquema (máx. 10 tablas relevantes), generación de queries SQL guiadas por LLM, ejecución segura (solo `SELECT`) y análisis de los datos retornados.
- **APIs**: Descubrimiento de endpoints a partir de una URL, detección de autenticación, ejecución de requests autenticados y análisis de las respuestas.
- **Agnóstico de interfaz**: El core de la aplicación expone puertos; las interfaces (CLI, API, Streamlit) solo son adaptadores.

## Arquitectura
- **Dominio** (`src/domain`): Entidades (`DatabaseSchema`, `ApiEndpoint`), Value Objects (`DatabaseConnection`, `ApiCredentials`) y servicios (`SchemaAnalyzer`, `DataAnalyzer`).
- **Aplicación** (`src/application`): Commands, QueryResult y Handlers que orquestan los agentes LangGraph.
- **Puertos** (`src/ports`): Interfaces que desacoplan la capa de aplicación de los adaptadores.
- **Adaptadores** (`src/adapters`):
  - *Output*: `SqlAlchemyDatabaseRepository`, `RequestsApiRepository`.
  - *Input*: CLI (Click), FastAPI y Streamlit.
  - *Presenters*: JSON, texto y Markdown.
- **Agentes LangGraph** (`src/agents`):
  - `DatabaseAgentRunner`: carga esquema → selecciona tablas → planea SQL → ejecuta → analiza.
  - `ApiAgentRunner`: descubre endpoints → selecciona → consume → analiza.
- **Entry points** (`entrypoints`): scripts para CLI, API server y app Streamlit.

## Requisitos
- Python 3.10+
- Cuenta y API Key de OpenAI (`OPENAI_API_KEY`).
- Base de datos SQL accesible (PostgreSQL/MySQL/SQLite/etc.) y/o API HTTP.

## Instalación
```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env  # Completa las variables
```

## Configuración `.env`
```env
OPENAI_API_KEY=sk-xxxx
DATABASE_URL=postgresql://user:password@host:5432/db
API_BASE_URL=https://api.example.com
API_KEY=your_api_key
```

## Ejecución
### CLI
```bash
python entrypoints/cli.py database --database-url "$DATABASE_URL" --query "¿Cuántos usuarios hay?"
python entrypoints/cli.py api --api-url "$API_BASE_URL" --query "Trae los 5 items más recientes"
```

### API REST
```bash
python entrypoints/api_server.py  # Levanta FastAPI en :8000
curl -X POST http://localhost:8000/api/v1/database/query \
  -H 'Content-Type: application/json' \
  -d '{"database_url":"'$DATABASE_URL'","query":"Resumen de ventas"}'
```

### Frontend (Streamlit)
```bash
streamlit run entrypoints/web_app.py
```

## Estructura principal
```
src/
├── domain/
├── application/
├── ports/
├── adapters/
├── agents/
└── common/
entrypoints/
```

## Pruebas
```bash
pytest
```

## Próximos pasos
- Añadir repositorios específicos por tipo de BD/API.
- Integrar autenticación avanzada (OAuth2) y caching.
- Expandir cobertura de tests end-to-end.
