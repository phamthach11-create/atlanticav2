# All comments in this project are written in English.

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, List

from src.atlantica2.model.effect import Proc

if TYPE_CHECKING:
    from src.atlantica2.model.board import Board
    from src.atlantica2.model.unit import Unit


@dataclass(frozen=True)
class AuraPlan:
    """
    A plan describing an aura "application set".
    Engine will apply aura as status/mods at the right phase (e.g. start of team turn).
    """
    aura_key: str
    aura_name: str
    source_team: str
    source_slot: int
    target_team: str
    target_slots: List[int]
    procs: List[Proc]


def _iter_team_units(board: Board, team: str) -> List[Unit]:
    """
    Duck-typed helper:
    - prefers board.iter_team(team)
    - fallback: board.units (dict/team map) if exists
    """
    if hasattr(board, "iter_team"):
        return list(board.iter_team(team))  # type: ignore[misc]
    units = getattr(board, "units", None)
    if isinstance(units, dict) and team in units:
        return list(units[team])
    # Last resort: board.all_units()
    if hasattr(board, "all_units"):
        return [u for u in board.all_units() if getattr(u, "team", None) == team]  # type: ignore[misc]
    return []


def _lazy_get_aura_skill(aura_key: str):
    from src.atlantica2.data.skills_data import get_aura_skill  # lazy

    return get_aura_skill(aura_key)


def build_team_aura_plans(board: Board, team: str) -> List[AuraPlan]:
    """
    Build aura plans for a team.
    Expected on Unit:
      - aura_skill_keys: List[str] (optional)
    Expected on aura skill def:
      - key, name
      - target: "team" (default) or "self"
      - procs: List[Proc]
    """
    plans: List[AuraPlan] = []
    allies = _iter_team_units(board, team)

    for src in allies:
        if not getattr(src, "alive", True):
            continue

        aura_keys = getattr(src, "aura_skill_keys", None) or []
        for ak in list(aura_keys):
            aura = _lazy_get_aura_skill(str(ak))
            procs = list(getattr(aura, "procs", []))
            if not procs:
                continue

            target_mode = str(getattr(aura, "target", "team")).lower().strip()
            if target_mode == "self":
                target_slots = [int(getattr(src, "slot", 0))]
            else:
                # default = whole team
                target_slots = [int(getattr(u, "slot", 0)) for u in allies if getattr(u, "alive", True)]

            plans.append(
                AuraPlan(
                    aura_key=str(getattr(aura, "key", ak)),
                    aura_name=str(getattr(aura, "name", ak)),
                    source_team=str(getattr(src, "team", team)),
                    source_slot=int(getattr(src, "slot", 0)),
                    target_team=str(team),
                    target_slots=target_slots,
                    procs=procs,
                )
            )

    return plans
