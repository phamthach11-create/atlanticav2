# src/atlantica2/model/battle_state.py
# All comments in this project are written in English.

from __future__ import annotations

from dataclasses import dataclass, field
from typing import List, Optional

from src.atlantica2.core.rng import RNG
from src.atlantica2.model.board import Board


@dataclass
class BattleState:
    """
    Holds global runtime state for the simulation.
    """
    board: Board
    rng: RNG = field(default_factory=lambda: RNG(seed=12345))

    team_turn: int = 0           # 1..N (tell which side starts per step)
    starts_team: str = "A"       # "A" or "B"

    # future: cooldown/duration tick counters, logs, etc.
    log_lines: List[str] = field(default_factory=list)

    def log(self, msg: str) -> None:
        self.log_lines.append(msg)
