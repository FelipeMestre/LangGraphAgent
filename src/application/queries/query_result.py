"""Application-level query result representation."""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional


class QueryStatus(str, Enum):
  SUCCESS = 'success'
  ERROR = 'error'
  PARTIAL = 'partial'


@dataclass
class QueryResult:
  status: QueryStatus
  response_text: str
  analysis: Optional[str] = None
  data: List[Dict[str, Any]] = field(default_factory=list)
  metadata: Dict[str, Any] = field(default_factory=dict)
  execution_time: float = 0.0
  timestamp: datetime = field(default_factory=datetime.utcnow)
  error: Optional[str] = None
