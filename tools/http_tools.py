from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Any, Dict, List, Union

import requests


def _cache_path(cache_dir: Path, key: str) -> Path:
    cache_dir.mkdir(parents=True, exist_ok=True)
    safe = "".join([c if c.isalnum() or c in "-_." else "_" for c in key])
    return cache_dir / f"{safe}.json"


def get_json_with_cache(
    url: str,
    cache_key: str,
    cache_dir: Path,
    ttl_sec: int = 3600,
    timeout_sec: int = 20,
) -> Any:
    p = _cache_path(cache_dir, cache_key)

    if p.exists():
        age = time.time() - p.stat().st_mtime
        if age <= ttl_sec:
            try:
                return json.loads(p.read_text(encoding="utf-8"))
            except Exception:
                pass

    r = requests.get(url, timeout=timeout_sec)
    r.raise_for_status()
    data = r.json()

    try:
        p.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
    except Exception:
        pass

    return data


def normalize_results(raw: Any) -> List[Dict[str, Any]]:
    """
    Normalizes API shapes:
    - {"data":[...]}
    - [...]
    - {...}
    """
    if raw is None:
        return []
    if isinstance(raw, dict) and isinstance(raw.get("data"), list):
        return [x for x in raw["data"] if isinstance(x, dict)]
    if isinstance(raw, list):
        return [x for x in raw if isinstance(x, dict)]
    if isinstance(raw, dict):
        return [raw]
    return []