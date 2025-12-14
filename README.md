# Chess AI App

A web-based and CLI chess application supporting human and AI players, with Stockfish engine integration, interactive chessboard, real-time game updates, and comprehensive microservices architecture.

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
- **Command-Line Interface (CLI)**: Full-featured terminal-based chess game
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
- **Unified User Storage**: Single SQLite database shared across all clients
- **Admin Dashboard**: Manage users and system settings
- **Microservices Architecture**: Scalable, modular design with separate services
- **Docker Support**: Complete containerization with docker-compose

## Project Structure

```
Chess-ai-app/
├── src/                        # CLI Application
│   ├── main.py                # Main entry point
│   ├── auth_client.py         # HTTP client for auth-service API
│   ├── user_manager.py        # User management (uses AuthClient)
│   ├── auth_ui.py             # CLI authentication prompts
│   ├── game_manager.py        # Game logic
│   ├── ui_manager.py          # Terminal UI
│   └── ...                    # Other modules
│
├── engine/                     # Chess engine service (Port 8000)
│   ├── main.py                # API endpoints & Stockfish integration
│   ├── Dockerfile             # Engine container config
│   └── requirements.txt       # Python dependencies
│
├── auth-service/              # Authentication service (Port 8002)
│   ├── main.py               # Auth API endpoints
│   ├── Dockerfile            # Auth container config
│   └── requirements.txt      # Python dependencies
│
├── admin-service/             # Admin dashboard service (Port 8001)
│   ├── main.py              # Admin API endpoints
│   ├── Dockerfile           # Admin container config
│   └── requirements.txt     # Python dependencies
│
├── ui/                        # Web interface (Port 8080)
│   ├── index.html           # Login/Register page
│   ├── chessboard.html      # Main game interface
│   ├── admin.html           # Admin dashboard
│   ├── chessboard.js        # Chessboard library
│   ├── chessboard.css       # Styling
│   ├── img/                 # Chess piece images
│   ├── nginx.conf           # Nginx configuration
│   └── Dockerfile           # UI container config
│
├── data/                      # Shared database directory
│   └── users.db             # SQLite database (shared volume)
│
├── scripts/                   # Utility scripts
│   ├── setup_test_user.py   # Create/reset test users
│   └── migrate_json_to_sqlite.py
│
├── docs/                      # Documentation
│   └── Docker_Design.md     # Architecture documentation
│
├── docker-compose.yml         # Docker orchestration
├── requirements.txt           # CLI dependencies
├── .env                       # Environment variables (create this)
└── README.md                  # This file
```

## Getting Started

### Prerequisites

- **Docker Desktop** (for web services)
- **Python 3.12+** (for CLI application)
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
   | Username | Password |
   |----------|----------|
   | admin | admin123 |
   | johndoe | password123 |

### Quick Start with CLI

1. **Install Python dependencies**
   ```powershell
   pip install -r requirements.txt
   ```

2. **Ensure Docker services are running**
   ```powershell
   docker-compose up -d
   ```

3. **Run the CLI**
   ```powershell
   python -m src.main
   ```

4. **Login with credentials**
   ```
   --- Authentication Required ---
     1: Login
     2: Register New Account
     q: Quit Application
   Enter your choice: 1

   --- Login ---
   Username or Email: johndoe
   Password: password123
   ```

## Running the Application

### Docker Compose (Web Services)

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

### CLI Application

```powershell
# Ensure Docker services are running first
docker-compose up -d

# Run the CLI
python -m src.main
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

### Unified Authentication

All clients (CLI, Web UI, Admin Dashboard) authenticate through the same auth-service API and share a single SQLite database:

```
┌─────────────┐   ┌─────────────┐   ┌─────────────┐
│   CLI App   │   │   Web UI    │   │   Admin UI  │
└──────┬──────┘   └──────┬──────┘   └──────┬──────┘
       │                 │                 │
       └─────────────────┼─────────────────┘
                         │
                         ▼
              ┌─────────────────────┐
              │   Auth Service      │
              │   (Port 8002)       │
              └──────────┬──────────┘
                         │
                         ▼
              ┌─────────────────────┐
              │   SQLite Database   │
              │   data/users.db     │
              └─────────────────────┘
```

### Default Accounts

| Username | Password | Email | Admin |
|----------|----------|-------|-------|
| `admin` | `admin123` | admin@chess.local | Yes |
| `johndoe` | `password123` | john@example.com | No |

**Important**: Change the default passwords after first login.

### Authentication Flow

1. User enters credentials (login page or CLI)
2. Auth service validates with bcrypt and returns JWT token
3. Token stored in browser localStorage or CLI session
4. All API requests include token in Authorization header
5. Token expires after 24 hours

### Auth API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/health` | GET | Health check |
| `/auth/login` | POST | User login (username OR email) |
| `/auth/register` | POST | Create account |
| `/auth/verify` | POST | Validate token |
| `/auth/verify-email` | POST | Verify email with token |
| `/auth/logout` | POST | End session |
| `/auth/change-password` | POST | Update password |
| `/auth/refresh` | POST | Refresh JWT token |

### Login Example (API)

```powershell
# Login request (supports username OR email)
$response = Invoke-RestMethod -Uri "http://localhost:8002/auth/login" `
  -Method Post `
  -ContentType "application/json" `
  -Body '{"username":"johndoe","password":"password123"}'

