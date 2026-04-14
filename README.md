# AI vs Human Debate

Real-time voice debate app for live society displays.  
A human participant debates an AI agent over selected topics, with strict turn flow, interruption support, and bilingual debating (English/Urdu).

## Overview

This project runs on:

`Frontend (Mic + Speaker UI) -> LiveKit (WebRTC) -> Python LiveKit Agent -> Gemini Live RealtimeModel`

The user enters name, selects topic, stance, and language, then starts a live audio debate.  
The AI always takes the opposite stance and responds in the selected language.

## Features

- Real-time speech-to-speech debate using `gemini-3.1-flash-live-preview`
- Self-hosted LiveKit (open source) support
- Topic-based debate personas (5 curated topics)
- User stance selection (`agree`/`disagree`) with enforced opposite AI stance
- Language selection (`english`/`urdu`) with strict language blocks in prompt logic
- Debate state machine: `INIT -> AI_INTRO -> USER_INTRO -> DEBATE_LOOP -> END`
- Human barge-in support while AI is speaking
- Turn limit control with graceful debate completion
- FastAPI token/room/dispatch backend
- Browser UI with live activity feed, AI speaking overlay, and ESC overlay minimize/restore

## Environment Variables

Copy `.env.example` to `.env` and set values:

- `LIVEKIT_URL`: URL returned to browser clients (example: `ws://localhost:7880`)
- `LIVEKIT_SERVER_URL`: URL used internally by API/worker to reach LiveKit
  - Docker Compose: `ws://livekit:7880`
  - Local host run: `ws://127.0.0.1:7880`
- `LIVEKIT_API_KEY`
- `LIVEKIT_API_SECRET` (use a strong 32+ character secret)
- `GOOGLE_API_KEY`
- Optional:
  - `AGENT_NAME` (default: `debate-agent`)
  - `GEMINI_MODEL` (default: `gemini-3.1-flash-live-preview`)
  - `GEMINI_VOICE` (default: `Puck`)
  - `MAX_HUMAN_TURNS` (default: `8`)

## Run with Docker Compose (Recommended)

1. Create env file:
```bash
cp .env.example .env
```

2. Update `.env` with your keys/secrets (especially `GOOGLE_API_KEY` and `LIVEKIT_API_SECRET`).

3. Start all services:
```bash
docker compose up --build
```

4. Open:

`http://localhost:8000`

If `7880` is already in use, stop the existing LiveKit container/process first.

If frontend is opened from another device on LAN, set:

- `LIVEKIT_NODE_IP=<host-lan-ip>`
- `LIVEKIT_URL=ws://<host-lan-ip>:7880`

## Run Locally (Without Compose)

1. Install Python dependencies:
```bash
pip install -r requirements.txt
```

2. Start LiveKit (example via Docker):
```bash
docker run --rm -p 7880:7880 -p 7881:7881 -p 7882:7882/udp \
  -e LIVEKIT_KEYS="$LIVEKIT_API_KEY: $LIVEKIT_API_SECRET" \
  livekit/livekit-server:v1.10 --dev --bind 0.0.0.0 --node-ip 127.0.0.1
```

3. Start worker:
```bash
python -m app.worker dev
```

4. Start API/frontend server:
```bash
uvicorn app.api:app --reload --port 8000
```

5. Open:

`http://localhost:8000`

## Debate Behavior Notes

- API creates room + explicit agent dispatch for each session.
- Frontend calls `/token`, joins LiveKit, publishes mic audio, and plays AI audio.
- Session ends when participant asks to stop, disconnects, or max turn limit is reached.
