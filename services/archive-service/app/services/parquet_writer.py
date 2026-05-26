
from __future__ import annotations

import io
from typing import Any

import pyarrow as pa
import pyarrow.parquet as pq

def records_to_parquet_bytes(records: list[dict[str, Any]]) -> bytes:
    if not records:
        return b""

    table = pa.Table.from_pylist(records)
    buf = io.BytesIO()
    pq.write_table(table, buf, compression="snappy")
    return buf.getvalue()

def parquet_bytes_to_records(blob: bytes) -> list[dict[str, Any]]:
    if not blob:
        return []
    buf = io.BytesIO(blob)
    table = pq.read_table(buf)
    return table.to_pylist()
