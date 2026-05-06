# Docker Architecture: Chess AI App

This document describes the Docker-based microservices architecture for the Chess AI App.

---

## Overview

The application consists of **four containerized microservices** plus a CLI application, all sharing a unified SQLite database for user authentication:

| Service | Port | Description |
|---------|------|-------------|
| **chess-ui** | 8080 | Frontend web interface with chessboard |
| **chess-engine** | 8000 | Chess game logic and AI integration |
| **chess-admin-service** | 8001 | Admin dashboard and user management |
| **chess-auth-service** | 8002 | Authentication and JWT token management |
| **CLI App** | - | Command-line interface (`python -m src.main`) |

---

## Architecture Diagram

```
┌─────────────────────────────────────────────────────────────────────────┐
│                              Clients                                     │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                          │
│  ┌──────────────┐    ┌──────────────┐    ┌──────────────────────────┐   │
│  │   CLI App    │    │   Web UI     │    │   Admin Dashboard        │   │
│  │ (python -m   │    │ (Port 8080)  │    │   (Port 8080/admin.html) │   │
│  │  src.main)   │    │              │    │                          │   │
│  └──────┬───────┘    └──────┬───────┘    └────────────┬─────────────┘   │
│         │                   │                         │                  │
└─────────┼───────────────────┼─────────────────────────┼──────────────────┘
          │                   │                         │
          │     HTTP API      │                         │
          └─────────┬─────────┴─────────────────────────┘
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

All clients (CLI, Web UI, Admin Dashboard) authenticate through the same auth-service API:

```
┌─────────────┐   ┌─────────────┐   ┌─────────────┐
│   CLI App   │   │   Web UI    │   │   Admin UI  │
│             │   │             │   │             │
│ AuthClient  │   │  fetch()    │   │  fetch()    │
└──────┬──────┘   └──────┬──────┘   └──────┬──────┘
       │                 │                 │
       │    HTTP POST /auth/login          │
       └─────────────────┼─────────────────┘
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
├── src/                       # CLI Application
│   ├── main.py               # Main entry point
│   ├── auth_client.py        # HTTP client for auth-service
│   ├── user_manager.py       # User management (uses AuthClient)
│   ├── auth_ui.py            # CLI authentication prompts
│   └── ...
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
│   ├── index.html             # Login page
│   ├── chessboard.html        # Game interface
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
├── scripts/                   # Utility scripts
│   ├── setup_test_user.py    # Create/reset test users
│   └── migrate_json_to_sqlite.py
│
├── docs/                      # Documentation
│   └── Docker_Design.md
│
├── docker-compose.yml         # Container orchestration
├── requirements.txt           # CLI dependencies
└── .env                       # Environment variables
```

---

## Services

### 1. CLI Application

**Purpose:** Command-line interface for playing chess, managing games, and user authentication.

**Tech Stack:**
- Python 3.12
- requests (for HTTP API calls)
- python-chess

**Authentication:**
The CLI uses `AuthClient` to communicate with the auth-service:

```python
from src.auth_client import AuthClient

client = AuthClient("http://localhost:8002")
success, message, token = client.login("johndoe", "password123")
```

**Running the CLI:**
```bash
python -m src.main
```

---

### 2. Chess UI (Port 8080)

**Purpose:** Serves the frontend web application with interactive chessboard.

**Tech Stack:**
- nginx (Alpine-based)
- HTML/CSS/JavaScript
- chessboard.js library
- chess.js for move validation

**Pages:**
| Page | Description |
|------|-------------|
| `index.html` | Login/Register page |
| `chessboard.html` | Main game interface |
| `admin.html` | Admin dashboard |

**Dockerfile:**
```dockerfile
FROM nginx:alpine
COPY . /usr/share/nginx/html
COPY nginx.conf /etc/nginx/conf.d/default.conf
EXPOSE 80
```

---

### 3. Chess Engine (Port 8000)

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
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
EXPOSE 8000
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
```

---

### 4. Auth Service (Port 8002)

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
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
EXPOSE 8002
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8002"]
```

---

### 5. Admin Service (Port 8001)

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
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
EXPOSE 8001
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8001"]
```

---

## Docker Compose

