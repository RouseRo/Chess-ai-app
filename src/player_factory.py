from ai_player import AIPlayer
from stockfish_player import StockfishPlayer
from human_player import HumanPlayer

class PlayerFactory:
    """A factory for creating different types of chess players."""

    def __init__(self, ui, ai_models, stockfish_configs, stockfish_path):
        """
        Initializes the factory with necessary configurations and UI manager.
        
        Args:
            ui: The UIManager instance for user interaction (e.g., getting names).
            ai_models (dict): Configuration for AI models.
            stockfish_configs (dict): Configuration for Stockfish instances.
            stockfish_path (str): Path to the Stockfish executable.
        """
        self.ui = ui
        self.ai_models = ai_models
        self.stockfish_configs = stockfish_configs
        self.stockfish_path = stockfish_path

    def create_player(self, player_key, color_label=None, name_override=None):
        """
        Creates a player object based on the provided key.

        This is the single point of entry for creating any player. It handles:
        - Human players (prompting for a name or using an override).
        - AI model players.
        - Stockfish players.
        
        Args:
            player_key (str): The key identifying the player type (e.g., 'hu', 'm1', 's2').
            color_label (str, optional): The player's color ('White' or 'Black') for UI prompts.
            name_override (str, optional): A specific name to assign, used when loading games.

        Returns:
            A player object (HumanPlayer, AIPlayer, or StockfishPlayer), or None if the key is invalid.
        """
        if not player_key:
            return None

        if player_key == 'hu':
            if name_override:
                # Use the name from a log file when loading a game
                return HumanPlayer(name=name_override)
            else:
                # Prompt for a name for a new game
                name = self.ui.get_human_player_name(color_label or "Human")
                return HumanPlayer(name=f"{name} ({player_key})")

        elif player_key.startswith('m'):
            model_name = self.ai_models.get(player_key)
            if model_name:
                return AIPlayer(model_name=model_name)

        elif player_key.startswith('s'):
            config = self.stockfish_configs.get(player_key)
            if config:
                return StockfishPlayer(self.stockfish_path, parameters=config.get('parameters'))

        raise ValueError(f"Unknown or invalid player key: {player_key}")