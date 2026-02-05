# Hetzner VPS Deployment Design

**Date:** 2026-02-04
**Status:** Approved (v2 - with security hardening)
**Goal:** Simple deployment for 10-15 beta users with per-session container isolation

## Architecture Overview

```
┌─────────────────┐     ┌─────────────────────────────────────────┐
│     Vercel      │     │           Hetzner VPS (CPX21)           │
│                 │     │                                         │
│  React Frontend │────▶│  Caddy (auto TLS)                       │
│                 │     │       │                                 │
└─────────────────┘     │       ▼                                 │
                        │  FastAPI Backend ◀──── WebSocket ────┐  │
                        │       │                              │  │
                        │       ▼                              │  │
                        │  Docker containers (one per session) │  │
                        │  ┌─────────┐ ┌─────────┐            │  │
                        │  │ ttyd +  │ │ ttyd +  │ ◀──────────┘  │
                        │  │ claude  │ │ claude  │               │
                        │  └─────────┘ └─────────┘               │
                        └─────────────────────────────────────────┘
```

### Components

- **Frontend**: Stays on Vercel (free, automatic deploys from git)
- **Hetzner CPX21**: ~€8/mo - 3 vCPU, 4GB RAM, 80GB disk
- **Caddy**: Automatic TLS via Let's Encrypt, reverse proxy (simpler than nginx)
- **FastAPI backend**: Handles REST API + WebSocket proxying to containers
- **Docker containers**: One per session, each running ttyd + Claude CLI

### Traffic Flow

1. User enters access code on frontend
2. Frontend calls backend to create session (with access code + API key)
3. Backend validates code, spins up container, writes API key to container
4. Backend returns session ID
5. Frontend opens WebSocket to backend
6. Backend proxies terminal data to/from container's ttyd

## Container Lifecycle

### Creation (on session start)

1. Backend receives `POST /api/sessions` with `{api_key, level_number, access_code}`
2. Validates access code against `DEMO_ACCESS_CODE` env var
3. **Check global session cap** - return 503 "server full" if at max (e.g., 5 concurrent)
4. Starts container from local `claude-game-sandbox:latest` image
5. Container config:
   - `LEVEL_NUMBER` env var set
   - **Bound to 127.0.0.1:PORT** (not 0.0.0.0 - prevents public exposure)
   - Network: custom bridge with egress restrictions
6. Writes API key to container's `/home/claude/.claude/.credentials.json` via **tmpfs mount**
7. Returns session ID to frontend

### Cleanup Rules

- **Idle timeout**: 15 minutes of no WebSocket activity
- **Hard cap**: 2 hours regardless of activity
- **Background task**: Runs every 60 seconds, enforces both conditions
- **Cleanup action**: `docker stop` + `docker rm`, remove session from memory
- **Heartbeat**: Backend sends WebSocket ping every 30s, tracks last pong for idle detection
- **Startup cleanup**: On backend start, kill all `sandbox-*` containers (handles restarts)

### Resource Limits (per container)

```bash
docker run \
  --name sandbox-${SESSION_ID} \
  --memory=1g \
  --cpus=1.0 \
  --pids-limit=100 \
  --storage-opt size=2G \
  --cap-drop=ALL \
  --cap-add=CHOWN,SETUID,SETGID,NET_BIND_SERVICE \
  --security-opt=no-new-privileges:true \
  --read-only \
  --tmpfs /tmp:rw,noexec,nosuid,size=256m \
  --tmpfs /home/claude/.claude:rw,noexec,nosuid,size=64m \
  -p 127.0.0.1:${PORT}:7681 \
  -e LEVEL_NUMBER=${LEVEL} \
  --network sandbox-net \
  claude-game-sandbox:latest
```

**Global cap**: Max 5 concurrent containers (leaves ~1.5GB for OS + backend)

## Network Security

### Container Network Isolation

Create a dedicated Docker network with restricted egress:

