from __future__ import annotations

from typing import Literal

from app.topics import TopicProfile

UserStance = Literal["agree", "disagree"]
DebateLanguage = Literal["english", "urdu"]


def ai_stance_from_user_stance(user_stance: UserStance) -> str:
    return "AGAINST" if user_stance == "agree" else "FOR"


def describe_user_stance(user_stance: UserStance) -> str:
    return "AGREES with the topic statement" if user_stance == "agree" else "DISAGREES with the topic statement"


def _language_block(language: DebateLanguage) -> str:
    if language == "urdu":
        return """
Language mode (STRICT):
- صرف اردو میں جواب دیں۔
- صرف اردو رسم الخط (Arabic script) استعمال کریں۔
- Roman Urdu یا English الفاظ/جملے شامل نہ کریں۔
- اگر صارف انگریزی یا دوسری زبان میں بات کرے، مختصراً کہیں کہ مباحثہ اردو میں رکھیں، پھر صرف اردو میں جواب جاری رکھیں۔
""".strip()

    return """
Language mode (STRICT):
- Respond only in English.
- Do not use Urdu script or Roman Urdu.
- If the participant speaks Urdu or another language, briefly ask them to continue in English, then continue the debate in English only.
""".strip()


def build_system_prompt(
    user_name: str,
    topic: TopicProfile,
    user_stance: UserStance,
    language: DebateLanguage,
) -> str:
    ai_stance = ai_stance_from_user_stance(user_stance)
    user_stance_text = describe_user_stance(user_stance)
    language_block = _language_block(language)
    return f"""
You are a professional live debater in front of an audience.

Persona:
- You are {topic.persona}.
- Debate topic: "{topic.title}".
- Human participant stance: {user_stance_text}.
- Your stance is strictly {ai_stance}, opposite to the participant.
- Selected debate language: {language.upper()}.
- Core framing: {topic.framing}

{language_block}

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
