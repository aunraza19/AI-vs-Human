# AI vs Human Debate System

Real-time debate app based on the required architecture:

Frontend (mic/speaker UI) -> LiveKit -> Python LiveKit Agent -> Gemini Live RealtimeModel

## What is implemented

- LiveKit Agents backend with Gemini Live Realtime model (`gemini-3.1-flash-live-preview`)
- Topic-based personas and strict debate prompt injection
- Debate state machine:
  - `INIT -> AI_INTRO -> USER_INTRO -> DEBATE_LOOP -> END`
- Human interruption (barge-in) handling during AI speech
- Silero VAD configuration tuned for noisy environments
- FastAPI token/room/dispatch service for frontend connection
- Browser UI for name entry, 5 topic selection, mic input, and speaker output

## Setup

1. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
2. Create env file:
   ```bash
   cp .env.example .env
   ```
3. Fill `.env` values:
   - `LIVEKIT_URL`
   - `LIVEKIT_API_KEY`
   - `LIVEKIT_API_SECRET`
   - `GOOGLE_API_KEY`

## Run

Run the agent worker:

```bash
python -m app.worker dev
```

Run the API + frontend server:

```bash
uvicorn app.api:app --reload --port 8000
```

Open:

`http://localhost:8000`

## Notes

- The API endpoint creates a room and explicit dispatch for `AGENT_NAME`.
- Frontend calls `/token`, connects to LiveKit, publishes mic audio, and plays AI audio.
- Session ends when the participant asks to stop or when `MAX_HUMAN_TURNS` is reached.
