from __future__ import annotations

import json
import logging
import re
from pathlib import Path
from typing import Literal
from uuid import uuid4

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from livekit import api
from livekit.api.twirp_client import TwirpError, TwirpErrorCode
from livekit.protocol.agent_dispatch import CreateAgentDispatchRequest
from livekit.protocol.room import CreateRoomRequest
from pydantic import BaseModel, Field

from app.config import load_settings
from app.topics import list_topics, topic_exists

logger = logging.getLogger("debate.api")
settings = load_settings()

app = FastAPI(title="AI vs Human Debate API")

PROJECT_ROOT = Path(__file__).resolve().parent.parent
FRONTEND_DIR = PROJECT_ROOT / "frontend"
AI_ICON_PATH = PROJECT_ROOT / "Adobe Express - file.png"
app.mount("/static", StaticFiles(directory=FRONTEND_DIR), name="static")

_NAME_SANITIZER = re.compile(r"\s+")


class TokenRequest(BaseModel):
    name: str = Field(min_length=1, max_length=60)
    topic_id: str
    user_stance: Literal["agree", "disagree"]
    room_name: str | None = None


class TokenResponse(BaseModel):
    token: str
    livekit_url: str
    room_name: str
    identity: str
    agent_name: str


def _sanitize_name(name: str) -> str:
    collapsed = _NAME_SANITIZER.sub(" ", name).strip()
    return collapsed[:60] or "Guest Debater"


def _build_room_name(topic_id: str) -> str:
    safe_topic = re.sub(r"[^a-z0-9-]", "-", topic_id.lower())
    safe_topic = safe_topic.strip("-") or "debate"
    return f"{safe_topic}-{uuid4().hex[:8]}"


async def _ensure_room_and_dispatch(room_name: str, metadata_json: str) -> None:
    async with api.LiveKitAPI(
        url=settings.livekit_server_url,
        api_key=settings.livekit_api_key,
        api_secret=settings.livekit_api_secret,
    ) as lkapi:
        try:
            await lkapi.room.create_room(CreateRoomRequest(name=room_name, empty_timeout=600))
        except TwirpError as exc:
            if exc.code != TwirpErrorCode.ALREADY_EXISTS:
                raise

        dispatches = await lkapi.agent_dispatch.list_dispatch(room_name)
        existing = next((item for item in dispatches if item.agent_name == settings.agent_name), None)
        if existing is None:
            await lkapi.agent_dispatch.create_dispatch(
                CreateAgentDispatchRequest(
                    agent_name=settings.agent_name,
                    room=room_name,
                    metadata=metadata_json,
                )
            )


@app.on_event("startup")
async def validate_environment() -> None:
    settings.validate_for_api()


@app.get("/")
async def index() -> FileResponse:
    return FileResponse(FRONTEND_DIR / "index.html")


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/ai-icon")
async def ai_icon() -> FileResponse:
    if not AI_ICON_PATH.exists():
        raise HTTPException(status_code=404, detail="AI icon not found")
    return FileResponse(AI_ICON_PATH)


@app.get("/topics")
async def topics() -> dict[str, list[dict[str, str]]]:
    return {"topics": list_topics()}


@app.post("/token", response_model=TokenResponse)
async def create_token(payload: TokenRequest) -> TokenResponse:
    if not topic_exists(payload.topic_id):
        raise HTTPException(status_code=422, detail="Invalid topic_id")

    user_name = _sanitize_name(payload.name)
    room_name = payload.room_name or _build_room_name(payload.topic_id)
    identity = f"human-{uuid4().hex[:12]}"

    metadata_json = json.dumps(
        {
            "name": user_name,
            "topic_id": payload.topic_id,
            "user_stance": payload.user_stance,
            "max_turns": settings.max_human_turns,
        }
    )

    try:
        await _ensure_room_and_dispatch(room_name=room_name, metadata_json=metadata_json)
    except TwirpError as exc:
        logger.exception("LiveKit API failure while creating room/dispatch")
        raise HTTPException(
            status_code=502,
            detail=f"LiveKit API error ({exc.code}): {exc.message}",
        ) from exc

    jwt = (
        api.AccessToken(settings.livekit_api_key, settings.livekit_api_secret)
        .with_identity(identity)
        .with_name(user_name)
        .with_metadata(metadata_json)
        .with_attributes({"topic_id": payload.topic_id, "user_stance": payload.user_stance})
        .with_grants(
            api.VideoGrants(
                room_join=True,
                room=room_name,
                can_publish=True,
                can_subscribe=True,
                can_publish_data=True,
            )
        )
        .to_jwt()
    )

    return TokenResponse(
        token=jwt,
        livekit_url=settings.livekit_url,
        room_name=room_name,
        identity=identity,
        agent_name=settings.agent_name,
    )
