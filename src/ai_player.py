import os
from dotenv import load_dotenv
import chess
from openai import OpenAI
import openai
import random

class AIPlayer:
    def __init__(self, model_name):
        self.model_name = model_name

        load_dotenv() # Load environment variables from .env file
        
        # Initialize the OpenAI API client to use OpenRouter
        self.client = OpenAI(
            base_url="https://openrouter.ai/api/v1",
            api_key=os.getenv("OPENAI_API_KEY"),
        )

    def compute_move(self, board: chess.Board, strategy_message=None):
        """
        Computes the next move using the specified AI model.
        """
        legal_moves_uci = [move.uci() for move in board.legal_moves]
        
        strategy_prompt = ""
        if strategy_message:
            strategy_prompt = f"Your designated strategy is: {strategy_message}."

        prompt = f"""You are a deterministic chess move selector. {strategy_prompt}
Analyze the position deeply, pick the best move by searching at least 3 moves ahead using minimax principles.
The current board state in FEN is:
{board.fen()}

The legal moves are: {', '.join(legal_moves_uci)}.
Your task is to select the absolute best possible move from the list of legal moves.
Respond with only the chosen move in UCI notation (e.g., 'e2e4')."""

        max_retries = 3
        for attempt in range(max_retries):
            try:
                completion = self.client.chat.completions.create(
                    model=self.model_name,
                    messages=[
                        {"role": "system", "content": 
                         "You are a helpful chess assistant that provides moves in UCI format."},
                        {"role": "user", "content": prompt},
                    ],
                    temperature=0.5,
                    max_tokens=10,
                )
                
                model_response = completion.choices[0].message.content.strip()

                # Check if the returned move is legal
                if model_response in legal_moves_uci:
                    print(f"Model {self.model_name} chose: {model_response}")
                    return model_response
                else:
                    print(f"Warning: Model returned an illegal move '{model_response}'. Attempt {attempt + 1}/{max_retries}")

            except Exception as e:
                print(f"An error occurred calling the API: {e}")
        
        # Fallback strategy if the model fails to provide a valid move
        print("AI failed to provide a valid move. Choosing a random legal move.")
        return random.choice(legal_moves_uci)


    def switch_model(self, new_model_name):
        self.model_name = new_model_name
        # Optionally reinitialize the API client if needed

    def ask_question(self, question, system_prompt):
        """Sends a general question to the AI model and returns the answer."""
        try:
            completion = self.client.chat.completions.create(
                model=self.model_name,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": question}
                ],
                temperature=0.5,
            )
            return completion.choices[0].message.content
        except openai.APIConnectionError as e:
            print(f"Failed to connect to API: {e}")
            return "Error: Could not connect to the AI service."
        except openai.APIError as e:
            print(f"An API error occurred: {e}")
            return f"Error: An API error occurred: {e}"

# Load environment variables
load_dotenv()