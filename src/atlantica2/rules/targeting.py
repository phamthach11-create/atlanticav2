# src/atlantica2/rules/targeting.py
# All comments in this project are written in English.

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Iterable, List, Literal, Optional, Sequence, Tuple

TeamId = Literal["A", "B"]
SlotId = int

# Who the action is intended to target
TargetSide = Literal["enemy", "ally", "self", "both"]

# Where the primary target is allowed to be selected from
TargetLocation = Literal["anywhere", "frontline", "self"]

# For multi-target selectors
TargetScope = Literal["single", "team", "all_alive"]


@dataclass(frozen=True)
class TargetingSpec:
    """
    Generic targeting specification usable for:
      - weapon basic attacks
      - active skills
      - aura/passive applications (battle start or event driven)

    Notes:
      - "frontline" is defined by LINE exposure: [1,4,7], [2,5,8], [3,6,9].
      - "anywhere" means any alive slot.
      - "team" scope ignores location and returns all alive slots on the resolved team.
    """
    side: TargetSide = "enemy"
    location: TargetLocation = "anywhere"
    scope: TargetScope = "single"
    allow_retarget: bool = True  # if preferred slot invalid/dead, auto select a legal one


# -----------------------------
# Board adapters (duck typing)
# -----------------------------

def _get_unit(board: Any, team: TeamId, slot: SlotId) -> Optional[Any]:
    if hasattr(board, "get"):
        return board.get(team, slot)  # type: ignore[misc]
    # fallback for dict-like boards: board.team_a / board.team_b
    if team == "A":
        m = getattr(board, "team_a", None)
    else:
        m = getattr(board, "team_b", None)
    if isinstance(m, dict):
        return m.get(slot)
    return None


def _is_alive(u: Any) -> bool:
    if u is None:
        return False
    if hasattr(u, "is_alive"):
        return bool(u.is_alive())  # type: ignore[misc]
    # fallback: hp>0
    hp = getattr(u, "hp", 0)
    return float(hp) > 0.0


def alive_slots(board: Any, team: TeamId) -> List[SlotId]:
    if hasattr(board, "alive_slots"):
        return list(board.alive_slots(team))  # type: ignore[misc]
    out: List[SlotId] = []
    for s in range(1, 10):
        if _is_alive(_get_unit(board, team, s)):
            out.append(s)
    return out


def exposed_frontline_slots(board: Any, team: TeamId) -> List[SlotId]:
    """
    Frontline exposure by LINE:
      line1: 1 -> 4 -> 7
      line2: 2 -> 5 -> 8
      line3: 3 -> 6 -> 9
    Exposed slot is the first alive one in each line.
    """
    if hasattr(board, "exposed_frontline_slots"):
        return list(board.exposed_frontline_slots(team))  # type: ignore[misc]

    lines: List[List[int]] = [[1, 4, 7], [2, 5, 8], [3, 6, 9]]
    out: List[SlotId] = []
    for line in lines:
        for s in line:
            if _is_alive(_get_unit(board, team, s)):
                out.append(s)
                break
    return out


def _line_index(slot: SlotId) -> int:
    """
    Returns 0..2 for line1..line3 based on your definition:
      line1 = 1,4,7 -> col 0
      line2 = 2,5,8 -> col 1
      line3 = 3,6,9 -> col 2
    """
    return (slot - 1) % 3


def _exposed_in_same_line(board: Any, team: TeamId, preferred_slot: SlotId) -> Optional[SlotId]:
    """
    If a preferred slot is dead/illegal, and location is frontline,
    retarget to the exposed slot in the same line (if any).
    Example: preferred=2 but slot2 dead -> return 5 if alive else 8 if alive.
    """
    col = _line_index(preferred_slot)
    candidates = [1 + col, 4 + col, 7 + col]
    for s in candidates:
        if _is_alive(_get_unit(board, team, s)):
            return s
    return None


# -----------------------------
# Team resolution
# -----------------------------

def resolve_target_teams(attacker_team: TeamId, side: TargetSide) -> List[TeamId]:
    if side == "self":
        return [attacker_team]
    if side == "ally":
        return [attacker_team]
    if side == "enemy":
        return ["B" if attacker_team == "A" else "A"]
    # both
    return [attacker_team, "B" if attacker_team == "A" else "A"]


# -----------------------------
# Candidate generation
# -----------------------------

def primary_candidates(board: Any, defender_team: TeamId, location: TargetLocation) -> List[SlotId]:
    if location == "self":
        # "self" location should not be used with enemy team, but keep safe:
        return []
    if location == "frontline":
        return exposed_frontline_slots(board, defender_team)
    # anywhere
    return alive_slots(board, defender_team)


