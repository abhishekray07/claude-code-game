# Claude Code Game

Interactive course for learning Claude Code through hands-on exercises.

## Architecture

- **Frontend**: React app in `frontend/`
- **Backend**: FastAPI in `backend/`
- **Sandbox**: Docker container (`claude-game-sandbox`) that runs student exercises
- **Levels**: Course content in `levels/XX-name/` directories

## Critical: Sandbox Image Contains Baked-In Levels

The `levels/` directory is **copied into the Docker image at build time** (see `sandbox/Dockerfile` line 26).

**When you modify any files in `levels/`**, you MUST rebuild the sandbox image:

```bash
docker build -t claude-game-sandbox:latest -f sandbox/Dockerfile .
```

Without rebuilding, the sandbox will use stale lesson content. This includes:
- Lesson YAML files (`lesson.yaml`)
- Exercise files (Python code, tests, etc.)
- Any new directories (like `docs/`)
- CLAUDE.md files in exercises

## Commands

- Run backend: `cd backend && uvicorn app.main:app --reload`
- Run frontend: `cd frontend && npm run dev`
- Rebuild sandbox: `docker build -t claude-game-sandbox:latest -f sandbox/Dockerfile .`
- Run tests: `cd backend && pytest`

## Lesson Structure

Each lesson lives in `levels/XX-name/`:
```
levels/01-context-is-everything/
├── lesson.yaml      # Lesson content, verification rules
└── exercise/        # Files copied to sandbox workspace
    ├── *.py         # Python exercise files
    ├── tests/       # pytest tests
    └── docs/        # Optional documentation
```

The `number:` field in `lesson.yaml` must match the directory prefix (`01-` = `number: 1`).

## Verification

Lessons use verification rules in `lesson.yaml` to check student progress:
- `file_contains`: Check if a file contains a pattern
- `min_user_messages`: Minimum messages sent to Claude
- `command_output`: Run a command and check output
- `glob_exists`: Check if files matching pattern exist
