# Claude Code Game

Interactive course for learning Claude Code through hands-on exercises.

## Stack

- **Frontend**: React + TypeScript + Vite (`frontend/`)
- **Backend**: FastAPI + Python (`backend/`)
- **Sandbox**: Docker container (`claude-game-sandbox`) with ttyd 1.7.7 terminal
- **Levels**: Course content in `levels/XX-name/` directories

## Commands

```bash
# Dev
cd backend && SANDBOX_MODE=docker uvicorn app.main:app --reload --port 8080
cd frontend && npm run dev

# Test
cd backend && pytest

# Rebuild sandbox (REQUIRED after changing levels/ or sandbox/)
docker build -t claude-game-sandbox:latest -f sandbox/Dockerfile .

# Verify sandbox works
docker run --rm -d --name test-sandbox -p 7777:7681 -e LEVEL_NUMBER=1 claude-game-sandbox:latest
curl -s -o /dev/null -w "%{http_code}" http://127.0.0.1:7777/  # Should return 200
docker stop test-sandbox
```

## Verification (run before committing)

1. `cd backend && pytest` — fix failing tests
2. `cd frontend && npx tsc --noEmit` — fix type errors
3. If sandbox files changed: rebuild image and verify with curl check above

## Architecture: Terminal WebSocket Proxy

```
Browser (xterm.js) → ws://backend:8080/ws/terminal/{session_id} → ws://container:{port}/ws (ttyd)
```

The backend proxies WebSocket between the browser and ttyd inside each Docker container. This is required for VPS deployment where containers aren't directly reachable from the browser.

Key files: `backend/app/api/docker_terminal.py`, `frontend/src/components/Terminal.tsx`

## Don't

- Don't use Ubuntu's `apt install ttyd` — it's 1.6.3 which crashes (SIGSEGV) on WebSocket connections. Use the binary from GitHub releases with SHA256 verification (see Dockerfile).
- Don't send messages to ttyd without the auth handshake first — ttyd 1.7.x requires `{"AuthToken":""}` as the first WebSocket message, even when no auth is configured.
- Don't look for ttyd output on message type `1` (49) — ttyd 1.7.x changed the protocol: output is type `0` (48), title is `1` (49), preferences is `2` (50).
- Don't forget `-W` flag when starting ttyd — since 1.7.4, terminals are readonly by default.
- Don't modify files in `levels/` without rebuilding the sandbox image — they are baked into the Docker image at build time.

## Sandbox Image: Baked-In Levels

The `levels/` directory is copied into the Docker image at build time (`sandbox/Dockerfile`). When you modify any files in `levels/`, you MUST rebuild:

```bash
docker build -t claude-game-sandbox:latest -f sandbox/Dockerfile .
```

## Lesson Structure

Each lesson lives in `levels/XX-name/`:
```
levels/01-context-is-everything/
├── lesson.yaml      # Content + verification rules
└── exercise/        # Files copied to sandbox workspace
```

The `number:` field in `lesson.yaml` must match the directory prefix (`01-` = `number: 1`).

Verification rule types: `file_contains`, `min_user_messages`, `command_output`, `glob_exists`

## Debugging Tips

- **Terminal blank?** Check browser console for WebSocket errors. Verify container is running: `docker ps --filter "name=sandbox-"`
- **Container crashes immediately?** Check `docker events --since 2m` for exit codes. Exit 139 = SIGSEGV (ttyd version issue).
- **WebSocket connects but no output?** Likely missing auth handshake or wrong message type parsing. Test directly: see `backend/app/api/docker_terminal.py` for the proxy code.
- **Stale lesson content?** Rebuild sandbox image. The levels are baked in at build time.
