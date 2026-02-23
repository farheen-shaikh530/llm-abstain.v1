from __future__ import annotations

import base64
from pathlib import Path

import streamlit as st

from core.config import get_config
from orchestrator import answer as orchestrated_answer
from tools.http_tools import get_json_with_cache, normalize_results

# ─────────────────────────────────────────────────────────────
# Page config (NO sidebar, NO slider)
# ─────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="Release Hub — Intelligent Release Note System",
    page_icon="🧭",
    layout="wide",
    initial_sidebar_state="collapsed",
)

cfg = get_config()

EMBEDDING_MODEL_NAME = "sentence-transformers/all-mpnet-base-v2"  # keep stable
RAG_TOP_K = 8  # fixed — no slider
BG_IMAGE_PATH = Path(__file__).resolve().parent / "assets" / "background.jpg"


def apply_background(image_path: Path, overlay_dark: float = 0.55) -> None:
    bg_css = ""
    if image_path.exists():
        b64 = base64.b64encode(image_path.read_bytes()).decode("utf-8")
        bg_css = f"""
        [data-testid="stAppViewContainer"] {{
            background-image:
              linear-gradient(rgba(0,0,0,{overlay_dark}), rgba(0,0,0,{overlay_dark})),
              url("data:image/jpg;base64,{b64}");
            background-size: cover;
            background-position: center;
            background-attachment: fixed;
        }}
        """

    st.markdown(
        f"""
        <style>
            {bg_css}

            section[data-testid="stSidebar"] {{ display: none !important; }}
            button[title="View sidebar"] {{ display: none !important; }}
            [data-testid="collapsedControl"] {{ display: none !important; }}
            [data-testid="stSidebarCollapsedControl"] {{ display: none !important; }}

            .block-container {{
                max-width: 1100px;
                padding-top: 1.2rem;
                padding-bottom: 2rem;
            }}

            [data-testid="stChatMessage"] {{
                background: rgba(0,0,0,0.22);
                border-radius: 14px;
                padding: 10px 14px;
                margin-bottom: 10px;
                backdrop-filter: blur(6px);
                border: 1px solid rgba(255,255,255,0.10);
            }}

            .loading-banner {{
                background: rgba(0,0,0,0.35);
                border-radius: 14px;
                padding: 14px;
                margin: 10px 0;
                font-weight: 600;
                border: 1px solid rgba(255,255,255,0.18);
            }}
        </style>
        """,
        unsafe_allow_html=True,
    )


apply_background(BG_IMAGE_PATH)

st.title("Release Hub — Intelligent Release Note System")

with st.expander("🔎 Debug", expanded=False):
    debug_enabled = st.toggle("Enable debug mode", value=False)
    show_full_trace = st.toggle("Show full trace JSON", value=False)


def build_seed_docs() -> list[str]:
    """
    Seed docs for vector store. Your pipeline uses vendor sources only.
    Keep it small and stable.
    """
    docs: list[str] = []

    # OS API name is legacy; it’s still “release signals” in your system.
    try:
        os_url = f"{cfg.os_api_base}?q=os"
        os_raw = get_json_with_cache(os_url, "os_seed", cfg.cache_dir, ttl_sec=6 * 3600, timeout_sec=20) or []
        os_items = normalize_results(os_raw)
        for it in os_items[: cfg.max_items_per_source]:
            docs.append(
                " | ".join(
                    [
                        f"title: {it.get('versionProductName','')}",
                        f"notes: {str(it.get('versionReleaseNotes',''))[:1500]}",
                        f"url: {it.get('url','')}",
                        f"date: {it.get('updatedAt') or it.get('createdAt') or ''}",
                        "source: os",
                    ]
                )
            )
    except Exception:
        pass

    try:
        rd_url = f"{cfg.reddit_api_base}?limit=100&page=1"
        rd_raw = get_json_with_cache(rd_url, "reddit_seed", cfg.cache_dir, ttl_sec=3600, timeout_sec=20) or []
        rd_items = normalize_results(rd_raw)
        for it in rd_items[: cfg.max_items_per_source]:
            docs.append(
                " | ".join(
                    [
                        f"title: {it.get('title','')}",
                        f"url: {it.get('url','')}",
                        f"date: {it.get('createdAt') or it.get('created_utc') or ''}",
                        "source: reddit",
                    ]
                )
            )
    except Exception:
        pass

    if not docs:
        st.error("❌ No seed docs available (OS + Reddit fetch failed).")
        st.stop()

    return docs




def render_debug(trace: dict) -> None:
    if show_full_trace:
        st.json(trace)
        return

    st.json(
        {
            "db_path": trace.get("db_path"),
            "vendor_api": trace.get("vendor_api"),
            "planner": trace.get("planner"),
            "bronze": trace.get("bronze"),
            "silver_build": trace.get("silver_build"),
            "silver": trace.get("silver"),
            "gold": trace.get("gold"),
            "rag": trace.get("rag"),
            "decision": trace.get("decision"),
        }
    )


if "history" not in st.session_state:
    st.session_state.history = []

for role, msg in st.session_state.history:
    st.chat_message(role).write(msg)

query = st.chat_input("Ask about latest versions, CVEs, patches... (vendors only)")

if query:
    st.chat_message("user").write(query)
    st.session_state.history.append(("user", query))

    with st.spinner("Retrieving..."):
        fa = orchestrated_answer(cfg=cfg, query=query, debug=debug_enabled)

    output = f"**Answer:** {fa.short_answer}\n\n**Meta:** {fa.meta}\n\n"

    # ✅ IMPORTANT: when abstained, show no evidence (your requirement)
    if (not fa.abstained) and fa.evidence:
        output += "**Evidence:**\n"
        for e in fa.evidence[:5]:
            output += f"- {e.get('title')} (score={round(float(e.get('score', 0)), 4)})\n"

    st.chat_message("assistant").write(output)
    st.session_state.history.append(("assistant", output))

    if debug_enabled and fa.debug_trace:
        render_debug(fa.debug_trace)