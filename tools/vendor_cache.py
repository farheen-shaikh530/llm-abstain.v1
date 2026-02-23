# tools/vendor_cache.py
from __future__ import annotations

import json
from pathlib import Path
from typing import Set, Tuple

from tools.http_tools import get_json_with_cache, normalize_results


def _vendor_cache_path(cfg) -> Path:
    cache_dir = Path(getattr(cfg, "cache_dir"))
    cache_dir.mkdir(parents=True, exist_ok=True)
    return cache_dir / "vendor_names_local.json"


def load_allowed_vendors_local_first(cfg, ttl_sec: int = 7 * 24 * 3600) -> Tuple[Set[str], str]:
    """
    Returns (vendors_set_lowercase, source)
    - source = "api" if fetched now / via http cache
    - source = "local_file" if loaded from file
    """
    url = (getattr(cfg, "vendor_api", "") or "").strip()
    cache_dir = getattr(cfg, "cache_dir", None)

    if not url or cache_dir is None:
        return set(), "missing_cfg"

    path = _vendor_cache_path(cfg)

    # Try local file first (fast)
    if path.exists():
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            if isinstance(data, list) and data:
                return {str(x).strip().lower() for x in data if str(x).strip()}, "local_file"
        except Exception:
            pass

    # Fetch via cached HTTP
    raw = get_json_with_cache(url, "vendor_names", cache_dir, ttl_sec=ttl_sec, timeout_sec=25)
    items = normalize_results(raw)

    vendors: Set[str] = set()
    for it in items:
        if isinstance(it, dict):
            name = it.get("name")
            if isinstance(name, str) and name.strip():
                vendors.add(name.strip().lower())

    # Defensive: if API returns list[str]
    if isinstance(raw, list) and raw and isinstance(raw[0], str):
        vendors |= {s.strip().lower() for s in raw if isinstance(s, str) and s.strip()}

    # Persist to local file for deploy stability
    try:
        path.write_text(json.dumps(sorted(vendors), ensure_ascii=False), encoding="utf-8")
    except Exception:
        pass

    return vendors, "api"