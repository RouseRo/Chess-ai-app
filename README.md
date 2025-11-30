# Chess AI App

A web-based chess application supporting human and AI players, with classic chess openings, move logging, and game analysis.

## Table of Contents

- [Features](#features)
- [Project Structure](#project-structure)
- [Getting Started](#getting-started)
- [Running the Application](#running-the-application)
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

## Project Structure

```
Chess-ai-app/
├── engine/              # Chess engine (FastAPI backend)
│   ├── main.py         # API endpoints
│   ├── game_service.py # Game management
│   └── requirements.txt # Python dependencies
├── ui/                 # Web interface
│   ├── index.html      # Main UI
│   ├── chessboard.js   # Chessboard library
│   └── chessboard.css  # Styling
├── src/                # Core application logic
│   ├── main.py         # Command-line entry point
│   ├── chess_game.py   # Game logic
│   ├── expert_service.py # Expert AI service
│   └── config.json     # Configuration
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
4. The chessboard will open in your default browser

## Viewing the Chessboard Interface

### Web Interface Features

- **Interactive Board**: Drag pieces to make moves
- **Game Panel**: View status, moves, and FEN in real-time
- **AI Controls**: White/Black buttons for AI vs AI games
- **Player Setup**: Configure players and strategies
- **Strategy Tab**: Choose openings and defenses
- **Expert Panel**: Ask chess questions and get advice
- **Move History**: See all moves played in the game

### Accessing the Interface

To view the chessboard in the browser, the URL is **`http://localhost:8080/`**

| Method | URL | Steps |
|--------|-----|-------|
| **Docker Compose** | `http://localhost` | Run `docker-compose up` |
| **Manual Setup** | `http://localhost:8080` | Start engine & serve UI |
| **Live Server** | Auto-opens | Right-click `index.html` → "Open with Live Server" |

## API Endpoints

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

---

Enjoy playing and analyzing chess with AI!
