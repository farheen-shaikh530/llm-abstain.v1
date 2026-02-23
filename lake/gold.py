from __future__ import annotations

import json
import re
from typing import Any, Dict, Optional, Tuple, List

import duckdb


def semver_key(v: str) -> Tuple[int, ...]:
    parts = re.split(r"[^\d]+", (v or "").strip())
    nums: List[int] = []
    for p in parts:
        if p.isdigit():
            nums.append(int(p))
    return tuple(nums) if nums else (0,)


def ensure_gold_tables(con: duckdb.DuckDBPyConnection) -> None:
    con.execute("""
    CREATE TABLE IF NOT EXISTS gold_latest_version (
        vendor TEXT PRIMARY KEY,
        latest_version TEXT,
        fact_date TEXT,
        source TEXT,
        url TEXT,
        snippet TEXT
    );
    """)
    con.execute("""
    CREATE TABLE IF NOT EXISTS gold_release_facts (
        fact_id TEXT PRIMARY KEY,
        vendor TEXT,
        intent TEXT,
        fact_date TEXT,
        source TEXT,
        url TEXT,
        snippet TEXT,
        fact_json TEXT
    );
    """)


def build_gold_layer_if_needed(db_path: str) -> None:
    """
    Build gold_latest_version from silver_sentences.
    Avoid rebuild if gold already has rows.
    """
    con = duckdb.connect(db_path)
    ensure_gold_tables(con)

    exists = con.execute("""
        SELECT COUNT(*)
        FROM information_schema.tables
        WHERE table_name='silver_sentences'
    """).fetchone()[0]
    if int(exists) == 0:
        con.close()
        return

    n = con.execute("SELECT COUNT(*) FROM gold_latest_version").fetchone()[0]
    if n and int(n) > 0:
        con.close()
        return

    rows = con.execute("""
        SELECT published_at, source, url, sentence, versions_json, vendors_json
        FROM silver_sentences
        WHERE versions_json IS NOT NULL AND versions_json != '[]'
          AND vendors_json IS NOT NULL AND vendors_json != '[]'
          AND has_version_kw = 1
        ORDER BY published_at DESC
    """).fetchall()

    best: Dict[str, Tuple[Tuple[str, Tuple[int, ...]], str, str, str, str]] = {}
    # best[vendor] = ((fact_date, semver_key), version, source, url, snippet)

    for fact_date, source, url, sentence, versions_json, vendors_json in rows:
        try:
            vendors = json.loads(vendors_json or "[]")
            versions = json.loads(versions_json or "[]")
        except Exception:
            continue
        if not isinstance(vendors, list) or not isinstance(versions, list):
            continue

        for v in vendors:
            if not isinstance(v, str) or not v.strip():
                continue
            vendor = v.strip().lower()

            for ver in versions:
                if not isinstance(ver, str) or not ver.strip():
                    continue
                ver_s = ver.strip()

                key = (str(fact_date or ""), semver_key(ver_s))
                if vendor not in best or key > best[vendor][0]:
                    best[vendor] = (key, ver_s, str(source or ""), str(url or ""), str(sentence or "")[:260])

    con.execute("DELETE FROM gold_latest_version")
    for vendor, pack in best.items():
        key, ver_s, source, url, snippet = pack
        fact_date = key[0]
        con.execute(
            """
            INSERT INTO gold_latest_version (vendor, latest_version, fact_date, source, url, snippet)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            [vendor, ver_s, fact_date, source, url, snippet],
        )

    con.close()


def query_gold_latest_version(db_path: str, vendor: str) -> Optional[Dict[str, Any]]:
    con = duckdb.connect(db_path, read_only=True)
    row = con.execute(
        """
        SELECT vendor, latest_version, fact_date, source, url, snippet
        FROM gold_latest_version
        WHERE lower(vendor) = lower(?)
        LIMIT 1
        """,
        [vendor],
    ).fetchone()
    con.close()

    if not row:
        return None

    v, latest_version, fact_date, source, url, snippet = row
    return {
        "vendor": v,
        "latest_version": latest_version,
        "fact_date": fact_date,
        "source": source,
        "url": url,
        "snippet": snippet,
    }


def query_gold_release_facts(db_path: str, vendor: str, intent: str) -> Optional[Dict[str, Any]]:
    con = duckdb.connect(db_path, read_only=True)
    row = con.execute(
        """
        SELECT vendor, intent, fact_date, source, url, snippet, fact_json
        FROM gold_release_facts
        WHERE lower(vendor) = lower(?)
          AND upper(intent) = upper(?)
        ORDER BY fact_date DESC
        LIMIT 1
        """,
        [vendor, intent],
    ).fetchone()
    con.close()

    if not row:
        return None

    v, i, fact_date, source, url, snippet, fact_json = row
    try:
        fact = json.loads(fact_json) if fact_json else None
    except Exception:
        fact = None

    return {
        "vendor": v,
        "intent": i,
        "fact_date": fact_date,
        "source": source,
        "url": url,
        "snippet": snippet,
        "fact": fact,
    }