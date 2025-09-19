import logging
import json
import re
import shutil
import chess
import os
from src.data_models import PlayerStats, GameHeader, stats_to_dict, GameLoopAction
from datetime import datetime

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

    def initialize_new_game_log(self):
        """
        Resets the log buffer for a new game.
        """
        self.log_buffer = []

    def parse_log_header(self, lines, all_player_keys, debug=False):
        header_data = {}
        for i, line in enumerate(lines[:10]):
            match = re.match(r"\[(\w+)\s+\"(.+?)\"\]", line)
            if match:
                key, value = match.groups()
                header_data[key.lower()] = value
            else:
                alt_match = re.search(r'.*- ([^:]+):\s*(.+)', line)
                if alt_match:
                    key, value = alt_match.groups()
                    clean_key = key.lower().replace(' ', '_')
                    header_data[clean_key] = value
        required_keys = ['white', 'black', 'white_player_key', 'black_player_key']
        if not all(k in header_data for k in required_keys):
            missing = [k for k in required_keys if k not in header_data]
            error_msg = f"Header is missing required tags ({', '.join(missing)})."
            return None, error_msg
        if header_data['white_player_key'] not in all_player_keys or header_data['black_player_key'] not in all_player_keys:
            error_msg = "Player key in log is not in current config."
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
            return game
        except Exception as e:
            self.ui.display_message(f"Error loading log file: {e}")
            return None

    def log_new_game_header(self, game, white_opening_obj=None, black_defense_obj=None):
        import chess
        # Write header to log buffer (for chess_game.log)
        self.log_buffer.append(f"[Date] {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        self.log_buffer.append(f"[White] {game.players[chess.WHITE].model_name}")
        self.log_buffer.append(f"[Black] {game.players[chess.BLACK].model_name}")
        self.log_buffer.append(f"[White_Player_Key] {getattr(game, 'white_player_key', '')}")
        self.log_buffer.append(f"[Black_Player_Key] {getattr(game, 'black_player_key', '')}")
        self.log_buffer.append(f"[White_Strategy] {white_opening_obj or 'No Classic Chess Opening'}")
        self.log_buffer.append(f"[Black_Strategy] {black_defense_obj or 'No Classic Chess Defense'}")
        self.log_buffer.append(f"[Initial_FEN] {game.board.fen()}")
        self.log_buffer.append("-" * 40)
        # Also log to debug.log for diagnostics
        logging.info("New Game Started")
        logging.info(f"White: {game.players[chess.WHITE].model_name}")
        logging.info(f"Black: {game.players[chess.BLACK].model_name}")
        logging.info(f"White Player Key: {getattr(game, 'white_player_key', '')}")
        logging.info(f"Black Player Key: {getattr(game, 'black_player_key', '')}")
        logging.info(f"White Strategy: {white_opening_obj or 'No Classic Chess Opening'}")
        logging.info(f"Black Strategy: {black_defense_obj or 'No Classic Chess Defense'}")
        logging.info(f"Initial FEN: {game.board.fen()}")

    def log_move(self, move_number, player, san, uci, fen):
        logger.info(f"Logging move {move_number}: {san} ({uci}) by {player}")
        logger.debug(f"FEN after move: {fen}")
        move_line = f"{move_number}. {player}: {san} ({uci}) FEN: {fen}"
        self.log_buffer.append(move_line)

    def log_last_move(self, board, player_name=None):
        """Logs the last move made on the board, including SAN, UCI, and FEN."""
        if board.move_stack:
            last_move = board.move_stack[-1]
            try:
                move_san = board.san(last_move)
            except Exception as e:
                move_san = "INVALID"
            move_uci = last_move.uci()
            if player_name is None:
                color = board.turn ^ 1  # The player who just moved
                if hasattr(board, 'players'):
                    player = board.players[color]
                    player_name = getattr(player, 'name', str(player))
                else:
                    player_name = "Unknown"
            self.log_move(board.fullmove_number, player_name, move_san, move_uci, board.fen())

    def log_game_start(self, player1, player2, white_key, black_key, white_opening, black_defense, initial_fen):
        logger.info("Logging game start")
        logger.debug(
            f"Players: {str(player1)} vs {str(player2)}, "
            f"Keys: {white_key}/{black_key}, "
            f"Openings: {white_opening}/{black_defense}, "
            f"FEN: {initial_fen}"
        )
        self.log_buffer.append(f"[White] {str(player1)} ({white_key})")
        self.log_buffer.append(f"[Black] {str(player2)} ({black_key})")
        self.log_buffer.append(f"[Initial FEN] {initial_fen}")
        self.log_buffer.append(f"[White Opening] {white_opening}")
        self.log_buffer.append(f"[Black Defense] {black_defense}")
        self.log_buffer.append("-" * 40)

    def play_turn(self, game):
        board = game.board
        logging.debug(f"Board FEN before move: {board.fen()}")

        if board.move_stack:
            last_move = board.move_stack[-1]
            move_uci = last_move.uci()
            logging.debug(f"Last move in UCI: {move_uci}")

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

            try:
                color = board.turn ^ 1  # The player who just moved
                player = game.players[color]
                player_name = getattr(player, 'name', str(player))
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
        self.save_game_log()
