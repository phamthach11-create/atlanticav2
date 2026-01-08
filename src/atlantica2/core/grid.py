# src/atlantica2/core/grid.py
# All comments in this project are written in English.

from __future__ import annotations

from typing import Dict, List, Optional, Tuple

from .types import SlotId


# ------------------------------------------------------------
# Grid definition (your PvP perspective)
#
# Rows are horizontal:
#   Row 0 (frontline): 1 2 3
#   Row 1 (mid):       4 5 6
#   Row 2 (back):      7 8 9
#
# Lines are vertical (columns):
#   Line 0: 1 4 7
#   Line 1: 2 5 8
#   Line 2: 3 6 9
#
# This mapping is the SAME for Team A and Team B.
# Team A is on the left, Team B is on the right (handled by targeting rules, not by numbering).
# ------------------------------------------------------------

ROWS = 3
COLS = 3

ROW_SLOTS: Dict[int, List[SlotId]] = {
    0: [1, 2, 3],
    1: [4, 5, 6],
    2: [7, 8, 9],
}

LINE_SLOTS: Dict[int, List[SlotId]] = {
    0: [1, 4, 7],
    1: [2, 5, 8],
    2: [3, 6, 9],
}

SLOT_TO_POS: Dict[SlotId, Tuple[int, int]] = {
    1: (0, 0), 2: (0, 1), 3: (0, 2),
    4: (1, 0), 5: (1, 1), 6: (1, 2),
    7: (2, 0), 8: (2, 1), 9: (2, 2),
}

POS_TO_SLOT: Dict[Tuple[int, int], SlotId] = {pos: slot for slot, pos in SLOT_TO_POS.items()}


def is_valid_slot(slot: SlotId) -> bool:
    return slot in SLOT_TO_POS


def require_slot(slot: SlotId) -> None:
    if not is_valid_slot(slot):
        raise ValueError(f"Invalid slot: {slot}. Must be 1..9.")


def slot_to_pos(slot: SlotId) -> Tuple[int, int]:
    require_slot(slot)
    return SLOT_TO_POS[slot]


def pos_to_slot(row: int, col: int) -> SlotId:
    if not (0 <= row < ROWS and 0 <= col < COLS):
        raise ValueError(f"Invalid position: ({row},{col})")
    return POS_TO_SLOT[(row, col)]


def row_of(slot: SlotId) -> int:
    r, _ = slot_to_pos(slot)
    return r


def col_of(slot: SlotId) -> int:
    _, c = slot_to_pos(slot)
    return c


def line_of(slot: SlotId) -> int:
    # In this grid, line == column.
    return col_of(slot)


def slots_in_row(row: int) -> List[SlotId]:
    if row not in ROW_SLOTS:
        raise ValueError(f"Invalid row: {row}")
    return list(ROW_SLOTS[row])


def slots_in_line(line: int) -> List[SlotId]:
    if line not in LINE_SLOTS:
        raise ValueError(f"Invalid line: {line}")
    return list(LINE_SLOTS[line])


def left_of(slot: SlotId) -> Optional[SlotId]:
    r, c = slot_to_pos(slot)
    if c - 1 < 0:
        return None
    return pos_to_slot(r, c - 1)


def right_of(slot: SlotId) -> Optional[SlotId]:
    r, c = slot_to_pos(slot)
    if c + 1 >= COLS:
        return None
    return pos_to_slot(r, c + 1)


def up_of(slot: SlotId) -> Optional[SlotId]:
    r, c = slot_to_pos(slot)
    if r - 1 < 0:
        return None
    return pos_to_slot(r - 1, c)


def down_of(slot: SlotId) -> Optional[SlotId]:
    r, c = slot_to_pos(slot)
    if r + 1 >= ROWS:
        return None
    return pos_to_slot(r + 1, c)


def adjacent_horizontal(slot: SlotId) -> List[SlotId]:
    """
    Adjacent targets in the same row (left/right only).
    Used by Axe AoE: main target + one adjacent cell (ratio handled elsewhere).
    """
    out: List[SlotId] = []
    l = left_of(slot)
    r = right_of(slot)
    if l is not None:
        out.append(l)
    if r is not None:
        out.append(r)
    return out


def cross_neighbors(slot: SlotId) -> List[SlotId]:
    """
    Cross around a target (excluding center):
    left, right, up, down if they exist.
    Used by Cannon AoE (ratios handled elsewhere).
    """
    out: List[SlotId] = []
    for fn in (left_of, right_of, up_of, down_of):
        n = fn(slot)
        if n is not None:
            out.append(n)
    return out


def behind_in_line(slot: SlotId, steps: int = 1) -> Optional[SlotId]:
    """
    Return the slot behind the target in the same line (deeper row),
    e.g. 1 -> 4 -> 7.
    steps=1 returns next row; steps=2 returns two rows behind if exists.
    Used by Spear AoE (2 cells in line).
    """
    if steps <= 0:
        return slot
    r, c = slot_to_pos(slot)
    rr = r + steps
    if rr >= ROWS:
        return None
    return pos_to_slot(rr, c)
