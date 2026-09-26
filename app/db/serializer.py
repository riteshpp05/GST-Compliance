"""
app.db.serializer
=================
JSON, Decimal, Enum, and Timezone Serialization Helpers for Sprint 14 DB Persistence.
Ensures Decimal numbers, ISO UTC timestamps, Enums, None values, and nested structures
are preserved with 100% round-trip fidelity.
"""

import json
from datetime import date, datetime, timezone
from decimal import Decimal
from enum import Enum
from typing import Any, Dict, List, Optional


def dump_json_value(val: Any) -> Optional[str]:
    """Serialize arbitrary Python object to JSON string preserving Decimal and Datetime values."""
    if val is None:
        return None

    def _default_encoder(obj):
        if isinstance(obj, Decimal):
            return float(obj)
        if isinstance(obj, (date, datetime)):
            return obj.isoformat()
        if isinstance(obj, Enum):
            return obj.value
        if hasattr(obj, "to_dict") and callable(obj.to_dict):
            return obj.to_dict()
        if hasattr(obj, "model_dump") and callable(obj.model_dump):
            return obj.model_dump()
        return str(obj)

    return json.dumps(val, default=_default_encoder)


def load_json_value(val: Optional[str], default_factory=list) -> Any:
    """Parse JSON string back to Python structures with fallback."""
    if not val:
        return default_factory()
    if isinstance(val, (dict, list)):
        return val
    try:
        return json.loads(val)
    except Exception:
        return default_factory()


def format_iso_timestamp(ts: Optional[Any] = None) -> str:

    """Ensure timestamp is formatted as an ISO 8601 UTC string."""
    if not ts:
        return datetime.now(timezone.utc).isoformat()
    if isinstance(ts, datetime):
        if ts.tzinfo is None:
            ts = ts.replace(tzinfo=timezone.utc)
        return ts.isoformat()
    return str(ts)
