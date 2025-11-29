"""Application-level configuration utilities."""
from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import Optional

from dotenv import load_dotenv


@dataclass(frozen=True)
class Settings:
  """Immutable application settings loaded from environment variables."""

  openai_api_key: str
  database_url: Optional[str] = None
  api_base_url: Optional[str] = None
  api_key: Optional[str] = None


@lru_cache(maxsize=1)
def get_settings() -> Settings:
  """Load settings from environment variables once per process."""
  env_path = Path(__file__).resolve().parents[2] / '.env'
  if env_path.exists():
    load_dotenv(env_path)
  else:
    load_dotenv()

  from os import getenv

  openai_api_key = getenv('OPENAI_API_KEY')
  if not openai_api_key:
    raise ValueError('OPENAI_API_KEY must be set in environment or .env file')

  return Settings(
    openai_api_key=openai_api_key,
    database_url=getenv('DATABASE_URL'),
    api_base_url=getenv('API_BASE_URL'),
    api_key=getenv('API_KEY'),
  )
