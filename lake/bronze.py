from __future__ import annotations

import json
import hashlib
from datetime import datetime, timezone
from typing import Any

import duckdb


def ensure_bronze(con: duckdb.DuckDBPyConnection) -> None:
    con.execute("""
    CREATE TABLE IF NOT EXISTS bronze_raw (
        raw_id TEXT PRIMARY KEY,
        source TEXT,
        fetched_at TEXT,
        url TEXT,
        payload_json TEXT
    );
    """)


def _sha256_hex(s: str) -> str:
    return hashlib.sha256((s or "").encode("utf-8")).hexdigest()


def ingest_bronze(db_path: str, source: str, url: str, payload: Any) -> None:
    con = duckdb.connect(db_path)
    ensure_bronze(con)

    fetched_at = datetime.now(timezone.utc).isoformat()
    raw_id = _sha256_hex(f"{source}|{url}|{fetched_at}")

    con.execute(
        """
        INSERT INTO bronze_raw (raw_id, source, fetched_at, url, payload_json)
        VALUES (?, ?, ?, ?, ?)
        """,
        [raw_id, source or "", fetched_at, url or "", json.dumps(payload, ensure_ascii=False)],
    )

    con.close()