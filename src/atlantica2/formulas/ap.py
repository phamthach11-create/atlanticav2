# src/atlantica2/formulas/ap.py
# All comments in this project are written in English.

from __future__ import annotations

from typing import Any, Iterable

from src.atlantica2.formulas.stats import evaluate_stat


def compute_ap_gain(*, mods: Iterable[Any], base_ap_gain: float = 100.0) -> float:
    """
    AP gain per turn uses the same base/inc/more/less pipeline.

    Example:
      base=100
      sword: -20 base
      shield: 20% less
      => (100-20) * (1-0.2) = 64
    """
    return evaluate_stat(stat_key="ap_gain", base_value=base_ap_gain, mods=mods, clamp_min=0.0)
