# Chess AI App

A web-based chess application supporting human and AI players, with classic chess openings, move logging, and game analysis.

## Table of Contents

- [Features](#features)
- [Project Structure](#project-structure)
- [Getting Started](#getting-started)
- [Running the Application](#running-the-application)
- [User Authentication](#user-authentication)
- [Viewing the Chessboard Interface](#viewing-the-chessboard-interface)
- [API Endpoints](#api-endpoints)
- [Configuration](#configuration)
- [Game Logging](#game-logging)
- [Notes](#notes)

## Features

- **Play against AI**: Support for various AI models (OpenAI, DeepSeek, Gemini, Claude, Llama, Stockfish)
- **Chess Strategies**: Choose classic chess openings and defenses for both White and Black
- **Game Management**: Save, load, and log games with full move history in FEN notation
- **Player Stats**: View player statistics and practice positions
- **Chess Expert**: Ask chess-related questions to an integrated expert assistant
- **Interactive UI**: Drag-and-drop chessboard with real-time game updates
- **Command-line Interface**: Play chess directly from the terminal
- **User Authentication**: Secure login and registration system with password hashing

## Project Structure

```
Chess-ai-app/
├── engine/              # Chess engine (FastAPI backend)
│   ├── main.py         # API endpoints
│   ├── user_manager.py # User authentication
│   ├── game_service.py # Game management
│   └── requirements.txt # Python dependencies
├── ui/                 # Web interface
│   ├── index.html      # Main UI with login/chessboard
│   ├── chessboard.js   # Chessboard library
│   └── chessboard.css  # Styling
├── src/                # Core application logic
│   ├── main.py         # Command-line entry point
│   ├── chess_game.py   # Game logic
│   ├── expert_service.py # Expert AI service
│   └── config.json     # Configuration
├── user_data/          # User database
│   ├── users.json      # Registered users
│   └── sessions.json   # Active sessions
├── docker-compose.yml  # Docker orchestration
└── README.md          # This file
```

## Getting Started

### Prerequisites

- **Python 3.12+** with virtual environment
- **Docker Desktop** (for containerized deployment)
- **Node.js** (optional, for frontend development)
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

4. **Configure the application**
   - Edit `src/config.json` to add or modify AI models and openings/defenses

## Running the Application

### Option 1: Command-line Version

Run the application directly from the terminal:

```powershell
cd C:\Users\rober\Source\Repos\Chess-ai-app
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

**Menu Options:**
- **1: Play a New Game** - Start a new chess game with player and strategy selection
- **2: Load a Saved Game** - Load a previously saved game from logs
- **3: Load a Practice Position** - Load a specific chess position to practice
- **4: View Player Stats** - View statistics for configured players
- **?: Ask a Chess Expert** - Ask chess-related questions to the expert
- **q: Quit** - Exit the application

### Option 2: Docker Compose (Web UI - Recommended)

1. **Start Docker Desktop**
   ```powershell
   # Verify Docker is running
   docker --version
   ```

2. **Run the application**
   ```powershell
   cd C:\Users\rober\Source\Repos\Chess-ai-app
   docker-compose build --no-cache
   docker-compose up
   ```

3. **Open in browser**
   ```
   http://localhost
   ```

4. **Stop the application**
   ```powershell
   docker-compose down
   ```

### Option 3: Manual Setup (Engine + UI Separately)

**Terminal 1: Start the Engine**
```powershell
cd C:\Users\rober\Source\Repos\Chess-ai-app
uvicorn engine.main:app --reload
```
Engine runs on: `http://localhost:8000`

**Terminal 2: Serve the UI**
```powershell
cd C:\Users\rober\Source\Repos\Chess-ai-app\ui
python -m http.server 8080
```
UI runs on: `http://localhost:8080`

### Option 4: VS Code Live Server

1. Install the **Live Server** extension in VS Code
2. Right-click on `ui/index.html`
3. Select **"Open with Live Server"**
4. The login interface will open in your default browser

## User Authentication

### Login & Registration

The application includes a secure user authentication system. Users must login or register before accessing the chessboard.

**Features:**
- **Secure Password Storage**: Passwords are hashed using PBKDF2-HMAC-SHA256 with salt
- **Session Tokens**: Users receive JWT-like tokens valid for 7 days
- **Persistent Login**: Session tokens are stored locally to keep users logged in
- **Account Registration**: New users can register with username, email, and password

### Login Screen

When you open the application at `http://localhost` or `http://localhost:8080`, you'll see:

1. **Login Form**
   - Enter your username
   - Enter your password
   - Click "Login" button

2. **Register Form**
   - Click "Register" button on login screen
   - Enter a username (minimum 3 characters)
   - Enter your email address
   - Enter a password (minimum 6 characters)
   - Click "Register" button
   - Login with your new credentials

### Authentication Endpoints

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/auth/register` | POST | Create a new user account |
| `/auth/login` | POST | Authenticate user and receive token |
| `/auth/logout` | POST | End user session |
| `/auth/verify` | GET | Verify current session token |
| `/auth/user/{username}` | GET | Retrieve user information |

**Request Examples:**

**Register:**
```json
POST /auth/register
{
  "username": "chessmaster",
  "email": "chessmaster@example.com",
  "password": "SecurePassword123"
}
```

**Login:**
```json
POST /auth/login
{
  "username": "chessmaster",
  "password": "SecurePassword123"
}
```

**Response:**
```json
{
  "success": true,
  "message": "Login successful",
  "token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
}
```

### User Data Storage

User information is stored in `user_data/users.json`:

```json
{
  "chessmaster": {
    "email": "chessmaster@example.com",
    "password": "salt$hash_hex",
    "created_at": "2025-11-30T17:14:47.123456",
    "games_played": 5
  }
}
```

**Security Notes:**
- Passwords are never stored in plain text
- Each password uses a unique salt
- Session tokens expire after 7 days
- Tokens are stored in browser's localStorage
- Use HTTPS in production environments

## Viewing the Chessboard Interface

### Web Interface Features

- **Interactive Board**: Drag pieces to make moves
- **Game Panel**: View status, moves, and FEN in real-time
- **AI Controls**: White/Black buttons for AI vs AI games
- **Player Setup**: Configure players and strategies
- **Strategy Tab**: Choose openings and defenses
- **Expert Panel**: Ask chess questions and get advice
- **Move History**: See all moves played in the game

### Accessing the Chessboard

After successful login, you'll be taken to the chessboard interface featuring:

- **Centered Chessboard**: 400x400px interactive board
- **Game Status**: Real-time game state updates
- **Player Setup Panel**: Select human or AI players
- **Strategy Selection**: Choose openings and defenses
- **Move History**: Track all moves in the game
- **FEN Notation**: View board state in standard notation
- **Expert Assistant**: Ask chess questions
- **User Info**: Username displayed in header
- **Logout Button**: Safely end your session

| Method | URL | Steps |
|--------|-----|-------|
| **Docker Compose** | `http://localhost` | Run `docker-compose up` |
| **Manual Setup** | `http://localhost:8080` | Start engine & serve UI |
| **Live Server** | Auto-opens | Right-click `index.html` → "Open with Live Server" |

## API Endpoints

### Authentication Endpoints
- **`POST /auth/register`** - Register new user account
- **`POST /auth/login`** - Login and receive session token
- **`POST /auth/logout`** - Logout and end session
- **`GET /auth/verify`** - Verify session token validity
- **`GET /auth/user/{username}`** - Get user information

### Move Management
- **`POST /move`**  
  Submit a chess move and get the updated board state
  ```json
  Request: { "move": "e2-e4", "fen": "..." }
  Response: { "status": "Move accepted", "fen": "...", "engine_move": "e7e5" }
  ```

### Expert Services
- **`POST /expert/question`** - Ask chess questions
- **`GET /expert/joke`** - Get a chess joke
- **`GET /expert/fact`** - Get a fun chess fact
- **`GET /expert/news`** - Get latest chess news
- **`POST /expert/analyze`** - Analyze a position
- **`GET /expert/opening`** - Get opening advice

## Configuration

Edit `src/config.json` to customize:

- **AI Models**: Add or modify OpenRouter API integrations
- **Stockfish Settings**: Configure engine skill levels and parameters
- **Openings**: Define white opening strategies
- **Defenses**: Define black defense strategies

Example config snippet:
```json
{
  "ai_models": {
    "m1": "openai/gpt-4o",
    "m2": "deepseek/deepseek-chat-v3.1"
  },
  "openings": [
    "Play the Ruy Lopez.",
    "Play the Italian Game."
  ]
}
```

## Game Logging

All games are logged to `logs/games/` with complete game information:

```
2025-09-16 13:01:24,818 - New Game Started
2025-09-16 13:01:24,818 - White: Stockfish (Skill: 10)
2025-09-16 13:01:24,818 - Black: Stockfish (Skill: 20)
2025-09-16 13:01:24,818 - White Strategy: Play the Ruy Lopez.
2025-09-16 13:01:24,818 - Black Strategy: Play the Sicilian Defense.
2025-09-16 13:01:24,818 - Initial FEN: rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1
```

## Notes

- If no opening/defense is selected, logs will show "No Classic Chess Opening"/"No Classic Chess Defense"
- All strategy selections are recorded in the game log file
- The FEN notation indicates whose turn it is and the board state after the previous move
- When both players are AI, use the White/Black buttons to make sequential moves
- You can play via command-line or use the web interface depending on your preference
- User sessions persist for 7 days; after that, you'll need to login again
- For development, user data is stored in plain JSON files; use a proper database in production

---

Enjoy playing and analyzing chess with AI!
