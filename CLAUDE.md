# Claude Code Game

Interactive course for learning Claude Code through hands-on exercises. Runs locally via `npx claude-code-game`.

## Stack

- **Server**: Node.js + Express + node-pty + WebSocket (`server/`)
- **Frontend**: React + TypeScript + Vite (`frontend/`)
- **Worker**: Cloudflare Worker for auth + leaderboard (`worker/`)
- **Levels**: Course content in `server/levels/XX-name/` directories

## Commands

```bash
# Run (end user)
npx claude-code-game

# Dev
cd server && npm run dev        # Express server with tsx watch
cd frontend && npm run dev      # Vite dev server

# Build
cd server && npm run build      # Compile TS -> dist/
cd frontend && npm run build    # Build React app

# Copy built frontend into server (required for local server testing)
rm -r server/frontend; cp -r frontend/dist server/frontend

# Package
cd server && npm pack           # Create tarball for testing
```

## Verification (run before committing)

1. `cd server && npx tsc --noEmit` — fix type errors
2. `cd frontend && npx tsc --noEmit` — fix type errors
3. `cd server && npm pack --dry-run` — verify package contents, < 5MB

## Architecture

```
Browser (xterm.js) -> ws://localhost:3000/ws/terminal/{session_id} -> node-pty (local shell)
```

The server spawns a local PTY (bash) per session. The browser connects via WebSocket and sends/receives terminal data directly. No Docker, no containers.

Key files:
- `server/src/cli.ts` — CLI entry point (`npx claude-code-game`)
- `server/src/server.ts` — Express server setup, static file serving
- `server/src/routes/sessions.ts` — Session management, PTY lifecycle, WebSocket handling
- `server/src/routes/levels.ts` — Level loading from YAML
- `server/src/verification.ts` — Exercise completion checking
- `server/src/terminal.ts` — PTY spawning
- `frontend/src/components/Terminal.tsx` — xterm.js terminal component

## Lesson Structure

Each lesson lives in `server/levels/XX-name/`:
```
server/levels/01-context-is-everything/
├── lesson.yaml      # Content + verification rules
└── exercise/        # Files copied to user's workspace
```

The `number:` field in `lesson.yaml` must match the directory prefix (`01-` = `number: 1`).

Verification rule types: `file_contains`, `min_user_messages`, `command_output`, `glob_exists`

## Don't

- Don't commit `server/dist/` or `server/frontend/` — they are build artifacts
- Don't edit levels without testing — run the server and verify the lesson loads
- Don't use zsh-specific syntax in terminal.ts — PTY is hardcoded to bash

## Debugging Tips

- **Terminal blank?** Check browser console for WebSocket errors
- **PTY not spawning?** Check that bash is available at `/bin/bash` or `/usr/bin/bash`
- **Levels not loading?** Verify path resolution — levels are at `server/levels/`, resolved via `__dirname` in levels.ts
