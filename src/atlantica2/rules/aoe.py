# src/atlantica2/rules/aoe.py
# All comments in this project are written in English.

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, List, Optional, Sequence

from src.atlantica2.core.types import SlotId, WeaponAoE
from src.atlantica2.core import grid


@dataclass(frozen=True)
class AoETarget:
    """A resolved AoE target slot with its damage ratio."""
    slot: SlotId
    ratio: float


def _aoe_key(aoe: WeaponAoE | str) -> str:
    """Normalize aoe enum/string into a lowercase key."""
    if hasattr(aoe, "name"):
        # Enum
        return str(aoe.name).lower()
    return str(aoe).strip().lower()


def _dedupe_keep_order(items: Sequence[AoETarget]) -> List[AoETarget]:
    seen: set[int] = set()
    out: List[AoETarget] = []
    for it in items:
        if it.slot in seen:
            continue
        seen.add(it.slot)
        out.append(it)
    return out


def _line_behind_slots(target_slot: SlotId, max_steps: int = 2) -> List[SlotId]:
    """
    Return slots behind the target in the same line (deeper row only).

    Examples:
      target=1 -> behind: 4, 7
      target=5 -> behind: 8
      target=9 -> behind: (none)
    """
    out: List[SlotId] = []
    for step in range(1, max_steps + 1):
        s = grid.behind_in_line(target_slot, steps=step)
        if s is None:
            break
        out.append(s)
    return out


def resolve_weapon_aoe(
    *,
    target_slot: SlotId,
    aoe: WeaponAoE | str,
    aoe_ratio_1: float = 0.50,
    aoe_ratio_2: float = 0.75,
) -> List[AoETarget]:
    """
    Resolve AoE slots for a weapon hit.

    Returned order is deterministic:
      - primary target first (ratio=1.0)
      - then AoE targets in a stable order (defined per AoE kind)

    Notes:
      - This function ONLY returns slots (does not check alive units).
      - Target legality (frontline-only vs anywhere) is handled in rules/targeting.py.
      - Ratios:
          aoe_ratio_1 = "far" / weaker splash (default 0.50)
          aoe_ratio_2 = "near" / stronger pierce (default 0.75)
    """
    key = _aoe_key(aoe)

    # Always include primary target.
    out: List[AoETarget] = [AoETarget(target_slot, 1.0)]

    # Single target.
    if key in ("single", "none"):
        return out

    # Adjacent in the same ROW (left/right).
    # Example: axe hitting slot 5 -> also hits 4 and 6
    if key in ("adjacent_1", "adjacent", "row_adjacent"):
        for s in grid.horizontal_neighbors(target_slot):
            out.append(AoETarget(s, aoe_ratio_1))
        return _dedupe_keep_order(out)

    # Cross shape (up/down/left/right).
    # Example: cannon hitting slot 1 -> also hits 2 and 4
    if key in ("cross", "cross_1", "plus"):
        for s in grid.cross_neighbors(target_slot):
            out.append(AoETarget(s, aoe_ratio_1))
        return _dedupe_keep_order(out)

    # Line pierce (same LINE, deeper rows only).
    # Example: gun hitting slot 1 -> also hits 4 and 7
    # We treat "LINE" as pierce-behind, not "full column both directions".
    if key in ("line", "column", "pierce", "line_2"):
        behind = _line_behind_slots(target_slot, max_steps=2)
        if len(behind) >= 1:
            out.append(AoETarget(behind[0], aoe_ratio_2))  # near behind
        if len(behind) >= 2:
            out.append(AoETarget(behind[1], aoe_ratio_1))  # far behind
        return _dedupe_keep_order(out)

    # Behind-only (1 step).
    if key in ("behind_1", "pierce_1"):
        s = grid.behind_in_line(target_slot, steps=1)
        if s is not None:
            out.append(AoETarget(s, aoe_ratio_1))
        return _dedupe_keep_order(out)

    # Behind-only (2 steps).
    if key in ("behind_2", "pierce_2"):
        behind = _line_behind_slots(target_slot, max_steps=2)
        if len(behind) >= 1:
            out.append(AoETarget(behind[0], aoe_ratio_2))
        if len(behind) >= 2:
            out.append(AoETarget(behind[1], aoe_ratio_1))
        return _dedupe_keep_order(out)

    # Fallback: treat unknown AoE as single target.
    return out
