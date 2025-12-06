# Chess AI App

A web-based chess application supporting human and AI players, with classic chess openings, move logging, and game analysis.

## Table of Contents

- [Features](#features)
- [Project Structure](#project-structure)
- [Getting Started](#getting-started)
- [Running the Application](#running-the-application)
- [User Authentication](#user-authentication)
- [Admin Dashboard](#admin-dashboard)
- [API Services](#api-services)
- [User Management](#user-management)
- [Configuration](#configuration)
- [Game Logging](#game-logging)
- [Troubleshooting](#troubleshooting)
- [Notes](#notes)

## Features

- **Play against AI**: Support for various AI models (OpenAI, DeepSeek, Gemini, Claude, Llama, Stockfish)
- **Chess Strategies**: Choose classic chess openings and defenses for both White and Black
- **Game Management**: Save, load, and log games with full move history in FEN notation
- **Player Stats**: View player statistics and practice positions
- **Chess Expert**: Ask chess-related questions to an integrated expert assistant
- **Interactive UI**: Drag-and-drop chessboard with real-time game updates
- **Command-line Interface**: Play chess directly from the terminal
- **User Authentication**: Secure JWT-based authentication with bcrypt password hashing
- **Admin Dashboard**: Manage users, AI models, and system settings
- **Microservices Architecture**: Separate services for auth, admin, engine, and UI

## Project Structure

```
Chess-ai-app/
├── engine/                 # Chess engine (FastAPI backend)
│   ├── main.py            # API endpoints
│   ├── user_manager.py    # User data management
│   ├── game_service.py    # Game management
│   ├── Dockerfile         # Engine container config
│   └── requirements.txt   # Python dependencies
├── auth-service/          # Authentication service
│   ├── main.py           # Auth API endpoints
│   ├── Dockerfile        # Auth container config
│   └── requirements.txt  # Python dependencies
├── admin-service/         # Admin dashboard service
│   ├── main.py           # Admin API endpoints
│   ├── static/           # Admin UI files
│   ├── Dockerfile        # Admin container config
│   └── requirements.txt  # Python dependencies
├── ui/                    # Web interface
│   ├── index.html        # Main UI with login/chessboard
│   ├── js/               # JavaScript files
│   ├── css/              # Stylesheets
│   ├── img/              # Chess piece images
│   └── nginx.conf        # Nginx configuration
├── src/                   # Core application logic
│   ├── main.py           # Command-line entry point
│   ├── chess_game.py     # Game logic
│   ├── expert_service.py # Expert AI service
│   └── config.json       # Configuration
├── user_data/            # User database
│   └── users/            # Individual user JSON files
├── docker-compose.yml    # Docker orchestration
├── add_user.py          # User management script
├── reset_admin.py       # Admin password reset script
└── README.md            # This file
```

## Getting Started

### Prerequisites

- **Python 3.12+** with virtual environment
- **Docker Desktop** (for containerized deployment)
- **Web Browser** (Chrome, Firefox, Safari, Edge)

### Installation

1. **Clone the repository**
   ```powershell
   git clone <repository-url>
   cd Chess-ai-app
   ```

2. **Set up Python virtual environment**
   ```powershell
   python -m venv .venv
   .\.venv\Scripts\Activate
   ```

3. **Install dependencies**
   ```powershell
   pip install -r engine/requirements.txt
   ```

4. **Configure environment variables**
   Create a `.env` file in the project root:
   ```env
   OPENAI_API_KEY=your_openai_api_key
   JWT_SECRET_KEY=your_secret_key_here
   ```

## Running the Application

### Option 1: Docker Compose (Recommended)

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
   | Service | URL | Description |
   |---------|-----|-------------|
   | Chess UI | http://localhost:8080 | Main web interface |
   | Auth Service | http://localhost:8002 | Authentication API |
   | Admin Service | http://localhost:8001 | Admin dashboard |
   | Chess Engine | http://localhost:8000 | Game engine API |

4. **Stop the application**
   ```powershell
   docker-compose down
   ```

### Option 2: Command-line Version

Run the application directly from the terminal:

```powershell
cd Chess-ai-app
python -m src.main
```

This will display the main menu:
```
--- Main Menu ---
  1: Play a New Game
  2: Load a Saved Game
  3: Load a Practice Position
  4: View Player Stats
  ?: Ask a Chess Expert
  q: Quit
Enter your choice:
```

### Option 3: Manual Setup (Development)

**Terminal 1: Start the Engine**
```powershell
cd Chess-ai-app
uvicorn engine.main:app --reload --port 8000
```

**Terminal 2: Start Auth Service**
```powershell
cd Chess-ai-app
uvicorn auth-service.main:app --reload --port 8002
```

**Terminal 3: Start Admin Service**
```powershell
cd Chess-ai-app
uvicorn admin-service.main:app --reload --port 8001
```

**Terminal 4: Serve the UI**
```powershell
cd Chess-ai-app/ui
python -m http.server 8080
```

## User Authentication

### Default Admin Account

After first deployment, create an admin user:

```powershell
python add_user.py -u admin -e admin@chess.local -p admin123 --admin
```

Or reset the admin password:
```powershell
python reset_admin.py
```

### Login & Registration

**Login via API:**
```powershell
Invoke-RestMethod -Uri "http://localhost:8002/auth/login" -Method Post -ContentType "application/json" -Body '{"username":"admin","password":"admin123"}'
```

**Response:**
```json
{
  "success": true,
  "token": "eyJhbGciOiJIUzI1NiIs...",
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

Access the admin dashboard at http://localhost:8001

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

## API Services

### Chess Engine (Port 8000)

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/` | GET | Health check |
| `/move` | POST | Submit a chess move |
| `/ai/suggest` | GET | Get AI move suggestion |
| `/expert/question` | POST | Ask chess expert |
| `/expert/joke` | GET | Get chess joke |
| `/expert/fact` | GET | Get chess fact |

**Example Move Request:**
```powershell
$token = "your_jwt_token"
Invoke-RestMethod -Uri "http://localhost:8000/move" -Method Post -ContentType "application/json" -Headers @{Authorization="Bearer $token"} -Body '{"move":"e2e4","fen":"rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1"}'
```

## UI-Server Communication Architecture

This section explains how the frontend UI communicates with the backend microservices, including the authentication token flow.

### Architecture Overview

```
┌─────────────────┐     ┌──────────────────┐     ┌─────────────────┐
│                 │     │                  │     │                 │
│   Chess UI      │────▶│   Auth Service   │     │  Chess Engine   │
│  (Port 8080)    │     │   (Port 8002)    │     │   (Port 8000)   │
│                 │     │                  │     │                 │
└────────┬────────┘     └──────────────────┘     └────────▲────────┘
         │                                                │
         │              ┌──────────────────┐              │
         │              │                  │              │
         └─────────────▶│  Admin Service   │──────────────┘
                        │   (Port 8001)    │
                        │                  │
                        └──────────────────┘
```

### Authentication Token Flow

The application uses **JWT (JSON Web Tokens)** for secure authentication. Here's the complete flow:

#### Step 1: User Login

```
┌─────────┐                              ┌──────────────┐
│   UI    │                              │ Auth Service │
└────┬────┘                              └──────┬───────┘
     │                                          │
     │  POST /auth/login                        │
     │  {username, password}                    │
     │─────────────────────────────────────────▶│
     │                                          │
     │                                          │ Verify credentials
     │                                          │ Generate JWT token
     │                                          │
     │  {success: true, token: "eyJ..."}        │
     │◀─────────────────────────────────────────│
     │                                          │
     │  Store token in localStorage             │
     │                                          │
```

**Login Request:**
```javascript
// UI sends login request
fetch('http://localhost:8002/auth/login', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ 
        username: 'admin', 
        password: 'admin123' 
    })
})
.then(response => response.json())
.then(data => {
    if (data.success) {
        // Store token for future requests
        localStorage.setItem('authToken', data.token);
        localStorage.setItem('username', data.username);
        localStorage.setItem('isAdmin', data.is_admin);
    }
});
```

**Login Response:**
```json
{
    "success": true,
    "token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJ1c2VybmFtZSI6ImFkbWluIiwiaXNfYWRtaW4iOnRydWUsImV4cCI6MTc2NDk5OTEwMywiaWF0IjoxNzY0OTEyNzAzfQ.I7JmcH5dDI3Ui76RhlWFs9Fchx6y6d2IP2LrsfAAtAI",
    "username": "admin",
    "email": "admin@chess.local",
    "is_admin": true
}
```

#### Step 2: JWT Token Structure

The JWT token contains three parts separated by dots (`.`):

```
eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.    <- Header (base64)
eyJ1c2VybmFtZSI6ImFkbWluIiwiaXNfYWRtaW4i... <- Payload (base64)
I7JmcH5dDI3Ui76RhlWFs9Fchx6y6d2IP2LrsfAAtAI <- Signature
```

**Decoded Payload:**
```json
{
    "username": "admin",
    "is_admin": true,
    "exp": 1764999103,    // Expiration timestamp (24 hours from creation)
    "iat": 1764912703     // Issued at timestamp
}
```

#### Step 3: Authenticated API Requests

All subsequent requests to protected endpoints must include the token in the `Authorization` header:

```
┌─────────┐                              ┌──────────────┐
│   UI    │                              │ Chess Engine │
└────┬────┘                              └──────┬───────┘
     │                                          │
     │  POST /move                              │
     │  Headers: Authorization: Bearer eyJ...   │
     │  Body: {move, fen}                       │
     │─────────────────────────────────────────▶│
     │                                          │
     │                                          │ Validate token
     │                                          │ Process move
     │                                          │
     │  {success: true, newFen: "..."}          │
     │◀─────────────────────────────────────────│
     │                                          │
```

**Authenticated Request Example:**
```javascript
// Get stored token
const token = localStorage.getItem('authToken');

// Make authenticated request to chess engine
fetch('http://localhost:8000/move', {
    method: 'POST',
    headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${token}`  // Include token
    },
    body: JSON.stringify({
        move: 'e2e4',
        fen: 'rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1'
    })
})
.then(response => {
    if (response.status === 401) {
        // Token expired or invalid - redirect to login
        window.location.href = '/login';
        return;
    }
    return response.json();
})
.then(data => {
    // Update chessboard with new position
    updateBoard(data.newFen);
});
```

### Request/Response Flow by Service

#### Auth Service (Port 8002)

| Flow | Description |
|------|-------------|
| `UI → Auth` | Login, register, logout, token refresh |
| `Auth → UI` | JWT token, user info, success/error |

**Endpoints:**
```
POST /auth/login      - Returns JWT token on success
POST /auth/register   - Creates user, returns success
POST /auth/verify     - Validates token, returns user info
POST /auth/refresh    - Returns new JWT token
POST /auth/logout     - Invalidates session (client-side)
POST /auth/change-password - Updates password
```

#### Chess Engine (Port 8000)

| Flow | Description |
|------|-------------|
| `UI → Engine` | Game moves, AI suggestions, expert questions |
| `Engine → UI` | New board state, AI moves, answers |

**All requests require `Authorization: Bearer <token>` header.**

**Request Flow:**
```javascript
// 1. User makes a move on the UI
const move = 'e2e4';
const currentFen = game.fen();

// 2. UI sends move to engine
const response = await fetch('http://localhost:8000/move', {
    method: 'POST',
    headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${token}`
    },
    body: JSON.stringify({ move, fen: currentFen })
});

// 3. Engine validates move and returns new state
const data = await response.json();
// { success: true, newFen: "...", aiMove: "e7e5" }

// 4. UI updates the board
game.load(data.newFen);
board.position(data.newFen);
```

#### Admin Service (Port 8001)

| Flow | Description |
|------|-------------|
| `UI → Admin` | User management, model config, stats |
| `Admin → UI` | User lists, system stats, config data |

**Admin endpoints require `Authorization: Bearer <token>` with `is_admin: true`.**

### Token Validation Process

When a protected endpoint receives a request:

```
┌─────────────────────────────────────────────────────────────┐
│                    Token Validation Flow                     │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
                    ┌─────────────────┐
                    │ Extract token   │
                    │ from header     │
                    └────────┬────────┘
                              │
                              ▼
                    ┌─────────────────┐
              No    │ Token present?  │
           ┌────────│                 │
           │        └────────┬────────┘
           │                 │ Yes
           ▼                 ▼
    ┌──────────────┐ ┌─────────────────┐
    │ 401 Missing  │ │ Decode JWT with │
    │ authorization│ │ secret key      │
    └──────────────┘ └────────┬────────┘
                              │
                              ▼
                    ┌─────────────────┐
              No    │ Signature valid?│
           ┌────────│                 │
           │        └────────┬────────┘
           │                 │ Yes
           ▼                 ▼
    ┌──────────────┐ ┌─────────────────┐
    │ 401 Invalid  │ │ Check expiration│
    │ token        │ │ (exp claim)     │
    └──────────────┘ └────────┬────────┘
                              │
                              ▼
                    ┌─────────────────┐
              No    │ Token expired?  │
           ┌────────│                 │
           │        └────────┬────────┘
           │                 │ Yes
           ▼                 ▼
    ┌──────────────┐ ┌──────────────┐
    │ Process      │ │ 401 Token    │
    │ request ✓    │ │ expired      │
    └──────────────┘ └──────────────┘
```

**Server-side validation code (Python):**
```python
def verify_token(token: str) -> tuple[bool, Optional[str], Optional[bool]]:
    """Verify JWT token and return (success, username, is_admin)."""
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=["HS256"])
        username = payload.get("username")
        is_admin = payload.get("is_admin", False)
        
        if username is None:
            return False, None, None
        
        return True, username, is_admin
    except jwt.ExpiredSignatureError:
        return False, None, None  # Token expired
    except jwt.InvalidTokenError:
        return False, None, None  # Invalid token
```

### CORS (Cross-Origin Resource Sharing)

Since the UI runs on a different port than the backend services, CORS is configured to allow cross-origin requests:

```python
# Each service includes CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],           # Allow all origins (restrict in production)
    allow_credentials=True,
    allow_methods=["*"],           # Allow all HTTP methods
    allow_headers=["*"],           # Allow all headers including Authorization
)
```

**Browser Request Flow with CORS:**
```
┌─────────┐                              ┌──────────────┐
│ Browser │                              │    Server    │
└────┬────┘                              └──────┬───────┘
     │                                          │
     │  OPTIONS /move (preflight)               │
     │  Origin: http://localhost:8080           │
     │─────────────────────────────────────────▶│
     │                                          │
     │  Access-Control-Allow-Origin: *          │
     │  Access-Control-Allow-Methods: POST      │
     │  Access-Control-Allow-Headers: Auth...   │
     │◀─────────────────────────────────────────│
     │                                          │
     │  POST /move (actual request)             │
     │  Authorization: Bearer eyJ...            │
     │─────────────────────────────────────────▶│
     │                                          │
     │  Response with data                      │
     │◀─────────────────────────────────────────│
```

### Token Storage & Security

| Storage Method | Pros | Cons |
|----------------|------|------|
| `localStorage` | Persists across sessions | Vulnerable to XSS |
| `sessionStorage` | Cleared on tab close | Lost on refresh |
| `httpOnly Cookie` | Protected from XSS | Requires CSRF protection |

**Current Implementation (localStorage):**
```javascript
// Store token after login
localStorage.setItem('authToken', token);

// Retrieve token for requests
const token = localStorage.getItem('authToken');

// Clear token on logout
localStorage.removeItem('authToken');
```

### Error Handling

The UI should handle authentication errors gracefully:

```javascript
async function makeAuthenticatedRequest(url, options = {}) {
    const token = localStorage.getItem('authToken');
    
    if (!token) {
        redirectToLogin();
        return null;
    }
    
    const response = await fetch(url, {
        ...options,
        headers: {
            ...options.headers,
            'Authorization': `Bearer ${token}`,
            'Content-Type': 'application/json'
        }
    });
    
    switch (response.status) {
        case 401:
            // Token expired or invalid
            localStorage.removeItem('authToken');
            redirectToLogin();
            return null;
        case 403:
            // Forbidden - user lacks permission
            showError('You do not have permission for this action');
            return null;
        case 200:
            return response.json();
        default:
            showError('An error occurred');
            return null;
    }
}
```

### Complete Request Lifecycle Example

Here's a complete example of a chess move from UI to response:

```
1. USER ACTION
   └─▶ User drags piece from e2 to e4 on chessboard

2. UI PROCESSING
   └─▶ JavaScript captures move: "e2e4"
   └─▶ Gets current FEN: "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1"
   └─▶ Retrieves token from localStorage

3. HTTP REQUEST
   └─▶ POST http://localhost:8000/move
       Headers:
         Content-Type: application/json
         Authorization: Bearer eyJhbGciOiJIUzI1NiIs...
       Body:
         {"move": "e2e4", "fen": "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1"}

4. SERVER PROCESSING (Chess Engine)
   └─▶ Extract token from Authorization header
   └─▶ Validate JWT signature and expiration
   └─▶ Parse move and validate legality
   └─▶ Update board state
   └─▶ (If vs AI) Calculate AI response move

5. HTTP RESPONSE
   └─▶ 200 OK
       {
         "success": true,
         "newFen": "rnbqkbnr/pppppppp/8/8/4P3/8/PPPP1PPP/RNBQKBNR b KQkq e3 0 1",
         "aiMove": "e7e5",
         "message": "Move accepted"
       }

6. UI UPDATE
   └─▶ Update internal game state with new FEN
   └─▶ Animate piece movement on board
   └─▶ Update move history display
   └─▶ Check for game end conditions
```

## User Management

### Add Users via Script

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

### User Data Storage

Users are stored as individual JSON files in `user_data/users/`:

```json
{
  "username": "johndoe",
  "email": "john@example.com",
  "password_hash": "$2b$12$...",
  "is_admin": false,
  "created_at": "2025-12-05T12:00:00.000000+00:00",
  "games_played": 0
}
```

## Configuration

### Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `OPENAI_API_KEY` | OpenAI API key for AI models | - |
| `JWT_SECRET_KEY` | Secret key for JWT tokens | `chess-ai-secret-key-change-in-production` |

### Game Configuration

Edit `src/config.json` to customize:

```json
{
  "ai_models": {
    "m1": "openai/gpt-4o",
    "m2": "deepseek/deepseek-chat-v3.1"
  },
  "openings": [
    "Play the Ruy Lopez.",
    "Play the Italian Game."
  ],
  "defenses": [
    "Play the Sicilian Defense.",
    "Play the French Defense."
  ]
}
```

## Game Logging

All games are logged to `logs/games/` with complete game information:

```
2025-12-05 13:01:24,818 - New Game Started
2025-12-05 13:01:24,818 - White: Stockfish (Skill: 10)
2025-12-05 13:01:24,818 - Black: Human
2025-12-05 13:01:24,818 - White Strategy: Play the Ruy Lopez.
2025-12-05 13:01:24,818 - Initial FEN: rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1
```

## Troubleshooting

### Common Issues

**1. Auth service fails to start (bcrypt error)**
```
AttributeError: module 'bcrypt' has no attribute '__about__'
```
Solution: The auth-service uses bcrypt directly instead of passlib. Rebuild:
```powershell
docker-compose build --no-cache
docker-compose up
```

**2. Login fails with "Invalid username or password"**
- Ensure user exists: `python add_user.py --list`
- Reset admin password inside container:
```powershell
docker exec chess-auth-service python -c "import json; import bcrypt; pw=bcrypt.hashpw(b'admin123', bcrypt.gensalt()).decode(); data={'username':'admin','email':'admin@chess.local','password_hash':pw,'is_admin':True,'created_at':'2025-12-05T00:00:00','games_played':0}; json.dump(data, open('/app/user_data/users/admin.json','w'), indent=2); print('Done')"
```

**3. 401 Unauthorized on /move endpoint**
- Ensure you're sending the JWT token in the Authorization header
- Token format: `Authorization: Bearer <token>`

**4. Container not seeing updated files**
```powershell
docker-compose down
docker-compose build --no-cache
docker-compose up
```

### Health Checks

Check service health:
```powershell
# Auth Service
Invoke-RestMethod -Uri "http://localhost:8002/health"

# Admin Service
Invoke-RestMethod -Uri "http://localhost:8001/health"

# Chess Engine
Invoke-RestMethod -Uri "http://localhost:8000/"
```

### View Container Logs

```powershell
# All services
docker-compose logs

# Specific service
docker logs chess-auth-service
docker logs chess-engine
docker logs chess-admin-service
```

## Notes

- JWT tokens expire after 24 hours
- Passwords must be between 6-72 characters (bcrypt limitation)
- User data is stored in JSON files; use a proper database in production
- For production, change `JWT_SECRET_KEY` to a secure random value
- Use HTTPS in production environments

---

Enjoy playing and analyzing chess with AI! ♟️
