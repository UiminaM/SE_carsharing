
from __future__ import annotations

import io
import json
from typing import Any

import pyarrow.parquet as pq

def parquet_find_trip(blob: bytes, trip_id: str) -> dict[str, Any] | None:
    if not blob:
        return None
    table = pq.read_table(io.BytesIO(blob))
    records = table.to_pylist()
    for row in records:
        raw = row.get("data")
        if not isinstance(raw, str):
            continue
        try:
            payload = json.loads(raw)
        except Exception:
            continue
        if payload.get("trip_id") == trip_id or row.get("subject") == trip_id:
            row["data"] = payload
            return row
    return None
