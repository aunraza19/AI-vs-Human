# AI vs Human Debate System

Real-time debate app based on the required architecture:

Frontend (mic/speaker UI) -> LiveKit -> Python LiveKit Agent -> Gemini Live RealtimeModel

## What is implemented

- LiveKit Agents backend with Gemini Live Realtime model (`gemini-3.1-flash-live-preview`)
- Topic-based personas and strict debate prompt injection
- Bilingual debate mode (English/Urdu) with strict language enforcement in system prompts
- Debate state machine:
  - `INIT -> AI_INTRO -> USER_INTRO -> DEBATE_LOOP -> END`
- Human interruption (barge-in) handling during AI speech
- Silero VAD configuration tuned for noisy environments
- FastAPI token/room/dispatch service for frontend connection
- Browser UI for name entry, 5 topic selection, mic input, and speaker output

## Run with Docker Compose (all services together)

1. Copy env file:
   ```bash
   cp .env.example .env
   ```
2. Update `.env`:
   - set `GOOGLE_API_KEY`
   - set a strong `LIVEKIT_API_SECRET` (32+ chars)
   - keep:
     - `LIVEKIT_URL=ws://localhost:7880` (browser)
     - `LIVEKIT_SERVER_URL=ws://livekit:7880` (internal container network)
3. Start everything:
   ```bash
   docker compose up --build
   ```
4. Open:
   - `http://localhost:8000`

If you open the frontend from another device, set:

- `LIVEKIT_NODE_IP=<your-host-lan-ip>`
- `LIVEKIT_URL=ws://<your-host-lan-ip>:7880`

## Run without Docker

1. Install dependencies:
```bash
pip install -r requirements.txt
```
2. Make sure a LiveKit server is running (local Docker example):
```bash
docker run --rm -p 7880:7880 -p 7881:7881 -p 7882:7882/udp \
  -e LIVEKIT_KEYS="$LIVEKIT_API_KEY: $LIVEKIT_API_SECRET" \
  livekit/livekit-server:v1.10 --dev --bind 0.0.0.0 --node-ip 127.0.0.1
```
3. Run worker:
```bash
python -m app.worker dev
```
4. Run API + frontend server:
```bash
uvicorn app.api:app --reload --port 8000
```
5. Open:
   - `http://localhost:8000`

## Notes

- The API endpoint creates a room and explicit dispatch for `AGENT_NAME`.
- Frontend calls `/token`, connects to LiveKit, publishes mic audio, and plays AI audio.
- Session ends when the participant asks to stop or when `MAX_HUMAN_TURNS` is reached.
