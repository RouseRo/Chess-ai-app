import os
import re
import openai
import chess
from dotenv import load_dotenv

load_dotenv()

class AIPlayer:
    """Represents a player using an AI model via OpenRouter."""

    def __init__(self, model_name="openai/gpt-3.5-turbo"):
        self.model_name = model_name
        self.client = openai.OpenAI(
            base_url="https://openrouter.ai/api/v1",
            api_key=os.getenv("OPENAI_API_KEY"),
        )

    def _get_ai_response(self, messages):
        """Generic method to get a response from the AI model."""
        response = self.client.chat.completions.create(
            model=self.model_name,
            messages=messages,
        )
        return response.choices[0].message.content

    def get_chess_fact_or_answer(self, question=None):
        """
        Gets a chess fact or an answer to a specific question from the AI.
        """
        if question:
            system_prompt = "You are a world-class chess grandmaster and historian. Answer the user's question about chess concisely and accurately."
            user_prompt = question
        else:
            system_prompt = "You are a chess historian. Provide one interesting, little-known fun fact about the history of chess. Be concise."
            user_prompt = "Tell me a fun chess fact."

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ]
        return self._get_ai_response(messages)

    def compute_move(self, board, strategy=None):
        """
        Computes the best move using the AI model.
        """
        system_prompt = "You are a world-class chess engine. Your only goal is to win. Analyze the given FEN position and provide the best move in UCI notation (e.g., e2e4, g1f3). Do not provide any explanation, commentary, or any text other than the single move in UCI format."
        
        strategy_text = ""
        if strategy:
            strategy_text = f"As a reminder, your strategy for this game is: {strategy}"

        user_prompt = f"Current FEN: {board.fen()}. {strategy_text} It is your turn to move. What is your move?"

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ]

        uci_move = self._get_ai_response(messages).strip()
        
        # Find a valid UCI move in the response, as models sometimes add extra text.
        match = re.search(r'[a-h][1-8][a-h][1-8][qrbn]?', uci_move)
        if match:
            uci_move = match.group(0)
            try:
                move = chess.Move.from_uci(uci_move)
                if move in board.legal_moves:
                    return move
            except ValueError:
                # The model returned an invalid UCI string
                pass
        
        # If parsing fails, we cannot make a move.
        return None

    def get_move(self, game):
        """
        Returns a legal move in UCI format for the current position, using the AI model and (optionally) the player's strategy.
        """
        import chess
        strategy = getattr(game, "white_strategy", None) if game.board.turn == chess.WHITE else getattr(game, "black_strategy", None)
        move = self.compute_move(game.board, strategy)
        if move is not None:
            return move.uci() if hasattr(move, "uci") else move
        return None