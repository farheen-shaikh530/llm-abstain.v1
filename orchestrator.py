# orchestrator.py
from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Set, Tuple

from tools.http_tools import get_json_with_cache, normalize_results
from tools.vendor_cache import load_allowed_vendors_local_first


# -----------------------------
# Output
# -----------------------------
@dataclass
class FinalAnswer:
    short_answer: str
    meta: str
    evidence: List[Dict[str, Any]] = field(default_factory=list)
    abstained: bool = False
    confidence: int = 0
    debug_trace: Optional[Dict[str, Any]] = None


# -----------------------------
# Vendor detection
# -----------------------------
STOP = {
    "latest", "current", "newest", "version", "release", "update",
    "what", "is", "the", "a", "an", "of", "for", "in", "on", "to", "and", "or",
    "please", "tell", "me"
}

def _tokenize(q: str) -> List[str]:
    return re.findall(r"[a-z0-9]+", (q or "").lower())

def infer_vendor_from_allowed_list(query: str, allowed: Set[str], max_n: int = 6) -> Optional[str]:
    toks = [t for t in _tokenize(query) if t and t not in STOP]
    if not toks or not allowed:
        return None

    # longest n-gram first
    for n in range(min(max_n, len(toks)), 0, -1):
        for i in range(len(toks) - n + 1):
            phrase = " ".join(toks[i : i + n])
            if phrase in allowed:
                return phrase
    return None


# -----------------------------
# Local-first vendor load compatibility
# loader may return:
# - set
# - (set, source_string)
# -----------------------------
def _load_vendors(cfg) -> Tuple[Set[str], str]:
    res = load_allowed_vendors_local_first(cfg, ttl_sec=7 * 24 * 3600)

    if isinstance(res, tuple) and len(res) == 2 and isinstance(res[0], set):
        return res[0], str(res[1])

    if isinstance(res, set):
        return res, "local_first_cache"

    return set(), "unknown"


# -----------------------------
# Reddit: strict subreddit match
# -----------------------------
def fetch_reddit_items(cfg) -> List[Dict[str, Any]]:
    rd_url = f"{cfg.reddit_api_base}?limit=100&page=1"
    raw = get_json_with_cache(
        rd_url,
        cache_key="reddit_seed",
        cache_dir=cfg.cache_dir,
        ttl_sec=3600,
        timeout_sec=25,
    )
    items = normalize_results(raw)
    return [it for it in items if isinstance(it, dict)]

def filter_reddit_by_subreddit(items: List[Dict[str, Any]], subreddit: str) -> List[Dict[str, Any]]:
    sub_lc = (subreddit or "").strip().lower()
    out: List[Dict[str, Any]] = []
    for it in items:
        if str(it.get("subreddit", "")).strip().lower() == sub_lc:
            out.append(it)
    return out

def format_reddit_discussions(matches: List[Dict[str, Any]], limit: int = 12) -> str:
    bullets: List[str] = []
    for it in matches[:limit]:
        txt = (it.get("author_description") or "").strip()
        if not txt:
            continue

        txt = re.sub(r"\s*\n\s*", " ", txt)   # newlines -> spaces
        txt = re.sub(r"\s{2,}", " ", txt).strip()
        bullets.append(f"- {txt}")

    return "\n".join(bullets)


# -----------------------------
# OS latest version mode (returns versionId)
# Looks inside reddit feed for objects with versionProductType=OS
# -----------------------------
def extract_date_yyyy_mm_dd(query: str) -> Optional[str]:
    """
    Returns 'YYYY-MM-DD' if found in query, else None.
    Accepts YYYY-MM-DD or YYYY/MM/DD.
    """
    q = (query or "")
    m = re.search(r"\b(20\d{2})[-/](\d{2})[-/](\d{2})\b", q)
    if not m:
        return None
    yyyy, mm, dd = m.group(1), m.group(2), m.group(3)
    return f"{yyyy}-{mm}-{dd}"


def same_day(vobj: Dict[str, Any], day: str) -> bool:
    """
    Match on day string 'YYYY-MM-DD' against:
    - versionTimestampLastUpdate (ISO string)
    - versionReleaseDate (often compact but sometimes ISO-ish)
    """
    if not day:
        return True

    tsu = str(vobj.get("versionTimestampLastUpdate") or "").strip()
    if tsu.startswith(day):
        return True

    # Some feeds store release date in different formats.
    # If versionReleaseDate contains the day substring, accept.
    rd = str(vobj.get("versionReleaseDate") or "").strip()
    if day in rd:
        return True

    return False


