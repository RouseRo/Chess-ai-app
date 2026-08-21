# Docker Architecture: Chess AI App

This document describes the Docker-based microservices architecture for the Chess AI App.

---

## Overview

The application consists of **four containerized microservices**, all sharing a unified SQLite database for user authentication:

| Service | Port | Description |
|---------|------|-------------|
| **chess-ui** | 8080 | Frontend web interface with chessboard |
| **chess-engine** | 8000 | Chess game logic and AI integration |
| **chess-admin-service** | 8001 | Admin dashboard and user management |
| **chess-auth-service** | 8002 | Authentication and JWT token management |

---

## Architecture Diagram

```
┌─────────────────────────────────────────────────────────────────────────┐
│                              Clients                                     │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                          │
│  ┌──────────────────────────┐    ┌──────────────────────────┐   │
│  │         Web UI           │    │   Admin Dashboard        │   │
│  │       (Port 8080)        │    │   (Port 8080/admin.html) │   │
│  └──────────────┬───────────┘    └────────────┬─────────────┘   │
│                 │                             │                  │
└─────────────────┼─────────────────────────────┼──────────────────┘
                  │                             │
                  │     HTTP API               │
                  └──────────────┬─────────────┘
                    │
┌───────────────────┼─────────────────────────────────────────────────────┐
│                   │           Docker Network                             │
├───────────────────┼─────────────────────────────────────────────────────┤
│                   ▼                                                      │
│         ┌──────────────────────┐                                        │
│         │  chess-auth-service  │◀───────────────────────┐               │
│         │     (Port 8002)      │                        │               │
│         └──────────┬───────────┘                        │               │
│                    │                                    │               │
│                    ▼                                    │               │
│         ┌──────────────────────┐         ┌──────────────┴───────────┐   │
│         │   SQLite Database    │◀────────│  chess-admin-service     │   │
│         │   data/users.db      │         │     (Port 8001)          │   │
│         │   (Shared Volume)    │         └──────────────────────────┘   │
│         └──────────────────────┘                                        │
│                                                                          │
│         ┌──────────────────────┐                                        │
│         │    chess-engine      │                                        │
│         │     (Port 8000)      │                                        │
│         └──────────────────────┘                                        │
│                                                                          │
│         ┌──────────────────────┐                                        │
│         │      chess-ui        │                                        │
│         │     (Port 8080)      │                                        │
│         └──────────────────────┘                                        │
│                                                                          │
└─────────────────────────────────────────────────────────────────────────┘
```

---

## Unified Authentication Architecture

All clients (Web UI, Admin Dashboard) authenticate through the same auth-service API:

```
┌─────────────┐   ┌─────────────┐
│   Web UI    │   │   Admin UI  │
│             │   │             │
│  fetch()    │   │  fetch()    │
└──────┬──────┘   └──────┬──────┘
       │                 │
       │    HTTP POST /auth/login
       └─────────────────┘
                         │
                         ▼
              ┌─────────────────────┐
              │   Auth Service      │
              │   (Port 8002)       │
              │                     │
              │  • Validates creds  │
              │  • Issues JWT       │
              │  • bcrypt passwords │
              └──────────┬──────────┘
                         │
                         ▼
              ┌─────────────────────┐
              │   SQLite Database   │
              │   data/users.db     │
              └─────────────────────┘
```

---

## Directory Structure

