"""Domain service for building database schema representations."""
from __future__ import annotations

from typing import Iterable, List, Mapping, Optional

from src.domain.entities.database_schema import DatabaseSchema, DatabaseTable, TableColumn


class SchemaAnalyzer:
  """Builds domain entities from raw database metadata."""

  def build_schema(
    self,
    database_name: str,
    tables_metadata: Iterable[Mapping],
  ) -> DatabaseSchema:
    tables: List[DatabaseTable] = []

    for table_meta in tables_metadata:
      columns_meta = table_meta.get('columns', [])
      columns: List[TableColumn] = []

      for column_meta in columns_meta:
        column = TableColumn(
          name=column_meta['name'],
          data_type=column_meta['type'],
          nullable=column_meta.get('nullable', True),
          is_primary_key=column_meta.get('is_primary_key', False),
          is_foreign_key=column_meta.get('is_foreign_key', False),
          referenced_table=column_meta.get('referenced_table'),
          referenced_column=column_meta.get('referenced_column'),
        )
        columns.append(column)

      table = DatabaseTable(
        name=table_meta['name'],
        columns=columns,
        row_count=table_meta.get('row_count'),
        description=table_meta.get('description'),
      )
      tables.append(table)

    return DatabaseSchema(database_name=database_name, tables=tables)
