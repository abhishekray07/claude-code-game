# Hetzner VPS Deployment Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Implement code changes needed for secure Hetzner VPS deployment with access code gating, container hardening, and session management.

**Architecture:** Single VPS running Docker containers per session, WebSocket proxy through FastAPI backend, Caddy for TLS, frontend access gate.

**Tech Stack:** FastAPI, Docker SDK for Python, React, Caddy

---

## Task 1: Add Access Code Validation to Docker Terminal API

**Files:**
- Modify: `backend/app/api/docker_terminal.py:22-25` (CreateSessionRequest model)
- Modify: `backend/app/api/docker_terminal.py:38-48` (create_session endpoint)
- Test: `backend/tests/test_docker_access_code.py` (new file)

**Step 1: Write the failing test**

Create `backend/tests/test_docker_access_code.py`:

```python
import pytest
from unittest.mock import patch, MagicMock
from fastapi.testclient import TestClient

# Mock settings before importing app
@pytest.fixture
def client_with_access_code():
    with patch("app.api.docker_terminal.settings") as mock_settings:
        mock_settings.demo_access_code = "secret123"
        mock_settings.sandbox_mode = "docker"
        from app.main import app
        yield TestClient(app)

@pytest.fixture
def client_no_access_code():
    with patch("app.api.docker_terminal.settings") as mock_settings:
        mock_settings.demo_access_code = ""
        mock_settings.sandbox_mode = "docker"
        from app.main import app
        yield TestClient(app)


def test_docker_session_rejects_invalid_access_code(client_with_access_code):
    """Should return 403 when access code is wrong."""
    response = client_with_access_code.post(
        "/api/docker/sessions",
        json={"level_number": 1, "access_code": "wrong"}
    )
    assert response.status_code == 403
    assert "Invalid access code" in response.json()["detail"]


def test_docker_session_accepts_valid_access_code(client_with_access_code):
    """Should accept request when access code matches."""
    with patch("app.api.docker_terminal.sandbox_manager") as mock_manager:
        mock_manager.create_session.return_value = {
            "session_id": "test-123",
            "port": 10001,
            "ttyd_token": "token123"
        }
        with patch("app.api.docker_terminal.get_level") as mock_level:
            mock_level.return_value = MagicMock(
                number=1, title="Test", content="Test content",
                model_dump=lambda: {"number": 1, "title": "Test"}
            )
            response = client_with_access_code.post(
                "/api/docker/sessions",
                json={"level_number": 1, "access_code": "secret123"}
            )
    assert response.status_code == 200


def test_docker_session_works_without_access_code_when_not_configured(client_no_access_code):
    """Should work when no access code is configured."""
    with patch("app.api.docker_terminal.sandbox_manager") as mock_manager:
        mock_manager.create_session.return_value = {
            "session_id": "test-123",
            "port": 10001,
            "ttyd_token": "token123"
        }
        with patch("app.api.docker_terminal.get_level") as mock_level:
            mock_level.return_value = MagicMock(
                number=1, title="Test", content="Test content",
                model_dump=lambda: {"number": 1, "title": "Test"}
            )
            response = client_no_access_code.post(
                "/api/docker/sessions",
                json={"level_number": 1}
            )
    assert response.status_code == 200
```

**Step 2: Run test to verify it fails**

Run: `cd backend && python -m pytest tests/test_docker_access_code.py -v`
Expected: FAIL (access_code field not in model, no validation)

**Step 3: Add access_code field to CreateSessionRequest**

Modify `backend/app/api/docker_terminal.py` lines 22-25:

```python
class CreateSessionRequest(BaseModel):
    level_number: int
    api_key: str = ""
    access_code: str = ""
```

**Step 4: Add access code validation to create_session**

Modify `backend/app/api/docker_terminal.py`, add after line 42 (after the function definition):

```python
@router.post("/sessions", response_model=CreateSessionResponse)
async def create_session(request: CreateSessionRequest):
    """Create a new Docker sandbox session."""
    # Check access code if configured
    if settings.demo_access_code:
        if request.access_code != settings.demo_access_code:
            raise HTTPException(status_code=403, detail="Invalid access code")

    # Rest of existing code...
```

**Step 5: Run test to verify it passes**

