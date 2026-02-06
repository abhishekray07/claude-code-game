# Hetzner VPS Deployment Guide

Deploy Claude Code Game on a Hetzner VPS using Docker mode with all security hardening enabled.

## Prerequisites

- Hetzner VPS (Ubuntu 22.04+, minimum 4GB RAM / 2 vCPU)
- Docker Engine installed (`apt install docker.io`)
- Node.js 20+ and Python 3.11+
- A domain pointed at the VPS (for HTTPS)
- Caddy or nginx for reverse proxy + TLS

## 1. Clone and Build

```bash
git clone <repo-url> /opt/claude-code-game
cd /opt/claude-code-game

# Build the sandbox Docker image
docker build -t claude-game-sandbox:latest -f sandbox/Dockerfile .

# Verify the image works
docker run --rm -d --name test-sandbox -p 7777:7681 -e LEVEL_NUMBER=1 claude-game-sandbox:latest
curl -s -o /dev/null -w "%{http_code}" http://127.0.0.1:7777/  # Should return 200
docker stop test-sandbox
```

## 2. Setup Network Isolation

Create the `sandbox-net` Docker network with egress restrictions. This blocks containers from accessing private networks while allowing DNS and HTTPS (needed for Anthropic API).

```bash
sudo bash scripts/setup-network.sh
```

This is idempotent -- safe to run multiple times. It:
- Creates a `sandbox-net` bridge network (172.30.0.0/16)
- Adds iptables rules to DOCKER-USER chain
- Allows: DNS (port 53), HTTPS (port 443)
- Blocks: all RFC 1918 private ranges, link-local, loopback

**Run this after every server reboot** -- iptables rules don't persist by default. To make them persist:

```bash
apt install iptables-persistent
# Run setup-network.sh first, then:
netfilter-persistent save
```

## 3. Configure Environment

Create `/opt/claude-code-game/backend/.env`:

```bash
# Required
SANDBOX_MODE=docker
DEMO_ACCESS_CODE=your-secret-code-here

# Optional (defaults shown)
MAX_SESSIONS=5           # Global session cap
# SANDBOX_IDLE_TIMEOUT_SECONDS=600  # 10 min idle timeout
# SANDBOX_TIMEOUT_SECONDS=3600      # 60 min hard cap
```

### Environment Variables Reference

| Variable | Default | Description |
|----------|---------|-------------|
| `SANDBOX_MODE` | `local` | Must be `docker` for VPS deployment |
| `DEMO_ACCESS_CODE` | `""` (disabled) | Access code users must enter to start a session |
| `MAX_SESSIONS` | `5` | Maximum concurrent sandbox containers |
| `SANDBOX_IDLE_TIMEOUT_SECONDS` | `600` | Idle session cleanup (seconds) |
| `SANDBOX_TIMEOUT_SECONDS` | `3600` | Hard session timeout (seconds) |

## 4. Install Backend Dependencies

```bash
cd /opt/claude-code-game/backend
python3 -m venv .venv
source .venv/bin/activate
pip install -e .
```

## 5. Build Frontend

```bash
cd /opt/claude-code-game/frontend
npm install

# Set the API URL to your domain
VITE_API_URL=https://yourdomain.com VITE_TERMINAL_MODE=docker npm run build
```

The built files will be in `frontend/dist/`.

## 6. Reverse Proxy (Caddy)

Caddy handles TLS automatically. Install: `apt install caddy`

`/etc/caddy/Caddyfile`:

```
yourdomain.com {
    # Frontend static files
    handle /api/* {
        reverse_proxy localhost:8080
    }
    handle /ws/* {
        reverse_proxy localhost:8080
    }
    handle /health {
        reverse_proxy localhost:8080
    }
    handle {
        root * /opt/claude-code-game/frontend/dist
        file_server
        try_files {path} /index.html
    }
}
```

```bash
systemctl restart caddy
```

## 7. Run the Backend

### Development / Testing

```bash
cd /opt/claude-code-game/backend
source .venv/bin/activate
SANDBOX_MODE=docker uvicorn app.main:app --host 0.0.0.0 --port 8080
```