```bash
# Create network
docker network create --driver bridge sandbox-net

# iptables rules (run on host)
# Block containers from accessing host services
iptables -I DOCKER-USER -s 172.18.0.0/16 -d 172.17.0.1 -j DROP
iptables -I DOCKER-USER -s 172.18.0.0/16 -d 10.0.0.0/8 -j DROP
iptables -I DOCKER-USER -s 172.18.0.0/16 -d 192.168.0.0/16 -j DROP

# Allow only Anthropic API (and DNS)
iptables -I DOCKER-USER -s 172.18.0.0/16 -d 0.0.0.0/0 -p tcp --dport 443 -j ACCEPT
iptables -I DOCKER-USER -s 172.18.0.0/16 -d 0.0.0.0/0 -p udp --dport 53 -j ACCEPT
```

This prevents containers from:
- Accessing the host (172.17.0.1)
- Scanning internal networks
- Making arbitrary outbound connections (only HTTPS allowed)

## Access Control & Security

### Frontend Gate (UX only)

- Landing page shows access code input before app renders
- Code stored in sessionStorage (not localStorage - cleared on tab close)
- Bypassable - purely for user experience

### Backend Validation (actual security)

- `DEMO_ACCESS_CODE` env var on backend
- Every `POST /api/sessions` must include `access_code` field
- Returns 403 if code doesn't match
- Constant-time comparison to prevent timing attacks

### Security Measures

| Measure | Implementation |
|---------|----------------|
| **Rate limiting** | Max 3 concurrent sessions per IP (use `X-Forwarded-For` from Caddy) |
| **Global cap** | Max 5 total sessions, return 503 when full |
| **Session IDs** | 43-char random tokens (unguessable) |
| **API keys** | Written to tmpfs, never logged, dies with container |
| **Container isolation** | Non-root user, no-new-privileges, capability drops |
| **Read-only root** | Container filesystem is read-only, only tmpfs writable |
| **Network isolation** | Egress restricted to HTTPS only, no host access |
| **TLS** | Automatic via Caddy |

### Acceptable Limitations for Beta

- No user accounts/login - just access code
- No audit logging
- No per-user rate limiting (only per-IP)

## Deployment

### Initial VPS Setup

```bash
# 1. Provision Hetzner CPX21 (Ubuntu 22.04) via console or CLI

# 2. SSH in and run initial hardening
apt update && apt upgrade -y
apt install -y ufw fail2ban unattended-upgrades

# 3. Configure firewall
ufw default deny incoming
ufw default allow outgoing
ufw allow 22/tcp    # SSH
ufw allow 80/tcp    # HTTP (for Caddy ACME)
ufw allow 443/tcp   # HTTPS
ufw enable

# 4. SSH hardening
sed -i 's/PermitRootLogin yes/PermitRootLogin no/' /etc/ssh/sshd_config
sed -i 's/#PasswordAuthentication yes/PasswordAuthentication no/' /etc/ssh/sshd_config
systemctl restart sshd

# 5. Create deploy user
adduser deploy
usermod -aG sudo deploy
usermod -aG docker deploy

# 6. Enable unattended security updates
dpkg-reconfigure -plow unattended-upgrades
```

### Install Dependencies

```bash
# Docker
curl -fsSL https://get.docker.com | sh

# Caddy
apt install -y debian-keyring debian-archive-keyring apt-transport-https
curl -1sLf 'https://dl.cloudsmith.io/public/caddy/stable/gpg.key' | gpg --dearmor -o /usr/share/keyrings/caddy-stable-archive-keyring.gpg
curl -1sLf 'https://dl.cloudsmith.io/public/caddy/stable/debian.deb.txt' | tee /etc/apt/sources.list.d/caddy-stable.list
apt update && apt install caddy

# Docker log rotation
cat > /etc/docker/daemon.json << 'EOF'
{
  "log-driver": "json-file",
  "log-opts": {
    "max-size": "10m",
    "max-file": "3"
  }
}
EOF
systemctl restart docker
```

### Directory Structure

```
/opt/claude-game/
├── backend/           # FastAPI app
├── sandbox/           # Dockerfile for sandbox image
├── levels/            # Lesson content
└── .env               # Production secrets
```

### Caddy Configuration

```bash
# /etc/caddy/Caddyfile
api.yourdomain.com {
    reverse_proxy localhost:8080 {
        # Pass real client IP for rate limiting
        header_up X-Forwarded-For {remote_host}
        header_up X-Real-IP {remote_host}
    }
}
```

That's it. Caddy handles TLS automatically.

### systemd Service

