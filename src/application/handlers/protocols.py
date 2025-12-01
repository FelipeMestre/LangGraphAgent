"""Protocols shared across application handlers."""
from __future__ import annotations

from typing import Protocol, runtime_checkable, Any, Mapping


@runtime_checkable
class AgentRunner(Protocol):
  """Represents a LangGraph agent runner that can be awaited."""

  async def run(self, state: Mapping[str, Any]) -> Mapping[str, Any]:
    ...
