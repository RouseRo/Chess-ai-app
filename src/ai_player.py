import os
import re
import openai
import chess
from dotenv import load_dotenv
load_dotenv(dotenv_path="c:/Users/rober/Source/Repos/Chess-ai-app/.env", override=True)

DEBUG = False  # Set to True to enable debug output

class AIPlayer:
    """Represents a player using an AI model via OpenRouter."""

    def __init__(self, model_name="openai/gpt-3.5-turbo"):
        self.model_name = model_name
        api_key = os.getenv("OPENAI_API_KEY")
        if DEBUG:
            print(f"[DEBUG] Using API key: {api_key[:15]}...")  # Only show first 15 chars for privacy
        try:
            self.client = openai.OpenAI(
                base_url="https://openrouter.ai/api/v1",
                api_key=api_key,
            )
            if DEBUG:
                print(f"[DEBUG] openai.OpenAI() returned: {self.client}")
        except Exception as e:
            if DEBUG:
                print(f"[ERROR] Exception initializing OpenAI client: {e}")
            self.client = None
        if DEBUG:
            print(f"[DEBUG] Initialized AIPlayer with model: {self.model_name}")

    def _get_ai_response(self, messages):
        """Generic method to get a response from the AI model."""
        if DEBUG:
            print(f"[DEBUG] Sending messages to AI: {messages}")
        try:
            response = self.client.chat.completions.create(
                model=self.model_name,
                messages=messages,
            )
            if DEBUG:
                print(f"[DEBUG] AI response: {response}")
            return response.choices[0].message.content
        except Exception as e:
            if DEBUG:
                print(f"[ERROR] Exception during AI response: {e}")
            return f"[ERROR] {e}"

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
        if DEBUG:
            print(f"[DEBUG] get_chess_fact_or_answer messages: {messages}")
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
        if DEBUG:
            print(f"[DEBUG] compute_move messages: {messages}")

        uci_move = self._get_ai_response(messages).strip()
        if DEBUG:
            print(f"[DEBUG] Raw AI move response: {uci_move}")
        
        # Find a valid UCI move in the response, as models sometimes add extra text.
        match = re.search(r'[a-h][1-8][a-h][1-8][qrbn]?', uci_move)
        if match:
            uci_move = match.group(0)
            if DEBUG:
                print(f"[DEBUG] Parsed UCI move: {uci_move}")
            try:
                move = chess.Move.from_uci(uci_move)
                if move in board.legal_moves:
                    if DEBUG:
                        print(f"[DEBUG] Move is legal: {move}")
                    return move
                else:
                    if DEBUG:
                        print(f"[DEBUG] Move is not legal: {move}")
            except ValueError:
                if DEBUG:
                    print(f"[ERROR] Invalid UCI string from AI: {uci_move}")
        
        # If parsing fails, we cannot make a move.
        if DEBUG:
            print("[DEBUG] No valid move found.")
        return None

    def get_move(self, game):
        """
        Returns a legal move in UCI format for the current position, using the AI model and (optionally) the player's strategy.
        """
        import chess
        strategy = getattr(game, "white_strategy", None) if game.board.turn == chess.WHITE else getattr(game, "black_strategy", None)
        if DEBUG:
            print(f"[DEBUG] get_move strategy: {strategy}")
        move = self.compute_move(game.board, strategy)
        if move is not None:
            if DEBUG:
                print(f"[DEBUG] get_move returning: {move.uci() if hasattr(move, 'uci') else move}")
            return move.uci() if hasattr(move, "uci") else move
        if DEBUG:
            print("[DEBUG] get_move returning: None")
        return None