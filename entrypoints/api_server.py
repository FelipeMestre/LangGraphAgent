"""API server entrypoint."""
from __future__ import annotations

import sys
from pathlib import Path

# Add project root to Python path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import uvicorn

from src.adapters.input.api.fastapi_adapter import FastAPIAdapter
from src.adapters.presentation.json_presenter import JsonPresenter
from src.common.container import create_query_service


def get_app():
  query_service = create_query_service()
  presenter = JsonPresenter()
  adapter = FastAPIAdapter(query_service, presenter)
  return adapter.app


def main() -> None:
  uvicorn.run(get_app(), host='0.0.0.0', port=8000)


if __name__ == '__main__':
  main()
