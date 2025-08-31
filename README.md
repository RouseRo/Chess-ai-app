# Chess AI Application

This project is a feature-rich, command-line chess application where two AI players, powered by large language models via the OpenRouter API, can play against each other. It is designed with a clean, object-oriented structure that separates application logic, user interface, and configuration.

## Features

*   **Configurable AI:** Easily add or change AI models and opening strategies by editing a simple JSON configuration file.
*   **Ask a Chess Expert:** Get answers to your chess-related questions from a dedicated grandmaster-level AI, accessible from any menu.
*   **Multiple Game Modes:** Start a new AI vs. AI game, load a previously saved game, or set up a board from a classic practice position.
*   **Interactive Gameplay:**
    *   Step through games move by move or auto-play a set number of turns.
    *   Take control at any time by manually entering a move for either player.
    *   Swap out the AI model for White or Black mid-game.
    *   Return to the main menu from an active game.
*   **Save & Load System:** Save an in-progress game at any time and load it later to continue.
*   **Game Logging:** Every move is logged to a file (`chess_game.log`), including the author (AI or User) and the board state in FEN notation.

## Project Structure

The project is organized with a separation of concerns to make it easy to maintain and extend:

*   `src/main.py`: The main entry point of the application. Contains the `ChessApp` class which manages the overall application flow.
*   `src/game.py`: Contains the `Game` class, which manages the state of a single chess game, including the board and players.
*   `src/ai_player.py`: Contains the `AIPlayer` class, responsible for communicating with the OpenRouter API to get AI moves and answer questions.
*   `src/ui_manager.py`: Contains the `UIManager` class, which handles all console input and output.
*   `src/config.json`: A JSON file for configuring AI models, strategies, and the chess expert model.
*   `src/endgame_positions.json`: A JSON file containing classic endgame scenarios for practice mode.

## Setup

1.  **Clone the repository:**
    ```bash
    git clone <repository-url>
    cd Chess-ai-app
    ```

2.  **Create a virtual environment:**
    ```bash
    python -m venv .venv
    source .venv/bin/activate  # On Windows, use `.venv\Scripts\activate`
    ```

3.  **Install dependencies:**
    ```bash
    pip install -r requirements.txt
    ```

4.  **Set up your API key:**
    *   Create a file named `.env` in the root directory.
    *   Add your OpenRouter API key to the `.env` file:
        ```
        OPENAI_API_KEY="your-openrouter-api-key"
        ```

## Configuration

You can customize the application by editing the `src/config.json` file.

*   **`ai_models`**: Add, remove, or change the AI models available for games.
*   **`white_openings` / `black_defenses`**: Customize the opening strategies.
*   **`chess_expert_model`**: Specify which model from your `ai_models` list should be used to answer questions.

Example `config.json`:
```json
{
  "white_openings": {
    "1": "Play the Ruy Lopez."
  },
  "black_defenses": {
    "a": "Play the Sicilian Defense."
  },
  "ai_models": {
    "m1": "openai/gpt-4o",
    "m3": "google/gemini-1.5-pro"
  },
  "chess_expert_model": "google/gemini-1.5-pro"
}
```

## Usage

### How to Run
To start the application, run the `main.py` script from the root directory:
```bash
python src/main.py
```

### Main Menu
You will be greeted with the Main Menu, which is the central hub for all application features.
*   `1`: Play a New AI vs AI Game
*   `2`: Load a Saved Game
*   `3`: Load a Practice Position
*   `?`: Ask a Chess Expert
*   `4`: Quit

### In-Game Controls
While a game is in progress, you can press `Enter` to let the AI make its move, or you can type `m` to access the in-game menu. This menu allows you to load another game, load a practice position, swap AI models, ask the expert, or return to the main menu.

## Game Modes

The application offers several game modes to suit your needs:

*   **AI vs. AI:** Watch two AI players compete against each other. You can configure the AI models and opening strategies before the game starts.
*   **Load Game:** If you have a saved game file, you can load it and continue from where you left off. The game state, including all moves and the current board position, will be restored.
*   **Practice Mode:** This mode allows you to practice specific chess scenarios. You can load positions from the provided `endgame_positions.json` file and play against an AI. This is useful for honing your skills in particular types of endgames.

## Interactive Features

The application provides several interactive features to enhance your experience:

*   **Move Entry:** You can manually enter moves for either player at any time. This allows you to experiment with different strategies or take control if you want to intervene in the AI's decision-making.
*   **AI Model Swap:** Mid-game, you have the option to swap out the AI model for either player. This can be useful if you want to change the difficulty or style of play.
*   **Game Stepping:** Instead of playing out the game in real-time, you can step through it move by move. This is useful for analyzing the game or if you want to take your time to consider each move carefully.

## Saving and Loading Games

The application includes a robust save and load system:

*   **Save Game:** At any point during a game, you can choose to save the current game state to a file. This will record all moves made, the current board position, and any other relevant game data.
*   **Load Game:** To load a saved game, simply select the load game option from the main menu. You will be prompted to select a save file, and the game will be restored to the exact state it was in when you saved it.

## Practice Mode

Practice mode is a special game mode designed to help you improve your chess skills:

*   You can load classic endgame positions from the `endgame_positions.json` file.
*   Play against an AI with adjustable strength to practice your tactics.
*   This mode does not require any configuration and is ready to use out of the box.

## Game Logging

All games are logged to a file named `chess_game.log`. This log includes:

*   A timestamp for each move.
*   The players involved (AI or User).
*   The moves made in standard algebraic notation.
*   The FEN string representing the board state after each move.

This log is useful for reviewing games later or for analyzing specific positions.
