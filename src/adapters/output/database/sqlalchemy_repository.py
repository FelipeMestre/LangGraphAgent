"""SQLAlchemy-powered database repository implementation."""
from __future__ import annotations

from typing import Iterable, Mapping, Sequence

from sqlalchemy import create_engine, text, inspect
from sqlalchemy.engine import Engine

from src.ports.output.database_repository import DatabaseRepository


class SqlAlchemyDatabaseRepository(DatabaseRepository):
  def __init__(self) -> None:
    self._engines: dict[str, Engine] = {}

  def describe_schema(self, database_url: str) -> Iterable[Mapping]:
    engine = self._get_engine(database_url)
    inspector = inspect(engine)

    for table_name in inspector.get_table_names():
      columns_meta = []
      columns = inspector.get_columns(table_name)
      pk_columns = set(inspector.get_pk_constraint(table_name).get('constrained_columns', []))
      fk_constraints = inspector.get_foreign_keys(table_name)

      fk_map = {}
      for fk in fk_constraints:
        for column in fk.get('constrained_columns', []):
          fk_map[column] = (
            fk.get('referred_table'),
            (fk.get('referred_columns') or [None])[0],
          )

      for column in columns:
        foreign_table, foreign_column = fk_map.get(column['name'], (None, None))
        columns_meta.append({
          'name': column['name'],
          'type': str(column['type']),
          'nullable': column.get('nullable', True),
          'is_primary_key': column['name'] in pk_columns,
          'is_foreign_key': column['name'] in fk_map,
          'referenced_table': foreign_table,
          'referenced_column': foreign_column,
        })

      yield {
        'name': table_name,
        'columns': columns_meta,
        'row_count': self._safe_row_count(engine, table_name),
      }

  def fetch_rows(self, database_url: str, query: str, limit: int = 1000) -> Sequence[Mapping]:
    engine = self._get_engine(database_url)
    sanitized_query = query.strip().upper()
    if not sanitized_query.startswith('SELECT'):
      raise ValueError('Solo se permiten consultas SELECT')

    limited_query = query if 'LIMIT' in sanitized_query else f'{query.rstrip(";")} LIMIT {limit}'

    with engine.connect() as connection:
      result = connection.execute(text(limited_query))
      columns = result.keys()
      rows = result.fetchall()
      return [dict(zip(columns, row)) for row in rows]

  def _get_engine(self, database_url: str) -> Engine:
    if database_url not in self._engines:
      self._engines[database_url] = create_engine(database_url)
    return self._engines[database_url]

  @staticmethod
  def _safe_row_count(engine: Engine, table_name: str) -> int | None:
    try:
      with engine.connect() as connection:
        result = connection.execute(text(f'SELECT COUNT(*) FROM {table_name}'))
        return result.scalar_one()
    except Exception:  # noqa: BLE001
      return None
