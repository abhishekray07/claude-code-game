# VPS Deployment Design

## Overview

Single Hetzner VPS running all services via Docker Compose. Replaces Fly.io approach to eliminate load balancing complexity.

## Architecture

```
┌─────────────────────────────────────────────────────┐
│                    Hetzner VPS                      │
│  ┌───────────────────────────────────────────────┐  │
│  │                    Nginx                      │  │
│  │  :80 → frontend, /api → backend, /ws → ttyd  │  │
│  └───────────────────┬───────────────────────────┘  │
│           ┌──────────┼──────────┐                   │
│           ▼          ▼          ▼                   │
│  ┌─────────────┐ ┌────────┐ ┌────────────────────┐  │
│  │  Frontend   │ │Backend │ │ Sandbox Containers │  │
│  │   (Vite)    │ │(FastAPI)│ │ ttyd on dynamic   │  │
│  │   :3000     │ │ :8000  │ │ ports 10001-10100  │  │
│  └─────────────┘ └────────┘ └────────────────────┘  │
│                       │              ▲              │
│                       └──────────────┘              │
│                    Docker API (create/destroy)      │
└─────────────────────────────────────────────────────┘
```

## Components

| Component | Tech | Port | Notes |
|-----------|------|------|-------|
| Reverse proxy | Nginx | 80 (public) | Routes all traffic |
| Frontend | Vite/React | 3000 (internal) | Static + WebSocket client |
| Backend | FastAPI | 8000 (internal) | Container lifecycle management |
| Sandboxes | ttyd in Docker | 10001-10100 | Dynamic, per-session |

## Request Flow

1. User visits `http://IP/` → Nginx serves frontend
2. Frontend calls `POST /api/sessions` → backend creates container on port 10001
3. Frontend connects WebSocket to `/ws/10001` → Nginx proxies to container
4. User disconnects → backend destroys container

## Docker Compose

```yaml
services:
  nginx:
    image: nginx:alpine
    ports:
      - "80:80"
    volumes:
      - ./nginx.conf:/etc/nginx/nginx.conf
    depends_on:
      - frontend
      - backend

  frontend:
    build: ./frontend
    expose:
      - "3000"

  backend:
    build: ./backend
    expose:
      - "8000"
    volumes:
      - /var/run/docker.sock:/var/run/docker.sock
    environment:
      - SANDBOX_IMAGE=claude-game-sandbox:latest

  # Sandbox containers created dynamically by backend, not in compose
```

## Nginx Configuration

```nginx
upstream frontend {
    server frontend:3000;
}

upstream backend {
    server backend:8000;
}

server {
    listen 80;

    # Frontend (default)
    location / {
        proxy_pass http://frontend;
    }

    # Backend API
    location /api/ {
        proxy_pass http://backend/;
    }

    # WebSocket to sandbox containers (dynamic port in URL)
    location ~ ^/ws/(\d+)$ {
        set $port $1;
        proxy_pass http://host.docker.internal:$port;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_read_timeout 86400;
    }
}
```

## Backend Container Management

```python
class SandboxManager:
    def __init__(self):
        self.docker = docker.from_env()
        self.sessions = {}  # session_id → {container_id, port, last_active}
        self.port_pool = set(range(10001, 10101))

    def create_session(self, level_number: int) -> Session:
        port = self.port_pool.pop()
        container = self.docker.containers.run(
            "claude-game-sandbox:latest",
            detach=True,
            remove=True,
            environment={"LEVEL_NUMBER": str(level_number)},
            ports={"7681/tcp": port},
        )
        session_id = generate_id()
        self.sessions[session_id] = {
            "container_id": container.id,
            "port": port,
            "last_active": now()
        }
        return {"session_id": session_id, "port": port}

    def destroy_session(self, session_id: str):
        session = self.sessions.pop(session_id)
        container = self.docker.containers.get(session["container_id"])
        container.stop()
        self.port_pool.add(session["port"])
```

### API Endpoints

- `POST /api/sessions` - Create container, return session_id and port
- `DELETE /api/sessions/{id}` - Destroy container
- `POST /api/sessions/{id}/heartbeat` - Update last_active timestamp

### Cleanup

Background task runs every 5 minutes, kills containers idle >30 minutes.

## Frontend Integration

```typescript
async function startSession(levelNumber: number) {
  // 1. Request container from backend
  const res = await fetch('/api/sessions', {
    method: 'POST',
    body: JSON.stringify({ level: levelNumber })
  });
  const { session_id, port } = await res.json();

  // 2. Connect WebSocket to container via Nginx
  const wsUrl = `ws://${window.location.host}/ws/${port}`;
  const socket = new WebSocket(wsUrl);

  // 3. Heartbeat to keep session alive
  const heartbeat = setInterval(() => {
    fetch(`/api/sessions/${session_id}/heartbeat`, { method: 'POST' });
  }, 60000);

  // 4. Cleanup on disconnect
  socket.onclose = () => {
    clearInterval(heartbeat);
    fetch(`/api/sessions/${session_id}`, { method: 'DELETE' });
  };
}
```

## Sandbox Container Image

```dockerfile
FROM ubuntu:22.04

RUN apt-get update && apt-get install -y \
    ttyd curl git sudo vim nano \
    python3 python3-pip python3-venv \
    && rm -rf /var/lib/apt/lists/*

RUN curl -fsSL https://deb.nodesource.com/setup_20.x | bash - \
    && apt-get install -y nodejs

RUN npm install -g @anthropic-ai/claude-code

RUN useradd -m -s /bin/bash claude && \
    echo "claude ALL=(ALL) NOPASSWD:ALL" >> /etc/sudoers

COPY levels/ /home/claude/levels/
COPY entrypoint.sh /home/claude/entrypoint.sh

USER claude
WORKDIR /home/claude/workspace
EXPOSE 7681

CMD ["/home/claude/entrypoint.sh"]
```

## Deployment

### Directory Structure on VPS

```
/opt/claude-game/
├── docker-compose.yml
├── nginx.conf
├── frontend/
│   └── Dockerfile
├── backend/
│   └── Dockerfile
├── sandbox/
│   ├── Dockerfile
│   └── entrypoint.sh
└── levels/
```

### Initial Deploy

```bash
ssh root@your-hetzner-ip
git clone your-repo /opt/claude-game
cd /opt/claude-game

# Build sandbox image
docker build -t claude-game-sandbox:latest -f sandbox/Dockerfile .

# Start services
docker compose up -d
```

### Updates

```bash
git pull
docker compose build
docker compose up -d
```

## Security Considerations

- Sandbox containers run as non-root `claude` user
- Each session gets fresh container - no state leakage
- Claude auth tokens stored in container, destroyed on termination
- Docker socket access limited to backend container only
- 30-minute idle timeout prevents resource exhaustion

## Constraints

- <10 concurrent users (single VPS)
- No persistence between sessions
- No domain initially (IP address only)

## Future Improvements

- Add domain + SSL via Let's Encrypt
- Add user accounts for progress tracking
- Scale to multiple VPS with simple routing layer
