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