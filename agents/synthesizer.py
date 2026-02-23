from __future__ import annotations
from dataclasses import dataclass
from typing import List, Dict, Optional

@dataclass
class FinalAnswer:
    short_answer: str
    meta: str
    citations: List[str]
    evidence: List[Dict]

def synthesize(intent: str, vendor: Optional[str], verification, gold_row: Optional[dict], evidence: List[Dict]) -> FinalAnswer:
    if verification.abstain:
        return FinalAnswer(
            short_answer=f"I don’t know from the current evidence.",
            meta=f"Intent: {intent} · Vendor: {vendor or '—'} · Abstained · Confidence: {verification.confidence*100:.0f}% · {verification.reason}",
            citations=[],
            evidence=evidence[:8],
        )

    if intent == "VERSION" and gold_row:
        v = gold_row["latest_version"]
        return FinalAnswer(
            short_answer=f"Latest version of **{vendor}** is **{v}**.",
            meta=f"Intent: VERSION · Vendor: {vendor} · VersionFound: yes · Confidence: {verification.confidence*100:.0f}%",
            citations=[c for c in [gold_row.get("url","")] if c],
            evidence=[{
                "title": f"{vendor} {v}",
                "source": gold_row.get("source",""),
                "date": gold_row.get("fact_date",""),
                "url": gold_row.get("url",""),
                "snippet": gold_row.get("snippet",""),
            }],
        )

    return FinalAnswer(
        short_answer=f"Here’s what I found for **{vendor}** related to **{intent}**.",
        meta=f"Intent: {intent} · Vendor: {vendor} · Confidence: {verification.confidence*100:.0f}%",
        citations=[e.get("url","") for e in evidence if e.get("url")][:6],
        evidence=evidence[:8],
    )