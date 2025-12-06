# Docker Upgrade Plan: Chess AI App

This document describes how to upgrade the Chess AI App to a two-container Docker architecture, separating the **visual interactive chessboard** (frontend) from the **chess engine** (backend).

---

## Overview

- **Frontend Container:**  
  Runs a web server serving a static web app using [chessboardjs.com](https://chessboardjs.com/) for the interactive chessboard.  
  Handles user interaction and communicates with the backend via HTTP or WebSocket.

- **Backend Container:**  
  Runs the Python chess engine (your existing app, with a new API layer).  
  Exposes a REST or WebSocket API for move validation, AI move generation, and game state.

- **Communication:**  
  The frontend container communicates with the backend container over a Docker network using HTTP (REST) or WebSocket.

---

## Directory Structure

```
chess-ai-app/
│
├── engine/           # Python backend (your current app, with API)
│   ├── Dockerfile
│   └── ...
│
├── ui/               # Static web UI (chessboardjs, JS, web server)
│   ├── Dockerfile
│   └── ...
│
└── docker-compose.yml
```

---

## Backend (Chess Engine) Container

- **Tech:** Python (FastAPI or Flask recommended for REST API)
- **Responsibilities:**
  - Accept new game requests
  - Validate moves
  - Generate AI moves
  - Return board state (FEN, PGN, etc.)

**Example Endpoints:**
- `POST /newgame`
- `POST /move`
- `GET /fen`
- `POST /ai-move`

**Dockerfile Example:**
```dockerfile
FROM python:3.12-slim
WORKDIR /app
COPY . .
RUN pip install -r requirements.txt
EXPOSE 8000
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
```

---

## Frontend (UI) Container

- **Tech:** Static HTML/JS (chessboardjs), served by Node.js/Express or Python/Flask
- **Responsibilities:**
  - Display chessboard and UI
  - Send/receive moves to/from backend API
  - Show move history, game status, etc.

**Dockerfile Example (Node.js/Express):**
```dockerfile
FROM node:20-alpine
WORKDIR /app
COPY . .
RUN npm install
EXPOSE 80
CMD ["node", "server.js"]
```

---

## Docker Compose

**docker-compose.yml Example:**
```yaml
version: '3'
services:
  chess-engine:
    build: ./engine
    ports:
      - "8000:8000"
  chess-ui:
    build: ./ui
    ports:
      - "8080:80"
    depends_on:
      - chess-engine
```

---

## Communication Flow

1. **User interacts with chessboard in browser (served by UI container).**
2. **Frontend JS sends move/command to backend API (engine container).**
3. **Backend processes move, returns result (valid/invalid, new FEN, AI move, etc.).**
4. **Frontend updates board and UI accordingly.**

---

## Next Steps

1. **Add REST API to your Python chess engine (FastAPI or Flask).**
2. **Build a minimal web UI using chessboardjs.com and connect it to the backend API.**
3. **Write Dockerfiles for both containers.**
4. **Create a docker-compose.yml to orchestrate both containers.**
5. **Test locally: `docker-compose up` and access the UI at `http://localhost:8080`.**

---

## Optional Enhancements

- Use WebSocket for real-time updates.
- Add authentication or user profiles.
- Deploy to cloud (Azure, AWS, etc.).
- Add persistent storage for game logs.

---

## References

- [chessboardjs.com](https://chessboardjs.com/)
- [FastAPI](https://fastapi.tiangolo.com/)
- [Docker Compose Docs](https://docs.docker.com/compose/)
- [Node.js](https://nodejs.org/)

---

## Running chessboard.js in a Docker Container

To use [chessboard.js](https://chessboardjs.com/) inside a Docker container, you can serve its static files using a lightweight web server such as nginx. This allows you to view and interact with the chessboard.js demo in your browser via a containerized environment.

### Steps

1. **Project Structure**

   Create a directory (e.g., `chessboardjs-docker`) and place the chessboard.js files and an `index.html` inside it. Example structure:

   ```
   chessboardjs-docker/
     index.html
     chessboard.js
     chessboard.css
     img/
   ```

2. **Sample `index.html`**

   ```html
   <!DOCTYPE html>
   <html>
   <head>
     <title>Chessboard.js Docker Demo</title>
     <link rel="stylesheet" href="chessboard.css">
     <style>
       #board { width: 400px; }
     </style>
   </head>
   <body>
     <div id="board"></div>
     <script src="chessboard.js"></script>
     <script>
       var board = Chessboard('board', 'start');
     </script>
   </body>
   </html>
   ```

3. **Dockerfile**

   Use nginx to serve the static files:

   ```dockerfile
   FROM nginx:alpine
   COPY . /usr/share/nginx/html
   EXPOSE 80
   ```

4. **Build and Run**

   In your project directory, run:

   ```sh
   docker build -t chessboardjs-demo .
   docker run -d -p 8080:80 chessboardjs-demo
   ```

   Then open [http://localhost:8080](http://localhost:8080) in your browser.

### Summary

- Download chessboard.js and its assets.
- Create an `index.html` that uses it.
- Use a Dockerfile with nginx to serve the files.
- Build and run the container, then access via your browser.

This approach provides a simple, reproducible way to use chessboard.js in any environment that supports Docker.

---

## Customizing chessboard.js Look and Feel & Adding Buttons

You can easily modify the appearance of chessboard.js and add custom buttons for new features.

### 1. Edit CSS for Look and Feel

- Open or create your own CSS file (or edit `chessboard.css`).
- Change board size, colors, borders, or piece images by overriding CSS classes.
- Example:
    ```css
    #board {
      width: 500px;
      margin: 20px auto;
    }
    .white-1e1d7 {
      background-color: #f0d9b5;
    }
    .black-3c85d {
      background-color: #b58863;
    }
    ```

### 2. Add Buttons for New Features

- Edit your `index.html` and add buttons above or below the board:
    ```html
    <div id="controls" style="text-align:center; margin-bottom:10px;">
      <button id="newGameBtn">New Game</button>
      <button id="flipBtn">Flip Board</button>
      <button id="customBtn">My Feature</button>
    </div>
    <div id="board"></div>
    ```

### 3. Add JavaScript for Button Actions

- In your `<script>` section or JS file, add event listeners for your buttons:
    ```javascript
    var board = Chessboard('board', 'start');

    document.getElementById('newGameBtn').onclick = function() {
      board.start();
    };

    document.getElementById('flipBtn').onclick = function() {
      board.flip();
    };

    document.getElementById('customBtn').onclick = function() {
      alert('Custom feature coming soon!');
      // Add your custom JS here
    };
    ```

### 4. (Optional) Use Custom Piece Images

- Download or create your own piece images and update the `pieceTheme` option:
    ```javascript
    var board = Chessboard('board', {
      pieceTheme: 'img/chesspieces/wikipedia/{piece}.png'
    });
    ```

### 5. Rebuild and Restart Docker Container (if using Docker)

- After editing your files, rebuild and restart your Docker container to see the changes.

---

## Installing chessboard.js and Creating the Directory Structure

To integrate [chessboard.js](https://chessboardjs.com/) as your frontend, follow these steps:

### 1. Create the UI Directory Structure

Within your main project directory (`chess-ai-app/`), create a `ui/` folder for the frontend assets:

```
chess-ai-app/
│
├── engine/           # Python backend (your current app, with API)
│   ├── Dockerfile
│   └── ...
│
├── ui/               # Static web UI (chessboardjs, JS, web server)
│   ├── Dockerfile
│   ├── index.html
│   ├── chessboard.js
│   ├── chessboard.css
│   └── img/
│
└── docker-compose.yml
```

### 2. Download chessboard.js

- Visit [https://chessboardjs.com/download/](https://chessboardjs.com/download/) and download the latest release.
- Extract the archive and copy the following files into your `ui/` directory:
  - `chessboard.js`
  - `chessboard.css`
  - The `img/` folder (contains chess piece images)

### 3. Add jQuery

chessboard.js depends on [jQuery](https://jquery.com/).  
You can include it in your `index.html` via CDN:

```html
<script src="https://code.jquery.com/jquery-3.7.1.min.js"></script>
```

### 4. Create a Minimal `index.html`

Create `ui/index.html` with the following content:

```html
<!DOCTYPE html>
<html>
<head>
  <title>Chessboard.js Frontend</title>
  <link rel="stylesheet" href="chessboard.css">
  <style>
    #board { width: 400px; }
  </style>
</head>
<body>
  <div id="board"></div>
  <script src="https://code.jquery.com/jquery-3.7.1.min.js"></script>
  <script src="chessboard.js"></script>
  <script>
    var board = Chessboard('board', 'start');
  </script>
</body>
</html>
```

### 5. (Optional) Customize Your UI

- chessboard.js is "just a board" and does not handle chess rules, move validation, or PGN parsing.
- For chess logic (move validation, game state, etc.), integrate [chess.js](https://github.com/jhlywa/chess.js) or connect to your backend API.
- You can add buttons, move history, and other UI elements as needed.

### 6. (Optional) Add a Simple Web Server

You can serve the static files using a simple web server (Node.js/Express, Python Flask, or nginx as shown in the Dockerfile examples above).

---

**Summary of Steps:**
1. Create the `ui/` directory under your project root.
2. Download and copy chessboard.js, chessboard.css, and the `img/` folder into `ui/`.
3. Add an `index.html` that loads jQuery and chessboard.js, and displays the chessboard.
4. (Optional) Add a Dockerfile and web server for containerized deployment.

---

**Note:**  
chessboard.js is a flexible JavaScript chessboard component that does not include chess logic or a chess engine. It is designed to be used alongside other libraries (such as chess.js) or your backend API for full chess functionality. For more information, see [chessboardjs.com](http://chessboardjs.com) and the [README](https://github.com/oakmac/chessboardjs/blob/master/README.md).

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
         Authorization: Bearer eyJ...

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

- **Admin Panel:**  
  Accessible at `/admin`, protected by JWT auth (admin role required).  
  Manage users, view stats, configure models, etc.

- **User Roles:**  
  - Admin: Full access
  - User: Limited access (play games, view stats)

- **Endpoints:**
  - `GET /admin/users`: List users
  - `POST /admin/user`: Create user
  - `PUT /admin/user/{id}`: Update user
  - `DELETE /admin/user/{id}`: Delete user

**Admin Login Example:**
```javascript
// Admin login (stores token with is_admin claim)
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
        // Store token and admin status
        localStorage.setItem('authToken', data.token);
        localStorage.setItem('isAdmin', data.is_admin);
    }
});
```

**Access Control Example:**
```javascript
// Check if user is admin
const isAdmin = localStorage.getItem('isAdmin') === 'true';

if (isAdmin) {
    // Show admin features
} else {
    // Hide admin features
}
```

**Admin Route Example (Python FastAPI):**
```python
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from . import crud, models, schemas
from .dependencies import get_db, get_current_user

router = APIRouter()

@router.get("/users", response_model=List[schemas.User])
def read_users(skip: int = 0, limit: int = 100, db: Session = Depends(get_db), current_user: models.User = Depends(get_current_user)):
    if not current_user.is_admin:
        raise HTTPException(status_code=403, detail="Not enough permissions")
    users = crud.get_users(db, skip=skip, limit=limit)
    return users
```

### Admin UI Mockup

- **User Management Page:**
  - Table of users (ID, username, email, role)
  - Actions: Edit, Delete, Reset Password
  - Pagination and search

- **Stats Dashboard:**
  - Total users, active games, etc.
  - Recent activity log

- **Model Configuration:**
  - List of available models
  - Enable/disable models
  - Set default model

---

**Note:**  
The admin features and user management are optional and can be added in later phases. The initial focus is on the core chess functionality.