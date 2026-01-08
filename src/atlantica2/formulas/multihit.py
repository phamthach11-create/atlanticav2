# src/atlantica2/formulas/multihit.py
# All comments in this project are written in English.

from __future__ import annotations

import math
from typing import Any

from src.atlantica2.core.rng import RNG


def roll_extra_hits(*, total_mhr: float, rng: RNG) -> int:
    """
    Your rule:
      x = total_mhr / 100
      if x < 0 => 0
      n = floor(x)
      f = x - n
      roll r in [0,1)
      if r < f => extra = n+1 else extra = n
    """
    x = total_mhr / 100.0
    if x <= 0:
        return 0
    n = int(math.floor(x))
    f = x - n
    return n + 1 if rng.roll() < f else n


def total_hits(*, base_hitcount: int, total_mhr: float, rng: RNG) -> tuple[int, int]:
    extra = roll_extra_hits(total_mhr=total_mhr, rng=rng)
    return base_hitcount + extra, extra
