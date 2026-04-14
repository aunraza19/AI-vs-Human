from __future__ import annotations

import logging

from livekit.agents import Agent

from app.state_machine import DebateState
from app.topics import TopicProfile

logger = logging.getLogger("debate.agent")


class DebateAgent(Agent):
    def __init__(self, instructions: str, *, state: DebateState, topic: TopicProfile) -> None:
        super().__init__(instructions=instructions)
        self.state = state
        self.topic = topic

    async def on_enter(self) -> None:
        logger.info("Debate agent active on topic '%s'", self.topic.title)
