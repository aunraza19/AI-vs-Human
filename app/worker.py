from __future__ import annotations

import asyncio
import contextlib
import json
import logging

from livekit import rtc
from livekit.agents import (
    AgentSession,
    AutoSubscribe,
    JobContext,
    WorkerOptions,
    cli,
)
from livekit.plugins import google, silero

from app.config import load_settings
from app.debate_agent import DebateAgent
from app.prompting import (
    DebateLanguage,
    UserStance,
    build_system_prompt,
    wants_to_end_debate,
)
from app.state_machine import DebateStage, DebateState
from app.topics import TopicProfile, get_topic

logger = logging.getLogger("debate.worker")


def _parse_session_metadata(
    participant: rtc.RemoteParticipant, default_max_turns: int
) -> tuple[str, TopicProfile, UserStance, DebateLanguage, int]:
    metadata: dict[str, object] = {}
    if participant.metadata:
        try:
            payload = json.loads(participant.metadata)
            if isinstance(payload, dict):
                metadata = payload
        except json.JSONDecodeError:
            logger.warning("Participant metadata is not valid JSON; using defaults.")

    raw_name = str(metadata.get("name") or participant.name or "Guest Debater").strip()
    user_name = (raw_name or "Guest Debater")[:60]

    topic = get_topic(str(metadata.get("topic_id", "")))
    raw_user_stance = str(metadata.get("user_stance", "disagree")).strip().lower()
    user_stance: UserStance = "agree" if raw_user_stance == "agree" else "disagree"
    raw_language = str(metadata.get("language", "english")).strip().lower()
    language: DebateLanguage = "urdu" if raw_language == "urdu" else "english"

    max_turns = metadata.get("max_turns", default_max_turns)
    if isinstance(max_turns, int):
        parsed_max_turns = max_turns
    elif isinstance(max_turns, str) and max_turns.isdigit():
        parsed_max_turns = int(max_turns)
    else:
        parsed_max_turns = default_max_turns

    parsed_max_turns = min(max(parsed_max_turns, 3), 20)
    return user_name, topic, user_stance, language, parsed_max_turns


def _build_session(
    *,
    instructions: str,
    model: str,
    voice: str,
    google_api_key: str,
    loop: asyncio.AbstractEventLoop,
) -> AgentSession:
    return AgentSession(
        llm=google.realtime.RealtimeModel(
            model=model,
            voice=voice,
            temperature=0.7,
            modalities=["AUDIO"],
            instructions=instructions,
            proactivity=True,
            api_key=google_api_key,
        ),
        vad=silero.VAD.load(
            sample_rate=16000,
            activation_threshold=0.65,
            min_speech_duration=0.08,
            min_silence_duration=0.3,
            prefix_padding_duration=0.2,
        ),
        turn_handling={
            "turn_detection": "realtime_llm",
            "endpointing": {"min_delay": 0.35, "max_delay": 1.5},
            "interruption": {
                "enabled": True,
                "mode": "vad",
                "min_duration": 0.2,
                "min_words": 0,
            },
        },
        preemptive_generation=False,
        loop=loop,
    )


