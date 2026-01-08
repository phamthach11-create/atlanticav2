# src/atlantica2/data/progression.py
# All comments in this project are written in English.

from __future__ import annotations

from dataclasses import dataclass
from typing import List, Tuple


@dataclass(frozen=True)
class KRange:
    """
    K value is treated as a balance constant by level.
    Each range is inclusive: [level_min, level_max].
    """
    level_min: int
    level_max: int
    k: int


# Default table based on your sheet (key milestones).
# You can extend/adjust anytime without touching formulas.
K_TABLE: List[KRange] = [
    KRange(1, 9, 4),
    KRange(10, 19, 126),
    KRange(20, 29, 358),
    KRange(30, 39, 657),
    KRange(40, 49, 1012),
    KRange(50, 59, 1414),
    KRange(60, 69, 1859),
    KRange(70, 79, 2343),
    KRange(80, 89, 2862),
    KRange(90, 99, 3415),
    KRange(100, 100, 4000),
]


def get_k_from_table(level: int, table: List[KRange] = K_TABLE) -> int:
    """
    Lookup K by level using the configured table.
    """
    if level <= 0:
        raise ValueError("level must be >= 1")

    for r in table:
        if r.level_min <= level <= r.level_max:
            return r.k

    # If level is outside the table, clamp to nearest edge.
    if level < table[0].level_min:
        return table[0].k
    return table[-1].k


def describe_k_table(table: List[KRange] = K_TABLE) -> List[Tuple[str, int]]:
    """
    Return a human-friendly representation for debugging/logging.
    """
    out: List[Tuple[str, int]] = []
    for r in table:
        out.append((f"{r.level_min}-{r.level_max}", r.k))
    return out
