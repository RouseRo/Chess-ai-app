import os
import json

def load_stockfish_config(config_path="src/config.json"):
    """
    Load Stockfish path and configs.
    Priority:
    1. STOCKFISH_EXECUTABLE environment variable (if set)
    2. "stockfish_executable" in config.json
    3. "stockfish_path" in config.json
    4. Default: "stockfish"
    Also sets os.environ["STOCKFISH_EXECUTABLE"] from config if present.
    """
    try:
        with open(config_path, 'r') as f:
            config = json.load(f)
            # Set the environment variable from config if present
            stockfish_executable = config.get("stockfish_executable")
            if stockfish_executable:
                os.environ["STOCKFISH_EXECUTABLE"] = stockfish_executable

            # Priority: env var > stockfish_executable > stockfish_path > "stockfish"
            stockfish_path = (
                os.environ.get("STOCKFISH_EXECUTABLE")
                or stockfish_executable
                or config.get("stockfish_path")
                or "stockfish"
            )
            stockfish_configs = config.get("stockfish_configs", {})
            return stockfish_path, stockfish_configs
    except (FileNotFoundError, json.JSONDecodeError) as e:
        raise RuntimeError(f"Could not load or parse '{config_path}': {e}")

def is_stockfish_available(stockfish_path):
    """Check if Stockfish binary is available."""
    return os.path.isfile(stockfish_path) or stockfish_path == "stockfish"