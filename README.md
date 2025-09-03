# Chess AI Application

This project is a feature-rich, command-line chess application where you can pit AI players, powered by large language models, against each other or against a classic chess engine like Stockfish. It is designed with a clean, object-oriented structure that separates application logic, user interface, and configuration.

## Features

*   **AI vs. Engine:** Play against various skill levels of the powerful Stockfish chess engine.
*   **Configurable Players:** Easily add or change AI models, Stockfish configurations, and opening strategies by editing a simple JSON configuration file.
*   **Ask a Chess Expert:** Get answers to your chess-related questions from a dedicated grandmaster-level AI, accessible from any menu.
*   **Multiple Game Modes:** Start a new game, load a previously saved game, or set up a board from a classic practice position.
*   **Enhanced Interactive Gameplay:**
    *   Visually enhanced board display with move highlighting and rank/file labels.
    *   Step through games move by move or auto-play a set number of turns.
    *   Take control at any time by manually entering a move for either player.
    *   Swap out the AI model for White or Black mid-game.
    *   Colored game-over messages (checkmate, stalemate, etc.) with total move count.
*   **Save & Load System:** Save an in-progress game at any time. After a game finishes, you are prompted to save the final game log.
*   **Comprehensive Logging:**
    *   **Game Logging:** Every move in a standard game is logged to `chess_game.log`, including the author and the board state in FEN notation.
    *   **Test Logging:** All test games are automatically logged to individual files in the `logs/test_games/` directory for detailed analysis and debugging.
*   **Advanced Puzzle Testing:** The test suite can handle multi-move checkmate puzzles, pitting players against a strong Stockfish defender to verify their solving ability.

## Project Structure

The project is organized with a separation of concerns to make it easy to maintain and extend:

*   `src/main.py`: The main entry point of the application. Manages the overall application flow.
*   `src/game.py`: Manages the state of a single chess game, including the board and players.
*   `src/ai_player.py`: Handles communication with the OpenRouter API to get AI moves and answer questions.
*   `src/stockfish_player.py`: Interacts with the Stockfish engine to get moves.
*   `src/ui_manager.py`: Handles all console input and output.
*   `src/config.json`: A JSON file for configuring AI models, Stockfish, strategies, and the chess expert model.
*   `src/endgame_positions.json`: A JSON file containing classic endgame scenarios for practice mode.
*   `tests/`: Contains all `pytest` tests for the application.
*   `logs/`: The default directory where game and test logs are stored.

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
    *   You will need the `stockfish` library. If it's not in your `requirements.txt`, add it:
        ```bash
        pip install stockfish
        ```
    *   Install all requirements:
        ```bash
        pip install -r requirements.txt
        ```

4.  **Download Stockfish:**
    *   Download the Stockfish executable for your operating system from the [official Stockfish website](https://stockfishchess.org/download/).
    *   Place the executable in a known location on your computer.

5.  **Configure the Application:**
    *   **Set up API Key:** Create a file named `.env` in the root directory and add your OpenRouter API key:
        ```
        OPENAI_API_KEY="your-openrouter-api-key"
        ```
    *   **Set Stockfish Path:** Open `src/config.json` and update the `stockfish_path` value to the full path of the Stockfish executable you downloaded (e.g., `"C:/path/to/stockfish.exe"`).

## Usage

### How to Run
To start the application, run the `main.py` script from the root directory:
```bash
python src/main.py
```

### Main Menu
You will be greeted with the Main Menu, which is the central hub for all application features.
*   `1`: Play a New Game
*   `2`: Load a Saved Game
*   `3`: Load a Practice Position
*   `?`: Ask a Chess Expert
*   `Q`: Quit

### In-Game Controls
While a game is in progress, you can press `Enter` to let the current player make its move, or you can type `m` to access the in-game menu. This menu allows you to load another game, load a practice position, swap AI models, ask the expert, or return to the main menu. After a game concludes, you will be prompted to save the game log before returning to the main menu.

## Testing

The project uses `pytest` for automated testing, particularly for verifying that players can solve checkmate puzzles. The test suite is configured to run every player against every puzzle defined in `src/config_pytest.json`.

### Useful Pytest Commands

All commands should be run from the root directory of the project. The `-s` flag is recommended to show all output, including the chess boards.

*   **Run All Tests:**
    Discovers and runs every test case.
    ```bash
    pytest -s
    ```

*   **Run Tests for a Specific Player Type:**
    Use the `-k` flag to filter tests by keywords.
    ```bash
    # Run only Stockfish tests
    pytest -s -k "Stockfish"

    # Run only AI tests
    pytest -s -k "AI"
    ```

*   **Run Tests for a Specific Puzzle:**
    This is useful for seeing how all players perform on a single puzzle.
    ```bash
    # Run only the "Queen-King" puzzle tests
    pytest -s -k "Queen-King"
    ```

*   **Run a Single, Highly Specific Test:**
    Combine keywords with `and` to target one specific test case. This is ideal for debugging.
    ```bash
    # Test the 'gpt-4o' model on the 'Queen-King' puzzle
    pytest -s -k "gpt-4o and Queen-King"
    ```

## Game Modes

The application offers several game modes to suit your needs:

*   **AI vs. AI:** Watch two AI players compete against each other. You can configure the AI models and opening strategies before the game starts.
*   **AI vs. Engine: **Play against the Stockfish chess engine at various difficulty levels. Configure the engine's skill level in the `config.json` file.
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
