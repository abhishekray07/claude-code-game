# Hetzner VPS Deployment Design

**Date:** 2026-02-04
**Status:** Approved
**Goal:** Simple deployment for 10-15 beta users with per-session container isolation

## Architecture Overview

```
┌─────────────────┐     ┌─────────────────────────────────────────┐
│     Vercel      │     │           Hetzner VPS (CPX21)           │
│                 │     │                                         │
│  React Frontend │────▶│  nginx (TLS termination)                │
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
- **nginx**: TLS termination via Let's Encrypt, proxies to backend
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
3. Starts container from local `claude-game-sandbox:latest` image
4. Container config:
   - `LEVEL_NUMBER` env var set
   - Mapped to localhost port (10001-10100 range)
   - No network restrictions (Claude needs Anthropic API access)
5. Writes API key to container's `/home/claude/.claude/.credentials.json`
6. Returns session ID to frontend

### Cleanup Rules

- **Idle timeout**: 15 minutes of no WebSocket activity
- **Hard cap**: 2 hours regardless of activity
- **Background task**: Runs every 60 seconds, enforces both conditions
- **Cleanup action**: `docker stop` + `docker rm`, remove session from memory

### Resource Limits (per container)

```yaml
mem_limit: 1g
cpus: 1.0
pids_limit: 100
```

With 4GB RAM on the VPS, this safely supports ~3 concurrent containers with headroom for the backend.

## Access Control & Security

### Frontend Gate (UX only)

- Landing page shows access code input before app renders
- Code stored in localStorage after validation
- Bypassable - purely for user experience

### Backend Validation (actual security)

- `DEMO_ACCESS_CODE` env var on backend
- Every `POST /api/sessions` must include `access_code` field
- Returns 403 if code doesn't match
- Constant-time comparison to prevent timing attacks

### Other Security Measures

- **Rate limiting**: Max 3 concurrent sessions per IP
- **Session IDs**: 43-char random tokens (unguessable)
- **API keys**: Written directly to container, never logged or stored in backend
- **Container isolation**: Non-root `claude` user, no privileged mode
- **TLS**: Let's Encrypt cert via certbot with auto-renewal

### Acceptable Limitations for Beta

- No user accounts/login - just access code
- No audit logging
- No per-user rate limiting (only per-IP)

## Deployment

### Initial VPS Setup

1. Provision Hetzner CPX21 (Ubuntu 22.04)
2. Point domain (e.g., `api.yourdomain.com`) to VPS IP
3. Install Docker, nginx, certbot
4. Clone repo, build sandbox image
5. Set up systemd service for backend

### Directory Structure

```
/opt/claude-game/
├── backend/           # FastAPI app
├── sandbox/           # Dockerfile for sandbox image
├── levels/            # Lesson content
└── .env               # Production secrets
```

### nginx Configuration

```nginx
server {
    listen 443 ssl;
    server_name api.yourdomain.com;

    ssl_certificate /etc/letsencrypt/live/api.yourdomain.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/api.yourdomain.com/privkey.pem;

    location / {
        proxy_pass http://127.0.0.1:8080;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_read_timeout 3600s;  # 1 hour for WebSocket
    }
}

server {
    listen 80;
    server_name api.yourdomain.com;
    return 301 https://$server_name$request_uri;
}
```

### Environment Variables

**Backend (.env):**
```bash
SANDBOX_MODE=docker
DEMO_ACCESS_CODE=your-beta-access-code
ALLOWED_ORIGINS=https://claude-code-game.vercel.app
DEBUG=false
PORT=8080
```

**Frontend (Vercel):**
```bash
VITE_API_URL=https://api.yourdomain.com
VITE_TERMINAL_MODE=docker
```

### Deploying Updates

- **Backend**: SSH in → `git pull` → `sudo systemctl restart claude-game-backend`
- **Levels changed**: Also rebuild sandbox image: `docker build -t claude-game-sandbox:latest -f sandbox/Dockerfile .`
- **Frontend**: Push to git, Vercel auto-deploys

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
```

### Troubleshooting

| Issue | Check |
|-------|-------|
| Container won't start | Docker logs, disk space |
| WebSocket disconnects | nginx `proxy_read_timeout` setting |
| High memory | Container `mem_limit`, cleanup frequency |

### Scaling Beyond Beta

When outgrowing one VPS:
1. **Simple**: Upgrade to bigger Hetzner box
2. **Medium**: Move to Fly.io Machines API
3. **Complex**: Load balancer + multiple VPS

For 10-15 beta users, single VPS has plenty of headroom.

## Implementation Checklist

- [ ] Provision Hetzner CPX21
- [ ] Configure DNS
- [ ] Install Docker, nginx, certbot
- [ ] Set up TLS certificate
- [ ] Clone repo and build images
- [ ] Create systemd service
- [ ] Configure nginx
- [ ] Set environment variables
- [ ] Add frontend access code gate
- [ ] Update Vercel environment variables
- [ ] Test end-to-end
