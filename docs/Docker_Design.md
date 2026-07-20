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
│   ├── index.html             # Login/Register + game interface (single-page app)
│   ├── admin.html             # Admin dashboard
│   ├── chessboard.js
│   ├── chessboard.css
│   └── img/
│
├── auth-service/              # Authentication service
│   ├── Dockerfile
│   ├── main.py
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
| `/auth/change-password` | POST | Update password |

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
HEALTHCHECK --interval=30s --timeout=10s --start-period=10s --retries=3 \
    CMD curl -f http://localhost:8002/health || exit 1
CMD ["uvicorn", "auth-service.main:app", "--host", "0.0.0.0", "--port", "8002"]
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
| `/admin/users` | GET | No | List all users |
| `/admin/users/{username}/promote` | POST | Yes | Promote user to admin |
| `/admin/users/{username}/demote` | POST | Yes | Demote admin to user |
| `/admin/users/{username}/verify` | POST | Yes | Manually verify user |
| `/admin/users/{username}` | DELETE | Yes | Delete user |

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
    environment:
      - DATABASE_PATH=/app/data/users.db
      - JWT_SECRET_KEY=${JWT_SECRET_KEY:-chess-app-secret-key}
      - CHESS_DEV_MODE=${CHESS_DEV_MODE:-false}
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
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

### Default Users

Created automatically on first startup or via setup script:

| Username | Email | Password | Admin | Verified |
|----------|-------|----------|-------|----------|
| `admin` | `admin@chess.local` | `admin123` | Yes | Yes |
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
| HTTPS | ❌ Not configured |
| Rate Limiting | ❌ Not implemented |
| Input Validation | ✅ Basic |

### Production Recommendations

1. **Enable HTTPS** - Use SSL certificates
2. **Restrict CORS** - Specify allowed origins
3. **Add Rate Limiting** - Prevent brute force attacks
4. **Use Strong JWT Secret** - Generate secure random key
5. **Database Backup** - Regular SQLite backups
6. **Change Default Passwords** - Update admin/johndoe on first use
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

## Migration from JSON to SQLite

If you have existing users in JSON files (`user_data/users/profiles/*.json`), import them manually into the SQLite database (`data/users.db`) before starting the services.

---

## Future Enhancements

- [ ] WebSocket support for real-time games
- [ ] Redis for session management
- [ ] PostgreSQL for production database
- [ ] Kubernetes deployment
- [ ] CI/CD pipeline
- [ ] Game history and replay
- [ ] Multiplayer support
- [ ] ELO rating system
- [ ] Email verification with real SMTP
- [ ] Password reset functionality
- [ ] OAuth2 social login

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