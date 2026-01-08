# src/atlantica2/formulas/progression.py
# All comments in this project are written in English.

from __future__ import annotations

from src.atlantica2.data.progression import get_k_from_table


def get_k(level: int) -> int:
    return int(get_k_from_table(level))
