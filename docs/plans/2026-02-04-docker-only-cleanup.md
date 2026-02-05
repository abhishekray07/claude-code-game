# Docker-Only Cleanup Plan

**Date:** 2026-02-04
**Goal:** Remove Modal, Fly, and Local PTY code. Simplify codebase to Docker-only sandbox mode.

## Summary

The codebase currently supports 4 deployment modes (Local PTY, Docker, Modal, Fly). This cleanup removes everything except Docker mode, hardcoding it as the only option.

## Files to Delete

### Backend Services (5 files)
- `backend/app/services/local_sandbox.py` - PTY sandbox
- `backend/app/services/sandbox.py` - Modal sandbox
- `backend/app/services/fly_sandbox.py` - Fly sandbox
- `backend/app/services/session_manager.py` - Modal/Fly session manager
- `backend/app/services/modal_config.py` - Modal image config

### Backend APIs (3 files)
- `backend/app/api/terminal.py` - Local WebSocket proxy
- `backend/app/api/modal_terminal.py` - Modal WebSocket proxy
- `backend/app/api/fly_terminal.py` - Fly WebSocket proxy

### Untracked Cloud Files (6 items)
- `fly.toml`
- `fly-sandbox.toml`
- `fly-sandbox/` (directory)
- `fly-test/` (directory)
- `backend/scripts/setup_modal_secrets.sh`
- `backend/modal_app.py`

### Planning Docs (2 files)
- `docs/plans/2026-01-30-modal-deployment.md`
- `docs/plans/2026-01-31-modal-websocket-proxy.md`

### Stray Files
- `backend/Untitled`

## Files to Modify

### `backend/app/config.py`
- Remove `sandbox_mode` setting entirely
- Remove any Modal/Fly-specific config

### `backend/app/main.py`
- Remove conditional routing logic
- Directly import and include `docker_terminal` router
- Remove Modal/Fly startup/shutdown lifecycle code

### `backend/.gitignore`
- Add `.playwright-mcp/`
- Ensure `.env` is ignored

### Dependencies
- Remove `modal` from requirements if present

## Files to Keep

### Core Docker Infrastructure
- `backend/app/services/docker_sandbox.py` - Container lifecycle
- `backend/app/services/sandbox_manager.py` - Session management
- `backend/app/api/docker_terminal.py` - REST API endpoints

### Sandbox Image
- `sandbox/Dockerfile`
- `sandbox/entrypoint.sh`

### Shared Code
- `backend/app/services/verification.py`
- `backend/app/services/levels.py`
- `backend/app/api/levels.py`

### Useful Untracked Files
- `backend/.env.example`
- `frontend/.env.example`
- `backend/Dockerfile`
- `.dockerignore`
- `frontend/vercel.json`

## Implementation Order

1. Delete files from deletion list
2. Modify `config.py` - remove `sandbox_mode`
3. Simplify `main.py` - direct Docker router inclusion
4. Update `.gitignore`
5. Clean up dependencies
6. Test backend startup and sandbox creation
7. Commit: "chore: remove Modal/Fly/Local code, simplify to Docker-only"

## Decision Log

- Keep `docker_` prefix on files for clarity about contents
- Delete planning docs rather than archive
- Hardcode Docker mode rather than keep config switching infrastructure
