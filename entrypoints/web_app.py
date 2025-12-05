"""Streamlit entrypoint."""
from __future__ import annotations

import sys
from pathlib import Path

# Add project root to Python path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.adapters.input.web.streamlit_adapter import StreamlitAdapter
from src.adapters.presentation.markdown_presenter import MarkdownPresenter
from src.common.container import create_query_service


def main() -> None:
  query_service = create_query_service()
  presenter = MarkdownPresenter()
  StreamlitAdapter(query_service, presenter).render()


if __name__ == '__main__':
  main()
