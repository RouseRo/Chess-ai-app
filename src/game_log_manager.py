import logging
import json
import re
import shutil
import chess
import os
from src.data_models import PlayerStats, GameHeader, stats_to_dict, GameLoopAction

LOG_FILE = 'chess_game.log'

logger = logging.getLogger()  # This will use the config from setup_logging()

class GameLogManager:
    def __init__(self, ui=None, ai_models=None, stockfish_configs=None, player_factory=None):
        self.log_buffer = []
        self.current_log_file = None
        self.ui = ui
        self.ai_models = ai_models
        self.stockfish_configs = stockfish_configs
        self.player_factory = player_factory
        # Self-diagnostics
        print("DIAGNOSTIC: GameLogManager __init__ called")
        print(f"  id(self): {id(self)}")
        print(f"  id(self.log_buffer): {id(self.log_buffer)}")
        print(f"  log_buffer initial: {self.log_buffer}")

    def initialize_new_game_log(self):
        """
        Resets the log buffer for a new game.
        """
        self.log_buffer = []

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

    def log_move(self, move_number, player, san, uci, fen):
        logger.info(f"Logging move {move_number}: {san} ({uci}) by {player}")
        logger.debug(f"FEN after move: {fen}")
        print("DIAGNOSTIC: log_move called")
        print(f"  move_number: {move_number}, player: {player}, san: {san}, uci: {uci}, fen: {fen}")
        move_line = f"{move_number}. {player}: {san} ({uci}) FEN: {fen}"
        self.log_buffer.append(move_line)
        print(f"DIAGNOSTIC: log_buffer after move: {self.log_buffer}")

    def log_last_move(self, board, player_name=None):
        print(f"DEBUG: Logging last move - Board FEN: {board.fen()}")
        """Logs the last move made on the board, including SAN, UCI, and FEN."""
        if board.move_stack:
            last_move = board.move_stack[-1]
            try:
                move_san = board.san(last_move)
            except Exception as e:
                print(f"DEBUG: Exception in SAN generation: {e}")
                move_san = "INVALID"
            move_uci = last_move.uci()
            # Determine player name if not provided
            if player_name is None:
                color = board.turn ^ 1  # The player who just moved
                if hasattr(board, 'players'):
                    player = board.players[color]
                    player_name = getattr(player, 'name', str(player))
                else:
                    player_name = "Unknown"
            print(f"DIAGNOSTIC: Calling log_move with: {board.fullmove_number}, {player_name}, {move_san}, {move_uci}, {board.fen()}")
            self.log_move(board.fullmove_number, player_name, move_san, move_uci, board.fen())

    def log_game_start(self, player1, player2, white_key, black_key, white_opening, black_defense, initial_fen):
        logger.info("Logging game start")
        logger.debug(
            f"Players: {str(player1)} vs {str(player2)}, "
            f"Keys: {white_key}/{black_key}, "
            f"Openings: {white_opening}/{black_defense}, "
            f"FEN: {initial_fen}"
        )
        print("DIAGNOSTIC: log_game_start called")
        print(f"  id(self): {id(self)}")
        print(f"  id(self.log_buffer): {id(self.log_buffer)}")
        print(f"  log_buffer before header append: {self.log_buffer}")
        print(f"  player1: {player1}, player2: {player2}")
        print(f"  white_key: {white_key}, black_key: {black_key}")
        print(f"  white_opening: {white_opening}, black_defense: {black_defense}")
        print(f"  initial_fen: {initial_fen}")
        self.log_buffer.append(f"[White] {str(player1)} ({white_key})")
        self.log_buffer.append(f"[Black] {str(player2)} ({black_key})")
        self.log_buffer.append(f"[Initial FEN] {initial_fen}")
        self.log_buffer.append(f"[White Opening] {white_opening}")
        self.log_buffer.append(f"[Black Defense] {black_defense}")
        self.log_buffer.append("-" * 40)
        print(f"DIAGNOSTIC: log_buffer after header: {self.log_buffer}")

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
                color = board.turn ^ 1  # The player who just moved
                player = game.players[color]
                player_name = getattr(player, 'name', str(player))
                print("DIAGNOSTIC: About to log move", board.fullmove_number, player_name, move_san, move_uci, board.fen())
                # Correct: includes the player argument
                self.log_move(board.fullmove_number, player_name, move_san, move_uci, board.fen())
            except Exception as e:
                logging.error(f"Error logging move {move_uci}: {e}")
        else:
            logging.debug("No moves have been made yet.")

        return game, GameLoopAction.CONTINUE

    def add_log_line(self, line):
        # Alternative to append
        self.log_buffer = self.log_buffer + [line]

    def save_game_log(self, file_path=None):
        project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        abs_path = os.path.join(project_root, 'chess_game.log')
        logger.info(f"Game log absolute path: {abs_path}")
        try:
            with open(abs_path, 'w', encoding='utf-8') as f:
                for line in self.log_buffer:
                    f.write(line + '\n')
                    logger.info(f"GameLog: {line}")
            logger.info(f"Game log successfully written to {abs_path}")
        except Exception as e:
            logger.error(f"Exception while writing game log: {e}")

    def flush_log(self):
        logger.info("Flushing log to disk")
        print("DIAGNOSTIC: flush_log called")
        print(f"  log_buffer before flush: {self.log_buffer}")
        self.save_game_log()
        print(f"  log_buffer after flush: {self.log_buffer}")
