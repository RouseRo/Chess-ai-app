# Chess AI Application

This project is a simple command-line chess application where two AI players, powered by large language models via the OpenRouter API, play against each other.

## Features

*   AI vs. AI chess gameplay.
*   Utilizes different language models for each player.
*   Customizable opening strategies for both White and Black.
*   Interactive and automatic move progression.
*   Displays the board in the console after each move.
*   Logs every game to a file for later review.

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
    *   Create a file named `.env` in the root directory of the project.
    *   Add your OpenRouter API key to the `.env` file:
        ```
        OPENAI_API_KEY="your-openrouter-api-key"
        ```

## How to Run

To start a game, simply run the `main.py` script:

```bash
python src/main.py
```

The game will start by presenting menus to select opening strategies and AI models. After making your selections, the game will begin. You can press Enter to step through the game move by move, or enter a number to have the game auto-play that many full moves.

## Setting Opening Strategies

When you run the application, a menu will be displayed allowing you to choose the opening strategies for both White and Black.

```
--- Choose Opening Strategies ---

White Openings:
  1: Ruy Lopez.
  2: Italian Game.
  3: Queen's Gambit.
  4: London System.
  5: King's Gambit.

Black Defenses:
  a: Sicilian Defense.
  b: French Defense.
  c: Caro-Kann Defense.

Enter your choice (e.g., '1a', '3c'):
```

To select the strategies, enter a two-character string consisting of a number for White's opening and a letter for Black's defense. For example, to have White play the **Ruy Lopez** and Black play the **Sicilian Defense**, you would enter `1a`.

## Selecting AI Models

After choosing the strategies, a second menu will appear, allowing you to select the AI models for each player.

```
--- Choose AI Models ---
  m1: openai/gpt-4o
  m2: deepseek/deepseek-chat-v3.1
  m3: google/gemini-1.5-pro
  ...

Enter your choice for White and Black models (e.g., 'm1m5'):
```

To select the models, enter a four-character string combining the keys for the White and Black players. For example, to have White use `openai/gpt-4o` (`m1`) and Black use `meta-llama/llama-3-70b-instruct` (`m5`), you would enter `m1m5`.

## Game Logging

Each game session is automatically logged to a file named `chess_game.log` in the project's root directory. The log file is overwritten for each new game.

For every move, the log records:
- The move number and the player who moved.
- The move in UCI (Universal Chess Interface) notation.
- The board state after the move in FEN (Forsyth–Edwards Notation).

This allows for detailed post-game analysis.
