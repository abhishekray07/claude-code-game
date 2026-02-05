# Docker-Only Cleanup Plan

**Date:** 2026-02-04
**Goal:** Remove Modal, Fly, and Local PTY code. Simplify codebase to Docker-only sandbox mode.
**Reviewed by:** Codex (2026-02-04)

## Summary

The codebase currently supports 4 deployment modes (Local PTY, Docker, Modal, Fly). This cleanup removes everything except Docker mode, hardcoding it as the only option.

## Files to Delete

### Backend Services (6 files)
- `backend/app/services/local_sandbox.py` - PTY sandbox
- `backend/app/services/sandbox.py` - Modal sandbox
- `backend/app/services/fly_sandbox.py` - Fly sandbox
- `backend/app/services/session_manager.py` - Modal/Fly session manager
- `backend/app/services/modal_config.py` - Modal image config
- `backend/app/services/watcher.py` - GameWatcher (only used by local/modal)

### Backend APIs (4 files)
- `backend/app/api/terminal.py` - Local WebSocket proxy
- `backend/app/api/modal_terminal.py` - Modal WebSocket proxy
- `backend/app/api/fly_terminal.py` - Fly WebSocket proxy
- `backend/app/api/sessions.py` - Modal sessions API (depends on deleted code)

### Backend Test/Script Files
- `backend/test_modal_auth.py`
- `backend/scripts/deploy.sh`
- `backend/scripts/test_ws_proxy.py`
- `backend/scripts/test_exec.py`
- `backend/scripts/setup_modal_secrets.sh`
- `backend/modal_app.py`

### Spike Directory
- `spike/` - Modal-specific experiments (entire directory)

### Untracked Cloud Files
- `fly.toml`
- `fly-sandbox.toml`
- `fly-sandbox/` (directory)
- `fly-test/` (directory)

### Planning Docs (2 files)
- `docs/plans/2026-01-30-modal-deployment.md`
- `docs/plans/2026-01-31-modal-websocket-proxy.md`

### Stray Files
- `backend/Untitled`

## Files to Modify

### Backend

**`backend/app/config.py`:**
- Remove `sandbox_mode` setting entirely
- Remove any Modal/Fly-specific config

**`backend/app/main.py`:**
- Remove conditional routing logic
- Directly import and include `docker_terminal` router
- Remove Modal/Fly startup/shutdown lifecycle code
- Stop logging `sandbox_mode`
- Always start/stop `sandbox_manager` unconditionally

**`backend/app/api/__init__.py`:**
- Remove imports of deleted modules (`terminal.py`)

**`backend/app/services/__init__.py`:**
- Remove imports of deleted modules (`local_sandbox.py`, etc.)

**`backend/.gitignore`:**
- Add `.playwright-mcp/`
- Ensure `.env` is ignored

**`backend/pyproject.toml`:**
- Remove `modal` dependency
- Remove `httpx` dependency (if only used by Fly)
- Remove `websockets` dependency (if only used by local/modal)
- Remove `wsproto` dependency (if only used by local/modal)

**`backend/.env.example`:**
- Remove Modal/Fly environment variables

### Frontend

**`frontend/src/config.ts`:**
- Remove `terminalMode` configuration
- Hardcode Docker endpoints

**`frontend/src/App.tsx`:**
- Remove mode branching logic
- Simplify to Docker-only paths

**`frontend/src/components/Terminal.tsx`:**
- Remove WebSocket terminal code paths
- Keep only iframe/Docker terminal
- Remove `ttydToken` gating (unused in Docker mode)

**`frontend/src/hooks/useVerificationProgress.ts`:**
- Remove mode-specific branching

**`frontend/.env.example`:**
- Remove Modal/Fly environment variables

**`frontend/package.json`:**
- Consider removing `@xterm/*` packages if WebSocket terminal is fully removed

### Documentation

**`README.md`:**
- Update to describe Docker-only setup
- Remove Modal/Fly/local instructions

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
- `backend/.env.example` (after updating)
- `frontend/.env.example` (after updating)
- `backend/Dockerfile`
- `.dockerignore`
- `frontend/vercel.json`

## Implementation Order

### Phase 1: Backend Cleanup
1. Delete backend files from deletion list
2. Update `backend/app/api/__init__.py` - remove broken imports
3. Update `backend/app/services/__init__.py` - remove broken imports
4. Modify `config.py` - remove `sandbox_mode`
5. Simplify `main.py` - direct Docker router, unconditional sandbox_manager
6. Update `backend/.gitignore`
7. Clean up `backend/pyproject.toml` dependencies
8. Update `backend/.env.example`
9. Test backend startup

### Phase 2: Frontend Cleanup
10. Simplify `frontend/src/config.ts`
11. Simplify `frontend/src/App.tsx`
12. Simplify `frontend/src/components/Terminal.tsx`
13. Simplify `frontend/src/hooks/useVerificationProgress.ts`
14. Update `frontend/.env.example`
15. Consider removing `@xterm/*` from `package.json`
16. Test frontend

### Phase 3: Documentation & Finalization
17. Update `README.md`
18. Delete remaining untracked cloud files (fly.toml, fly-sandbox/, etc.)
19. Delete spike/ directory
20. End-to-end test: create sandbox, run level, verify progress
21. Commit: "chore: remove Modal/Fly/Local code, simplify to Docker-only"

## API Change Consideration

**Optional:** Flatten API from `/api/docker/sessions` to `/api/sessions` since Docker is now the only mode. This would require updating:
- `backend/app/api/docker_terminal.py` - change route prefix
- `frontend/src/config.ts` or API calls - update endpoint URLs

**Decision:** Defer for now, can do in a follow-up PR.

## Decision Log

- Keep `docker_` prefix on files for clarity about contents
- Delete planning docs rather than archive
- Hardcode Docker mode rather than keep config switching infrastructure
- Defer API path flattening to follow-up PR
- Remove unused dependencies to reduce bundle size
