# Chess AI App

A web-based chess application supporting human and AI players, with Stockfish engine integration, interactive chessboard, real-time game updates, and comprehensive microservices architecture.

The application is for people that are new to the game of chess and want to learn more about it for mental exercise and are interested in the history of the game and currents events in the chess community.

## Table of Contents

- [Features](#features)
- [Project Structure](#project-structure)
- [Getting Started](#getting-started)
- [Running the Application](#running-the-application)
- [Azure Deployment](#azure-deployment)
- [User Authentication](#user-authentication)
- [Admin Dashboard](#admin-dashboard)
- [API Services](#api-services)
- [Playing Chess](#playing-chess)
- [Classic Game Rewards](#classic-game-rewards)
- [Configuration](#configuration)
- [Troubleshooting](#troubleshooting)
- [Architecture](#architecture)
- [Security](#security)
- [Future Enhancements](#future-enhancements)

## Features

- **Interactive Web UI**: Drag-and-drop chessboard with real-time updates
- **Human vs Human (H vs H) Sync**: Two players can play against each other from separate browser sessions with automatic board synchronization every 2 seconds
- **Game ID Banner**: A unique sync game ID is displayed above the board during H vs H games
- **Community Panel**: See who is online, send public chat messages, send direct messages to other players, and send/receive game invitations
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
- **Captured Pieces & Material Advantage**: Live display of captured pieces with material score
- **Opening & Defense Selection**: Configure White opening and Black defense strategy before each game
- **Practice Hub**: A single button combining **Openings** (Ruy López, Sicilian, Italian, Queen's Gambit, King's Indian) and **Endgame Drills** (King & Pawn vs King, King & Rook vs King, Lucena Position, Philidor Position) in one place
- **Classic Games Library**: Step through 6 famous games (The Opera Game, The Immortal Game, The Evergreen Game, Game of the Century, Fischer vs Spassky Game 6, Kasparov's Immortal) with move-by-move commentary explaining why each move matters
- **Classic Game Board Banner**: The chessboard banner automatically updates to display the name of the game being reviewed (e.g. "🏆 Reviewing: The Opera Game — Morphy vs Duke & Count (Paris, 1858)")
- **Step-through Position Review**: Navigate any loaded position move-by-move with First / Prev / Next / Last controls
- **Move Commentary Panel**: Annotated analysis appears automatically at key moments during classic game review, explaining sacrifices, principles, and historical context
- **Live Captured Pieces During Review**: The captured pieces box updates in real time as you step through a classic game, showing exactly which pieces have been taken at each point with material advantage score
- **Classic Game Rewards**: Earn a badge every time you step through an entire classic game review; collect all 6 to unlock the 🎓 Grand Scholar award. Progress is saved server-side and displayed in the new **🏅 Rewards** tab
- **Player Stats**: Win/loss/draw record per opponent, stored locally in the browser
- **Chess News & Jokes**: Built-in rotating chess news articles and jokes
- **Comm Log**: Diagnostics panel showing all API requests and responses, including H vs H sync events (purple)
- **Clear Activity**: Button in the header lets a player reset their game activity status visible to admins
- **User Authentication**: Secure JWT-based authentication with bcrypt hashing
- **Unified User Storage**: Single SQLite database shared across all clients
- **Admin Dashboard**: Manage users and system settings; User Management shows real-time online status, game activity, and a Refresh Status button
- **Microservices Architecture**: Scalable, modular design with separate services
- **Docker Support**: Complete containerization with docker-compose

## Requirements

### User Interface Requirements
1. **Website (Web UI)** - A graphical interface compatible with most popular browsers
2. **Smartphone** - A mobile application for chess gameplay on smartphones

### Application Requirements
1. Each chess game has a unique identifier
2. Each registered user to the application has a profile and a unique identifier.
3. The Administrator Interface is only available as a Web UI.

### Administrator Interface Operations
1. **User Management**
   - 1.1 View all users with summary information (username, email, role, games played)
   - 1.2 View detailed user information (username, email, created date, last login, role, verification status, games list)
   - 1.3 Promote regular users to administrator status
   - 1.4 Demote administrators to regular user status
   - 1.5 Verify user email addresses
   - 1.6 Delete user accounts
   - 1.7 View real-time online status and game activity for each user
   - 1.8 Refresh user statuses on demand with the Refresh Status button

2. **System Statistics**
   - 2.1 View dashboard statistics (total users, admin count, verified users, total games played)
   - 2.2 Track admin and verification metrics

## Project Structure

```
Chess-ai-app/
├── engine/                     # Chess engine service (Port 8000)
│   ├── main.py                # API endpoints & Stockfish integration
│   ├── game_service.py        # Game helper utilities
│   ├── user_manager.py        # User/model management for engine
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
│   ├── index.html           # Login/Register + game interface (single-page app)
│   ├── admin.html           # Admin dashboard
│   ├── game-play.ts         # Chessboard drag-and-drop logic (TypeScript)
│   ├── player-selection.ts  # Player/opening/defense selection logic (TypeScript)
│   ├── chessboard.js        # Chessboard library
│   ├── chessboard.css       # Styling
│   ├── img/                 # Chess piece images
│   ├── nginx.conf           # Nginx configuration
│   └── Dockerfile           # UI container config
│
├── data/                      # Shared database directory
│   └── users.db             # SQLite database (shared volume)
│
├── scripts/                   # Utility scripts (reserved for future use)
│
├── src/                       # Shared Python modules (used by engine)
│   ├── ai_player.py          # AI model integration via OpenRouter
│   ├── chess_game.py         # Core game logic
│   ├── stockfish_player.py   # Stockfish integration
│   ├── stockfish_utils.py    # Stockfish config helpers
│   ├── data_models.py        # Shared data models
│   ├── constants.py          # Shared constants
│   ├── config.json           # AI model & opening configuration
│   └── utils/
│       └── input_handler.py
│
├── user_data/                 # AI model registry (engine volume)
│   └── ai_models.json        # Registered AI models
│
├── data/                      # Shared database directory
│   └── users.db              # SQLite database (shared volume)
│
├── docs/                      # Documentation
│   └── Docker_Design.md     # Architecture documentation
│
├── docker-compose.yml         # Docker orchestration
├── .env                       # Environment variables (create this)
└── README.md                  # This file
```

## Getting Started

### Prerequisites

- **Docker Desktop** (for web services)
- **Web Browser** (Chrome, Firefox, Safari, Edge)

### Quick Start with Docker

1. **Clone the repository**
   ```powershell
   git clone <repository-url>
   cd Chess-ai-app
   ```

2. **Create environment file** (optional, for AI features)
   ```powershell
   # Create .env file in project root — one key covers all AI providers via OpenRouter
   echo "OPENAI_API_KEY=your_openrouter_key" > .env
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

### Service URLs

| Service | URL | Description |
|---------|-----|-------------|
| **Chess UI** | http://localhost:8080 | Login, registration & game interface |
| **Admin Dashboard** | http://localhost:8080/admin.html | User management |
| **Auth API** | http://localhost:8002 | Authentication service |
| **Admin API** | http://localhost:8001 | Admin service |
| **Engine API** | http://localhost:8000 | Chess engine |

## Azure Deployment

The application can be deployed to **Azure Container Apps** using the provided PowerShell script. All four services (engine, auth, admin, UI) are built and pushed to Azure Container Registry, then deployed as Container Apps backed by Azure Files for persistent storage.

### Prerequisites

- [Azure CLI](https://learn.microsoft.com/cli/azure/install-azure-cli) installed and logged in (`az login`)
- Docker running locally
- An active Azure subscription

### First-time Deployment

Run the full deployment script from the repo root:

```powershell
.\deploy-azure.ps1
```

This script performs the following steps:

| Step | What it does |
|------|--------------|
| 0 | Registers required Azure resource providers |
| 1 | Creates resource group `chess-ai-rg` (East US) |
| 2 | Creates Azure Container Registry (`chessairegistry7646`) |
| 3 | Creates storage account and two Azure Files shares (`chessdata`, `chessuserdata`) |
| 4 | Creates the Container Apps Environment (`chess-ai-env`) |
| 5 | Links the Azure Files shares to the environment as volumes |
| 6 | Builds and pushes Docker images for all four services to ACR |
| 7 | Fetches ACR credentials |
| 8 | Deploys all four Container Apps via YAML |

At the end the script prints the public HTTPS URL for the Chess UI.

### Redeployment (infra already exists)

When the Azure infrastructure is already provisioned and you only need to rebuild and redeploy the container images, use:

```powershell
.\redeploy-azure.ps1
```

### Deployed Services

| Container App | Visibility | Port | Description |
|---------------|-----------|------|-------------|
| `chess-ui` | Public (external) | 80 | Nginx-served web frontend |
| `chess-engine` | Internal | 8000 | Chess engine & game logic |
| `chess-auth` | Internal | 8002 | JWT authentication service |
| `chess-admin` | Internal | 8001 | Admin dashboard backend |

### Live Deployment URLs

| Service | FQDN |
|---------|------|
| **Chess UI (public)** | `chess-ui.calmdesert-0b7461a5.eastus.azurecontainerapps.io` |
| chess-auth (internal) | `chess-auth.internal.calmdesert-0b7461a5.eastus.azurecontainerapps.io` |
| chess-admin (internal) | `chess-admin.internal.calmdesert-0b7461a5.eastus.azurecontainerapps.io` |
| chess-engine (internal) | `chess-engine.internal.calmdesert-0b7461a5.eastus.azurecontainerapps.io` |

### Accessing the Deployed App

Open the app in a browser:

```
https://chess-ui.calmdesert-0b7461a5.eastus.azurecontainerapps.io
```

| Page | URL |
|------|-----|
| Login / Play Chess | `https://chess-ui.calmdesert-0b7461a5.eastus.azurecontainerapps.io` |
| Admin Dashboard | `https://chess-ui.calmdesert-0b7461a5.eastus.azurecontainerapps.io/admin.html` |

The three backend services (`chess-engine`, `chess-auth`, `chess-admin`) are internal-only and not reachable from the public internet — they communicate with each other over the private Container Apps Environment network.

### Resource Configuration

| Resource | Name |
|----------|------|
| Resource Group | `chess-ai-rg` |
| Location | `eastus` |
| Container Registry | `chessairegistry7646` |
| Storage Account | `chessaistorage4996` |
| Container Apps Environment | `chess-ai-env` |

> **Note:** The `JWT_SECRET` in the script (`chess-ai-jwt-secret-change-me-in-prod`) must be changed to a strong random value before deploying to production.

## User Authentication

### Unified Authentication

All clients (Web UI, Admin Dashboard) authenticate through the same auth-service API and share a single SQLite database:

```
┌─────────────┐   ┌─────────────┐
│   Web UI    │   │   Admin UI  │
└──────┬──────┘   └──────┬──────┘
       │                 │
       └─────────────────┘
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

1. User enters credentials (login page)
2. Auth service validates with bcrypt and returns JWT token
3. Token stored in browser localStorage
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
| `/auth/activity` | POST | Update online/playing status |

### Community API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/community/online-users` | GET | List currently online users |
| `/community/messages` | GET | Get recent chat messages and DMs |
| `/community/messages` | POST | Post a public chat message |
| `/community/announcements` | POST | Post an announcement (admin only) |
| `/community/dm` | POST | Send a direct message |
| `/community/game-invite` | POST | Send a game invitation |
| `/community/clear-activity` | POST | Clear own game activity status |

### Rewards API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/rewards/complete-review` | POST | Record a classic game review completion |
| `/rewards/my-reviews` | GET | Get review progress and earned badges |

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

## Admin Dashboard

Access at **http://localhost:8080/admin.html**

### Features

| Tab | Description |
|-----|-------------|
| **Dashboard** | System statistics (users, games, models) |
| **User Management** | Create, delete, promote/demote users; view online status and game activity |
| **AI Models** | Configure AI model settings |
| **Settings** | Change admin password |

### User Management Panel

The User Management table displays:

| Column | Description |
|--------|-------------|
| **Username** | Player's username |
| **Email** | Registered email |
| **Status** | Online / Last seen X min ago / Offline |
| **Game Activity** | Current game activity (only shown when player is online) |
| **Actions** | Promote, Demote, Verify, Delete |

The **&#8635; Refresh Status** button refreshes the user list and online statuses on demand.

### Admin API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/health` | GET | Health check |
| `/admin/stats` | GET | System statistics |
| `/admin/users` | GET | List all users |
| `/admin/users/{username}` | GET | Get detailed user info |
| `/admin/users/{username}/promote` | POST | Promote to admin |
| `/admin/users/{username}/demote` | POST | Demote from admin |
| `/admin/users/{username}/verify` | POST | Manually verify user |
| `/admin/users/{username}` | DELETE | Delete user |
| `/admin/models` | GET | List configured AI models |

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
| `/` | GET | No | Health check with component status |
| `/health` | GET | No | Simple health check |
| `/move` | POST | Yes | Submit move & get AI response |
| `/game/sync` | POST | Yes | Push board state for H vs H sync |
| `/game/sync/{game_id}` | GET | Yes | Poll board state for H vs H sync |
| `/ai/suggest` | GET | Yes | Get AI move suggestion |
| `/expert/question` | POST | Yes | Ask chess expert |

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

1. Open http://localhost:8080 and log in
2. After login the game interface loads automatically with a tabbed panel:

| Tab | Description |
|-----|-------------|
| **Welcome** | Quick-start buttons: Start New Game, My Saves, Practice (Openings & Endgames), Classic Games, Chess News, Chess Joke |
| **Player Setup** | Configure White/Black as Human or AI; select AI engine, skill level, opening and defense. Includes **Setup Position from Moves** panel (see below) |
| **Move History** | Full move list for the current game |
| **Ask Expert** | Chat with the AI chess expert; quick-action buttons for position analysis |
| **Stats** | Win/loss/draw record per opponent stored in the browser |
| **🏅 Rewards** | Badge collection showing which classic games you have reviewed; earn the Grand Scholar award for completing all 6 |
| **Community** | See online users, send public chat, send DMs, send/accept game invitations |
| **Comm** | Diagnostics log of all API requests and responses (sync events shown in purple) |

3. Go to the **Player Setup** tab, configure both players and click **Start New Game**
4. Drag pieces to make moves; the AI responds automatically

### Setup Position from Moves

The **Player Setup** tab contains a "Setup Position from Moves" panel for loading and reviewing positions:

- **Classic Games** — select one of 6 legendary games from the dropdown. The board immediately loads at the starting position and step-through navigation controls appear. The **board banner** updates to show the game name (e.g. *🏆 Reviewing: The Immortal Game — Anderssen vs Kieseritzky (London, 1851)*).
- **Preset Openings** — jump to the end of a named opening line (Ruy López, Sicilian, etc.).
- **Manual PGN / move input** — paste any move sequence in SAN or PGN format and click **Preview Position**.

Once a position is loaded the navigation bar appears:

| Button | Action |
|--------|--------|
| ⏮ | Jump to starting position |
| ◀ | Step back one move |
| ▶ | Step forward one move |
| ⏭ | Jump to final position |

For classic games, a **yellow commentary panel** appears automatically at annotated positions explaining key moves, sacrifices, and strategic ideas. The **captured pieces box** below the board updates in real time at every step, showing which pieces have been taken and the current material advantage.

Clicking **Clear** resets the board to the starting position, clears the game name banner, and empties the captured pieces display.

> **Reward trigger**: reaching the final move of any classic game automatically records a completion and awards a badge (see [Classic Game Rewards](#classic-game-rewards)).

#### Classic Games included

| Game | Players | Year | Opening |
|------|---------|------|---------|
| The Opera Game | Morphy vs Duke Karl & Count Isouard | 1858 | Philidor Defence |
| The Immortal Game | Anderssen vs Kieseritzky | 1851 | King's Gambit |
| The Evergreen Game | Anderssen vs Dufresne | 1852 | Evans Gambit |
| Game of the Century | Byrne vs Fischer | 1956 | Grünfeld Defence |
| Fischer vs Spassky, Game 6 | Fischer vs Spassky | 1972 | QGD Tartakower |
| Kasparov's Immortal | Kasparov vs Topalov | 1999 | Pirc Defence |

## Classic Game Rewards

The app tracks which classic games each logged-in user has stepped through to completion and awards a badge for each one.

### Badges

| Game | Badge | Title |
|------|-------|-------|
| The Opera Game | 🎭 | Opera Maestro |
| The Immortal Game | ♾️ | Immortal Scholar |
| The Evergreen Game | 🌿 | Evergreen Aficionado |
| Game of the Century | 🏆 | Century Witness |
| Fischer vs Spassky, Game 6 | ⚔️ | Cold War Classic |
| Kasparov's Immortal | 👑 | Kasparov's Devotee |
| **All 6 completed** | 🎓 | **Grand Scholar** |

### How it works

1. Open **Player Setup → Classic Games** and select a game.
2. Use ▶ / ⏭ to step through every move until you reach the end.
3. A **reward toast** slides in from the bottom-right corner confirming the badge earned.
4. Open the **🏅 Rewards** tab at any time to see your full progress, completion dates, and whether you have unlocked the Grand Scholar badge.

Completions are stored in the database under the logged-in username, so they persist across sessions and devices.

### Reward API Endpoints

Both endpoints require a valid `Authorization: Bearer <token>` header.

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/rewards/complete-review` | POST | Record completion of a classic game review |
| `/rewards/my-reviews` | GET | Fetch all review progress and earned badges |

#### Record a completion

```powershell
Invoke-RestMethod -Uri "http://localhost:8002/rewards/complete-review" `
  -Method POST `
  -ContentType "application/json" `
  -Headers @{Authorization="Bearer $token"} `
  -Body '{"game_key":"game-of-century"}'
```

```json
{
  "success": true,
  "newly_completed": true,
  "game_key": "game-of-century",
  "game_name": "Game of the Century",
  "badge": "🏆",
  "badge_title": "Century Witness",
  "completed_count": 1,
  "total_games": 6,
  "grand_scholar_unlocked": false
}
```

Valid `game_key` values: `opera-game`, `immortal-game`, `evergreen-game`, `game-of-century`, `fischer-spassky-g6`, `kasparov-topalov`.

### Human vs Human (H vs H) Sync

Two players can play against each other from different browser tabs or computers on the same network:

1. Both players log in and go to **Player Setup**
2. Set **White** and **Black** both to **Human**, entering both players' usernames
3. Click **Start New Game** — a **Game ID** appears above the board
4. The other player loads their saved game (or sets up the same names) — the board syncs automatically every 2 seconds
5. Each player can only move their own pieces
6. After a game, click **Clear Activity** in the header to reset your game status

### Make Moves

**Web UI:**
- Drag pieces to valid squares
- Invalid moves snap back automatically

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
# OpenRouter API key — used for ALL AI models (GPT, Claude, DeepSeek, Gemini, Llama, etc.)
OPENAI_API_KEY=your_openrouter_key

# JWT Configuration (optional, has defaults)
JWT_SECRET_KEY=your_secret_key
JWT_EXPIRATION_HOURS=24

# Development Mode (auto-verifies new users)
CHESS_DEV_MODE=false
```

> **AI model selection**: The active AI model for the chess expert and AI opponents is configured in `src/config.json` under `chess_expert_model` and `ai_models`. All models are accessed through [OpenRouter](https://openrouter.ai) using the `OPENAI_API_KEY`.

### Docker Compose Services

```yaml
services:
  chess-ui:            # Port 8080 - Frontend
  chess-engine:        # Port 8000 - Game logic
  auth-service:        # Port 8002 - Authentication
  admin-service:       # Port 8001 - Admin functions
```

## Troubleshooting

### Common Issues

| Issue | Solution |
|-------|----------|
| Can't login | Check credentials, verify auth service is running |
| "Invalid username or password" | Reset the database and restart auth-service |
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


### Reset Database

```powershell
# Copy a fresh database to the auth container
docker cp data/users.db chess-auth-service:/app/data/users.db

# Restart auth service to pick up changes
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
│  ┌──────────────┐    ┌──────────────────────────┐   │
│  │   Web UI     │    │   Admin Dashboard        │   │
│  │ (Port 8080)  │    │   (Port 8080/admin.html) │   │
│  └──────┬───────┘    └────────────┬─────────────┘   │
│         │                         │                  │
└─────────┼─────────────────────────┼──────────────────┘
          │                         │
          │     HTTP API            │
          └─────────────────────────┘
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
- [x] Classic games step-through review with annotated move commentary
- [x] Classic game reward badges and Grand Scholar award
- [ ] Full game replay from saved game history
- [ ] ELO rating system
- [x] Human vs Human multiplayer (browser-to-browser sync)
- [x] Community chat, DMs, and game invitations
- [ ] PostgreSQL database
- [ ] WebSocket for real-time updates (currently uses 2-second polling)
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
| Login / Play Chess | http://localhost:8080 |
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

# Stop services
docker-compose down

# View logs
docker-compose logs -f

# Reset auth database
docker cp data/users.db chess-auth-service:/app/data/users.db
docker-compose restart auth-service

# Rebuild
docker-compose build --no-cache
```

---

**Enjoy playing chess with AI!** ♟️

For detailed architecture documentation, see [docs/Docker_Design.md](docs/Docker_Design.md).
