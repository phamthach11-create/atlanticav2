# src/atlantica2/rules/turn_order.py
# All comments in this project are written in English.

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, Iterable, List, Literal, Optional, Tuple

TeamId = Literal["A", "B"]


# -----------------------------
# Helpers: board/unit adapters
# -----------------------------

def _iter_team_units(board: Any, team: TeamId) -> List[Any]:
    """
    Duck-typed iteration over team units.
    Supports:
      - board.team_a / board.team_b as dict[slot]->Unit
      - board.iter_team(team)
      - board.all_units()
    """
    if team == "A":
        m = getattr(board, "team_a", None)
    else:
        m = getattr(board, "team_b", None)

    if isinstance(m, dict):
        return list(m.values())

    if hasattr(board, "iter_team"):
        return list(board.iter_team(team))  # type: ignore[misc]

    if hasattr(board, "all_units"):
        return [u for u in board.all_units() if getattr(u, "team", None) == team]  # type: ignore[misc]

    return []


def _uid(u: Any) -> str:
    return str(getattr(u, "uid", f"{getattr(u,'team','?')}-{getattr(u,'slot','?')}"))


def _slot(u: Any) -> int:
    return int(getattr(u, "slot", 0))


def _is_alive(u: Any) -> bool:
    if u is None:
        return False
    if hasattr(u, "is_alive"):
        return bool(u.is_alive())  # type: ignore[misc]
    return float(getattr(u, "hp", 0.0)) > 0.0


# -----------------------------
# Start team / turn mapping
# -----------------------------

def team_for_team_turn(starts_team: TeamId, team_turn: int) -> TeamId:
    """
    team_turn starts at 1.
    If starts_team="A":
      1:A, 2:B, 3:A, 4:B, ...
    """
    if team_turn <= 0:
        return starts_team
    if (team_turn % 2) == 1:
        return starts_team
    return "B" if starts_team == "A" else "A"


# -----------------------------
# Early-turn fairness rule (2/3/4/5 actors)
# -----------------------------

@dataclass(frozen=True)
class TurnSelectionRule:
    """
    For the first 4 TEAM turns (global):
      T1: 2 actors, ignore AP>=100 threshold
      T2: 3 actors, ignore AP>=100 threshold
      T3: 4 actors, ignore AP>=100 threshold
      T4: 5 actors, ignore AP>=100 threshold
    From T5 onward: normal rule (max=5, require AP>=100).
    """
    early_map: Dict[int, int] = field(default_factory=lambda: {1: 2, 2: 3, 3: 4, 4: 5})
    normal_max: int = 5
    normal_ap_threshold: int = 100


def selection_params(team_turn: int, rule: TurnSelectionRule) -> Tuple[int, bool, int]:
    """
    Returns:
      (max_actors, ignore_threshold, ap_threshold)
    """
    if team_turn in rule.early_map:
        return int(rule.early_map[team_turn]), True, rule.normal_ap_threshold
    return int(rule.normal_max), False, int(rule.normal_ap_threshold)


# -----------------------------
# Status-aware AP gain
# -----------------------------

@dataclass
class StartTurnContext:
    """
    What we computed at start of the TEAM turn for each unit.
    """
    can_act: bool = True
    block_ap_gain: bool = False
    ap_base_delta: float = 0.0
    events: List[Any] = field(default_factory=list)  # status events (damage/log), engine may consume


@dataclass
class StartTeamTurnResult:
    team: TeamId
    team_turn: int

    # Ordered list of actors selected to act this team turn
    actors: List[Any] = field(default_factory=list)

    # Extra info for engine/logging
    contexts: Dict[str, StartTurnContext] = field(default_factory=dict)
    logs: List[str] = field(default_factory=list)


