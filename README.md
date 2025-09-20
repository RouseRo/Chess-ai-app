# Chess AI App

A console-based chess application supporting human and AI players, classic chess openings, move logging, and game analysis.

## Features

- Play as human or against various AI models (OpenAI, DeepSeek, Gemini, Claude, Llama, Stockfish)
- Choose classic chess openings and defenses for both White and Black
- Game logs record player models, chosen strategies, and all moves in FEN notation
- Save and load games from log files
- View player stats and practice positions
- Ask chess-related questions to an integrated chess expert

## How to Use

1. **Install dependencies**  
   Activate your virtual environment and install requirements:
   ```
   pip install -r requirements.txt
   ```

2. **Run the app**
   ```
   python -m src.main
   ```

3. **Main Menu Options**
   - `1`: Play a New Game (choose players, opening, defense)
   - `2`: Load a Saved Game
   - `3`: Load a Practice Position
   - `4`: View Player Stats
   - `?`: Ask a Chess Expert
   - `q`: Quit

4. **Game Logging**
   - Each game is logged in `logs/games/` with player info, chosen strategies, and all moves.
   - Example log excerpt:
     ```
     2025-09-16 13:01:24,818 - New Game Started
     2025-09-16 13:01:24,818 - White: Stockfish (Skill: 10)
     2025-09-16 13:01:24,818 - Black: Stockfish (Skill: 20)
     2025-09-16 13:01:24,818 - White Player Key: s2
     2025-09-16 13:01:24,818 - Black Player Key: s3
     2025-09-16 13:01:24,818 - White Strategy: Play the Ruy Lopez.
     2025-09-16 13:01:24,818 - Black Strategy: Play the Sicilian Defense.
     2025-09-16 13:01:24,818 - Initial FEN: rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1
     ```

## Configuration

- Edit `src/config.json` to add or modify AI models, Stockfish configs, and available openings/defenses.

## Notes

- If you select no opening/defense, the log will show "No Classic Chess Opening"/"No Classic Chess Defense".
- All strategy selections are now correctly logged in the game log file.

---

Enjoy playing and analyzing chess with AI!