### Production (systemd)

Create `/etc/systemd/system/claude-game.service`:

```ini
[Unit]
Description=Claude Code Game Backend
After=docker.service
Requires=docker.service

[Service]
Type=simple
User=root
WorkingDirectory=/opt/claude-code-game/backend
Environment=PATH=/opt/claude-code-game/backend/.venv/bin:/usr/bin
ExecStart=/opt/claude-code-game/backend/.venv/bin/uvicorn app.main:app --host 0.0.0.0 --port 8080
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
```

```bash
systemctl daemon-reload
systemctl enable claude-game
systemctl start claude-game
```

## 8. Verify Deployment

```bash
# Health check
curl https://yourdomain.com/health
# Expected: {"status":"healthy","app":"Claude Code Game","mode":"docker"}

# Access code enforcement (should return 403)
curl -s -X POST https://yourdomain.com/api/docker/sessions \
  -H "Content-Type: application/json" \
  -d '{"level_number": 1}' | jq .
# Expected: {"detail": "Invalid access code"}

# Valid access code (should return 200)
curl -s -X POST https://yourdomain.com/api/docker/sessions \
  -H "Content-Type: application/json" \
  -d '{"level_number": 1, "access_code": "your-secret-code-here"}' | jq .
# Expected: {"session_id": "...", "port": ..., ...}
```

## Security Hardening Summary

All protections are enabled automatically when running in Docker mode:

| Protection | What it does |
|------------|-------------|
| **Access code** | Requires `DEMO_ACCESS_CODE` to create sessions (403 if wrong) |
| **Global session cap** | Limits total concurrent containers to `MAX_SESSIONS` (503 when full) |
| **IP rate limiting** | Max 3 sessions per IP address (429 when exceeded) |
| **Container resource limits** | 1GB RAM, 1 CPU, 100 PIDs per container |
| **Read-only rootfs** | Container filesystem is immutable; writable tmpfs for /tmp, workspace, .claude |
| **Capability dropping** | `CAP_DROP ALL`, only CHOWN/SETUID/SETGID added back |
| **No privilege escalation** | `no-new-privileges:true` security option |
| **Network isolation** | Containers on `sandbox-net`; blocked from private networks; only DNS + HTTPS allowed |
| **Orphan cleanup** | Removes leftover `sandbox-*` containers on backend startup |
| **Idle cleanup** | Background task kills containers idle > 30 minutes |
| **Heartbeat tracking** | WebSocket keepalive pings update session activity to prevent false timeouts |

## Updating Lessons

When you change files in `levels/`, you must rebuild the sandbox image:

```bash
cd /opt/claude-code-game
docker build -t claude-game-sandbox:latest -f sandbox/Dockerfile .
# Existing sessions keep the old image; new sessions get the new one
```

## Troubleshooting

### Terminal shows blank screen
1. Check browser console for WebSocket errors
2. Verify container is running: `docker ps --filter "name=sandbox-"`
3. Check backend logs: `journalctl -u claude-game -f`

### Container crashes immediately (exit 139)
SIGSEGV from ttyd. Verify the sandbox image uses ttyd 1.7.7 from GitHub releases, not Ubuntu's apt package:
```bash
docker run --rm claude-game-sandbox:latest ttyd --version
# Expected: ttyd version 1.7.7
```

### "Maximum sessions reached" (503)
```bash
# Check running containers
docker ps --filter "name=sandbox-" --format "{{.Names}} {{.Status}}"

# Force cleanup if stuck
docker ps --filter "name=sandbox-" -q | xargs -r docker rm -f

# Restart backend to reset state
systemctl restart claude-game
```

### Network rules not working after reboot
```bash
# Re-apply iptables rules
sudo bash scripts/setup-network.sh

# Or if using iptables-persistent:
netfilter-persistent reload
```

### Containers can't reach Anthropic API
Verify DNS and HTTPS are allowed through the network:
```bash
docker run --rm --network sandbox-net ubuntu:22.04 \
  bash -c "apt-get update && apt-get install -y curl && curl -s https://api.anthropic.com"
```
If this fails, check that `scripts/setup-network.sh` ran successfully.
