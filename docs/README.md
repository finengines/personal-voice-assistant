# Personal Voice Assistant – Detailed Guide

This guide complements the root `README.md` with deeper details for setup, services, and troubleshooting. The stack consists of a React + Vite frontend (served by Nginx in Docker), multiple FastAPI services (Auth, MCP, Presets, Global Settings), a simple token server for LiveKit access, PostgreSQL for persistence, and a LiveKit server (dev-only container).

## Quick Start (Docker, recommended)

1) Prepare environment:
```bash
cp env.example .env
./scripts/setup_auth.sh   # generates strong JWT + encryption keys, validates required vars
```

2) Start services:
```bash
docker compose up -d
```

3) Open the app and login:
- UI: http://localhost:8080
- Login with `ADMIN_EMAIL` / `ADMIN_PASSWORD` from `.env`

4) Voice flow:
- Open Voice tab → Settings → Generate Token → Connect → allow microphone

## Services and Ports (development)

- Frontend (Nginx): `http://localhost:8080`
  - Routes to backend APIs based on `frontend/src/config.js`
- Auth API: `http://localhost:8001` (docs at `/docs`, health at `/auth/health`)
- MCP API: `http://localhost:8082` (health at `/health`)
- Preset API: `http://localhost:8083` (health at `/health`)
- Global Settings API: `http://localhost:8084` (health at `/health`)
- Token Server: `http://localhost:8081/health`
- LiveKit (dev): `ws://localhost:7883` (exposed from `livekit` container)

All services are orchestrated by `backend/start_all.py` in the backend container.

## Environment Variables

Set via `.env` (see `env.example` for the full list). Critical:
- `OPENAI_API_KEY`, `DEEPGRAM_API_KEY`
- `JWT_SECRET`, `API_KEY_ENCRYPTION_KEY` (use `scripts/setup_auth.sh` to generate)
- `ADMIN_EMAIL`, `ADMIN_PASSWORD`
- Optional providers: `ELEVENLABS_API_KEY`, `CARTESIA_API_KEY`, `GROQ_API_KEY`, `ANTHROPIC_API_KEY`, `OPENROUTER_API_KEY`

Container-specific defaults exist in `docker-compose.yml` environment sections.

## MCP Integration

- Manage servers via MCP API (`/servers`, `/servers/{id}/start|stop|restart`, `/tools`) or UI (MCP tab)
- Supported types: SSE, HTTP (streamable), OpenAI Tools format, STDIO
- Auth modes: none, bearer, API key, basic, custom header
- On startup, the manager initializes and can auto-start enabled servers

Health and status:
```bash
curl http://localhost:8082/health
curl http://localhost:8082/servers
curl http://localhost:8082/tools
```

## Database

PostgreSQL is used for persistence (e.g., MCP configs). Initialization uses `backend/core/init.sql` and ORM table creation on app start. For migration/verification helpers inside Docker, see `scripts/setup_database.sh`.

## Running Without Docker (advanced)

Backend:
```bash
python -m venv .venv && source .venv/bin/activate
pip install -r backend/requirements/requirements-agent.txt \
            -r backend/requirements/requirements-db.txt \
            -r backend/requirements/requirements-mcp.txt
cd backend
python start_all.py
```

Token server (another shell):
```bash
python backend/utils/simple_token_server.py
```

Frontend:
```bash
cd frontend
npm install
npm run dev
```

LiveKit:
- Use dev container: `docker compose up -d livekit`
- Or configure `LIVEKIT_URL`, `LIVEKIT_API_KEY`, `LIVEKIT_API_SECRET` to use LiveKit Cloud

## Troubleshooting

- Mic access: Use HTTPS or `localhost`; ensure browser permissions are granted
- Token errors: Check token server at `http://localhost:8081/health`
- Service health: `/health` endpoints listed above, and backend container logs
- MCP not responding: ensure backend container is healthy; check `/health` and container logs
- LiveKit connection: verify `ws://localhost:7883` (dev) or your external `LIVEKIT_URL`

Common checks:
```bash
docker compose logs -f backend
docker compose logs -f token-server
docker compose ps
```

## Production (docker-compose.prod.yml)

- Expects an external LiveKit (e.g., LiveKit Cloud) and no host port exposure (platform routes traffic)
- Set all secrets in `.env`
- Bring up:
```bash
docker compose -f docker-compose.prod.yml up -d --build
```

## References

- Frontend config routing: `frontend/src/config.js`
- Orchestrator: `backend/start_all.py`
- MCP API: `backend/api/mcp_api.py`
- Auth startup: `backend/start_simple_auth_server.py`
- Preset API: `backend/start_preset_server.py`
- Global Settings API: `backend/start_global_settings_api.py`
- Token server: `backend/utils/simple_token_server.py`