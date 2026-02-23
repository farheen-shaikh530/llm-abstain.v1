from __future__ import annotations
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

@dataclass
class Verification:
    abstain: bool
    confidence: float
    reason: str

def verify(intent: str, vendor: Optional[str], gold_row: Optional[dict], evidence: List[dict]) -> Verification:
    # VERSION must have a gold fact
    if intent == "VERSION":
        if not vendor:
            return Verification(True, 0.30, "Vendor not found.")
        if not gold_row:
            return Verification(True, 0.45, "No gold latest-version fact found.")
        return Verification(False, 0.85, "Gold version fact found.")

    # CVE/PATCH must have vendor+intent evidence
    if intent in ("CVE", "PATCH"):
        if not vendor:
            return Verification(True, 0.30, "Vendor not found.")
        if not evidence:
            return Verification(True, 0.49, "No matching evidence sentences found.")
        return Verification(False, 0.70, "Evidence found.")

    # default
    return Verification(False, 0.50, "Fallback.")