**docker-compose.yml:**
```yaml
version: '3.8'

services:
  chess-engine:
    build: ./engine
    container_name: chess-engine
    ports:
      - "8000:8000"
    environment:
      - OPENAI_API_KEY=${OPENAI_API_KEY}
      - DEEPSEEK_API_KEY=${DEEPSEEK_API_KEY}
    networks:
      - chess-network
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/"]
      interval: 30s
      timeout: 10s
      retries: 3

  chess-ui:
    build: ./ui
    container_name: chess-ui
    ports:
      - "8080:80"
    depends_on:
      - chess-engine
      - auth-service
    networks:
      - chess-network

  auth-service:
    build: ./auth-service
    container_name: chess-auth-service
    ports:
      - "8002:8002"
    environment:
      - DATABASE_PATH=/app/data/users.db
      - JWT_SECRET_KEY=${JWT_SECRET_KEY:-chess-app-secret-key}
      - JWT_EXPIRATION_HOURS=${JWT_EXPIRATION_HOURS:-24}
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

  admin-service:
    build: ./admin-service
    container_name: chess-admin-service
    ports:
      - "8001:8001"
    environment:
      - DATABASE_PATH=/app/data/users.db
    volumes:
      - ./data:/app/data
    depends_on:
      - auth-service
    networks:
      - chess-network
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8001/health"]
      interval: 30s
      timeout: 10s
      retries: 3

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
| CLI Application | Accesses via auth-service API (http://localhost:8002) |

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

```powershell
# Run the setup script
python scripts/setup_test_user.py

# Copy database to container (if needed)
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

### CLI Login Sequence

```
┌─────────┐         ┌────────────┐         ┌──────────────┐
│   CLI   │         │ AuthClient │         │ Auth Service │
└────┬────┘         └─────┬──────┘         └──────┬───────┘
     │                    │                       │
     │  User enters       │                       │
     │  credentials       │                       │
     │                    │                       │
     │  login(user, pass) │                       │
     │───────────────────▶│                       │
     │                    │                       │
     │                    │  POST /auth/login     │
     │                    │  {username, password} │
     │                    │──────────────────────▶│
     │                    │                       │
     │                    │                       │  Validate with bcrypt
     │                    │                       │  Generate JWT
     │                    │                       │
     │                    │  {success, token}     │
     │                    │◀──────────────────────│
     │                    │                       │
     │  (success, msg,    │                       │
     │   token)           │                       │
     │◀───────────────────│                       │
     │                    │                       │
     │  Store token       │                       │
     │  Show menu         │                       │
```

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
     │  chessboard.html  │                      │
     │──────────────────▶│                      │
```

---

## Running the Application

### Prerequisites

1. Docker and Docker Compose installed
2. Python 3.12+ (for CLI)
3. Required Python packages: `pip install -r requirements.txt`

### Start All Docker Services

```bash
cd c:\Users\rober\Source\Repos\Chess-ai-app
docker-compose up --build
```

### Start in Background

```bash
docker-compose up -d
```

### Run CLI Application

```bash
# Ensure Docker services are running first
python -m src.main
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
| Login Page | http://localhost:8080 |
| Chessboard | http://localhost:8080/chessboard.html |
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
DEEPSEEK_API_KEY=your_deepseek_key

# JWT Configuration
JWT_SECRET_KEY=your-secure-secret-key-change-in-production
JWT_EXPIRATION_HOURS=24

# Development Mode (auto-verifies new users)
CHESS_DEV_MODE=false

# Auth Service URL (for CLI)
AUTH_SERVICE_URL=http://localhost:8002
```

---

## CLI Dependencies

The CLI application requires these Python packages (in `requirements.txt`):

```
requests>=2.28.0
python-chess>=1.999
bcrypt>=4.0.0
```

Install with:
```bash
pip install -r requirements.txt
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
| "Invalid username or password" (CLI) | Ensure `requests` is installed: `pip install requests` |
| CLI can't reach auth service | Ensure Docker services are running: `docker-compose up -d` |
| Database not syncing | Copy manually: `docker cp data/users.db chess-auth-service:/app/data/` |
| Port already in use | `docker-compose down` then retry |
| Token expired | Login again |

### Debug CLI Authentication

```powershell
# Test AuthClient directly
python -c "
from src.auth_client import AuthClient
client = AuthClient()
print('Health:', client.health_check())
success, msg, token = client.login('johndoe', 'password123')
print('Login:', success, msg)
"
```

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

If you have existing users in JSON files (`user_data/users/profiles/*.json`), run the migration script:

```powershell
python scripts/migrate_json_to_sqlite.py
docker cp data/users.db chess-auth-service:/app/data/users.db
docker-compose restart auth-service
```

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