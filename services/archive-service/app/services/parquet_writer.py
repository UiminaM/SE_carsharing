"""Serialize buffered records to Apache Parquet bytes using pyarrow."""

from __future__ import annotations

import io
from typing import Any

import pyarrow as pa
import pyarrow.parquet as pq

def records_to_parquet_bytes(records: list[dict[str, Any]]) -> bytes:
    """Convert a list of dicts into a Parquet-serialized byte blob.

    Uses Snappy compression by default. Schema is inferred from the records:
    pyarrow promotes types automatically, so heterogeneous keys are tolerated
    as long as the value types per column are consistent.
    """
    if not records:
        return b""

    table = pa.Table.from_pylist(records)
    buf = io.BytesIO()
    pq.write_table(table, buf, compression="snappy")
    return buf.getvalue()

def parquet_bytes_to_records(blob: bytes) -> list[dict[str, Any]]:
    """Inverse operation — decode a Parquet blob into a list of dicts."""
    if not blob:
        return []
    buf = io.BytesIO(blob)
    table = pq.read_table(buf)
    return table.to_pylist()
