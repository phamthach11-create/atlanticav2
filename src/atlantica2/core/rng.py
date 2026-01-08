# src/atlantica2/core/rng.py
# All comments in this project are written in English.

from __future__ import annotations

import random
from dataclasses import dataclass
from typing import Optional


@dataclass
class RNG:
    """
    Central RNG wrapper for the whole simulation.

    Why:
    - Make combat logs reproducible by using a fixed seed.
    - Keep all rolls (hit/crit/multihit/procs) consistent and debuggable.

    Usage:
      rng = RNG(seed=123)
      r = rng.roll()         # float in [0.0, 1.0)
      ok = rng.chance(0.25)  # 25% chance
      x = rng.randint(1, 6)
      idx = rng.choice_index(n)
    """

    seed: Optional[int] = None

    def __post_init__(self) -> None:
        self._random = random.Random(self.seed)

    def reseed(self, seed: int) -> None:
        """Reset RNG with a new seed."""
        self.seed = seed
        self._random = random.Random(self.seed)

    def roll(self) -> float:
        """Return a float in [0.0, 1.0)."""
        return self._random.random()

    def chance(self, p: float) -> bool:
        """
        Return True with probability p.

        p is a fraction:
          0.10 = 10%
          0.05 = 5%

        Values <= 0 always fail, values >= 1 always succeed.
        """
        if p <= 0:
            return False
        if p >= 1:
            return True
        return self.roll() < p

    def randint(self, a: int, b: int) -> int:
        """Inclusive randint [a, b]."""
        return self._random.randint(a, b)

    def choice_index(self, n: int) -> int:
        """Return a random index in [0, n-1]."""
        if n <= 0:
            raise ValueError("n must be >= 1")
        return self._random.randrange(n)

    def shuffle(self, items: list) -> None:
        """In-place shuffle."""
        self._random.shuffle(items)
