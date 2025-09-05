class HumanPlayer:
    """Represents a human player in the game."""
    def __init__(self, name="Human"):
        self._name = name

    @property
    def model_name(self):
        """Returns the name of the human player."""
        return self._name

    def compute_move(self, board, **kwargs):
        """
        For a human player, move computation is handled by the main game loop's
        manual input. This method does nothing and returns None.
        """
        return None