import os
import re
from datetime import datetime, timezone
from src.ai_player import AIPlayer
from src.game import RED, ENDC

class ExpertService:
    """Handles expert Q&A, fun facts, and jokes storage."""

    def __init__(self, ui, expert_model_name: str):
        self.ui = ui
        self.expert_model_name = expert_model_name

    # ---------- Public API ----------

    def ask_expert(self, question: str | None = None):
        """
        If question is None or blank, show menu:
          1: Ask a chess question
          2: Tell me a chess joke
          3: Tell me some chess news
        Saves jokes if requested.
        """
        request_type = None
        if not question or not question.strip():
            choice = self.ui.display_ask_expert_menu().strip().lower()
            if choice == '1':
                question = self.ui.get_user_input("What is your chess question? ").strip()
                if not question:
                    return
                request_type = 'question'
            elif choice == '2':
                question = "Tell me a short, clean chess joke."
                request_type = 'joke'
            elif choice == '3':
                question = "Provide 3 brief, recent chess news headlines with one-sentence summaries. Be concise."
                request_type = 'news'
            else:
                return

        self.ui.display_message("\nAsking the Chessmaster...")
        try:
            expert_player = AIPlayer(model_name=self.expert_model_name)
            answer = expert_player.get_chess_fact_or_answer(question)
            self.ui.display_message("\n--- Chessmaster's Answer ---")
            self.ui.display_message(answer)
            self.ui.display_message("-----------------------------")
            if request_type == 'joke' and answer:
                saved = self._save_chess_joke(answer)
                if saved:
                    self.ui.display_message("Joke saved to docs/CHESS_JOKES.md")
                else:
                    self.ui.display_message("Joke appears recently in CHESS_JOKES.md — not saved.")
        except Exception as e:
            self.ui.display_message(f"{RED}Sorry, I couldn't get an answer. Error: {e}{ENDC}")
        self.ui.get_user_input("Press Enter to return.")

    def get_fun_fact(self):
        """Fetch a random fun chess fact and persist it if not a recent duplicate."""
        self.ui.display_message("\nGetting a fun chess fact...")
        try:
            expert_player = AIPlayer(model_name=self.expert_model_name)
            prompt = (
                "Give me a unique chess fact or piece of trivia. "
                "Do not repeat facts about the Queen's movement. "
                "You may share a historical event, a famous player's achievement, a record, a rule, or something from recent chess news. "
                "If possible, avoid repeating facts from previous answers."
            )
            answer = expert_player.get_chess_fact_or_answer(prompt)
            self.ui.display_message("\n--- Fun Chess Fact ---")
            self.ui.display_message(answer)
            self.ui.display_message("----------------------")
            saved = self._save_fun_fact(answer)
            if saved:
                self.ui.display_message("Fun fact saved to docs/CHESS_FUN_FACTS.md")
            else:
                self.ui.display_message("This fact appears recently in CHESS_FUN_FACTS.md — not saved.")
        except Exception as e:
            self.ui.display_message(f"{RED}Sorry, I couldn't get a fact. Error: {e}{ENDC}")
        self.ui.get_user_input("Press Enter to return to the main menu.")

    def analyze_position(self, position_fen):
        """
        Ask the chessmaster AI model to analyze the given FEN board position.
        """
        self.ui.display_message("\nAnalyzing position with the Chessmaster...")
        try:
            expert_player = AIPlayer(model_name=self.expert_model_name)
            prompt = (
                f"Analyze this chess position (FEN): {position_fen}\n"
                "Give a brief evaluation, best moves for both sides, and any tactical ideas."
            )
            answer = expert_player.get_chess_fact_or_answer(prompt)
            self.ui.display_message("\n--- Chessmaster's Analysis ---")
            self.ui.display_message(answer)
            self.ui.display_message("-------------------------------")
        except Exception as e:
            self.ui.display_message(f"{RED}Sorry, analysis failed. Error: {e}{ENDC}")
        self.ui.get_user_input("Press Enter to return to the menu.")

    def opening_advice(self):
        """
        Ask the chessmaster AI model for general chess opening advice.
        Saves the answer to docs/EXPERT_ANSWERS.md.
        """
        self.ui.display_message("\nGetting opening advice from the Chessmaster...")
        try:
            expert_player = AIPlayer(model_name=self.expert_model_name)
            prompt = (
                "Give practical advice for chess openings. "
                "Include general principles, common mistakes, and tips for improvement."
            )
            answer = expert_player.get_chess_fact_or_answer(prompt)
            self.ui.display_message("\n--- Chessmaster's Opening Advice ---")
            self.ui.display_message(answer)
            self.ui.display_message("-------------------------------")
            self._save_expert_answer(prompt, answer)
        except Exception as e:
            self.ui.display_message(f"{RED}Sorry, opening advice failed. Error: {e}{ENDC}")
        self.ui.get_user_input("Press Enter to return to the menu.")

    def ask_chess_question(self):
        """
        Prompt the user for a chess question, ask the chessmaster AI model, and save the answer.
        """
        question = self.ui.get_user_input("Enter your chess question: ").strip()
        if not question:
            self.ui.display_message("No question entered. Returning to menu.")
            return
        self.ui.display_message("\nAsking the Chessmaster your question...")
        try:
            expert_player = AIPlayer(model_name=self.expert_model_name)
            answer = expert_player.get_chess_fact_or_answer(question)
            self.ui.display_message("\n--- Chessmaster's Answer ---")
            self.ui.display_message(answer)
            self.ui.display_message("-----------------------------")
            self._save_expert_answer(question, answer)
        except Exception as e:
            self.ui.display_message(f"{RED}Sorry, I couldn't get an answer. Error: {e}{ENDC}")
        self.ui.get_user_input("Press Enter to return to the menu.")

    # ---------- Internal persistence helpers ----------

    def _save_chess_joke(self, joke_text: str) -> bool:
        """Append a numbered, dated joke unless recently duplicated."""
        return self._append_numbered_block(
            filename="CHESS_JOKES.md",
            header="# Chess Jokes\n\n_Generated chess jokes. Duplicates within recent entries are skipped._\n\n---\n\n",
            body_text=joke_text,
            recent_check=50
        )

    def _save_fun_fact(self, fact_text: str) -> bool:
        """Append a numbered, dated fun fact unless recently duplicated."""
        return self._append_numbered_block(
            filename="CHESS_FUN_FACTS.md",
            header="# Chess Fun Facts\n\n_Generated fun facts. Duplicates within recent entries are skipped._\n\n---\n\n",
            body_text=fact_text,
            recent_check=20
        )

    def _append_numbered_block(self, filename: str, header: str, body_text: str, recent_check: int) -> bool:
        """Generic helper for numbered markdown blocks with duplicate suppression."""
        try:
            docs_dir = os.path.join(os.getcwd(), "docs")
            os.makedirs(docs_dir, exist_ok=True)
            path = os.path.join(docs_dir, filename)

            if not os.path.exists(path):
                with open(path, "w", encoding="utf-8") as f:
                    f.write(header)

            with open(path, "r", encoding="utf-8") as f:
                content = f.read()

            entries = [e.strip() for e in re.split(r"\n-{3,}\n", content) if e.strip()]
            recent_entries = entries[-recent_check:] if len(entries) > 1 else []

            normalized_new = re.sub(r"\s+", " ", body_text.strip()).lower()
            for entry in recent_entries:
                parts = entry.split("\n\n", 1)
                body = parts[1].strip() if len(parts) > 1 else parts[0].strip()
                if re.sub(r"\s+", " ", body).lower() == normalized_new:
                    return False

            existing_nums = re.findall(r"^###\s+(\d+)\.", content, flags=re.M)
            next_num = max(map(int, existing_nums)) + 1 if existing_nums else 1
            date_str = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
            block = f"### {next_num}. {date_str}\n\n{body_text.strip()}\n\n---\n\n"

            with open(path, "a", encoding="utf-8") as f:
                f.write(block)
            return True
        except Exception:
            return False

    def _save_expert_answer(self, question: str, answer: str) -> bool:
        """
        Save expert Q&A to docs/EXPERT_ANSWERS.md with timestamp and sequential numbering.
        """
        try:
            docs_dir = os.path.join(os.getcwd(), "docs")
            os.makedirs(docs_dir, exist_ok=True)
            path = os.path.join(docs_dir, "EXPERT_ANSWERS.md")
            # Count existing questions
            if os.path.exists(path):
                with open(path, "r", encoding="utf-8") as f:
                    content = f.read()
                # Count lines starting with '#### Question'
                import re
                matches = re.findall(r"#### Question (\d+)", content)
                next_num = int(matches[-1]) + 1 if matches else 1
            else:
                next_num = 1
            date_str = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
            block = (
                f"#### Question {next_num}\n"
                f"**Asked:** {date_str}\n"
                f"**Question:** {question}\n\n"
                f"**Answer:**\n{answer}\n\n---\n\n"
            )
            with open(path, "a", encoding="utf-8") as f:
                f.write(block)
            return True
        except Exception:
            return False