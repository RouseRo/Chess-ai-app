# Chess AI Application

This project is a feature-rich, command-line chess application where two AI players, powered by large language models via the OpenRouter API, can play against each other. It is designed with a clean, object-oriented structure that separates application logic, user interface, and configuration.

## Features

*   **Configurable AI:** Easily add or change AI models and opening strategies by editing a simple JSON configuration file.
*   **Multiple Game Modes:** Start a new AI vs. AI game, load a previously saved game, or set up a board from a classic practice position.
*   **Interactive Gameplay:**
    *   Step through games move by move or auto-play a set number of turns.
    *   Take control at any time by manually entering a move for either player.
    *   Swap out the AI model for White or Black mid-game.
*   **Save & Load System:** Save an in-progress game at any time and load it later to continue.
*   **Practice Mode:** Load classic endgame checkmate positions to practice your skills against an AI.
*   **Game Logging:** Every move is logged to a file (`chess_game.log`), including the author (AI or User) and the board state in FEN notation.

## Project Structure

The project is organized with a separation of concerns to make it easy to maintain and extend:

*   `src/main.py`: The main entry point of the application. Contains the `ChessApp` class which manages the overall application flow.
*   `src/game.py`: Contains the `Game` class, which manages the state of a single chess game, including the board and players.
*   `src/ai_player.py`: Contains the `AIPlayer` class, responsible for communicating with the OpenRouter API to get AI moves.
*   `src/ui_manager.py`: Contains the `UIManager` class, which handles all console input and output, such as displaying menus and the board.
*   `src/config.json`: A JSON file for configuring the available AI models and opening strategies.
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

You can customize the available AI models and opening strategies by editing the `src/config.json` file.

For example, to add a new AI model, simply add a new entry to the `ai_models` object with a unique key (e.g., "m6"):

```json
"ai_models": {
  "m1": "openai/gpt-4o",
  "m2": "deepseek/deepseek-chat-v3.1",
  "m3": "google/gemini-1.5-pro",
  "m4": "anthropic/claude-3-opus",
  "m5": "meta-llama/llama-3-70b-instruct",
  "m6": "new-model/some-model-name"
}
```

The application will automatically pick up these changes the next time you run it.

## How to Run

To start the application, run the `main.py` script:

```bash
python src/main.py
```

You will be greeted with the Main Menu, which is the central hub for all application features. From here, you can choose to start a new game, load an existing game, or exit the application.

### Main Menu Options

1.  **New Game:** Start a new AI vs. AI game with your chosen settings.
2.  **Load Game:** Load a previously saved game from a file.
3.  **Practice Mode:** Enter practice mode to play out classic endgame scenarios against an AI.
4.  **Exit:** Close the application.

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
