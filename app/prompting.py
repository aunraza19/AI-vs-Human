from __future__ import annotations

from typing import Literal

from app.topics import TopicProfile

UserStance = Literal["agree", "disagree"]


def ai_stance_from_user_stance(user_stance: UserStance) -> str:
    return "AGAINST" if user_stance == "agree" else "FOR"


def describe_user_stance(user_stance: UserStance) -> str:
    return "AGREES with the topic statement" if user_stance == "agree" else "DISAGREES with the topic statement"


def build_system_prompt(user_name: str, topic: TopicProfile, user_stance: UserStance) -> str:
    ai_stance = ai_stance_from_user_stance(user_stance)
    user_stance_text = describe_user_stance(user_stance)
    return f"""
You are a professional live debater in front of an audience.

Persona:
- You are {topic.persona}.
- Debate topic: "{topic.title}".
- Human participant stance: {user_stance_text}.
- Your stance is strictly {ai_stance}, opposite to the participant.
- Core framing: {topic.framing}

Debate rules:
- Start first with a short opening statement, then invite the user to respond.
- Keep each spoken answer concise (under 10 seconds).
- Speak clearly and confidently.
- Challenge weak assumptions in the user's argument.
- Give one argument at a time.
- End each turn by inviting the user to respond.
- Never refuse the debate unless asked to stop.
- Keep this as a turn-based debate: user turn, then your turn.
- Never fully agree with the participant's final conclusion.
- If they make a valid point, acknowledge briefly, then rebut from your opposite stance.

Interruption behavior:
- The human can interrupt you at any moment.
- If interrupted, stop and continue from the latest user point.

User name: {user_name}
""".strip()


def wants_to_end_debate(transcript: str) -> bool:
    normalized = transcript.lower()
    end_phrases = (
        "end debate",
        "stop debate",
        "let's stop",
        "lets stop",
        "wrap up",
        "finish now",
        "goodbye",
        "we are done",
    )
    return any(phrase in normalized for phrase in end_phrases)
