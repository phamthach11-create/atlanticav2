# src/atlantica2/model/board.py
# All comments in this project are written in English.

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple

from src.atlantica2.model.unit import Unit


ROWS: List[List[int]] = [
    [1, 2, 3],   # row 1 (front row, tanks)
    [4, 5, 6],   # row 2
    [7, 8, 9],   # row 3 (back row)
]

LINES: List[List[int]] = [
    [1, 4, 7],   # line 1
    [2, 5, 8],   # line 2
    [3, 6, 9],   # line 3
]


def slot_to_rc(slot: int) -> Tuple[int, int]:
    # row index 0..2, col index 0..2
    r = (slot - 1) // 3
    c = (slot - 1) % 3
    return r, c


def rc_to_slot(r: int, c: int) -> int:
    return r * 3 + c + 1


def adjacent_in_row(slot: int) -> List[int]:
    """
    Horizontal adjacency (same row): left/right.
    Used by Axe AoE: adjacent_1 (hits 1 neighbor).
    """
    r, c = slot_to_rc(slot)
    out: List[int] = []
    if c - 1 >= 0:
        out.append(rc_to_slot(r, c - 1))
    if c + 1 <= 2:
        out.append(rc_to_slot(r, c + 1))
    return out


def cross_neighbors(slot: int) -> List[int]:
    """
    Cross AoE: up/down/left/right (within 3x3).
    Used by Cannon/Staff etc (depending on your sheet).
    """
    r, c = slot_to_rc(slot)
    out: List[int] = []
    if r - 1 >= 0:
        out.append(rc_to_slot(r - 1, c))
    if r + 1 <= 2:
        out.append(rc_to_slot(r + 1, c))
    if c - 1 >= 0:
        out.append(rc_to_slot(r, c - 1))
    if c + 1 <= 2:
        out.append(rc_to_slot(r, c + 1))
    return out


def behind_in_line(slot: int, steps: int = 1) -> Optional[int]:
    """
    Slot behind target in the same line (deeper row):
      1 -> 4 -> 7,  2 -> 5 -> 8,  3 -> 6 -> 9
    Used by Spear AoE (2 cells in line).
    """
    r, c = slot_to_rc(slot)
    rr = r + steps
    if rr > 2:
        return None
    return rc_to_slot(rr, c)


@dataclass
class Board:
    """
    Stores two teams and provides formation logic.
    """
    team_a: Dict[int, Unit] = field(default_factory=dict)  # slot -> Unit
    team_b: Dict[int, Unit] = field(default_factory=dict)  # slot -> Unit

    def get(self, team: str, slot: int) -> Optional[Unit]:
        if team == "A":
            return self.team_a.get(slot)
        return self.team_b.get(slot)

    def set(self, unit: Unit) -> None:
        if unit.team == "A":
            self.team_a[unit.slot] = unit
        else:
            self.team_b[unit.slot] = unit

    def alive_slots(self, team: str) -> List[int]:
        out: List[int] = []
        for s in range(1, 10):
            u = self.get(team, s)
            if u is not None and u.is_alive():
                out.append(s)
        return out

    def exposed_frontline_slots(self, team: str) -> List[int]:
        """
        Your rule:
        Frontline targeting is per LINE.
        For each line:
          pick the first alive slot in [front -> back].
        Example:
          if slot 2 is dead, line2 exposes slot 5 (if alive) even when 1 and 3 are alive.
        """
        exposed: List[int] = []
        for line in LINES:
            chosen: Optional[int] = None
            for s in line:
                u = self.get(team, s)
                if u is not None and u.is_alive():
                    chosen = s
                    break
            if chosen is not None:
                exposed.append(chosen)
        return exposed
