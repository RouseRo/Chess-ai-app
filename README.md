# Chess AI App

This project is a simple chess application that utilizes the OpenRouter.ai API through the OpenAI SDK to play chess with two different AI models. The application displays a chessboard after each move and requires user input to proceed to the next move.

## Project Structure

```
chess-ai-app
├── src
│   ├── main.py        # Entry point of the application
│   ├── game.py        # Manages the chessboard state and game logic
│   └── ai_player.py   # Interacts with the OpenRouter.ai API for AI moves
├── requirements.txt    # Lists project dependencies
└── README.md           # Documentation for the project
```

## Setup Instructions

1. Clone the repository:
   ```
   git clone <repository-url>
   cd chess-ai-app
   ```

2. Install the required dependencies:
   ```
   pip install -r requirements.txt
   ```

3. Set up your OpenAI API key as an environment variable:
   ```
   export OPENAI_API_KEY='your-api-key'
   ```

## Usage

To start the chess game, run the following command:
```
python src/main.py
```

Follow the on-screen instructions to play against the AI. After each move, press the ENTER character to compute the player's next move.

## Overview

The application consists of three main components:

- **Game Class**: Manages the chessboard state, validates moves, and updates the board after each move. It also handles the display of the chessboard to the user.

- **AIPlayer Class**: Interacts with the OpenRouter.ai API to compute the next move based on the current board state using two different AI models.

- **Main Application**: Initializes the game, manages the game loop, and handles user input to trigger the next move.

Enjoy playing chess with AI!