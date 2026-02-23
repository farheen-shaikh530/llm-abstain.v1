from __future__ import annotations

import json
import re
import hashlib
from typing import Any, Dict, List, Optional, Set

import duckdb


def sha1(s: str) -> str:
    return hashlib.sha1((s or "").encode("utf-8")).hexdigest()


def ensure_silver(con: duckdb.DuckDBPyConnection) -> None:
    con.execute("""
    CREATE TABLE IF NOT EXISTS silver_sentences (
        sent_id TEXT PRIMARY KEY,
        source TEXT,
        url TEXT,
        published_at TEXT,
        sentence TEXT,
        versions_json TEXT,
        vendors_json TEXT,
        has_version_kw INTEGER
    );
    """)


def normalize_payload(payload_json: str) -> List[Dict[str, Any]]:
    try:
        obj = json.loads(payload_json)
    except Exception:
        return []

    if isinstance(obj, dict) and isinstance(obj.get("data"), list):
        return [x for x in obj["data"] if isinstance(x, dict)]
    if isinstance(obj, list):
        return [x for x in obj if isinstance(x, dict)]
    if isinstance(obj, dict):
        return [obj]
    return []


_VERSION_RE = re.compile(r"\b\d+\.\d+(?:\.\d+)?(?:\.\d+)?(?:[-+][a-z0-9.]+)?\b", re.IGNORECASE)


def extract_versions(text: str) -> List[str]:
    if not text:
        return []
    vs = _VERSION_RE.findall(text)
    out: List[str] = []
    seen = set()
    for v in vs:
        vv = v.strip()
        if vv and vv not in seen:
            out.append(vv)
            seen.add(vv)
    return out


def tokenize_words(text: str) -> List[str]:
    return re.findall(r"[a-z0-9]+", (text or "").lower())


def detect_vendors_by_ngrams(text: str, allowed: Set[str], max_n: int = 4) -> List[str]:
    toks = tokenize_words(text)
    if not toks:
        return []
    found: List[str] = []
    found_set = set()

    for n in range(max_n, 0, -1):
        for i in range(len(toks) - n + 1):
            phrase = " ".join(toks[i : i + n])
            if phrase in allowed and phrase not in found_set:
                found.append(phrase)
                found_set.add(phrase)
    return found


def split_sentences(text: str, max_sentences: int = 200) -> List[str]:
    if not text:
        return []
    parts = re.split(r"(?<=[.!?])\s+", text.strip())
    parts = [p.strip() for p in parts if p.strip()]
    return parts[:max_sentences]


def build_silver_layer_if_needed(db_path: str, allowed_vendors: Optional[Set[str]] = None) -> None:
    """
    Build silver_sentences from bronze_raw.
    Avoid rebuild if already has rows.
    """
    con = duckdb.connect(db_path)
    ensure_silver(con)

    count = con.execute("SELECT COUNT(*) FROM silver_sentences").fetchone()[0]
    if count and int(count) > 0:
        con.close()
        return

    # bronze may already exist
    con.execute("""
    CREATE TABLE IF NOT EXISTS bronze_raw (
        raw_id TEXT PRIMARY KEY,
        source TEXT,
        fetched_at TEXT,
        url TEXT,
        payload_json TEXT
    );
    """)

    rows = con.execute(
        "SELECT source, url, fetched_at, payload_json FROM bronze_raw ORDER BY fetched_at DESC"
    ).fetchall()

    allowed = allowed_vendors or set()

    for source, url, fetched_at, payload_json in rows:
        items = normalize_payload(payload_json)
        for it in items:
            title = str(it.get("title") or it.get("versionProductName") or "")
            notes = str(it.get("notes") or it.get("versionReleaseNotes") or it.get("body") or "")
            sentence_blob = f"{title}. {notes}".strip()

            published_at = str(it.get("updatedAt") or it.get("createdAt") or it.get("created_utc") or fetched_at or "")

            for sent in split_sentences(sentence_blob, max_sentences=200):
                versions = extract_versions(sent)
                vendors = detect_vendors_by_ngrams(sent, allowed) if allowed else []
                has_version_kw = 1 if ("version" in sent.lower() or "release" in sent.lower()) else 0
                sent_id = sha1(f"{source}|{url}|{published_at}|{sent}")

                con.execute(
                    """
                    INSERT INTO silver_sentences
                    (sent_id, source, url, published_at, sentence, versions_json, vendors_json, has_version_kw)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    ON CONFLICT(sent_id) DO NOTHING
                    """,
                    [
                        sent_id,
                        source or "",
                        url or "",
                        published_at or "",
                        sent,
                        json.dumps(versions, ensure_ascii=False),
                        json.dumps(vendors, ensure_ascii=False),
                        int(has_version_kw),
                    ],
                )

    con.close()


def query_silver_sentences(db_path: str, vendor: Optional[str], intent: str, limit: int = 20) -> List[Dict[str, Any]]:
    con = duckdb.connect(db_path, read_only=True)

    intent_u = (intent or "OTHER").upper()
    vendor_lc = (vendor or "").lower().strip()

    where = []
    params: List[Any] = []

    if vendor_lc:
        where.append("lower(vendors_json) LIKE ?")
        params.append(f"%{vendor_lc}%")

    if intent_u == "VERSION":
        where.append("has_version_kw = 1")
        where.append("versions_json IS NOT NULL AND versions_json != '[]'")
    elif intent_u in {"PATCH", "CVE"}:
        where.append("has_version_kw = 1")

    where_sql = "WHERE " + " AND ".join(where) if where else ""

    q = f"""
        SELECT source, url, published_at, sentence, versions_json, vendors_json
        FROM silver_sentences
        {where_sql}
        ORDER BY published_at DESC
        LIMIT ?
    """
    params.append(int(limit))

    rows = con.execute(q, params).fetchall()
    con.close()

    out: List[Dict[str, Any]] = []
    for source, url, published_at, sentence, versions_json, vendors_json in rows:
        out.append(
            {
                "source": source,
                "url": url,
                "published_at": published_at,
                "sentence": sentence,
                "versions_json": versions_json,
                "vendors_json": vendors_json,
                "vendor": vendor_lc or None,
            }
        )
    return out