# llm-abstain/tools/llm_optional.py
from __future__ import annotations

from typing import Any, Dict, List, Optional

try:
    import google.generativeai as genai  # type: ignore
except Exception:
    genai = None


ABSTAIN_TEXT = "I don’t know from the current evidence."


def llm_answer_with_evidence(
    cfg,
    query: str,
    intent: str,
    evidence: List[Dict[str, Any]],
    best_version: Optional[str] = None,
) -> Optional[str]:
    """
    SAFE MODE:
    - LLM is only allowed to rephrase deterministic result.
    - If best_version is None → no call.
    - If LLM output doesn't contain best_version (and isn't abstain text) → reject.
    """

    # Never let the LLM guess a version
    if not best_version:
        return None

    api_key = (getattr(cfg, "google_api_key", "") or "").strip()
    model_name = (getattr(cfg, "gemini_model", "gemini-1.5-flash") or "").strip()

    if not api_key or genai is None:
        return None

    genai.configure(api_key=api_key)
    llm = genai.GenerativeModel(model_name)

    prompt_text = f"""
You are formatting a deterministic system output.

User question:
{query}

Verified version (DO NOT CHANGE):
{best_version}

Rules:
- Do NOT invent new version numbers.
- Do NOT use any external knowledge.
- Do NOT modify the version value.
- If unsure, return exactly: "{ABSTAIN_TEXT}"

Return 1 short sentence.
""".strip()

    try:
        resp = llm.generate_content(prompt_text)
        text = (getattr(resp, "text", "") or "").strip()

        if not text:
            return None

        # Allow abstain (rare but valid)
        if text == ABSTAIN_TEXT:
            return text

        # STRICT VALIDATION: must include the deterministic version
        if best_version not in text:
            return None

        return text

    except Exception:
        return None