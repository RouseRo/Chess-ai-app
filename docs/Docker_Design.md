# Docker Architecture: Chess AI App

This document describes the Docker-based microservices architecture for the Chess AI App.

---

## Overview

The application consists of **four containerized microservices**:

| Service | Port | Description |
|---------|------|-------------|
| **chess-ui** | 8080 | Frontend web interface with chessboard |
| **chess-engine** | 8000 | Chess game logic and AI integration |
| **chess-admin-service** | 8001 | Admin dashboard and user management |
| **chess-auth-service** | 8002 | Authentication and JWT token management |

---

## Architecture Diagram

```
┌─────────────────────────────────────────────────────────────────────┐
│                         Docker Network                               │
├─────────────────────────────────────────────────────────────────────┤
│                                                                      │
│  ┌──────────────┐    ┌──────────────┐    ┌──────────────────────┐   │
│  │              │    │              │    │  chess-admin-service │   │
│  │   chess-ui   │───▶│ chess-engine │    │     (Port 8001)      │   │
│  │  (Port 8080) │    │ (Port 8000)  │    │                      │   │
│  │              │    │              │    │                      │   │
│  └──────┬───────┘    └──────────────┘    └──────────┬───────────┘   │
│         │                                           │               │
│         │            ┌──────────────────────┐       │               │
│         │            │                      │       │               │
│         └───────────▶│  chess-auth-service  │◀──────┘               │
│                      │     (Port 8002)      │                       │
│                      │                      │                       │
│                      └──────────┬───────────┘                       │
│                                 │                                   │
│                      ┌──────────▼───────────┐                       │
│                      │                      │                       │
│                      │   SQLite Database    │                       │
│                      │     (users.db)       │                       │
│                      │                      │                       │
│                      └──────────────────────┘                       │
│                                                                      │
└─────────────────────────────────────────────────────────────────────┘
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
│   ├── requirements.txt
│   └── users.db               # SQLite database (created at runtime)
│
├── admin-service/             # Admin management service
│   ├── Dockerfile
│   ├── main.py
│   ├── requirements.txt
│   └── ...
│
├── docs/                      # Documentation
│   └── Docker_Design.md
│
└── docker-compose.yml         # Container orchestration
```

---

## Services