def validate_primary_target(board: Any, defender_team: TeamId, slot: SlotId, location: TargetLocation) -> bool:
    if not _is_alive(_get_unit(board, defender_team, slot)):
        return False
    if location == "frontline":
        return slot in exposed_frontline_slots(board, defender_team)
    if location == "anywhere":
        return True
    # location == "self" cannot validate against defender_team here
    return False


# -----------------------------
# Selection (RNG adapter)
# -----------------------------

def _rng_choice(rng: Any, items: Sequence[SlotId]) -> SlotId:
    """
    Supports:
      - rng.choice(list)
      - rng.randint-like via rng.roll_int(0, n-1)
      - fallback to python random (non-deterministic)
    """
    if hasattr(rng, "choice"):
        return rng.choice(list(items))  # type: ignore[misc]
    if hasattr(rng, "roll_int"):
        idx = int(rng.roll_int(0, len(items) - 1))  # type: ignore[misc]
        return items[idx]
    # last resort
    import random
    return random.choice(list(items))


def pick_primary_target(
    *,
    board: Any,
    attacker_team: TeamId,
    spec: TargetingSpec,
    preferred_team: Optional[TeamId] = None,
    preferred_slot: Optional[SlotId] = None,
    rng: Optional[Any] = None,
) -> Tuple[Optional[TeamId], Optional[SlotId], str]:
    """
    Returns (target_team, target_slot, reason).

    Rules:
      - Resolve target team(s) from spec.side
      - If spec.scope != "single", this function returns (team, slot, reason) = (None,None,...) and you should use
        resolve_targets(...) instead.
      - If preferred_slot provided:
          - accept if valid
          - else if allow_retarget:
              - if location=frontline: try exposed slot in same line
              - else pick random from legal candidates
    """
    if spec.scope != "single":
        return None, None, "scope_not_single"

    teams = resolve_target_teams(attacker_team, spec.side)

    # Decide which team to target for "single" if multiple possible
    target_team: TeamId
    if preferred_team in teams:
        target_team = preferred_team  # type: ignore[assignment]
    else:
        # default: enemy if exists else self/ally
        target_team = teams[0]

    # Self targeting
    if spec.side == "self" or spec.location == "self":
        return attacker_team, int(getattr(_get_unit(board, attacker_team, getattr(_get_unit(board, attacker_team, 1), "slot", 1)), "slot", 0) or 0), "self"

    # Candidates based on location
    cands = primary_candidates(board, target_team, spec.location)
    if not cands:
        return target_team, None, "no_candidates"

    # Preferred target path
    if preferred_slot is not None:
        if validate_primary_target(board, target_team, preferred_slot, spec.location):
            return target_team, preferred_slot, "preferred_ok"

        if spec.allow_retarget:
            if spec.location == "frontline":
                same_line = _exposed_in_same_line(board, target_team, preferred_slot)
                if same_line is not None and validate_primary_target(board, target_team, same_line, spec.location):
                    return target_team, same_line, "retarget_same_line_exposed"
            # fallback random legal
            if rng is not None:
                return target_team, _rng_choice(rng, cands), "retarget_random"
            return target_team, cands[0], "retarget_first"

        return target_team, None, "preferred_invalid"

    # No preference: choose random if rng provided, else first stable
    if rng is not None:
        return target_team, _rng_choice(rng, cands), "random"
    return target_team, cands[0], "first"


def resolve_targets(
    *,
    board: Any,
    attacker_team: TeamId,
    spec: TargetingSpec,
    preferred_team: Optional[TeamId] = None,
    preferred_slot: Optional[SlotId] = None,
    rng: Optional[Any] = None,
) -> List[Tuple[TeamId, SlotId]]:
    """
    Resolve final target list for non-single scopes (team/all_alive), or for single (wrap pick_primary_target).

    Returned items are (team, slot) pairs.

    Scopes:
      - single: one target from pick_primary_target
      - team: all alive slots on resolved team
      - all_alive: all alive slots on both teams (used for some auras/debug)
    """
    if spec.scope == "single":
        t_team, t_slot, _ = pick_primary_target(
            board=board,
            attacker_team=attacker_team,
            spec=spec,
            preferred_team=preferred_team,
            preferred_slot=preferred_slot,
            rng=rng,
        )
        if t_team is None or t_slot is None:
            return []
        return [(t_team, t_slot)]

    if spec.scope == "team":
        teams = resolve_target_teams(attacker_team, spec.side)
        # pick preferred team if provided, else first resolved
        team: TeamId
        if preferred_team in teams:
            team = preferred_team  # type: ignore[assignment]
        else:
            team = teams[0]
        return [(team, s) for s in alive_slots(board, team)]

    # all_alive
    out: List[Tuple[TeamId, SlotId]] = []
    for team in ["A", "B"]:
        for s in alive_slots(board, team):  # type: ignore[arg-type]
            out.append((team, s))  # type: ignore[list-item]
    return out
