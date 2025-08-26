# Chess AI Application

This project is a simple command-line chess application where two AI players, powered by large language models via the OpenRouter API, play against each other.

## Features

*   AI vs. AI chess gameplay.
*   Utilizes different language models for each player.
*   Customizable opening strategies for both White and Black.
*   Interactive and automatic move progression.
*   Displays the board in the console after each move.

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

The game will start, and you will see the board printed in the terminal. You can press Enter to step through the game move by move, or enter a number to have the game auto-play that many full moves.

## Setting Opening Strategies

You can specify an opening strategy for both the White and Black players directly within the `src/main.py` file. These strategies are passed as text prompts to the AI to influence their opening moves for the first three turns.

To change the strategies, locate the following line in `src/main.py`:

```python
# filepath: src/main.py
game = Game(ai_player1, ai_player2, white_strategy="Play the Ruy Lopez.", black_strategy="Play the Sicilian Defense.")
```

You can modify the `white_strategy` and `black_strategy` string values to guide the AI players. For example, to have White play the Queen's Gambit, you would change the line to:

```python
# filepath: src/main.py
game = Game(ai_player1, ai_player2, white_strategy="Play the Queen's Gambit.", black_strategy="Play the Sicilian Defense.")
```