```
chess-ai-app/
│
├── engine/                    # Chess engine service
│   ├── Dockerfile
│   ├── main.py
│   ├── requirements.txt
│   └── ...
│
├── ui/                        # Frontend web UI
│   ├── Dockerfile
│   ├── nginx.conf
│   ├── nginx.local.conf       # Local dev nginx config
│   ├── package.json
│   ├── tsconfig.json
│   ├── index.html             # Login/Register + game interface (single-page app)
│   ├── admin.html             # Admin dashboard
│   ├── mobile.html            # Mobile-optimised interface
│   ├── game-play.ts
│   ├── player-selection.ts
│   ├── helloworld.ts
│   ├── chessboard.js
│   ├── chessboard.css
│   └── img/
│
├── auth-service/              # Authentication service
│   ├── Dockerfile
│   ├── main.py
│   ├── start.sh               # Launches both port 8002 and port 8003 processes
│   └── requirements.txt
│
├── admin-service/             # Admin management service
│   ├── Dockerfile
│   ├── main.py
│   └── requirements.txt
│
├── data/                      # Shared database directory
│   └── users.db              # SQLite database (shared volume)
│
├── scripts/                   # Utility scripts (currently empty)
│
├── docs/                      # Documentation
│   └── Docker_Design.md
│
├── docker-compose.yml         # Container orchestration
└── .env                       # Environment variables
```

---

## Services

### 1. Chess UI (Port 8080)

**Purpose:** Serves the frontend web application with interactive chessboard.

**Tech Stack:**
- Node.js 20 / TypeScript (build stage)
- nginx (Alpine-based, serve stage)
- HTML/CSS/JavaScript
- chessboard.js library
- chess.js for move validation

**Pages:**
| Page | Description |
|------|-------------|
| `index.html` | Login/Register + game interface (single-page app) |
| `admin.html` | Admin dashboard |

**Dockerfile** (multi-stage build — TypeScript compiled before serving):
```dockerfile
FROM node:20-alpine AS build
WORKDIR /app
COPY . .
RUN npm install && chmod +x node_modules/.bin/tsc
RUN npm run build
RUN cp index.html dist/ || true
RUN cp admin.html dist/ || true
RUN cp mobile.html dist/ || true
RUN [ -d "assets" ] && cp -r assets dist/ || true
RUN cp chessboard.js dist/ || true
RUN cp chessboard.css dist/ || true
RUN [ -d "img" ] && cp -r img dist/ || true

FROM nginx:alpine
COPY --from=build /app/dist /usr/share/nginx/html
COPY nginx.conf /etc/nginx/conf.d/default.conf
EXPOSE 80
```

---

### 2. Chess Engine (Port 8000)

**Purpose:** Handles chess game logic, move validation, and AI integration.

**Tech Stack:**
- Python 3.12
- FastAPI
- python-chess
- OpenAI/DeepSeek integration

**Endpoints:**
| Endpoint | Method | Auth | Description |
|----------|--------|------|-------------|
| `/` | GET | No | Health check |
| `/move` | POST | Yes | Submit a chess move |
| `/ai/suggest` | GET | Yes | Get AI move suggestion |
| `/expert/question` | POST | Yes | Ask chess expert |
| `/expert/joke` | GET | Yes | Get chess joke |
| `/expert/fact` | GET | Yes | Get chess fact |