async def entrypoint(ctx: JobContext) -> None:
    settings = load_settings()
    settings.validate_for_agent()

    await ctx.connect(auto_subscribe=AutoSubscribe.AUDIO_ONLY)
    try:
        participant = await ctx.wait_for_participant(
            kind=rtc.ParticipantKind.PARTICIPANT_KIND_STANDARD
        )
    except RuntimeError as exc:
        if "room disconnected while waiting for participant" in str(exc).lower():
            logger.warning("Room disconnected before participant joined; closing job cleanly.")
            return
        raise

    user_name, topic, user_stance, language, max_turns = _parse_session_metadata(
        participant, settings.max_human_turns
    )
    state = DebateState(max_human_turns=max_turns)

    logger.info(
        "Starting debate room=%s participant=%s topic=%s user_stance=%s language=%s max_turns=%s",
        ctx.room.name,
        participant.identity,
        topic.topic_id,
        user_stance,
        language,
        max_turns,
    )

    base_prompt = build_system_prompt(
        user_name=user_name,
        topic=topic,
        user_stance=user_stance,
        language=language,
    )
    agent = DebateAgent(instructions=base_prompt, state=state, topic=topic)
    session = _build_session(
        instructions=base_prompt,
        model=settings.gemini_model,
        voice=settings.gemini_voice,
        google_api_key=settings.google_api_key,
        loop=asyncio.get_running_loop(),
    )

    session_finished = asyncio.Event()
    shutdown_requested = False

    def request_shutdown(reason: str) -> None:
        nonlocal shutdown_requested
        if shutdown_requested:
            return
        shutdown_requested = True
        logger.info("Shutting down debate session: %s", reason)
        session_finished.set()
        ctx.shutdown(reason)

    async def on_ctx_shutdown(reason: str = "") -> None:
        logger.info("Job shutdown callback invoked: %s", reason)
        session_finished.set()

    ctx.add_shutdown_callback(on_ctx_shutdown)

    async def end_debate(reason: str, _transcript: str) -> None:
        if state.end_requested:
            return
        state.end_requested = True
        state.transition(DebateStage.END)

        logger.info("Ending debate: %s", reason)

        await session.wait_for_inactive()
        request_shutdown("Debate complete")

    @session.on("user_state_changed")
    def on_user_state_changed(event) -> None:  # type: ignore[no-untyped-def]
        if event.new_state == "speaking" and session.agent_state == "speaking":
            logger.info("Human barge-in detected; interrupting AI speech now.")
            interrupt_future = session.interrupt()

            def on_interrupt_done(fut: asyncio.Future[None]) -> None:
                if fut.cancelled():
                    return
                exc = fut.exception()
                if exc is not None:
                    logger.warning("Interrupt call failed: %s", exc)

            interrupt_future.add_done_callback(on_interrupt_done)

    @session.on("agent_state_changed")
    def on_agent_state_changed(event) -> None:  # type: ignore[no-untyped-def]
        if (
            state.stage == DebateStage.AI_INTRO
            and event.old_state == "speaking"
            and event.new_state in ("listening", "idle")
        ):
            state.transition(DebateStage.USER_INTRO)
            logger.info("State transition: AI_INTRO -> USER_INTRO")

    @session.on("user_input_transcribed")
    def on_user_input_transcribed(event) -> None:  # type: ignore[no-untyped-def]
        if not event.is_final:
            return

        transcript = event.transcript.strip()
        if not transcript:
            return

        logger.info("Final transcript: %s", transcript)

    @session.on("conversation_item_added")
    def on_conversation_item_added(event) -> None:  # type: ignore[no-untyped-def]
        item = event.item
        role = getattr(item, "role", None)
        transcript = getattr(item, "text_content", "").strip()

        if role != "user" or not transcript:
            return

        async def handle_user_turn() -> None:
            if state.stage == DebateStage.END:
                return

            turn_number = state.register_human_turn()
            logger.info("User turn %s transcript: %s", turn_number, transcript)

            if state.stage in (DebateStage.AI_INTRO, DebateStage.USER_INTRO):
                previous_stage = state.stage
                state.transition(DebateStage.DEBATE_LOOP)
                logger.info("State transition: %s -> DEBATE_LOOP", previous_stage.value)

            if wants_to_end_debate(transcript):
                await end_debate("the participant requested to stop", transcript)
                return

            if state.should_end_for_turn_limit():
                await end_debate(
                    f"the maximum turn limit ({state.max_human_turns}) was reached",
                    transcript,
                )

        asyncio.create_task(handle_user_turn())

    @session.on("close")
    def on_session_close(_event) -> None:  # type: ignore[no-untyped-def]
        session_finished.set()

    @ctx.room.on("participant_disconnected")
    def on_participant_disconnected(remote: rtc.RemoteParticipant) -> None:
        if remote.identity == participant.identity:
            request_shutdown("Human participant disconnected")

    try:
        await session.start(agent=agent, room=ctx.room)
        state.transition(DebateStage.AI_INTRO)
        logger.info("State transition: INIT -> AI_INTRO")

        await session_finished.wait()
    finally:
        with contextlib.suppress(Exception):
            await session.aclose()


def main() -> None:
    settings = load_settings()
    cli.run_app(
        WorkerOptions(
            entrypoint_fnc=entrypoint,
            agent_name=settings.agent_name,
            ws_url=settings.livekit_server_url,
            api_key=settings.livekit_api_key,
            api_secret=settings.livekit_api_secret,
        )
    )


if __name__ == "__main__":
    main()
