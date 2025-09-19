import logging
import os

def setup_logging():
    project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    chess_log_path = os.path.join(project_root, 'chess_game.log')
    debug_log_path = os.path.join(project_root, 'debug.log')

    # Remove all handlers associated with the root logger object (for re-init)
    for handler in logging.root.handlers[:]:
        logging.root.removeHandler(handler)

    # Create handlers
    file_handler1 = logging.FileHandler(chess_log_path, mode='w', encoding='utf-8')
    file_handler1.setLevel(logging.INFO)  # Only log INFO and above to chess_game.log
    file_handler2 = logging.FileHandler(debug_log_path, mode='a', encoding='utf-8')
    file_handler2.setLevel(logging.DEBUG)  # Keep DEBUG logs in debug.log
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.WARNING)  # Only show WARNING and above in console

    formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
    file_handler1.setFormatter(formatter)
    file_handler2.setFormatter(formatter)
    console_handler.setFormatter(formatter)

    logging.basicConfig(
        level=logging.DEBUG,
        handlers=[file_handler1, file_handler2, console_handler]
    )

    # Suppress DEBUG logs from Stockfish UCI protocol handlers
    logging.getLogger("chess.engine").setLevel(logging.WARNING)
    logging.getLogger("asyncio").setLevel(logging.WARNING)

    # Suppress INFO logs from external libraries
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("openai").setLevel(logging.WARNING)
    logging.getLogger("urllib3").setLevel(logging.WARNING)
    # Add any other noisy libraries as needed