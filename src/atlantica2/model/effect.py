# src/atlantica2/model/effect.py
# All comments in this project are written in English.

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, Optional


@dataclass(frozen=True)
class Proc:
    """
    A generic proc/effect descriptor.
    Example uses:
      - pure_damage chance
      - enemy_ap_drain_on_hit
      - apply_status (stun/bleed/etc.)
    """
    key: str
    chance_pct: float = 0.0            # 0..100
    params: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ProcOutcome:
    """
    A resolved proc result (after RNG roll).
    """
    proc_key: str
    triggered: bool
    payload: Dict[str, Any] = field(default_factory=dict)