# Response
# {
#   "success": true,
#   "message": "Welcome back, johndoe!",
#   "token": "eyJhbGciOiJIUzI1NiIs...",
#   "username": "johndoe",
#   "is_admin": false
# }

# Use token for authenticated requests
$token = $response.token
```

### Login Example (CLI)

```powershell
python -m src.main
```

```
--- Authentication Required ---
  1: Login
  2: Register New Account
  q: Quit Application
Enter your choice: 1

--- Login ---
Username or Email: johndoe
Password: 

Welcome back, johndoe!

--- Main Menu ---
  1: Play a New Game
  2: Load a Saved Game
  ...
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
| `/admin/users/{username}/verify` | POST | Manually verify user |
| `/admin/users/{username}` | DELETE | Delete user |

### Stats Response

```json
{
  "total_users": 2,
  "admin_count": 1,
  "verified_users": 2,
  "total_games": 0,
  "timestamp": "2025-12-15T10:30:00.000000+00:00"
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

### Web Interface

1. Login at http://localhost:8080
2. Select player types (Human/AI)
3. Choose AI engine (Stockfish recommended)
4. Set skill level (1-20)
5. Click "Start New Game"

### CLI Interface

1. Run `python -m src.main`
2. Login with your credentials
3. Select "Play a New Game" from the menu
4. Choose player types and AI settings
5. Enter moves in algebraic notation

### Make Moves

**Web UI:**
- Drag pieces to valid squares
- Invalid moves snap back automatically

**CLI:**
- Enter moves like `e2e4` or `Nf3`
- Type `help` for available commands

### Game Status

| Status | Description |
|--------|-------------|
| Check | King is under attack |
| Checkmate | Game over, king captured |
| Stalemate | Draw, no legal moves |
| Draw | Game ends without winner |

### Skill Levels (Stockfish)

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

# Development Mode (auto-verifies new users)
CHESS_DEV_MODE=false

# Auth Service URL (for CLI, default: http://localhost:8002)
AUTH_SERVICE_URL=http://localhost:8002
```

### Docker Compose Services

```yaml
services:
  chess-ui:            # Port 8080 - Frontend
  chess-engine:        # Port 8000 - Game logic
  auth-service:        # Port 8002 - Authentication
  admin-service:       # Port 8001 - Admin functions
```

### CLI Dependencies

Install with:
```powershell
pip install -r requirements.txt
```

Required packages:
- `requests>=2.28.0`
- `python-chess>=1.999`
- `bcrypt>=4.0.0`

## Troubleshooting

### Common Issues

| Issue | Solution |
|-------|----------|
| Can't login (Web) | Check credentials, verify auth service is running |
| Can't login (CLI) | Ensure Docker services are running and `requests` is installed |
| "Invalid username or password" | Reset password with `scripts/setup_test_user.py` |
| Token expired | Logout and login again |
| AI not responding | Check engine logs: `docker logs chess-engine` |
| Port in use | `docker-compose down` then restart |
| CORS errors | Ensure all services are running |
| Database not syncing | Copy manually: `docker cp data/users.db chess-auth-service:/app/data/` |

### Health Checks

```powershell
# Check all services
curl http://localhost:8000/        # Engine
curl http://localhost:8001/health  # Admin
curl http://localhost:8002/health  # Auth
curl http://localhost:8001/admin/stats  # Stats
```

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

### Reset Test Users

```powershell
# Run setup script to reset passwords
python scripts/setup_test_user.py

# Copy database to container
docker cp data/users.db chess-auth-service:/app/data/users.db

# Restart auth service
docker-compose restart auth-service
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
│         │    auth-service      │◀───────────────────────┐               │
│         │     (Port 8002)      │                        │               │
│         └──────────┬───────────┘                        │               │
│                    │                                    │               │
│                    ▼                                    │               │
│         ┌──────────────────────┐         ┌──────────────┴───────────┐   │
│         │   SQLite Database    │◀────────│    admin-service         │   │
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

### Database

- **Type**: SQLite
- **Location**: `data/users.db` (shared volume)
- **Accessed by**: auth-service, admin-service
- **CLI Access**: Via auth-service API (http://localhost:8002)

### Users Table Schema

```sql
CREATE TABLE users (
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

## Security

### Current Implementation

| Feature | Status |
|---------|--------|
| Password Hashing | ✅ bcrypt |
| JWT Authentication | ✅ 24-hour expiry |
| Unified User Storage | ✅ Single SQLite database |
| Login by Username/Email | ✅ Supported |
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
- [ ] Email verification with SMTP
- [ ] Password reset functionality
- [ ] OAuth2 social login

---

## Quick Reference

### URLs

| Service | URL |
|---------|-----|
| Login | http://localhost:8080 |
| Play Chess | http://localhost:8080/chessboard.html |
| Admin | http://localhost:8080/admin.html |

### Default Credentials

| Username | Password | Admin |
|----------|----------|-------|
| admin | admin123 | Yes |
| johndoe | password123 | No |

### Commands

```powershell
# Start Docker services
docker-compose up --build

# Start in background
docker-compose up -d

# Run CLI
python -m src.main

# Stop services
docker-compose down

# View logs
docker-compose logs -f

# Reset test users
python scripts/setup_test_user.py
docker-compose restart auth-service

# Rebuild
docker-compose build --no-cache
```

---

**Enjoy playing chess with AI!** ♟️

For detailed architecture documentation, see [docs/Docker_Design.md](docs/Docker_Design.md).