Run: `cd backend && python -m pytest tests/test_docker_access_code.py -v`
Expected: PASS

**Step 6: Commit**

```bash
git add backend/app/api/docker_terminal.py backend/tests/test_docker_access_code.py
git commit -m "feat: add access code validation to Docker terminal API"
```

---

## Task 2: Add Global Session Cap to Sandbox Manager

**Files:**
- Modify: `backend/app/config.py:29` (add max_sessions setting)
- Modify: `backend/app/services/sandbox_manager.py:57-84` (add session cap check)
- Test: `backend/tests/test_session_cap.py` (new file)

**Step 1: Write the failing test**

Create `backend/tests/test_session_cap.py`:

```python
import pytest
from unittest.mock import patch, MagicMock
from app.services.sandbox_manager import SandboxManager


def test_session_cap_rejects_when_full():
    """Should raise exception when max sessions reached."""
    manager = SandboxManager()

    # Fill up the sessions
    for i in range(5):
        manager.sessions[f"session-{i}"] = MagicMock()

    with patch("app.services.sandbox_manager.settings") as mock_settings:
        mock_settings.max_sessions = 5

        with pytest.raises(Exception) as exc_info:
            manager.create_session("new-session", 1)

        assert "server full" in str(exc_info.value).lower() or exc_info.value.status_code == 503


def test_session_cap_allows_when_under_limit():
    """Should allow session creation when under limit."""
    manager = SandboxManager()

    with patch("app.services.sandbox_manager.settings") as mock_settings:
        mock_settings.max_sessions = 5
        with patch("app.services.sandbox_manager.DockerSandbox") as mock_sandbox:
            mock_sandbox.return_value = MagicMock(
                port=10001,
                get_ttyd_token=lambda: "token123"
            )

            result = manager.create_session("test-session", 1)
            assert result["session_id"] == "test-session"
```

**Step 2: Run test to verify it fails**

Run: `cd backend && python -m pytest tests/test_session_cap.py -v`
Expected: FAIL (max_sessions not in settings, no cap check)

**Step 3: Add max_sessions to config**

Modify `backend/app/config.py`, add after line 29:

```python
    demo_access_code: str = ""
    max_sessions: int = 5
```

**Step 4: Add session cap check to SandboxManager**

Modify `backend/app/services/sandbox_manager.py`, add at the start of `create_session()` method (after line 58):

```python
    def create_session(
        self, session_id: str, level_number: int, api_key: str | None = None
    ) -> dict:
        """Create a new sandbox session."""
        # Check global session cap
        if len(self.sessions) >= settings.max_sessions:
            raise HTTPException(
                status_code=503,
                detail=f"Server full. Maximum {settings.max_sessions} concurrent sessions."
            )

        # Rest of existing code...
```

Also add the import at the top of the file:

```python
from fastapi import HTTPException
```

**Step 5: Run test to verify it passes**

Run: `cd backend && python -m pytest tests/test_session_cap.py -v`
Expected: PASS

**Step 6: Commit**

```bash
git add backend/app/config.py backend/app/services/sandbox_manager.py backend/tests/test_session_cap.py
git commit -m "feat: add global session cap (MAX_SESSIONS)"
```

---

## Task 3: Bind Container Ports to 127.0.0.1 Explicitly

**Files:**
- Modify: `backend/app/services/docker_sandbox.py:96` (port binding)
- Test: Manual verification

**Step 1: Read current implementation**

Read `backend/app/services/docker_sandbox.py` to verify current port binding.

**Step 2: Verify port binding is already correct**

The current code at line 96 should already have:
```python
ports={"7681/tcp": ("127.0.0.1", self.port)}
```

If it shows `("0.0.0.0", self.port)` or just `self.port`, change to:
```python
ports={"7681/tcp": ("127.0.0.1", self.port)}
```

**Step 3: Verify with Docker command**

Run: `docker ps --format "{{.Ports}}" | head -1`
Expected: Should show `127.0.0.1:PORT->7681/tcp` (not `0.0.0.0`)

**Step 4: Commit if changed**

```bash
git add backend/app/services/docker_sandbox.py
git commit -m "fix: bind container ports to 127.0.0.1 only"
```

---

## Task 4: Add Container Hardening Flags

