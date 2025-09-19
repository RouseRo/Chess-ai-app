import logging
import os

def setup_logging():
    project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    chess_log_path = os.path.join(project_root, 'chess_game.log')
    debug_log_path = os.path.join(project_root, 'debug.log')

    # Remove all handlers associated with the root logger object (for re-init)
    for handler in logging.root.handlers[:]:
        logging.root.removeHandler(handler)

    logging.basicConfig(
        level=logging.DEBUG,
        format='%(asctime)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler(chess_log_path, mode='w', encoding='utf-8'),   # Overwrite each run
            logging.FileHandler(debug_log_path, mode='a', encoding='utf-8'),   # Append each run
            logging.StreamHandler()  # Optional: also log to console
        ]
    )