def _compute_ap_gain_with_status(u: Any, ap_base_delta: float) -> float:
    """
    Exact pipeline:
      AP_gain = evaluate_stat(stat_key='ap_gain', base_value=100, mods=mods)
    where mods include weapon/offhand/gear and an extra base delta from status.
    """
    # Fast path: no delta, use precomputed stats.ap_gain if available
    st = getattr(u, "stats", None)
    if ap_base_delta == 0 and st is not None and getattr(st, "ap_gain", None) is not None:
        return float(st.ap_gain)

    # Otherwise compute from mods
    try:
        mods = list(u._collect_mods())  # type: ignore[attr-defined]
    except Exception:
        mods = []

    if ap_base_delta != 0:
        mods.append(("ap_gain", "base", float(ap_base_delta)))

    from src.atlantica2.formulas.ap import compute_ap_gain

    return float(compute_ap_gain(mods=mods, base_ap_gain=100.0))


def start_team_turn(
    *,
    state: Any,
    team: TeamId,
    team_turn: int,
    rule: TurnSelectionRule = TurnSelectionRule(),
) -> StartTeamTurnResult:
    """
    This is the main API engine should call each TEAM turn.

    It does:
      1) Build per-unit start-turn status context (can_act, block_ap_gain, ap_base_delta, events)
      2) Apply AP gain to alive units (status-aware)
      3) Select actors in order (early fairness + normal AP rule)

    Engine then executes actions for `result.actors` in that order.
    """
    board = getattr(state, "board", state)
    units = [u for u in _iter_team_units(board, team) if _is_alive(u)]

    out = StartTeamTurnResult(team=team, team_turn=int(team_turn))
    max_actors, ignore_threshold, ap_threshold = selection_params(team_turn, rule)

    # 1) Build status contexts (optional but supported)
    # We call build_start_turn_frame to get block_ap_gain + ap_base_delta and DoT events.
    from src.atlantica2.rules.status_pipeline import build_start_turn_frame

    ctx_by_uid: Dict[str, StartTurnContext] = {}
    for u in units:
        frame = build_start_turn_frame(u)
        ctx = StartTurnContext(
            can_act=bool(frame.can_act),
            block_ap_gain=bool(frame.block_ap_gain),
            ap_base_delta=float(frame.ap_gain_base_delta),
            events=list(frame.events),
        )
        ctx_by_uid[_uid(u)] = ctx
    out.contexts = ctx_by_uid

    # 2) Apply AP gain
    for u in units:
        uid = _uid(u)
        ctx = ctx_by_uid.get(uid, StartTurnContext())
        ap_before = int(getattr(u, "ap", 0))

        if ctx.block_ap_gain:
            gain = 0
        else:
            gain = int(round(_compute_ap_gain_with_status(u, ctx.ap_base_delta)))

        setattr(u, "ap", ap_before + gain)

        out.logs.append(f"  AP gain: {uid}: {ap_before} -> {ap_before + gain} (+{gain})")

    # 3) Select actors
    # Sort by AP desc, then slot asc for deterministic ties.
    units_sorted = sorted(units, key=lambda x: (-int(getattr(x, "ap", 0)), _slot(x)))

    # Filter by AP threshold in normal mode
    if not ignore_threshold:
        units_sorted = [u for u in units_sorted if int(getattr(u, "ap", 0)) >= ap_threshold]

    # Filter out units that cannot act (stun/immobilized etc.)
    units_sorted = [u for u in units_sorted if ctx_by_uid.get(_uid(u), StartTurnContext()).can_act]

    # Take top N
    actors = units_sorted[:max_actors]
    out.actors = actors

    # Actor selection log
    if ignore_threshold:
        rule_note = f"ignore AP>=100 (early fairness T{team_turn})"
    else:
        rule_note = f"AP>={ap_threshold}"

    if actors:
        s = ", ".join([f"{_uid(a)}(AP={int(getattr(a,'ap',0))})" for a in actors])
    else:
        s = "(none)"
    out.logs.append(f"  Actors selected: max={max_actors}, rule={rule_note}: {s}")

    return out