**Files:**
- Modify: `backend/app/services/docker_sandbox.py:84-103` (container run options)
- Test: Manual verification

**Step 1: Write test for container security options**

Create `backend/tests/test_container_hardening.py`:

```python
import pytest
from unittest.mock import patch, MagicMock


def test_container_has_security_options():
    """Verify container is created with security hardening."""
    with patch("app.services.docker_sandbox.docker") as mock_docker:
        mock_client = MagicMock()
        mock_docker.from_env.return_value = mock_client
        mock_container = MagicMock()
        mock_client.containers.run.return_value = mock_container

        from app.services.docker_sandbox import DockerSandbox
        sandbox = DockerSandbox("test-session", 10001, 1)

        # Verify security options were passed
        call_kwargs = mock_client.containers.run.call_args[1]

        assert call_kwargs.get("mem_limit") == "1g"
        assert call_kwargs.get("cpu_quota") == 100000  # 1 CPU
        assert call_kwargs.get("pids_limit") == 100
        assert call_kwargs.get("read_only") == True
        assert "no-new-privileges:true" in call_kwargs.get("security_opt", [])
```

**Step 2: Run test to verify it fails**

Run: `cd backend && python -m pytest tests/test_container_hardening.py -v`
Expected: FAIL (hardening options not set)

**Step 3: Add hardening options to docker run**

Modify `backend/app/services/docker_sandbox.py`, update the `containers.run()` call (around line 84-103):

```python
        self.container = self.client.containers.run(
            "claude-game-sandbox:latest",
            detach=True,
            name=f"sandbox-{session_id}",
            environment={
                "LEVEL_NUMBER": str(level_number),
                "TTYD_TOKEN": self.ttyd_token,
            },
            ports={"7681/tcp": ("127.0.0.1", self.port)},
            # Resource limits
            mem_limit="1g",
            cpu_quota=100000,  # 1 CPU (100000 microseconds per 100ms period)
            pids_limit=100,
            # Security hardening
            read_only=True,
            security_opt=["no-new-privileges:true"],
            cap_drop=["ALL"],
            cap_add=["CHOWN", "SETUID", "SETGID"],
            # Tmpfs for writable directories
            tmpfs={
                "/tmp": "rw,noexec,nosuid,size=256m",
                "/home/claude/.claude": "rw,noexec,nosuid,size=64m",
                "/home/claude/workspace": "rw,noexec,nosuid,size=512m",
            },
        )
```

**Step 4: Run test to verify it passes**

Run: `cd backend && python -m pytest tests/test_container_hardening.py -v`
Expected: PASS

**Step 5: Manual test - start a container and verify**

Run: `docker inspect sandbox-test | jq '.[0].HostConfig | {ReadonlyRootfs, SecurityOpt, CapDrop, CapAdd}'`

**Step 6: Commit**

```bash
git add backend/app/services/docker_sandbox.py backend/tests/test_container_hardening.py
git commit -m "feat: add container hardening (read-only, cap-drop, no-new-privileges)"
```

---

## Task 5: Add Startup Orphan Cleanup

**Files:**
- Modify: `backend/app/services/sandbox_manager.py:20-27` (add cleanup on init)
- Test: `backend/tests/test_orphan_cleanup.py` (new file)

**Step 1: Write the failing test**

Create `backend/tests/test_orphan_cleanup.py`:

```python
import pytest
from unittest.mock import patch, MagicMock


def test_cleanup_orphaned_containers_on_startup():
    """Should remove all sandbox-* containers on manager init."""
    with patch("app.services.sandbox_manager.docker") as mock_docker:
        mock_client = MagicMock()
        mock_docker.from_env.return_value = mock_client

        # Simulate orphaned containers
        orphan1 = MagicMock()
        orphan1.name = "sandbox-old-session-1"
        orphan2 = MagicMock()
        orphan2.name = "sandbox-old-session-2"
        mock_client.containers.list.return_value = [orphan1, orphan2]

        from importlib import reload
        import app.services.sandbox_manager as sm
        reload(sm)

        manager = sm.SandboxManager()

        # Verify containers were stopped and removed
        orphan1.stop.assert_called_once()
        orphan1.remove.assert_called_once()
        orphan2.stop.assert_called_once()
        orphan2.remove.assert_called_once()
```

