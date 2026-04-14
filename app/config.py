from __future__ import annotations

import os
import re
from dataclasses import dataclass
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent

_ENV_KEY_PATTERN = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")


def _load_env_file(path: Path) -> None:
    if not path.exists():
        return

    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue

        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip()
        if not _ENV_KEY_PATTERN.match(key):
            continue

        if len(value) >= 2 and value[0] == value[-1] and value[0] in ("'", '"'):
            value = value[1:-1]

        os.environ.setdefault(key, value)


_load_env_file(PROJECT_ROOT / ".env")


@dataclass(frozen=True)
class Settings:
    livekit_url: str
    livekit_api_key: str
    livekit_api_secret: str
    google_api_key: str
    agent_name: str
    gemini_model: str
    gemini_voice: str
    max_human_turns: int

    def validate_for_api(self) -> None:
        missing: list[str] = []
        if not self.livekit_url:
            missing.append("LIVEKIT_URL")
        if not self.livekit_api_key:
            missing.append("LIVEKIT_API_KEY")
        if not self.livekit_api_secret:
            missing.append("LIVEKIT_API_SECRET")

        if missing:
            raise RuntimeError(f"Missing required environment variables: {', '.join(missing)}")

    def validate_for_agent(self) -> None:
        missing: list[str] = []
        if not self.livekit_url:
            missing.append("LIVEKIT_URL")
        if not self.livekit_api_key:
            missing.append("LIVEKIT_API_KEY")
        if not self.livekit_api_secret:
            missing.append("LIVEKIT_API_SECRET")
        if not self.google_api_key:
            missing.append("GOOGLE_API_KEY")

        if missing:
            raise RuntimeError(f"Missing required environment variables: {', '.join(missing)}")


def load_settings() -> Settings:
    max_turns_raw = os.getenv("MAX_HUMAN_TURNS", "8")
    try:
        max_human_turns = int(max_turns_raw)
    except ValueError:
        max_human_turns = 8

    max_human_turns = min(max(max_human_turns, 3), 20)

    return Settings(
        livekit_url=os.getenv("LIVEKIT_URL", "").strip(),
        livekit_api_key=os.getenv("LIVEKIT_API_KEY", "").strip(),
        livekit_api_secret=os.getenv("LIVEKIT_API_SECRET", "").strip(),
        google_api_key=os.getenv("GOOGLE_API_KEY", "").strip(),
        agent_name=os.getenv("AGENT_NAME", "debate-agent").strip() or "debate-agent",
        gemini_model=(
            os.getenv("GEMINI_MODEL", "gemini-3.1-flash-live-preview").strip()
            or "gemini-3.1-flash-live-preview"
        ),
        gemini_voice=os.getenv("GEMINI_VOICE", "Puck").strip() or "Puck",
        max_human_turns=max_human_turns,
    )
