"""Domain entities representing database schema metadata."""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import List, Optional


@dataclass(frozen=True)
class TableColumn:
  """Represents a database column definition."""

  name: str
  data_type: str
  nullable: bool
  is_primary_key: bool = False
  is_foreign_key: bool = False
  referenced_table: Optional[str] = None
  referenced_column: Optional[str] = None

  def as_dict(self) -> dict:
    """Serialize the column to a dictionary for downstream use."""
    return {
      'name': self.name,
      'data_type': self.data_type,
      'nullable': self.nullable,
      'is_primary_key': self.is_primary_key,
      'is_foreign_key': self.is_foreign_key,
      'referenced_table': self.referenced_table,
      'referenced_column': self.referenced_column,
    }


@dataclass(frozen=True)
class DatabaseTable:
  """Represents a database table and its metadata."""

  name: str
  columns: List[TableColumn]
  row_count: Optional[int] = None
  description: Optional[str] = None

  def column_names(self) -> List[str]:
    return [column.name for column in self.columns]

  def primary_keys(self) -> List[str]:
    return [column.name for column in self.columns if column.is_primary_key]

  def foreign_keys(self) -> List[str]:
    return [column.name for column in self.columns if column.is_foreign_key]


@dataclass
class DatabaseSchema:
  """Represents the discovered schema for a database."""

  database_name: str
  tables: List[DatabaseTable] = field(default_factory=list)
  discovered_at: datetime = field(default_factory=datetime.utcnow)

  def get_table(self, name: str) -> Optional[DatabaseTable]:
    """Return a table by name if it exists."""
    return next((table for table in self.tables if table.name == name), None)

  def top_tables(self, limit: int = 10) -> List[DatabaseTable]:
    """Return the top N tables ordered by row count (desc)."""
    sorted_tables = sorted(
      self.tables,
      key=lambda table: table.row_count if table.row_count is not None else 0,
      reverse=True,
    )
    return sorted_tables[:limit]

  def summary(self) -> str:
    """Generate a human-readable summary of the schema."""
    lines: List[str] = ['']
    for table in self.tables:
      lines.append(f'Tabla: {table.name}')
      for column in table.columns:
        column_meta = []
        if column.is_primary_key:
          column_meta.append('PK')
        if column.is_foreign_key:
          column_meta.append(f'FK->{column.referenced_table}.{column.referenced_column}')
        column_desc = f"  - {column.name}: {column.data_type}"
        if column_meta:
          column_desc += f" ({', '.join(column_meta)})"
        column_desc += ' NULLABLE' if column.nullable else ' NOT NULL'
        lines.append(column_desc)
      lines.append('')
    return '\n'.join(lines)
