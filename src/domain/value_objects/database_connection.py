"""Value object for database connection metadata."""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Optional

from sqlalchemy.engine import make_url


class DatabaseType(str, Enum):
  POSTGRESQL = 'postgresql'
  MYSQL = 'mysql'
  SQLITE = 'sqlite'
  SQLSERVER = 'mssql'
  OTHER = 'other'


@dataclass(frozen=True)
class DatabaseConnection:
  """Immutable representation of a database connection string."""

  url: str
  db_type: DatabaseType
  host: Optional[str]
  port: Optional[int]
  database: Optional[str]
  username: Optional[str] = None
  password: Optional[str] = None

  @staticmethod
  def from_url(url: str) -> 'DatabaseConnection':
    if not url:
      raise ValueError('Database URL is required')

    parsed = make_url(url)
    dialect_name = parsed.get_backend_name()

    db_type = DatabaseType(dialect_name) if dialect_name in DatabaseType._value2member_map_ else DatabaseType.OTHER

    return DatabaseConnection(
      url=url,
      db_type=db_type,
      host=parsed.host,
      port=parsed.port,
      database=parsed.database,
      username=parsed.username,
      password=parsed.password,
    )
