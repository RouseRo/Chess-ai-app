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
- [User Management](#user-management)
- [Configuration](#configuration)
- [Game Logging](#game-logging)
- [Troubleshooting](#troubleshooting)
- [Notes](#notes)

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
├── engine/                      # Chess engine (FastAPI backend)
│   ├── main.py                 # API endpoints & Stockfish integration
│   ├── user_manager.py         # User data management
│   ├── Dockerfile              # Engine container config
│   └── requirements.txt         # Python dependencies
├── auth-service/               # Authentication service
│   ├── main.py                # Auth API endpoints
│   ├── Dockerfile             # Auth container config
│   └── requirements.txt        # Python dependencies
├── admin-service/              # Admin dashboard service
│   ├── main.py               # Admin API endpoints
│   ├── static/               # Admin UI files
│   ├── Dockerfile            # Admin container config
│   └── requirements.txt       # Python dependencies
├── ui/                         # Web interface (Frontend)
│   ├── index.html            # Main UI with login/chessboard
│   ├── chessboard.js         # Chessboard library
│   ├── chessboard.css        # Styling
│   ├── img/                  # Chess piece images
│   ├── nginx.conf            # Nginx configuration
│   └── Dockerfile            # UI container config
├── src/                        # Core application logic
│   ├── main.py              # Command-line entry point
│   ├── chess_game.py        # Game logic
│   ├── expert_service.py    # Chess expert AI service
│   └── config.json          # Configuration
├── user_data/                # User database
│   └── users/               # Individual user JSON files
├── docker-compose.yml        # Docker orchestration
├── add_user.py              # User management script
├── reset_admin.py           # Admin password reset script
└── README.md                # This file
```

## Getting Started

### Prerequisites

- **Python 3.12+** with virtual environment
- **Docker Desktop** (for containerized deployment)
- **Web Browser** (Chrome, Firefox, Safari, Edge)
- **Stockfish** (automatically installed in Docker)

### Installation

1. **Clone the repository**
   ```powershell
   git clone <repository-url>
   cd Chess-ai-app
   ```

2. **Set up Python virtual environment** (optional for Docker)
   ```powershell
   python -m venv .venv
   .\.venv\Scripts\Activate
   ```

3. **Install dependencies** (if running without Docker)
   ```powershell
   pip install -r engine/requirements.txt
   ```

4. **Configure environment variables**
   Create a `.env` file in the project root:
   ```env
   OPENAI_API_KEY=your_openai_api_key_here
   JWT_SECRET_KEY=your_secret_key_here_change_in_production
   STOCKFISH_PATH=/usr/games/stockfish
   ```

## Running the Application

### Option 1: Docker Compose (Recommended) ⭐

1. **Start Docker Desktop**
   ```powershell
   docker --version
   ```

2. **Build and run the application**
   ```powershell
   cd Chess-ai-app
   docker-compose build --no-cache
   docker-compose up
   ```

3. **Access the services**
   
   | Service | URL | Purpose |
   |---------|-----|---------|
   | **Chess UI** | http://localhost:8080 | Main web interface - Play chess |
   | **Auth Service** | http://localhost:8002 | User authentication |
   | **Admin Service** | http://localhost:8001 | Admin dashboard |
   | **Chess Engine** | http://localhost:8000 | Game engine API |

4. **Default Login Credentials**
   - Username: `admin`
   - Password: `admin123`

5. **Stop the application**
   ```powershell
   docker-compose down
   ```

### Option 2: Manual Setup (Development)

**Terminal 1: Start the Chess Engine**
```powershell
cd Chess-ai-app
pip install python-chess uvicorn fastapi
uvicorn engine.main:app --reload --port 8000
```

**Terminal 2: Start Auth Service**
```powershell
cd Chess-ai-app
pip install uvicorn fastapi bcrypt pyjwt
uvicorn auth-service.main:app --reload --port 8002
```

**Terminal 3: Start Admin Service**
```powershell
cd Chess-ai-app
pip install uvicorn fastapi
uvicorn admin-service.main:app --reload --port 8001
```

**Terminal 4: Serve the UI**
```powershell
cd Chess-ai-app/ui
python -m http.server 8080
```

**Then visit:** http://localhost:8080

### Option 3: Command-line Version

Run the application directly from the terminal (without web UI):

```powershell
cd Chess-ai-app
python -m src.main
```

## User Authentication

### Default Admin Account

The application includes a default admin account:
- **Username**: `admin`
- **Password**: `admin123`

To change admin password:
```powershell
python reset_admin.py
```

### Create New Users

**Interactive mode:**
```powershell
python add_user.py
```

**Command line:**
```powershell
# Add regular user
python add_user.py -u johndoe -e john@example.com -p mypassword123

# Add admin user
python add_user.py -u newadmin -e admin2@example.com -p adminpass123 --admin

# List all users
python add_user.py --list
```

### Login via API

```powershell
$response = Invoke-RestMethod -Uri "http://localhost:8002/auth/login" `
  -Method Post `
  -ContentType "application/json" `
  -Body '{"username":"admin","password":"admin123"}'

$token = $response.token
Write-Host "Token: $token"
```

**Response:**
```json
{
  "success": true,
  "token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "username": "admin",
  "email": "admin@chess.local",
  "is_admin": true
}
```

### Authentication Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/auth/register` | POST | Create new user account |
| `/auth/login` | POST | Authenticate and receive JWT token |
| `/auth/logout` | POST | End user session |
| `/auth/verify` | POST | Verify JWT token validity |
| `/auth/refresh` | POST | Refresh JWT token |
| `/auth/change-password` | POST | Change user password |

## Admin Dashboard

Access the admin dashboard at **http://localhost:8001**

### Admin Features

- **User Management**: View, create, delete, promote/demote users
- **AI Model Management**: Add, remove, configure AI models
- **System Statistics**: View game stats and system health
- **Service Health**: Monitor all microservices

### Admin API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/admin/users` | GET | List all users |
| `/admin/users/delete` | POST | Delete a user |
| `/admin/users/promote` | POST | Promote user to admin |
| `/admin/users/demote` | POST | Demote admin to user |
| `/admin/models` | GET | List AI models |
| `/admin/models/add` | POST | Add new AI model |
| `/admin/models/remove` | POST | Remove AI model |
| `/admin/stats` | GET | Get system statistics |

## Playing Chess

### Web UI Gameplay

1. **Start a New Game**
   - Select White and Black players (Human or AI)
   - Choose AI type (Stockfish recommended)
   - Set skill level (1-20, where 20 is hardest)
   - Click "Start New Game"

2. **Make Moves**
   - Drag a piece to a legal square
   - The move is validated locally
   - Status box shows confirmation
   - AI responds automatically (if configured)

3. **Monitor Game Status**
   - **Status Box**: Shows all moves and AI responses with timestamps
   - **Move History**: Tracks moves in algebraic notation (e.g., "e4", "Nf3")
   - **Game Status**: Displays current turn, check, checkmate, etc.
   - **FEN Display**: View board state in FEN notation

4. **Game Events**
   - Check detection: "White is in check"
   - Checkmate: "Black wins by checkmate!"
   - Stalemate: "Game drawn!"
   - Invalid moves: Piece snaps back with error message

### UI Components

```
┌──────────────────────────────────────────────────────────────┐
│  Welcome, admin  |  Chess AI App  |  [Logout]              │
├─────────────────┬──────────────────────────────────────────┤
│                 │                                          │
│   Chessboard    │          Game Panel                      │
│                 │  ┌──────────────────────────┐            │
│                 │  │ Player Setup             │            │
│  ┌───────────┐  │  │ White: Human             │            │
│  │ ♖ ♘ ♗ ♕  │  │  │ Black: AI                │            │
│  │ ♙ ♙ ♙ ♙  │  │  │ AI Type: Stockfish      │            │
│  │ □ □ □ □  │  │  │ Skill: [10]              │            │
│  │ □ □ □ □  │  │  │ [Start New Game]         │            │
│  │ ♟ ♟ ♟ ♟  │  │  └──────────────────────────┘            │
│  │ ♜ ♞ ♝ ♛  │  │  ┌──────────────────────────┐            │
│  └───────────┘  │  │ Move History             │            │
│                 │  │ 1. e4 e5                 │            │
│ Status Box:     │  │ 2. Nf3 Nc6              │            │
│ [12:34:56] You  │  │                          │            │
│ played: e4      │  │ FEN: rnbqkbnr...        │            │
│                 │  │                          │            │
│ [12:34:57] AI   │  │                          │            │
│ played: c5      │  │                          │            │
└─────────────────┴──────────────────────────────────────────┘
```

## API Services

### Chess Engine (Port 8000)

**Base URL:** `http://localhost:8000`

| Endpoint | Method | Description | Auth Required |
|----------|--------|-------------|---------------|
| `/` | GET | Health check | No |
| `/health` | GET | Service health | No |
| `/move` | POST | Submit move & get AI response | Yes |
| `/ai/suggest` | GET | Get AI move suggestion | Yes |
| `/expert/question` | POST | Ask chess expert | Yes |

#### POST /move

Submit a chess move and receive AI response.

**Request:**
```powershell
$token = "your_jwt_token"
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

**Response:**
```json
{
  "success": true,
  "status": "AI move applied",
  "fen": "rnbqkbnr/pppppppp/8/8/4P3/8/PPPP1PPP/RNBQKBNR b KQkq e3 0 1",
  "ai_move": "e7e5",
  "ai_move_san": "e5",
  "ai_type": "stockfish",
  "source": "chess-engine-1"
}
```

#### GET /ai/suggest

Get an AI move suggestion for the current position.

**Request:**
```powershell
$fen = "rnbqkbnr/pppppppp/8/8/4P3/8/PPPP1PPP/RNBQKBNR b KQkq e3 0 1"
Invoke-RestMethod -Uri "http://localhost:8000/ai/suggest?fen=$fen&ai_type=stockfish" `
  -Method Get `
  -Headers @{Authorization="Bearer $token"}
```

**Response:**
```json
{
  "success": true,
  "suggested_move": "e7e5",
  "fen": "rnbqkbnr/pppppppp/8/8/4P3/8/PPPP1PPP/RNBQKBNR b KQkq e3 0 1",
  "ai_type": "stockfish"
}
```

#### POST /expert/question

Ask chess expert a question.

**Request:**
```powershell
$body = @{
    question = "What's the best opening for Black against 1.e4?"
    fen = "rnbqkbnr/pppppppp/8/8/4P3/8/PPPP1PPP/RNBQKBNR b KQkq e3 0 1"
} | ConvertTo-Json

Invoke-RestMethod -Uri "http://localhost:8000/expert/question" `
  -Method Post `
  -ContentType "application/json" `
  -Headers @{Authorization="Bearer $token"} `
  -Body $body
```

**Response:**
```json
{
  "success": true,
  "question": "What's the best opening for Black against 1.e4?",
  "response": "Against 1.e4, Black has several strong options: 1...c5 (Sicilian Defense), 1...e5 (Open Game), 1...c6 (Caro-Kann), or 1...d5 (Scandinavian). The Sicilian is objectively the most ambitious..."
}
```

## User Management

### User Data Storage

Users are stored as individual JSON files in `user_data/users/`:

```json
{
  "username": "johndoe",
  "email": "john@example.com",
  "password_hash": "$2b$12$...",
  "is_admin": false,
  "created_at": "2025-12-06T12:00:00.000000+00:00",
  "games_played": 0
}
```

### Manage Users

**View all users:**
```powershell
python add_user.py --list
```

**Delete a user:**
```powershell
python add_user.py --delete johndoe
```

**Promote to admin:**
```powershell
python add_user.py --promote johndoe
```

**Demote from admin:**
```powershell
python add_user.py --demote johndoe
```

## Configuration

### Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `OPENAI_API_KEY` | OpenAI API key for GPT models | (required if using OpenAI) |
| `JWT_SECRET_KEY` | Secret key for JWT signing | `chess-ai-secret-key-change-in-production` |
| `STOCKFISH_PATH` | Path to Stockfish executable | `/usr/games/stockfish` |

### Game Configuration

Edit `src/config.json`:

```json
{
  "ai_models": {
    "stockfish": "Local Stockfish Engine",
    "openai": "OpenAI GPT-4o",
    "deepseek": "DeepSeek Chat v3.1",
    "claude": "Claude 3.5 Sonnet"
  },
  "openings": [
    "Play the Ruy Lopez.",
    "Play the Italian Game.",
    "Play the Scotch Game."
  ],
  "defenses": [
    "Play the Sicilian Defense.",
    "Play the French Defense.",
    "Play the Caro-Kann Defense."
  ]
}
```

## Game Logging

All games are logged with complete move information and timestamps.

**Log location:** `logs/games/`

**Example log entry:**
```
2025-12-06 12:34:56,123 - New Game Started
2025-12-06 12:34:56,123 - White: Human (admin)
2025-12-06 12:34:56,123 - Black: Stockfish (Skill: 10)
2025-12-06 12:34:56,123 - Initial FEN: rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1
2025-12-06 12:35:01,456 - Move 1: e2-e4
2025-12-06 12:35:02,789 - AI Move 1: e7-e5
```

## Troubleshooting

### Common Issues

#### 1. Login fails with "Invalid username or password"
- Ensure user exists: `python add_user.py --list`
- Reset admin password:
  ```powershell
  python reset_admin.py
  ```

#### 2. Stockfish not found when running moves
```
✗ Failed to load Stockfish from /usr/games/stockfish
[AI] Random fallback move: b8c6
```

**Solution**: Rebuild Docker containers
```powershell
docker-compose down
docker-compose build --no-cache
docker-compose up
```

#### 3. 401 Unauthorized error
- Token may have expired
- Ensure Authorization header is included: `Authorization: Bearer <token>`
- Token format must be: `Bearer eyJ...`

**Solution**: Log out and log back in
```javascript
localStorage.removeItem('authToken');
window.location.reload();
```

#### 4. AI move not displayed on board
- Check browser console (F12) for JavaScript errors
- Verify chess engine is responding: `curl http://localhost:8000/`
- Check Docker logs: `docker logs chess-engine`

**Solution**: Refresh page and restart game
```powershell
docker-compose down
docker-compose up
```

#### 5. CORS errors (cross-origin requests)
Check that all services are running and accessible:
```powershell
Invoke-RestMethod -Uri "http://localhost:8000/" # Chess Engine
Invoke-RestMethod -Uri "http://localhost:8002/health" # Auth Service
Invoke-RestMethod -Uri "http://localhost:8001/health" # Admin Service
```

### Health Checks

**Check all services:**
```powershell
# Chess Engine
Invoke-RestMethod -Uri "http://localhost:8000/"

# Auth Service
Invoke-RestMethod -Uri "http://localhost:8002/health"

# Admin Service
Invoke-RestMethod -Uri "http://localhost:8001/health"
```

### View Container Logs

```powershell
# All services
docker-compose logs

# Specific service
docker logs chess-engine
docker logs chess-auth-service
docker logs chess-admin-service
docker logs chess-ui

# Follow logs in real-time
docker-compose logs -f chess-engine
```

### Debug Browser Console

Press **F12** in your browser to open the console. Look for:
- `[UI]` messages showing request/response flow
- `[ERROR]` messages indicating failures
- Network tab showing HTTP requests/responses

### Rebuild Everything

```powershell
docker-compose down
docker volume prune
docker-compose build --no-cache
docker-compose up
```

## Architecture Overview

```
┌──────────────────────────────────────────────────────────┐
│                     CLIENT BROWSER                        │
│              (http://localhost:8080)                     │
│                                                          │
│  ┌─────────────────────────────────────────────────┐   │
│  │  Chess UI (Chessboard.js + Chess.js)           │   │
│  │  - Interactive drag-and-drop board             │   │
│  │  - Move validation (chess.js)                  │   │
│  │  - Game status display                         │   │
│  │  - Move history tracking                       │   │
│  │  - Status messages                             │   │
│  └─────────────────────────────────────────────────┘   │
└──────────────────────────────────────────────────────────┘
              ↓ HTTP/CORS                ↑
              │                          │
              ↓                          ↑
┌──────────────────────────────────────────────────────────┐
│                    BACKEND SERVICES                       │
│                                                          │
│  ┌──────────────┐ ┌──────────────┐ ┌─────────────────┐ │
│  │  Auth Srv    │ │ Admin Srv    │ │  Chess Engine   │ │
│  │ (Port 8002)  │ │ (Port 8001)  │ │   (Port 8000)   │ │
│  ├──────────────┤ ├──────────────┤ ├─────────────────┤ │
│  │ • JWT tokens │ │ • User mgmt  │ │ • Stockfish     │ │
│  │ • Login      │ │ • AI models  │ │ • Move validate │ │
│  │ • Register   │ │ • Statistics │ │ • AI responses  │ │
│  │ • Password   │ │ • Models     │ │ • Expert AI     │ │
│  └──────────────┘ └──────────────┘ └─────────────────┘ │
│                                                          │
│              ↓ User Data              ↓ Games           │
│                                                          │
│  ┌──────────────────────────┐  ┌─────────────────────┐ │
│  │  user_data/users/        │  │  Chess.js Library   │ │
│  │  - admin.json            │  │  - Move validation  │ │
│  │  - user1.json            │  │  - FEN parsing      │ │
│  │  - user2.json            │  │  - State tracking   │ │
│  └──────────────────────────┘  └─────────────────────┘ │
└──────────────────────────────────────────────────────────┘
```

## Security Considerations

1. **JWT Tokens**: 24-hour expiration, signed with secret key
2. **Password Hashing**: bcrypt with salt rounds
3. **CORS**: Configured to allow cross-origin requests
4. **Authorization Headers**: Required for all protected endpoints

**Production Recommendations:**
- Change `JWT_SECRET_KEY` to a secure random value
- Use HTTPS/TLS for all communications
- Store secrets in environment variables or secret management system
- Use a database instead of JSON files for user data
- Implement rate limiting on authentication endpoints
- Enable CSRF protection in production

## Performance Tips

- **Stockfish Skill Levels**: 
  - Levels 1-5: Fast, easy to beat
  - Levels 6-15: Balanced play, good for practice
  - Levels 16-20: Strong, challenging for humans

- **API Response Time**: 
  - Move validation: ~10ms
  - Stockfish move: ~1000-2000ms (depends on skill level)
  - AI move (LLM): 2000-5000ms

- **Browser Performance**:
  - Use modern browser (Chrome, Firefox, Safari, Edge)
  - Clear browser cache if UI not updating: Ctrl+Shift+Del
  - Close unused tabs for better performance

## Notes

- Passwords must be 6-72 characters (bcrypt requirement)
- User data is stored in JSON files (not recommended for production)
- JWT tokens expire after 24 hours
- Stockfish is automatically installed in Docker containers
- For LLM-based AI, an API key is required (OpenAI, DeepSeek, etc.)
- Move history is tracked with standard algebraic notation (SAN)
- Games can be replayed by loading FEN positions

## Future Enhancements

- [ ] PGN export/import for games
- [ ] Game replay/analysis mode
- [ ] ELO rating system
- [ ] Multiplayer support
- [ ] Database backend (PostgreSQL/MongoDB)
- [ ] Mobile app (React Native)
- [ ] Voice commands for moves
- [ ] Opening book/endgame tablebase
- [ ] Tournament mode
- [ ] Social features (friend challenges)

---

**Enjoy playing chess with AI!** ♟️

For issues or questions, check the [Troubleshooting](#troubleshooting) section or review the Docker logs.