**Step 2: Run test to verify it fails**

Run: `cd backend && python -m pytest tests/test_orphan_cleanup.py -v`
Expected: FAIL (no cleanup on init)

**Step 3: Add cleanup method to SandboxManager**

Modify `backend/app/services/sandbox_manager.py`, add after `__init__`:

```python
class SandboxManager:
    def __init__(self):
        self.sessions: dict[str, DockerSandbox] = {}
        self.available_ports = set(range(10001, 10101))
        self.client = docker.from_env()
        self._cleanup_orphaned_containers()
        asyncio.create_task(self._cleanup_loop())

    def _cleanup_orphaned_containers(self):
        """Remove any sandbox containers from previous runs."""
        try:
            containers = self.client.containers.list(
                all=True,
                filters={"name": "sandbox-"}
            )
            for container in containers:
                if container.name.startswith("sandbox-"):
                    logger.info(f"Cleaning up orphaned container: {container.name}")
                    try:
                        container.stop(timeout=5)
                    except Exception:
                        pass
                    try:
                        container.remove(force=True)
                    except Exception as e:
                        logger.warning(f"Failed to remove {container.name}: {e}")
        except Exception as e:
            logger.warning(f"Failed to cleanup orphaned containers: {e}")
```

**Step 4: Run test to verify it passes**

Run: `cd backend && python -m pytest tests/test_orphan_cleanup.py -v`
Expected: PASS

**Step 5: Commit**

```bash
git add backend/app/services/sandbox_manager.py backend/tests/test_orphan_cleanup.py
git commit -m "feat: cleanup orphaned containers on backend startup"
```

---

## Task 6: Add X-Forwarded-For Parsing for Rate Limiting

**Files:**
- Modify: `backend/app/api/docker_terminal.py:38-48` (add IP extraction and rate limiting)
- Test: `backend/tests/test_rate_limiting.py` (new file)

**Step 1: Write the failing test**

Create `backend/tests/test_rate_limiting.py`:

```python
import pytest
from app.api.docker_terminal import get_client_ip
from unittest.mock import MagicMock


def test_get_client_ip_from_forwarded_header():
    """Should extract IP from X-Forwarded-For header."""
    request = MagicMock()
    request.headers = {"x-forwarded-for": "1.2.3.4, 5.6.7.8"}
    request.client.host = "127.0.0.1"

    ip = get_client_ip(request)
    assert ip == "1.2.3.4"


def test_get_client_ip_fallback_to_client():
    """Should use client.host when no forwarded header."""
    request = MagicMock()
    request.headers = {}
    request.client.host = "192.168.1.100"

    ip = get_client_ip(request)
    assert ip == "192.168.1.100"
```

**Step 2: Run test to verify it fails**