```ini
# /etc/systemd/system/claude-game-backend.service
[Unit]
Description=Claude Code Game Backend
After=network.target docker.service
Requires=docker.service

[Service]
Type=simple
User=deploy
WorkingDirectory=/opt/claude-game/backend
Environment=PATH=/opt/claude-game/backend/.venv/bin:/usr/local/bin:/usr/bin
EnvironmentFile=/opt/claude-game/.env
ExecStartPre=/usr/bin/docker rm -f $(docker ps -aq --filter "name=sandbox-") || true
ExecStart=/opt/claude-game/backend/.venv/bin/uvicorn app.main:app --host 127.0.0.1 --port 8080
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
```

Note: `ExecStartPre` cleans up orphaned containers on restart.

### Environment Variables

**Backend (.env):**
```bash
SANDBOX_MODE=docker
DEMO_ACCESS_CODE=your-beta-access-code
ALLOWED_ORIGINS=https://claude-code-game.vercel.app
DEBUG=false
PORT=8080
MAX_SESSIONS=5
```

**Frontend (Vercel):**
```bash
VITE_API_URL=https://api.yourdomain.com
VITE_TERMINAL_MODE=docker
```

### Deploying Updates

```bash
# Backend updates
cd /opt/claude-game && git pull
sudo systemctl restart claude-game-backend

# Level changes (must rebuild sandbox image)
docker build -t claude-game-sandbox:latest -f sandbox/Dockerfile .
sudo systemctl restart claude-game-backend

# Frontend: just push to git, Vercel auto-deploys
```

## Operations

### Useful Commands

```bash
# See running containers
docker ps --filter "name=sandbox-"

# Check resource usage
docker stats

# Manual cleanup of stuck containers
docker rm -f $(docker ps -q --filter "name=sandbox-")

# Tail backend logs
journalctl -u claude-game-backend -f

# Check disk space
df -h

# Check Caddy status
systemctl status caddy
caddy validate --config /etc/caddy/Caddyfile
```

### Troubleshooting

| Issue | Check |
|-------|-------|
| Container won't start | `docker logs sandbox-XXX`, disk space, port conflicts |
| WebSocket disconnects | Backend logs, check heartbeat handling |
| High memory | `docker stats`, reduce MAX_SESSIONS |
| TLS not working | `caddy validate`, check DNS points to VPS |
| Rate limiting not working | Verify `X-Forwarded-For` header in backend |

### Scaling Beyond Beta

When outgrowing one VPS:
1. **Simple**: Upgrade to bigger Hetzner box (CPX31 = 4 vCPU, 8GB)
2. **Medium**: Multiple VPS behind load balancer
3. **Complex**: Kubernetes or Fly.io Machines

For 10-15 beta users, single VPS has plenty of headroom.

## Implementation Checklist

### VPS Setup
- [ ] Provision Hetzner CPX21 (Ubuntu 22.04)
- [ ] Configure DNS (point `api.yourdomain.com` to VPS IP)
- [ ] Run initial hardening (firewall, SSH, fail2ban)
- [ ] Create deploy user
- [ ] Enable unattended-upgrades

### Software Installation
- [ ] Install Docker with log rotation
- [ ] Install Caddy
- [ ] Create sandbox-net Docker network
- [ ] Configure iptables egress rules

### Application Deployment
- [ ] Clone repo to /opt/claude-game
- [ ] Build sandbox image
- [ ] Create Python venv, install dependencies
- [ ] Create .env file with secrets
- [ ] Create systemd service
- [ ] Configure Caddy

### Code Changes
- [ ] Add global session cap (MAX_SESSIONS env var)
- [ ] Bind container ports to 127.0.0.1 explicitly
- [ ] Add startup orphan cleanup
- [ ] Add WebSocket heartbeat/ping handling
- [ ] Use tmpfs for credentials directory
- [ ] Add container hardening flags to docker run
- [ ] Parse X-Forwarded-For for rate limiting
- [ ] Add frontend access code gate (sessionStorage)

### Testing
- [ ] Test session creation with access code
- [ ] Test session cap (try to exceed MAX_SESSIONS)
- [ ] Test idle timeout (wait 15 min)
- [ ] Test hard cap (wait 2 hours)
- [ ] Test backend restart (verify orphan cleanup)
- [ ] Test WebSocket reconnection
- [ ] Verify container can't access host network
