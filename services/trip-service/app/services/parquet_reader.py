"""Cold-read helper — locate a single trip inside a Parquet shard."""

from __future__ import annotations

import io
import json
from typing import Any

import pyarrow.parquet as pq

def parquet_find_trip(blob: bytes, trip_id: str) -> dict[str, Any] | None:
    """Scan a Parquet blob emitted by Archive Service and return the record
    whose embedded ``data.trip_id`` matches ``trip_id``.

    The shard layout is produced by
    ``archive-service/app/consumers/archive_consumer.ArchiveConsumer._flatten``:
    each row is a flattened CloudEvent with the original ``data`` dict stored
    as a JSON-encoded string in column ``data``.
    """
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
