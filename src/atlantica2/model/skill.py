# src/atlantica2/model/skill.py
# All comments in this project are written in English.

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, Literal, Optional


SkillKind = Literal["active", "passive", "aura"]


@dataclass(frozen=True)
class SkillDef:
    """
    Runtime skill definition.
    Actual execution is handled later in rules/skills/* and rules/status_pipeline.py
    """
    key: str
    name: str
    kind: SkillKind

    ap_cost: int = 0
    mp_cost: int = 0

    cooldown: int = 0          # in turns (two-turn tick handled elsewhere)
    duration: int = 0          # in turns (two-turn tick handled elsewhere)

    params: Dict[str, Any] = field(default_factory=dict)