def answer_latest_os_version(cfg, query: str, debug: bool = False) -> Optional[FinalAnswer]:
    query_lc = (query or "").lower()

    # Trigger on "latest" + (version OR release OR build)
    has_latest = "latest" in query_lc
    has_release_word = any(w in query_lc for w in ("version", "release", "build"))
    if not (has_latest and has_release_word):
        return None

    # OS name detection
    os_name = None
    for name in ["android", "ios", "windows", "macos", "linux"]:
        if name in query_lc:
            os_name = name
            break
    if not os_name:
        return None

    day = extract_date_yyyy_mm_dd(query)  # e.g. "2026-02-04" or None

    trace: Dict[str, Any] = {"mode": "os_latest", "os_name": os_name, "day": day}
    candidates: List[Dict[str, Any]] = []

    def looks_like_version_obj(d: Dict[str, Any]) -> bool:
        return any(k in d for k in ("versionProductType", "versionProductName", "versionNumber", "versionId"))

    def add_candidates(items: List[Dict[str, Any]], source: str):
        for it in items:
            if not isinstance(it, dict):
                continue

            # inline
            if looks_like_version_obj(it):
                if (
                    str(it.get("versionProductType", "")).lower() == "os"
                    and str(it.get("versionProductName", "")).lower() == os_name
                    and same_day(it, day)  # ✅ date match
                ):
                    x = dict(it)
                    x["_source"] = source
                    candidates.append(x)

            # nested versionList
            vl = it.get("versionList")
            if isinstance(vl, list):
                for v in vl:
                    if not isinstance(v, dict):
                        continue
                    if looks_like_version_obj(v):
                        if (
                            str(v.get("versionProductType", "")).lower() == "os"
                            and str(v.get("versionProductName", "")).lower() == os_name
                            and same_day(v, day)  # ✅ date match
                        ):
                            x = dict(v)
                            x["_source"] = source
                            candidates.append(x)

    # Fetch Reddit feed
    try:
        rd_url = f"{cfg.reddit_api_base}?limit=100&page=1"
        rd_raw = get_json_with_cache(
            rd_url,
            cache_key="reddit_seed",
            cache_dir=cfg.cache_dir,
            ttl_sec=3600,
            timeout_sec=25,
        )
        rd_items = normalize_results(rd_raw)
        rd_items = [it for it in rd_items if isinstance(it, dict)]
        add_candidates(rd_items, "reddit")
        trace["reddit_items"] = len(rd_items)
    except Exception as e:
        trace["reddit_error"] = repr(e)

    # Fetch component OS feed
    try:
        os_url = f"{cfg.os_api_base}?q=os"
        os_raw = get_json_with_cache(
            os_url,
            cache_key="os_seed",
            cache_dir=cfg.cache_dir,
            ttl_sec=12 * 3600,
            timeout_sec=25,
        )
        os_items = normalize_results(os_raw)
        os_items = [it for it in os_items if isinstance(it, dict)]
        add_candidates(os_items, "component_os")
        trace["os_items"] = len(os_items)
    except Exception as e:
        trace["os_error"] = repr(e)

    trace["candidates"] = len(candidates)

    if not candidates:
        day_note = f" on {day}" if day else ""
        return FinalAnswer(
            short_answer="I don’t know from the current evidence.",
            meta=f"OS: {os_name}{day_note} · Abstained (no matching OS version object found)",
            abstained=True,
            confidence=40,
            debug_trace=(trace if debug else None),
        )

    # Pick latest (within that day if provided) by versionTimestamp
    def sort_key(x: Dict[str, Any]) -> int:
        try:
            return int(x.get("versionTimestamp", 0))
        except Exception:
            return 0

    latest = sorted(candidates, key=sort_key, reverse=True)[0]
    version_id = latest.get("versionId") or "Unknown"

    day_note = f" on {day}" if day else ""
    return FinalAnswer(
        short_answer=version_id,  # ✅ ONLY versionId
        meta=f"OS: {os_name}{day_note} · Matched by versionTimestampLastUpdate date",
        evidence=[latest] if debug else [],
        abstained=False,
        confidence=90,
        debug_trace=(trace if debug else None),
    )
    
    
# -----------------------------
# Main
# -----------------------------
def _norm(s: Any) -> str:
    return str(s or "").strip().lower()

def extract_day_from_query(query: str) -> Optional[str]:
    m = re.search(r"\b(20\d{2}-\d{2}-\d{2})\b", query or "")
    return m.group(1) if m else None

def day_from_iso(ts: Any) -> Optional[str]:
    s = str(ts or "").strip()
    if not s:
        return None

    # Fast path: ISO string
    if len(s) >= 10 and s[:10].count("-") == 2:
        return s[:10]

    return None
