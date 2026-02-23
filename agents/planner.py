from __future__ import annotations
from dataclasses import dataclass
from typing import Optional

@dataclass
class Plan:
    intent: str
    vendor: Optional[str]

def plan(intent: str, vendor: Optional[str]) -> Plan:
    return Plan(intent=intent, vendor=vendor)