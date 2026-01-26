# Claude Code Game

An interactive terminal-based game that teaches Claude Code through hands-on practice in a sandboxed environment.

## Architecture

- **Frontend**: React + Vite + xterm.js for terminal UI
- **Backend**: Python/FastAPI for game logic and WebSocket terminal
- **Sandbox**: Modal for isolated Claude Code environments (or local PTY for development)
- **Verification**: Parses Claude's session logs (messages.jsonl) to verify level completion

## Project Structure

```
├── backend/           # FastAPI backend
│   └── app/
│       ├── api/       # WebSocket terminal endpoint
│       ├── models/    # Level and verification models
│       └── services/  # Sandbox, verification, watcher services
├── frontend/          # React + xterm.js frontend
├── levels/
│   ├── definitions/   # YAML level definitions
│   └── starter-app/   # Todo app with intentional bug
├── spike/             # Validation spikes for Modal/ttyd
└── docs/plans/        # Implementation plans
```

## Development

### Backend

```bash
cd backend
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```

### Frontend

```bash
cd frontend
npm install
npm run dev
```

Open http://localhost:5173 to play.

## Game Flow

1. User enters API key and starts session
2. Backend creates sandbox (Modal or local PTY)
3. Frontend connects via WebSocket to terminal
4. User interacts with Claude Code to complete level objectives
5. Watcher polls messages.jsonl to detect completion
6. Level advances when verification rules pass

## Levels

| # | Title | Objective |
|---|-------|-----------|
| 1 | Your First Conversation | Chat with Claude |
| 2 | Reading Code | Have Claude read a file |
| 3 | Fix a Bug | Have Claude edit a file |
| 4 | Run Tests | Have Claude run tests |

## License

MIT