def detect_vendor_from_query_by_allowed(query: str, allowed: Set[str]) -> Optional[str]:
    """
    Prefer longest vendor match from allowed set (case-insensitive).
    Works for multi-word vendors (e.g. 'Slimbook OS', 'WatchGuard Fireware OS').
    """
    q = _norm(query)
    if not q or not allowed:
        return None

    # Try longest names first to avoid partial matches
    for v in sorted(allowed, key=lambda x: len(x), reverse=True):
        if v and _norm(v) in q:
            return _norm(v)
    return None

def filter_os_records(os_items: List[Dict[str, Any]], vendor_lc: str, day: Optional[str]) -> List[Dict[str, Any]]:
    hits: List[Dict[str, Any]] = []
    for it in os_items:
        if not isinstance(it, dict):
            continue

        brand = _norm(it.get("versionProductBrand"))
        if brand != vendor_lc:
            continue

        # If you want to restrict to OS only:
        # if _norm(it.get("versionProductType")) != "os":
        #     continue

        if day:
            it_day = day_from_iso(it.get("versionTimestampLastUpdate"))
            if it_day != day:
                continue

        hits.append(it)

    return hits

def pick_latest_by_last_update(records: List[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
    """
    Pick max by versionTimestampLastUpdate, fallback to versionTimestamp.
    """
    def key(it: Dict[str, Any]) -> Tuple[int, str]:
        tsu = str(it.get("versionTimestampLastUpdate") or "")
        # normalize for sorting
        if tsu.endswith("Z"):
            tsu = tsu[:-1] + "+00:00"
        # secondary: numeric timestamp
        try:
            ts = int(it.get("versionTimestamp") or 0)
        except Exception:
            ts = 0
        return (ts, tsu)

    if not records:
        return None
    return sorted(records, key=key, reverse=True)[0]

def answer(cfg, query: str, debug: bool = False) -> FinalAnswer:
    trace: Dict[str, Any] = {"query": query}

    # 1) Load vendor names (from /api/c/names) via your cache loader
    allowed, vendor_source = _load_vendors(cfg)
    allowed_lc = {_norm(v) for v in allowed if v}

    trace["vendor_api"] = getattr(cfg, "vendor_api", None)
    trace["vendor_source"] = vendor_source
    trace["allowed_vendors_count"] = len(allowed_lc)

    # 2) Detect vendor from query (must exist in allowed list)
    vendor_lc = detect_vendor_from_query_by_allowed(query, allowed_lc)
    trace["vendor_detected"] = vendor_lc

    if not vendor_lc:
        return FinalAnswer(
            short_answer="I don’t know from the current evidence.",
            meta="Abstained",
            abstained=True,
            confidence=20,
            debug_trace=(trace if debug else None),
        )

    # 3) Extract day (optional)
    day = extract_day_from_query(query)
    trace["day"] = day

    # 4) Fetch OS component feed ONLY
    os_url = f"{cfg.os_api_base}?q=os"
    try:
        raw = get_json_with_cache(os_url, "os_seed", cfg.cache_dir, ttl_sec=12 * 3600, timeout_sec=25)
        os_items = normalize_results(raw)
    except Exception as e:
        trace["os_error"] = repr(e)
        os_items = []

    trace["os_items"] = len(os_items)

    # 5) Filter by (brand == vendor) + (date match if provided)
    candidates = filter_os_records(os_items, vendor_lc, day)
    trace["candidates"] = len(candidates)

    if not candidates:
        # IMPORTANT: if day was provided, do not fallback unless you explicitly want it
        return FinalAnswer(
            short_answer="I don’t know from the current evidence.",
            meta=f"Abstained",
            abstained=True,
            confidence=40,
            debug_trace=(trace if debug else None),
        )

    # 6) Pick latest among candidates
    best = pick_latest_by_last_update(candidates)

    # 7) Return ONLY versionNumber (as you requested)
    version_number = str(best.get("versionNumber") or "").strip()
    version_id = str(best.get("versionId") or "").strip()

    trace["picked_versionId"] = version_id
    trace["picked_versionNumber"] = version_number
    trace["picked_last_update"] = best.get("versionTimestampLastUpdate")

    if not version_number:
        return FinalAnswer(
            short_answer="I don’t know from the current evidence.",
            meta="Abstained",
            abstained=True,
            confidence=40,
            debug_trace=(trace if debug else None),
        )

    return FinalAnswer(
        short_answer=version_number,  # ONLY versionNumber
        meta=f"Vendor: {vendor_lc} · {'On ' + day if day else 'Latest'}",
        evidence=[{
            "versionId": version_id,
            "versionNumber": version_number,
            "versionProductBrand": best.get("versionProductBrand"),
            "versionTimestampLastUpdate": best.get("versionTimestampLastUpdate"),
        }],
        abstained=False,
        confidence=90,
        debug_trace=(trace if debug else None),
    )
    