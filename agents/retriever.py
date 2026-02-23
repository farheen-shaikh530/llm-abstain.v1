from __future__ import annotations
from typing import Any, Dict, List
from tools.rag_store import search_store

def retrieve(embedder, datastore, query: str, k: int = 6) -> List[Dict[str, Any]]:
    hits = search_store(embedder, datastore, query, k=k)
    out = []
    for doc, score in hits:
        out.append({"text": doc, "score": score})
    return out