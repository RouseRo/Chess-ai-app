# Chess AI App

A web-based chess application supporting human and AI players, with Stockfish engine integration, interactive chessboard, real-time game updates, and comprehensive microservices architecture.

## Table of Contents

- [Features](#features)
- [Project Structure](#project-structure)
- [Getting Started](#getting-started)
- [Running the Application](#running-the-application)
- [User Authentication](#user-authentication)
- [Admin Dashboard](#admin-dashboard)
- [API Services](#api-services)
- [Playing Chess](#playing-chess)
- [Configuration](#configuration)
- [Troubleshooting](#troubleshooting)
- [Architecture](#architecture)
- [Security](#security)
- [Future Enhancements](#future-enhancements)

## Features

- **Interactive Web UI**: Drag-and-drop chessboard with real-time updates
- **Multiple AI Engines**: 
  - Stockfish (local, fast, strong)
  - OpenAI GPT models
  - DeepSeek
  - Claude
  - Other LLM-based chess engines
- **Skill Level Control**: Adjust Stockfish difficulty from 1-20
- **Game Status Display**: Real-time check, checkmate, stalemate detection
- **Move History**: Track all moves in algebraic notation
- **Status Box**: Live feed of moves and engine responses
- **FEN Notation**: View and track game state
- **User Authentication**: Secure JWT-based authentication with bcrypt hashing
- **Admin Dashboard**: Manage users and system settings
- **Microservices Architecture**: Scalable, modular design with separate services
- **Docker Support**: Complete containerization with docker-compose

## Project Structure

```
Chess-ai-app/
├── engine/                      # Chess engine service (Port 8000)
│   ├── main.py                 # API endpoints & Stockfish integration
│   ├── Dockerfile              # Engine container config
│   └── requirements.txt        # Python dependencies
│
├── auth-service/               # Authentication service (Port 8002)
│   ├── main.py                # Auth API endpoints
│   ├── Dockerfile             # Auth container config
│   ├── requirements.txt       # Python dependencies
│   └── users.db               # SQLite database (auto-created)
│
├── admin-service/              # Admin dashboard service (Port 8001)
│   ├── main.py               # Admin API endpoints
│   ├── Dockerfile            # Admin container config
│   └── requirements.txt      # Python dependencies
│
├── ui/                         # Web interface (Port 8080)
│   ├── index.html            # Login/Register page
│   ├── chessboard.html       # Main game interface
│   ├── admin.html            # Admin dashboard
│   ├── chessboard.js         # Chessboard library
│   ├── chessboard.css        # Styling
│   ├── img/                  # Chess piece images
│   ├── nginx.conf            # Nginx configuration
│   └── Dockerfile            # UI container config
│
├── docs/                       # Documentation
│   └── Docker_Design.md      # Architecture documentation
│
├── docker-compose.yml          # Docker orchestration
├── .env                        # Environment variables (create this)
└── README.md                   # This file
```

## Getting Started

### Prerequisites

- **Docker Desktop** (recommended)
- **Web Browser** (Chrome, Firefox, Safari, Edge)

### Quick Start with Docker

1. **Clone the repository**
   ```powershell
   git clone <repository-url>
   cd Chess-ai-app
   ```

2. **Create environment file** (optional, for AI features)
   ```powershell
   # Create .env file in project root
   echo "OPENAI_API_KEY=your_key_here" > .env
   echo "DEEPSEEK_API_KEY=your_key_here" >> .env
   ```

3. **Build and run**
   ```powershell
   docker-compose up --build
   ```

4. **Access the application**
   - **Chess UI**: http://localhost:8080
   - **Admin Dashboard**: http://localhost:8080/admin.html

5. **Login with default credentials**
   - Username: `admin`
   - Password: `admin123`

## Running the Application

### Docker Compose (Recommended)

```powershell
# Start all services
docker-compose up --build

# Start in background
docker-compose up -d

# View logs
docker-compose logs -f

# Stop services
docker-compose down
```

### Service URLs

| Service | URL | Description |
|---------|-----|-------------|
| **Chess UI** | http://localhost:8080 | Main web interface |
| **Chessboard** | http://localhost:8080/chessboard.html | Game interface |
| **Admin Dashboard** | http://localhost:8080/admin.html | User management |
| **Auth API** | http://localhost:8002 | Authentication service |
| **Admin API** | http://localhost:8001 | Admin service |
| **Engine API** | http://localhost:8000 | Chess engine |

## User Authentication

### Default Admin Account

| Field | Value |
|-------|-------|
| Username | `admin` |
| Password | `admin123` |
| Email | `admin@chess.local` |

**Important**: Change the default password after first login.

### Authentication Flow

1. User enters credentials on login page
2. Auth service validates and returns JWT token
3. Token stored in browser localStorage
4. All API requests include token in Authorization header
5. Token expires after 24 hours

### Auth API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/health` | GET | Health check |
| `/auth/login` | POST | User login |
| `/auth/register` | POST | Create account |
| `/auth/verify` | POST | Validate token |
| `/auth/logout` | POST | End session |
| `/auth/change-password` | POST | Update password |

### Login Example

```powershell
# Login request
$response = Invoke-RestMethod -Uri "http://localhost:8002/auth/login" `
  -Method Post `
  -ContentType "application/json" `
  -Body '{"username":"admin","password":"admin123"}'

# Use token for authenticated requests
$token = $response.token
```

## Admin Dashboard

Access at **http://localhost:8080/admin.html**

### Features

| Tab | Description |
|-----|-------------|
| **Dashboard** | System statistics (users, games, models) |
| **User Management** | Create, delete, promote/demote users |
| **AI Models** | Configure AI model settings |
| **Settings** | Change admin password |

### Admin API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/health` | GET | Health check |
| `/admin/stats` | GET | System statistics |
| `/admin/users` | GET | List all users |
| `/admin/users/{username}/promote` | POST | Promote to admin |
| `/admin/users/{username}/demote` | POST | Demote from admin |
| `/admin/users/{username}` | DELETE | Delete user |

### Stats Response

```json
{
  "total_users": 2,
  "admin_count": 1,
  "verified_users": 0,
  "total_games": 0,
  "timestamp": "2025-12-08T02:46:18.517617"
}
```

## API Services

### Chess Engine (Port 8000)

| Endpoint | Method | Auth | Description |
|----------|--------|------|-------------|
| `/` | GET | No | Health check |
| `/move` | POST | Yes | Submit move & get AI response |
| `/ai/suggest` | GET | Yes | Get AI move suggestion |
| `/expert/question` | POST | Yes | Ask chess expert |
| `/expert/joke` | GET | Yes | Get chess joke |
| `/expert/fact` | GET | Yes | Get chess fact |

#### Submit Move

```powershell
$body = @{
    move = "e2e4"
    fen = "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1"
    request_ai_move = $true
    ai_type = "stockfish"
    skill_level = 10
} | ConvertTo-Json

Invoke-RestMethod -Uri "http://localhost:8000/move" `
  -Method Post `
  -ContentType "application/json" `
  -Headers @{Authorization="Bearer $token"} `
  -Body $body
```

#### Response

```json
{
  "success": true,
  "status": "AI move applied",
  "fen": "rnbqkbnr/pppp1ppp/8/4p3/4P3/8/PPPP1PPP/RNBQKBNR w KQkq e6 0 2",
  "ai_move": "e7e5",
  "ai_move_san": "e5",
  "ai_type": "stockfish"
}
```

## Playing Chess

### Start a Game

1. Login at http://localhost:8080
2. Select player types (Human/AI)
3. Choose AI engine (Stockfish recommended)
4. Set skill level (1-20)
5. Click "Start New Game"

### Make Moves

- Drag pieces to valid squares
- Invalid moves snap back automatically
- AI responds after your move
- Status box shows move history

### Game Status

| Status | Description |
|--------|-------------|
| Check | King is under attack |
| Checkmate | Game over, king captured |
| Stalemate | Draw, no legal moves |
| Draw | Game ends without winner |

### Skill Levels

| Level | Description |
|-------|-------------|
| 1-5 | Beginner (makes mistakes) |
| 6-10 | Intermediate |
| 11-15 | Advanced |
| 16-20 | Expert (very strong) |

## Configuration

### Environment Variables

Create a `.env` file in the project root:

```env
# AI API Keys (optional)
OPENAI_API_KEY=your_openai_key
DEEPSEEK_API_KEY=your_deepseek_key

# JWT Configuration (optional, has defaults)
JWT_SECRET_KEY=your_secret_key
JWT_EXPIRATION_HOURS=24
```

### Docker Compose Services

```yaml
services:
  chess-ui:        # Port 8080 - Frontend
  chess-engine:    # Port 8000 - Game logic
  chess-auth-service:    # Port 8002 - Authentication
  chess-admin-service:   # Port 8001 - Admin functions
```

## Troubleshooting

### Common Issues

| Issue | Solution |
|-------|----------|
| Can't login | Check credentials, verify auth service is running |
| Token expired | Logout and login again |
| AI not responding | Check engine logs: `docker logs chess-engine` |
| Port in use | `docker-compose down` then restart |
| CORS errors | Ensure all services are running |

### Health Checks

```powershell
# Check all services
curl http://localhost:8000/        # Engine
curl http://localhost:8001/health  # Admin
curl http://localhost:8002/health  # Auth
curl http://localhost:8001/admin/stats  # Stats
```

### View Logs

```powershell
# All services
docker-compose logs -f

# Specific service
docker logs chess-engine
docker logs chess-auth-service
docker logs chess-admin-service
docker logs chess-ui
```

### Reset Everything

```powershell
docker-compose down
docker volume prune -f
docker-compose build --no-cache
docker-compose up
```

### Browser Issues

1. Press **F12** to open Developer Tools
2. Check **Console** tab for errors
3. Check **Network** tab for failed requests
4. Clear cache: **Ctrl+Shift+Del**

## Architecture

```
┌─────────────────────────────────────────────────────────────────────┐
│                         Docker Network                               │
├─────────────────────────────────────────────────────────────────────┤
│                                                                      │
│  ┌──────────────┐    ┌──────────────┐    ┌──────────────────────┐   │
│  │   chess-ui   │    │ chess-engine │    │  chess-admin-service │   │
│  │  (Port 8080) │───▶│ (Port 8000)  │    │     (Port 8001)      │   │
│  └──────┬───────┘    └──────────────┘    └──────────┬───────────┘   │
│         │                                           │               │
│         │            ┌──────────────────────┐       │               │
│         └───────────▶│  chess-auth-service  │◀──────┘               │
│                      │     (Port 8002)      │                       │
│                      └──────────┬───────────┘                       │
│                                 │                                   │
│                      ┌──────────▼───────────┐                       │
│                      │   SQLite Database    │                       │
│                      │     (users.db)       │                       │
│                      └──────────────────────┘                       │
└─────────────────────────────────────────────────────────────────────┘
```

### Database

- **Type**: SQLite
- **Location**: `auth-service/users.db` (auto-created)
- **Tables**: `users`

### Users Table Schema

```sql
CREATE TABLE users (
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

## Security

### Current Implementation

| Feature | Status |
|---------|--------|
| Password Hashing | ✅ bcrypt |
| JWT Authentication | ✅ 24-hour expiry |
| CORS | ⚠️ Open (for development) |
| HTTPS | ❌ Not configured |
| Rate Limiting | ❌ Not implemented |

### Production Recommendations

1. Change default admin password
2. Set strong `JWT_SECRET_KEY`
3. Enable HTTPS/TLS
4. Restrict CORS origins
5. Add rate limiting
6. Use PostgreSQL instead of SQLite
7. Implement proper logging
8. Add monitoring/alerting

## Future Enhancements

- [ ] PGN export/import
- [ ] Game replay/analysis
- [ ] ELO rating system
- [ ] Multiplayer support
- [ ] PostgreSQL database
- [ ] WebSocket for real-time updates
- [ ] Mobile responsive design
- [ ] Opening book integration
- [ ] Tournament mode
- [ ] Game history storage

---

## Quick Reference

### URLs

| Service | URL |
|---------|-----|
| Login | http://localhost:8080 |
| Play Chess | http://localhost:8080/chessboard.html |
| Admin | http://localhost:8080/admin.html |

### Default Credentials

| Username | Password |
|----------|----------|
| admin | admin123 |

### Commands

```powershell
# Start
docker-compose up --build

# Stop
docker-compose down

# Logs
docker-compose logs -f

# Rebuild
docker-compose build --no-cache
```

---

**Enjoy playing chess with AI!** ♟️

For detailed architecture documentation, see [docs/Docker_Design.md](docs/Docker_Design.md).
