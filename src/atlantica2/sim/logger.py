# src/atlantica2/sim/logger.py
# All comments in this project are written in English.

from __future__ import annotations

from dataclasses import dataclass, field
from typing import List, Optional

from src.atlantica2.model.battle_state import BattleState


@dataclass
class BattleLogger:
    """
    Simple logger that writes to:
    - BattleState.log_lines (in-memory)
    - optional stdout printing
    """

    print_to_stdout: bool = True
    lines: List[str] = field(default_factory=list)

    def log(self, state: BattleState, msg: str) -> None:
        self.lines.append(msg)

        # Keep a copy inside BattleState as well (handy for exporting)
        if hasattr(state, "log_lines") and isinstance(state.log_lines, list):
            state.log_lines.append(msg)

        if self.print_to_stdout:
            print(msg)

    def header(self, state: BattleState, title: str, width: int = 42) -> None:
        bar = "=" * width
        self.log(state, bar)
        self.log(state, title)
        self.log(state, bar)

    def blank(self, state: BattleState) -> None:
        self.log(state, "")

    def export_text(self) -> str:
        return "\n".join(self.lines)

    def export_to_file(self, filepath: str) -> None:
        with open(filepath, "w", encoding="utf-8") as f:
            f.write(self.export_text())


def get_state_logger(state: BattleState) -> BattleLogger:
    """
    Return a shared logger instance stored on BattleState.
    """
    lg = getattr(state, "logger", None)
    if isinstance(lg, BattleLogger):
        return lg

    lg = BattleLogger(print_to_stdout=True)
    setattr(state, "logger", lg)
    return lg


def state_log(state: BattleState, msg: str) -> None:
    """
    Convenience function:
    - if state has .logger use it
    - else fallback to state.log(msg) if exists
    """
    lg = getattr(state, "logger", None)
    if isinstance(lg, BattleLogger):
        lg.log(state, msg)
        return

    if hasattr(state, "log"):
        try:
            state.log(msg)
            return
        except Exception:
            pass

    # Last resort: print only
    print(msg)
