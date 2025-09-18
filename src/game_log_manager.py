import logging
import json
import re
import shutil
import chess
from src.data_models import PlayerStats, GameHeader, stats_to_dict, GameLoopAction

LOG_FILE = 'chess_game.log'

class GameLogManager:
    def __init__(self, ui, player_factory, ai_models, stockfish_configs):
        self.ui = ui
        self.player_factory = player_factory
        self.ai_models = ai_models
        self.stockfish_configs = stockfish_configs

    def initialize_new_game_log(self):
        """Shuts down existing log handlers and re-initializes the log file in write mode."""
        logging.shutdown()
        logging.basicConfig(
            filename=LOG_FILE,
            level=logging.INFO,
            format='%(asctime)s - %(message)s',
            filemode='w'
        )
        logging.getLogger("httpx").setLevel(logging.WARNING)

    def parse_log_header(self, lines, all_player_keys, debug=False):
        # ...copy the full function body from main.py...
        # (No changes needed except indentation and self if you use instance variables)
        header_data = {}
        if debug:
            print("\n==== DIAGNOSTICS: PARSING LOG HEADER ====", flush=True)
            print(f"Processing {len(lines)} lines, looking at first 10", flush=True)
            print(f"Available player keys: {all_player_keys}", flush=True)
        if debug:
            print("\n--- FIRST 10 LINES OF FILE ---", flush=True)
            for i, line in enumerate(lines[:10]):
                print(f"LINE {i+1}: {line.strip()}", flush=True)
        if debug:
            print("\n--- REGEX MATCHING RESULTS ---", flush=True)
        for i, line in enumerate(lines[:10]):
            if debug:
                print(f"Processing line {i+1}: {line.strip()}", flush=True)
            match = re.match(r"\[(\w+)\s+\"(.+?)\"\]", line)
            if match:
                key, value = match.groups()
                header_data[key.lower()] = value
                if debug:
                    print(f"  ✓ MATCHED: key='{key.lower()}', value='{value}'", flush=True)
            else:
                alt_match = re.search(r'.*- ([^:]+):\s*(.+)', line)
                if alt_match:
                    key, value = alt_match.groups()
                    clean_key = key.lower().replace(' ', '_')
                    header_data[clean_key] = value
                    if debug:
                        print(f"  ✓ ALT MATCHED: key='{clean_key}', value='{value}'", flush=True)
        required_keys = ['white', 'black', 'white_player_key', 'black_player_key']
        if not all(k in header_data for k in required_keys):
            missing = [k for k in required_keys if k not in header_data]
            error_msg = f"Header is missing required tags ({', '.join(missing)})."
            if debug:
                print(f"\n❌ ERROR: {error_msg}", flush=True)
            return None, error_msg
        if header_data['white_player_key'] not in all_player_keys or header_data['black_player_key'] not in all_player_keys:
            error_msg = "Player key in log is not in current config."
            if debug:
                print(f"\n❌ ERROR: {error_msg}", flush=True)
            return None, error_msg
        return GameHeader(
            white_name=header_data['white'],
            black_name=header_data['black'],
            white_key=header_data['white_player_key'],
            black_key=header_data['black_player_key'],
            white_strategy=header_data.get('white_strategy'),
            black_strategy=header_data.get('black_strategy'),
            result=header_data.get('result'),
            termination=header_data.get('termination'),
            date=header_data.get('date')
        ), None

    def load_game_from_log(self, log_file):
        try:
            with open(log_file, 'r') as f:
                lines = f.readlines()
            all_keys = list(self.ai_models.keys()) + list(self.stockfish_configs.keys()) + ['hu']
            header, error_reason = self.parse_log_header(lines, all_keys)
            if not header:
                self.ui.display_message(f"Failed to load game: {error_reason}")
                return None
            player1 = self.player_factory.create_player(header.white_key, name_override=header.white_name)
            # FIX: Use 'black_name' instead of 'blackName'
            player2 = self.player_factory.create_player(header.black_key, name_override=header.black_name)
            from src.game_manager import Game
            game = Game(player1, player2, white_strategy=header.white_strategy, 
                   black_strategy=header.black_strategy, 
                   white_player_key=header.white_key, 
                   black_player_key=header.black_key)
            initial_fen = None
            for line in lines:
                if "Initial FEN:" in line:
                    initial_fen = line.split("Initial FEN:")[1].strip()
                    break
            last_fen = initial_fen
            for line in lines:
                if "FEN:" in line and "Initial FEN:" not in line:
                    fen_part = line.split("FEN:")[1].strip()
                    if ' ' in fen_part:
                        last_fen = fen_part.split(',')[0].strip()
                    else:
                        last_fen = fen_part
            if last_fen:
                game.set_board_from_fen(last_fen)
                print(f"Set board position from FEN", flush=True)
            else:
                print("Warning: No FEN found in log file", flush=True)
            return game
        except Exception as e:
            self.ui.display_message(f"Error loading log file: {e}")
            return None

    def log_new_game_header(self, game, white_opening_obj=None, black_defense_obj=None):
        import chess

        logging.info("New Game Started")
        logging.info(f"White: {game.players[chess.WHITE].model_name}")
        logging.info(f"Black: {game.players[chess.BLACK].model_name}")
        logging.info(f"White Player Key: {getattr(game, 'white_player_key', '')}")
        logging.info(f"Black Player Key: {getattr(game, 'black_player_key', '')}")
        logging.info(
            f"White Strategy: {white_opening_obj or 'No Classic Chess Opening'}"
        )
        logging.info(
            f"Black Strategy: {black_defense_obj or 'No Classic Chess Defense'}"
        )
        logging.info(f"Initial FEN: {game.board.fen()}")

    def log_move(self, move_number, move_san, move_uci, fen=None):
        msg = f"Move {move_number}: {move_san} ({move_uci})"
        if fen:
            msg += f" | FEN: {fen}"
        logging.info(msg)

    def log_last_move(self, board):
        """Logs the last move made on the board, including SAN, UCI, and FEN."""
        if board.move_stack:
            last_move = board.move_stack[-1]
            try:
                move_san = board.san(last_move)
            except Exception:
                move_san = "INVALID"
            move_uci = last_move.uci()
            self.log_move(board.fullmove_number, move_san, move_uci, fen=board.fen())

    def play_turn(self, game):
        board = game.board
        logging.debug(f"Board FEN before move: {board.fen()}")

        if board.move_stack:
            last_move = board.move_stack[-1]
            move_uci = last_move.uci()
            logging.debug(f"Last move in UCI: {move_uci}")

            # Check if the move is legal
            if board.is_legal(last_move):
                try:
                    move_san = board.san(last_move)
                    logging.debug(f"Last move in SAN: {move_san}")
                except Exception as e:
                    logging.error(f"Error generating SAN for move {last_move}: {e}")
                    move_san = "INVALID"
            else:
                logging.error(f"Move {move_uci} is not legal in the current board state: {board.fen()}")
                move_san = "ILLEGAL"

            # Log the move
            try:
                self.game_log_manager.log_move(board.fullmove_number, move_san, move_uci, fen=board.fen())
            except Exception as e:
                logging.error(f"Error logging move {move_uci}: {e}")
        else:
            logging.debug("No moves have been made yet.")

        return game, GameLoopAction.CONTINUE