### 1. Chess UI (Port 8080)

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
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
EXPOSE 8000
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
```

---

### 3. Auth Service (Port 8002)

**Purpose:** Manages user authentication, registration, and JWT tokens.

**Tech Stack:**
- Python 3.12
- FastAPI
- SQLite
- PyJWT
- bcrypt

**Database Location:** `auth-service/users.db` (auto-created on first run)

**Endpoints:**
| Endpoint | Method | Description |
|----------|--------|-------------|
| `/health` | GET | Health check |
| `/auth/login` | POST | User login, returns JWT |
| `/auth/register` | POST | User registration |
| `/auth/verify` | POST | Validate JWT token |
| `/auth/refresh` | POST | Refresh JWT token |
| `/auth/logout` | POST | Logout (client-side) |
| `/auth/change-password` | POST | Update password |

**JWT Token Structure:**
```json
{
  "username": "admin",
  "is_admin": true,
  "exp": 1764999103,
  "iat": 1764912703
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

### 4. Admin Service (Port 8001)

**Purpose:** Provides admin dashboard functionality, user management, and system statistics.

**Tech Stack:**
- Python 3.12
- FastAPI
- SQLite (connects to auth-service database)

**Endpoints:**
| Endpoint | Method | Auth | Description |
|----------|--------|------|-------------|
| `/health` | GET | No | Health check |
| `/admin/stats` | GET | No | System statistics |
| `/admin/users` | GET | No | List all users |
| `/admin/users/{username}/promote` | POST | Yes | Promote user to admin |
| `/admin/users/{username}/demote` | POST | Yes | Demote admin to user |
| `/admin/users/{username}` | DELETE | Yes | Delete user |
| `/admin/models` | GET | Yes | List AI models |
| `/admin/models/add` | POST | Yes | Add AI model |
| `/admin/models/{id}/toggle` | POST | Yes | Toggle model status |
| `/admin/models/{id}` | DELETE | Yes | Delete model |

**Stats Response Example:**
```json
{
  "total_users": 2,
  "admin_count": 1,
  "verified_users": 0,
  "total_games": 0,
  "timestamp": "2025-12-08T02:46:18.517617"
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
      - chess-auth-service
    networks:
      - chess-network

  chess-auth-service:
    build: ./auth-service
    container_name: chess-auth-service
    ports:
      - "8002:8002"
    volumes:
      - auth-data:/app/data
    networks:
      - chess-network
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8002/health"]
      interval: 30s
      timeout: 10s
      retries: 3

  chess-admin-service:
    build: ./admin-service
    container_name: chess-admin-service
    ports:
      - "8001:8001"
    volumes:
      - auth-data:/app/data
    depends_on:
      - chess-auth-service
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

volumes:
  auth-data:
```

---

## Authentication Flow

### Login Sequence

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

### Authenticated Request

```
┌─────────┐         ┌──────────────┐         ┌──────────────┐
│   UI    │         │ Chess Engine │         │ Auth Service │
└────┬────┘         └──────┬───────┘         └──────┬───────┘
     │                     │                        │
     │  POST /move         │                        │
     │  Auth: Bearer <JWT> │                        │
     │────────────────────▶│                        │
     │                     │                        │
     │                     │  POST /auth/verify     │
     │                     │  {token}               │
     │                     │───────────────────────▶│
     │                     │                        │
     │                     │  {valid, username}     │
     │                     │◀───────────────────────│
     │                     │                        │
     │                     │  Process move          │
     │                     │                        │
     │  {success, newFen}  │                        │
     │◀────────────────────│                        │
```

---

## CORS Configuration

All backend services include CORS middleware to allow cross-origin requests from the UI:

```python
from fastapi.middleware.cors import CORSMiddleware

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

**Production Note:** Replace `allow_origins=["*"]` with specific allowed origins.

---

## Database

### Location

The SQLite database is created automatically by the auth-service on first startup:

| Environment | Location |
|-------------|----------|
| Docker Container | `/app/users.db` or `/app/data/users.db` |
| Local Development | `auth-service/users.db` |

### Users Table Schema

```sql
CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT UNIQUE NOT NULL,
    email TEXT UNIQUE NOT NULL,
    password_hash TEXT NOT NULL,
    is_admin BOOLEAN DEFAULT 0,
    is_verified BOOLEAN DEFAULT 0,
    games_count INTEGER DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

### Default Admin User

Created automatically on first startup:

| Field | Value |
|-------|-------|
| Username | `admin` |
| Email | `admin@chess.local` |
| Password | `admin123` |
| Is Admin | `true` |

### Database Initialization Code

```python
def init_db():
    conn = sqlite3.connect('users.db')
    cursor = conn.cursor()
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            email TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            is_admin BOOLEAN DEFAULT 0,
            is_verified BOOLEAN DEFAULT 0,
            games_count INTEGER DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # Create default admin user if not exists
    cursor.execute('SELECT * FROM users WHERE username = ?', ('admin',))
    if not cursor.fetchone():
        password_hash = bcrypt.hashpw('admin123'.encode(), bcrypt.gensalt())
        cursor.execute('''
            INSERT INTO users (username, email, password_hash, is_admin)
            VALUES (?, ?, ?, ?)
        ''', ('admin', 'admin@chess.local', password_hash.decode(), True))
    
    conn.commit()
    conn.close()
```

---

## Running the Application

### Start All Services

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

### Rebuild Specific Service

```bash
docker-compose build chess-ui
docker-compose up -d chess-ui
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

# Admin Service
curl http://localhost:8001/health

# Chess Engine
curl http://localhost:8000/

# Admin Stats
curl http://localhost:8001/admin/stats
```

**Expected Responses:**
```json
// Health check
{"status": "healthy"}

// Admin stats
{"total_users": 2, "admin_count": 1, "verified_users": 0, "total_games": 0}
```

---

## Environment Variables

Create a `.env` file in the project root:

```env
# AI API Keys
OPENAI_API_KEY=your_openai_key
DEEPSEEK_API_KEY=your_deepseek_key

# JWT Configuration (optional - defaults provided)
JWT_SECRET_KEY=your_secret_key
JWT_EXPIRATION_HOURS=24
```

---

## Security Considerations

### Current Implementation

| Feature | Status |
|---------|--------|
| Password Hashing | ✅ bcrypt |
| JWT Authentication | ✅ Implemented |
| CORS | ⚠️ Open (restrict in prod) |
| HTTPS | ❌ Not configured |
| Rate Limiting | ❌ Not implemented |
| Input Validation | ✅ Basic |

### Production Recommendations

1. **Enable HTTPS** - Use SSL certificates
2. **Restrict CORS** - Specify allowed origins
3. **Add Rate Limiting** - Prevent abuse
4. **Use Environment Variables** - For sensitive data
5. **Database Backup** - Regular SQLite backups
6. **Logging** - Centralized logging solution
7. **Monitoring** - Health check alerts
8. **Change Default Admin Password** - Update on first login

---

## Troubleshooting

### Common Issues

| Issue | Solution |
|-------|----------|
| Port already in use | `docker-compose down` then retry |
| Database locked | Restart auth-service |
| CORS errors | Check browser console, verify origins |
| Token expired | Login again |
| 404 favicon | Add favicon.ico to ui folder |
| Database not found | Auth-service creates it automatically on startup |

### View Container Logs

```bash
# All containers
docker-compose logs

# Specific container
docker-compose logs chess-auth-service

# Follow logs
docker-compose logs -f chess-engine
```

### Access Container Shell

```bash
docker exec -it chess-engine /bin/sh
docker exec -it chess-auth-service /bin/bash
```

### View Database Contents

```bash
# Access auth-service container
docker exec -it chess-auth-service /bin/bash

# Inside container, use sqlite3
sqlite3 users.db
.tables
SELECT * FROM users;
.quit
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
- [ ] Shared volume for database between services

---

## References

- [chessboard.js](https://chessboardjs.com/)
- [chess.js](https://github.com/jhlywa/chess.js)
- [FastAPI](https://fastapi.tiangolo.com/)
- [Docker Compose](https://docs.docker.com/compose/)
- [JWT.io](https://jwt.io/)
- [python-chess](https://python-chess.readthedocs.io/)
- [SQLite](https://www.sqlite.org/)