**Dockerfile:**
```dockerfile
FROM python:3.12-slim
WORKDIR /app
RUN apt-get update && apt-get install -y \
    curl \
    stockfish \
    && rm -rf /var/lib/apt/lists/*
COPY engine/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY engine/ ./engine/
COPY src/ ./src/
COPY user_data/ ./user_data/
ENV STOCKFISH_PATH=/usr/games/stockfish
EXPOSE 8000
CMD ["uvicorn", "engine.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

---

### 3. Auth Service (Port 8002)

**Purpose:** Manages user authentication, registration, and JWT tokens. **Single source of truth for all user data.**

**Tech Stack:**
- Python 3.12
- FastAPI
- SQLite
- PyJWT
- bcrypt

**Database Location:** `data/users.db` (shared Docker volume)

**Endpoints:**
| Endpoint | Method | Description |
|----------|--------|-------------|
| `/health` | GET | Health check |
| `/auth/login` | POST | User login (username or email), returns JWT |
| `/auth/register` | POST | User registration |
| `/auth/verify` | POST | Validate JWT token |
| `/auth/verify-email` | POST | Verify email with token |
| `/auth/refresh` | POST | Refresh JWT token |
| `/auth/logout` | POST | Logout (client-side) |
| `/auth/change-password` | POST | Update password || `/auth/activity` | POST | Update online/playing status |
| `/community/online-users` | GET | List currently online users |
| `/community/messages` | GET | Get recent chat and DMs |
| `/community/messages` | POST | Post a public chat message |
| `/community/dm` | POST | Send a direct message |
| `/community/game-invite` | POST | Send a game invitation |
| `/community/clear-activity` | POST | Clear own game activity status |
| `/rewards/complete-review` | POST | Record a classic game review completion |
| `/rewards/my-reviews` | GET | Fetch review progress and earned badges |
**Login Request (supports username OR email):**
```json
{
  "username": "johndoe",
  "password": "password123"
}
```

**Login Response:**
```json
{
  "success": true,
  "message": "Welcome back, johndoe!",
  "token": "eyJhbGciOiJIUzI1NiIs...",
  "username": "johndoe",
  "is_admin": false
}
```

**JWT Token Structure:**
```json
{
  "username": "johndoe",
  "is_admin": false,
  "email": "john@example.com",
  "exp": 1765824254,
  "iat": 1765737854
}
```

**Dockerfile:**
```dockerfile
FROM python:3.12-slim
WORKDIR /app
RUN apt-get update && apt-get install -y curl && rm -rf /var/lib/apt/lists/*
COPY auth-service/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY auth-service ./auth-service
COPY engine ./engine
COPY user_data ./user_data
EXPOSE 8002
EXPOSE 8003
HEALTHCHECK --interval=30s --timeout=10s --start-period=10s --retries=3 \
    CMD curl -f http://localhost:8002/health || exit 1
# Launches auth on 8002 (public) and admin_app on 8003 (internal)
COPY auth-service/start.sh /app/start.sh
RUN chmod +x /app/start.sh
CMD ["/bin/sh", "/app/start.sh"]
```

---

### 4. Admin Service (Port 8001)

**Purpose:** Provides admin dashboard functionality, user management, and system statistics.

**Tech Stack:**
- Python 3.12
- FastAPI
- SQLite (connects to shared database)

**Endpoints:**
| Endpoint | Method | Auth | Description |
|----------|--------|------|-------------|
| `/health` | GET | No | Health check |
| `/admin/stats` | GET | No | System statistics |
| `/admin/users` | GET | No | List all users with online status |
| `/admin/users/{username}` | GET | No | Get detailed user info |
| `/admin/users/{username}/promote` | POST | No | Promote user to admin |
| `/admin/users/{username}/demote` | POST | No | Demote admin to user |
| `/admin/users/{username}/verify` | POST | No | Manually verify user |
| `/admin/users/{username}` | DELETE | No | Delete user |
| `/admin/models` | GET | Yes | List configured AI models |

**Stats Response Example:**
```json
{
  "total_users": 2,
  "admin_count": 1,
  "verified_users": 2,
  "total_games": 0,
  "timestamp": "2025-12-15T10:30:00.000000+00:00"
}
```

**Dockerfile:**
```dockerfile
FROM python:3.12-slim
WORKDIR /app
RUN apt-get update && apt-get install -y curl && rm -rf /var/lib/apt/lists/*
COPY admin-service/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY admin-service ./admin-service
COPY engine ./engine
COPY user_data ./user_data
EXPOSE 8001
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "import requests; requests.get('http://localhost:8001/health')"
CMD ["uvicorn", "admin-service.main:app", "--host", "0.0.0.0", "--port", "8001"]
```

---

## Docker Compose

**docker-compose.yml:**
```yaml
services:
  chess-engine:
    build:
      context: .
      dockerfile: engine/Dockerfile
    container_name: chess-engine
    ports:
      - "8000:8000"
    environment:
      - OPENAI_API_KEY=${OPENAI_API_KEY}
      - JWT_SECRET_KEY=${JWT_SECRET_KEY:-chess-ai-secret-key-change-in-production}
      - AUTH_SERVICE_URL=http://auth-service:8002
    volumes:
      - ./engine:/app/engine
      - ./src:/app/src
      - ./user_data:/app/user_data
    networks:
      - chess-network
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/"]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 10s

  auth-service:
    build:
      context: .
      dockerfile: auth-service/Dockerfile
    container_name: chess-auth-service
    ports:
      - "8002:8002"
    expose:
      - "8003"
    environment:
      - DATABASE_PATH=/app/data/users.db
      - JWT_SECRET_KEY=${JWT_SECRET_KEY:-chess-app-secret-key}
      - CHESS_DEV_MODE=${CHESS_DEV_MODE:-false}
      - SMTP_HOST=${SMTP_HOST:-}
      - SMTP_PORT=${SMTP_PORT:-587}
      - SMTP_USER=${SMTP_USER:-}
      - SMTP_PASSWORD=${SMTP_PASSWORD:-}
      - SMTP_FROM_EMAIL=${SMTP_FROM_EMAIL:-}
      - APP_BASE_URL=${APP_BASE_URL:-http://localhost:8080}
    volumes:
      - ./data:/app/data
    networks:
      - chess-network
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8002/health"]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 10s

  admin-service:
    build:
      context: .
      dockerfile: admin-service/Dockerfile
    container_name: chess-admin-service
    ports:
      - "8001:8001"
    environment:
      - DATABASE_PATH=/app/data/users.db
    volumes:
      - ./data:/app/data
      - ./user_data:/app/user_data
    networks:
      - chess-network
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8001/health"]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 10s

  chess-ui:
    build: ./ui
    container_name: chess-ui
    ports:
      - "8080:80"
    volumes:
      - ./ui:/usr/share/nginx/html
      - ./ui/nginx.local.conf:/etc/nginx/conf.d/default.conf
    depends_on:
      - chess-engine
      - auth-service
      - admin-service
    networks:
      - chess-network

networks:
  chess-network:
    driver: bridge
```

---

## Database

### Unified Storage

All services and clients share a single SQLite database:

| Environment | Location |
|-------------|----------|
| Docker Containers | `/app/data/users.db` (mounted from `./data`) |
| Local Development | `data/users.db` |

### Users Table Schema

```sql
CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT UNIQUE NOT NULL,
    email TEXT UNIQUE NOT NULL,
    password_hash TEXT NOT NULL,
    is_admin BOOLEAN DEFAULT 0,
    is_verified BOOLEAN DEFAULT 0,
    verification_token TEXT,
    games_count INTEGER DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    last_login TIMESTAMP,
    last_activity TIMESTAMP,
    current_activity TEXT DEFAULT 'offline'
);
```

### Classic Game Reviews Table Schema

```sql
CREATE TABLE classic_game_reviews (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT NOT NULL,
    game_key TEXT NOT NULL,
    completed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(username, game_key)
);
```

### Default Users

Created automatically on first startup or via setup script:

| Username | Email | Password | Admin | Verified |
|----------|-------|----------|-------|----------|
| `admin` | `admin@chess.local` | `admin123` | Yes | Yes |
| `testuser` | `testuser@chess.local` | `Chess123` | No | Yes |
| `johndoe` | `john@example.com` | `password123` | No | Yes |

### Setup Test Users

Default users are created automatically by the auth service on first startup. To reset or inspect user data, connect to the running container:

```powershell
# Copy an existing database into the container (if needed)
docker cp data/users.db chess-auth-service:/app/data/users.db

# Restart auth service
docker-compose restart auth-service
```

### View Database Contents

```powershell
# Local database
sqlite3 data/users.db "SELECT username, email, is_admin, is_verified FROM users;"

# Inside container
docker exec chess-auth-service python -c "
import sqlite3
conn = sqlite3.connect('/app/data/users.db')
for row in conn.execute('SELECT username, is_admin, is_verified FROM users'):
    print(row)
"
```

---

## Authentication Flow

### Web Login Sequence

```
┌─────────┐         ┌──────────┐         ┌──────────────┐
│   UI    │         │  Browser │         │ Auth Service │
└────┬────┘         └────┬─────┘         └──────┬───────┘
     │                   │                      │
     │  User enters      │                      │
     │  credentials      │                      │
     │◀──────────────────│                      │
     │                   │                      │
     │  POST /auth/login │                      │
     │  {username, pass} │                      │
     │───────────────────┼─────────────────────▶│
     │                   │                      │
     │                   │      Validate creds  │
     │                   │      Generate JWT    │
     │                   │                      │
     │  {success, token} │                      │
     │◀──────────────────┼──────────────────────│
     │                   │                      │
     │  Store in         │                      │
     │  localStorage     │                      │
     │                   │                      │
     │  Redirect to      │                      │
     │  game interface   │                      │
     │──────────────────▶│                      │
```

---

## Running the Application

### Prerequisites

1. Docker and Docker Compose installed

### Start All Docker Services

```bash
cd c:\Users\rober\Source\Repos\Chess-ai-app
docker-compose up --build
```

### Start in Background

```bash
docker-compose up -d
```

### View Logs

```bash
docker-compose logs -f
```

### Stop Services

```bash
docker-compose down
```

---

## Access URLs

| Service | URL |
|---------|-----|
| Login / Play Chess | http://localhost:8080 |
| Admin Dashboard | http://localhost:8080/admin.html |
| Engine API | http://localhost:8000 |
| Admin API | http://localhost:8001 |
| Auth API | http://localhost:8002 |

---

## Health Checks

Verify all services are running:

```bash
# Auth Service
curl http://localhost:8002/health
# Expected: {"status":"healthy","service":"auth","storage":"sqlite"}

# Admin Service
curl http://localhost:8001/health
# Expected: {"status":"healthy","service":"admin","storage":"sqlite"}

# Chess Engine
curl http://localhost:8000/
# Expected: {"status":"healthy"}

# Admin Stats
curl http://localhost:8001/admin/stats
# Expected: {"total_users":2,"admin_count":1,"verified_users":2,...}
```

---

## Environment Variables

Create a `.env` file in the project root:

```env
# AI API Keys
OPENAI_API_KEY=your_openai_key

# JWT Configuration
JWT_SECRET_KEY=your-secure-secret-key-change-in-production

# Development Mode (auto-verifies new users)
CHESS_DEV_MODE=false

# Email verification (optional — users auto-verified if unset)
SMTP_HOST=
SMTP_PORT=587
SMTP_USER=
SMTP_PASSWORD=
SMTP_FROM_EMAIL=
APP_BASE_URL=http://localhost:8080
```

---

## Security Considerations

### Current Implementation

| Feature | Status |
|---------|--------|
| Password Hashing | ✅ bcrypt |
| JWT Authentication | ✅ Implemented |
| Unified User Storage | ✅ Single SQLite database |
| CORS | ⚠️ Open (restrict in prod) |
| HTTPS | ✅ Enabled on Azure (Container Apps TLS) / ❌ Local Docker only |
| Rate Limiting | ❌ Not implemented |
| Input Validation | ✅ Basic |

### Production Recommendations

1. **Enable HTTPS** - Use SSL certificates
2. **Restrict CORS** - Specify allowed origins
3. **Add Rate Limiting** - Prevent brute force attacks
4. **Use Strong JWT Secret** - Generate secure random key
5. **Database Backup** - Regular SQLite backups
6. **Change Default Passwords** - Update admin/testuser/johndoe on first use
7. **Environment Variables** - Never commit secrets to git

---

## Troubleshooting

### Common Issues

| Issue | Solution |
|-------|----------|
| "Invalid username or password" | Reset password with `scripts/setup_test_user.py` |
| Database not syncing | Copy manually: `docker cp data/users.db chess-auth-service:/app/data/` |
| Port already in use | `docker-compose down` then retry |
| Token expired | Login again |

### View Container Logs

```bash
docker-compose logs auth-service
docker-compose logs -f admin-service
```

### Access Container Shell

```bash
docker exec -it chess-auth-service /bin/bash
docker exec -it chess-admin-service /bin/bash
```

---

## Azure Deployment

The application is deployed to **Azure Container Apps** (ACA) with all four services running as separate container apps in a shared environment.

### Deployed Services

| Container App | Ingress | Port | Description |
|---------------|---------|------|-------------|
| `chess-ui` | External (public) | 80 | Nginx frontend — the only public entry point |
| `chess-engine` | Internal | 8000 | Chess engine & game logic |
| `chess-auth` | External (public) | 8002 | JWT authentication service |
| `chess-admin` | Internal | 8001 | Admin dashboard backend |

### Public URLs

| Service | URL |
|---------|-----|
| Chess UI | `https://chess-ui.calmdesert-0b7461a5.eastus.azurecontainerapps.io` |
| Chess Auth | `https://chess-auth.calmdesert-0b7461a5.eastus.azurecontainerapps.io` |

### nginx Proxy Routing (chess-ui)

All browser requests go to `chess-ui`. nginx routes them to the appropriate backend:

| Path prefix | Proxy target | Transport |
|-------------|-------------|----------|
| `/auth/`, `/community/`, `/rewards/` | `chess-auth` external HTTPS URL | HTTPS (external ACA URL) |
| `/admin/` | `chess-admin` internal ACA FQDN | HTTPS (internal ACA FQDN) |
| `/move`, `/game/`, `/expert/` | `chess-engine` K8s ClusterIP | HTTP (internal) |

> **Note:** `chess-auth` uses its public HTTPS URL rather than the K8s ClusterIP because ACA's internal Envoy routing can become corrupted after a container app is deleted and recreated. Using the external URL bypasses this. `chess-admin` uses the internal ACA FQDN (`chess-admin.internal.calmdesert-0b7461a5.eastus.azurecontainerapps.io`) for the same reason, while keeping the service private.

### Persistent Storage

Both `chess-auth` and `chess-admin` mount the same Azure Files share (`chessdata`) for the SQLite database:

| Share | Mount path | Used by |
|-------|-----------|--------|
| `chessdata` | `/app/data` | chess-auth, chess-admin |
| `chessuserdata` | `/app/user_data` | chess-engine |

> **SQLite on Azure Files:** Azure Files (SMB) does not support POSIX `fcntl()` advisory locks. All `sqlite3.connect()` calls use the `unix-dotfile` VFS with a 30-second timeout: `sqlite3.connect("file:path?vfs=unix-dotfile", uri=True, timeout=30)`.

### Azure Resources

| Resource | Name |
|----------|------|
| Resource Group | `chess-ai-rg` |
| Location | `eastus` |
| Container Registry | `chessairegistry7646` |
| Storage Account | `chessaistorage4996` |
| Container Apps Environment | `chess-ai-env` |

---

## Migration from JSON to SQLite

If you have existing users in JSON files (`user_data/users/profiles/*.json`), import them manually into the SQLite database (`data/users.db`) before starting the services.

---

## Future Enhancements

- [ ] WebSocket support for real-time games (currently 2-second polling)
- [ ] Redis for session management
- [ ] PostgreSQL for production database
- [ ] Kubernetes deployment
- [ ] CI/CD pipeline
- [ ] Full game history and replay from saved games
- [x] Human vs Human multiplayer (browser-to-browser sync via `/game/sync`)
- [x] Community chat, DMs, and game invitations
- [x] Classic game review with step-through and move commentary
- [x] Classic game reward badges and Grand Scholar award
- [ ] ELO rating system
- [ ] Email verification with real SMTP
- [ ] Password reset functionality
- [ ] OAuth2 social login
- [ ] Mobile responsive design
- [ ] Tournament mode

---

## References

- [chessboard.js](https://chessboardjs.com/)
- [chess.js](https://github.com/jhlywa/chess.js)
- [FastAPI](https://fastapi.tiangolo.com/)
- [Docker Compose](https://docs.docker.com/compose/)
- [JWT.io](https://jwt.io/)
- [python-chess](https://python-chess.readthedocs.io/)
- [SQLite](https://www.sqlite.org/)
- [bcrypt](https://github.com/pyca/bcrypt)