"""CLI entrypoint for LangGraphAgent."""
from __future__ import annotations

import sys
from pathlib import Path

# Add project root to Python path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.adapters.input.cli.cli_adapter import CLIAdapter
from src.adapters.presentation.text_presenter import TextPresenter
from src.common.container import create_query_service


def main() -> None:
  query_service = create_query_service()
  presenter = TextPresenter()
  CLIAdapter(query_service, presenter).run()


if __name__ == '__main__':
  main()
