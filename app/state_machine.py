from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class DebateStage(str, Enum):
    INIT = "INIT"
    AI_INTRO = "AI_INTRO"
    USER_INTRO = "USER_INTRO"
    DEBATE_LOOP = "DEBATE_LOOP"
    END = "END"


@dataclass
class DebateState:
    stage: DebateStage = DebateStage.INIT
    human_turns: int = 0
    max_human_turns: int = 8
    end_requested: bool = False

    def transition(self, next_stage: DebateStage) -> None:
        self.stage = next_stage

    def register_human_turn(self) -> int:
        self.human_turns += 1
        return self.human_turns

    def should_end_for_turn_limit(self) -> bool:
        return self.human_turns >= self.max_human_turns