Run: `cd backend && python -m pytest tests/test_rate_limiting.py -v`
Expected: FAIL (get_client_ip doesn't exist)

**Step 3: Add get_client_ip function**

Modify `backend/app/api/docker_terminal.py`, add after imports:

```python
from fastapi import Request

def get_client_ip(request: Request) -> str:
    """Get client IP from request, handling proxies."""
    forwarded = request.headers.get("x-forwarded-for")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.client.host if request.client else "unknown"
```

**Step 4: Add rate limiting to create_session**

Modify the `create_session` function signature and add rate limiting:

```python
@router.post("/sessions", response_model=CreateSessionResponse)
async def create_session(request: CreateSessionRequest, http_request: Request):
    """Create a new Docker sandbox session."""
    # Check access code if configured
    if settings.demo_access_code:
        if request.access_code != settings.demo_access_code:
            raise HTTPException(status_code=403, detail="Invalid access code")

    # Rate limiting by IP
    client_ip = get_client_ip(http_request)
    ip_session_count = sum(
        1 for s in sandbox_manager.sessions.values()
        if getattr(s, 'client_ip', None) == client_ip
    )
    if ip_session_count >= 3:
        raise HTTPException(
            status_code=429,
            detail="Too many active sessions. Maximum 3 per IP."
        )

    # Rest of existing code...
```

**Step 5: Run test to verify it passes**

Run: `cd backend && python -m pytest tests/test_rate_limiting.py -v`
Expected: PASS

**Step 6: Commit**

```bash
git add backend/app/api/docker_terminal.py backend/tests/test_rate_limiting.py
git commit -m "feat: add IP-based rate limiting with X-Forwarded-For support"
```

---

## Task 7: Add Frontend Access Code Gate

**Files:**
- Modify: `frontend/src/App.tsx:261-269` (show access code for Docker mode)
- Modify: `frontend/src/App.tsx:126-128` (send access code in request)
- Test: Manual verification

**Step 1: Show access code input for Docker mode**

Modify `frontend/src/App.tsx`, find lines 261-269 and remove the `!isDockerMode &&` condition:

Before:
```tsx
{!isDockerMode && (
  <input
    type="text"
    placeholder="Access code (if required)"
    value={accessCode}
    onChange={(e) => setAccessCode(e.target.value)}
    onKeyDown={(e) => e.key === "Enter" && startGame(selectedLesson)}
  />
)}
```

After:
```tsx
<input
  type="text"
  placeholder="Access code (if required)"
  value={accessCode}
  onChange={(e) => setAccessCode(e.target.value)}
  onKeyDown={(e) => e.key === "Enter" && startGame(selectedLesson)}
/>
```

**Step 2: Send access code in Docker session request**

Modify `frontend/src/App.tsx`, find the Docker session creation (around lines 123-129):

Before:
```tsx
const response = await fetch(`${config.apiUrl}/api/docker/sessions`, {
  method: "POST",
  headers: { "Content-Type": "application/json" },
  body: JSON.stringify({
    level_number: levelNumber,
  }),
});
```

After:
```tsx
const response = await fetch(`${config.apiUrl}/api/docker/sessions`, {
  method: "POST",
  headers: { "Content-Type": "application/json" },
  body: JSON.stringify({
    level_number: levelNumber,
    access_code: accessCode,
  }),
});
```

**Step 3: Use sessionStorage instead of localStorage**

Find where `accessCode` might be stored (if any localStorage usage) and change to sessionStorage:

```tsx
// If storing access code for convenience
useEffect(() => {
  const saved = sessionStorage.getItem('accessCode');
  if (saved) setAccessCode(saved);
}, []);

// When access code is validated
sessionStorage.setItem('accessCode', accessCode);
```

**Step 4: Manual test**

1. Start backend with `DEMO_ACCESS_CODE=test123`
2. Start frontend
3. Try to start a session without access code - should get 403
4. Try with correct access code - should work

**Step 5: Commit**

```bash
git add frontend/src/App.tsx
git commit -m "feat: add access code gate to frontend for Docker mode"
```

---

## Task 8: Add WebSocket Heartbeat for Idle Detection

**Files:**
- Modify: `backend/app/api/docker_terminal.py` (WebSocket endpoint)
- Test: Manual verification

**Step 1: Check current WebSocket implementation**

Read the WebSocket terminal proxy code in `backend/app/api/docker_terminal.py` to understand current implementation.

**Step 2: Add heartbeat to WebSocket proxy**

If there's a WebSocket endpoint, add ping/pong handling:

```python
@router.websocket("/ws/terminal/{session_id}")
async def terminal_websocket(websocket: WebSocket, session_id: str):
    await websocket.accept(subprotocol="tty")

    sandbox = sandbox_manager.get_session(session_id)
    if not sandbox:
        await websocket.close(code=4004, reason="Session not found")
        return

    last_activity = time.time()

    async def send_heartbeat():
        nonlocal last_activity
        while True:
            await asyncio.sleep(30)
            try:
                await websocket.send_bytes(b"")  # Empty ping
                last_activity = time.time()
            except:
                break

    heartbeat_task = asyncio.create_task(send_heartbeat())

    try:
        # ... existing proxy code ...
        # Update last_activity on each message
    finally:
        heartbeat_task.cancel()
```

**Step 3: Update session activity tracking**

Ensure `sandbox_manager` tracks `last_activity` for each session:

```python
# In cleanup loop
for session_id, sandbox in list(self.sessions.items()):
    if time.time() - sandbox.last_activity > 900:  # 15 min idle
        await self.terminate_session(session_id)
```

**Step 4: Commit**

```bash
git add backend/app/api/docker_terminal.py
git commit -m "feat: add WebSocket heartbeat for reliable idle detection"
```

---

## Task 9: Create Docker Network with Egress Rules

**Files:**
- Create: `scripts/setup-network.sh` (new file)
- Document in: `docs/plans/2026-02-04-hetzner-vps-deployment.md`

**Step 1: Create network setup script**

Create `scripts/setup-network.sh`:

```bash
#!/bin/bash
set -e

# Create isolated network for sandbox containers
docker network create --driver bridge sandbox-net 2>/dev/null || true

# Get the subnet (usually 172.18.0.0/16 for second bridge network)
SUBNET=$(docker network inspect sandbox-net --format '{{range .IPAM.Config}}{{.Subnet}}{{end}}')
echo "Sandbox network subnet: $SUBNET"

# Block containers from accessing host services
iptables -C DOCKER-USER -s $SUBNET -d 172.17.0.1 -j DROP 2>/dev/null || \
    iptables -I DOCKER-USER -s $SUBNET -d 172.17.0.1 -j DROP

# Block access to private networks
iptables -C DOCKER-USER -s $SUBNET -d 10.0.0.0/8 -j DROP 2>/dev/null || \
    iptables -I DOCKER-USER -s $SUBNET -d 10.0.0.0/8 -j DROP

iptables -C DOCKER-USER -s $SUBNET -d 192.168.0.0/16 -j DROP 2>/dev/null || \
    iptables -I DOCKER-USER -s $SUBNET -d 192.168.0.0/16 -j DROP

# Allow HTTPS (for Anthropic API) and DNS
iptables -C DOCKER-USER -s $SUBNET -p tcp --dport 443 -j ACCEPT 2>/dev/null || \
    iptables -I DOCKER-USER -s $SUBNET -p tcp --dport 443 -j ACCEPT

iptables -C DOCKER-USER -s $SUBNET -p udp --dport 53 -j ACCEPT 2>/dev/null || \
    iptables -I DOCKER-USER -s $SUBNET -p udp --dport 53 -j ACCEPT

echo "Network egress rules configured."
```

**Step 2: Make executable**

Run: `chmod +x scripts/setup-network.sh`

**Step 3: Update docker_sandbox.py to use sandbox-net**

Add `network="sandbox-net"` to container run options.

**Step 4: Commit**

```bash
git add scripts/setup-network.sh backend/app/services/docker_sandbox.py
git commit -m "feat: add Docker network with egress restrictions"
```

---

## Task 10: Final Integration Test

**Files:**
- Test: Manual end-to-end verification

**Step 1: Set environment variables**

```bash
export DEMO_ACCESS_CODE=beta2024
export MAX_SESSIONS=5
export SANDBOX_MODE=docker
```

**Step 2: Start backend**

```bash
cd backend && uvicorn app.main:app --reload
```

**Step 3: Test access code rejection**

```bash
curl -X POST http://localhost:8080/api/docker/sessions \
  -H "Content-Type: application/json" \
  -d '{"level_number": 1, "access_code": "wrong"}'
# Expected: 403 Forbidden
```

**Step 4: Test access code acceptance**

```bash
curl -X POST http://localhost:8080/api/docker/sessions \
  -H "Content-Type: application/json" \
  -d '{"level_number": 1, "access_code": "beta2024"}'
# Expected: 200 with session_id
```

**Step 5: Test session cap**

Create 5 sessions, then try a 6th:
```bash
# Should return 503 Server Full
```

**Step 6: Verify container hardening**

```bash
docker inspect sandbox-* | jq '.[0].HostConfig | {ReadonlyRootfs, SecurityOpt, CapDrop}'
# Expected: ReadonlyRootfs=true, SecurityOpt includes no-new-privileges
```

**Step 7: Commit any fixes**

```bash
git add -A
git commit -m "fix: integration test fixes"
```

---

## Summary

| Task | Component | Status |
|------|-----------|--------|
| 1 | Access code validation | |
| 2 | Global session cap | |
| 3 | Port binding to 127.0.0.1 | |
| 4 | Container hardening | |
| 5 | Startup orphan cleanup | |
| 6 | X-Forwarded-For rate limiting | |
| 7 | Frontend access code gate | |
| 8 | WebSocket heartbeat | |
| 9 | Docker network egress rules | |
| 10 | Integration test | |
