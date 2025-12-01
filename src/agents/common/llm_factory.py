"""Helpers to initialize LLM clients used by agents."""
from __future__ import annotations

from langchain_openai import ChatOpenAI

from src.common.config import get_settings


def build_default_llm(temperature: float = 0.0) -> ChatOpenAI:
  settings = get_settings()
  return ChatOpenAI(
    model='gpt-4',
    temperature=temperature,
    api_key=settings.openai_api_key,
  )
