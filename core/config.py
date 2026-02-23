from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path


@dataclass
class Config:
    # APIs
    os_api_base: str = "https://releasetrain.io/api/component"
    reddit_api_base: str = "https://releasetrain.io/api/reddit"
    vendor_api: str = "https://releasetrain.io/api/c/names"

    # Paths
    root_dir: Path = Path(__file__).resolve().parents[1]
    data_dir: Path = Path(__file__).resolve().parents[1] / "release_notes_store"
    cache_dir: Path = Path(__file__).resolve().parents[1] / ".live_cache"
    duckdb_path: str = str(Path(__file__).resolve().parents[1] / "releasetrain.duckdb")

    # Limits
    max_items_per_source: int = 50
    rebuild_ttl_sec: int = 900

    # LLM (optional)
    google_api_key: str = ""
    gemini_model: str = "gemini-1.5-flash"


def get_config() -> Config:
    cfg = Config()

    # env overrides
    cfg.os_api_base = os.getenv("OS_API", cfg.os_api_base)
    cfg.reddit_api_base = os.getenv("REDDIT_API", cfg.reddit_api_base)
    cfg.vendor_api = os.getenv("VENDOR_API", cfg.vendor_api)

    cfg.google_api_key = os.getenv("GOOGLE_API_KEY", cfg.google_api_key)
    cfg.gemini_model = os.getenv("GEMINI_MODEL", cfg.gemini_model)

    # Optional: override cache dir path via env
    cache_dir_env = os.getenv("CACHE_DIR")
    if cache_dir_env:
        cfg.cache_dir = Path(cache_dir_env)

    # ensure dirs exist
    cfg.cache_dir.mkdir(parents=True, exist_ok=True)
    cfg.data_dir.mkdir(parents=True, exist_ok=True)

    return cfg