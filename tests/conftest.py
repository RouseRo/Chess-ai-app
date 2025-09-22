import sys
import os
import pytest

# Add the project root directory to the Python path.
# This allows tests to import modules from the 'src' directory, even when running from the 'tests' folder.
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# Set the Stockfish executable path for all tests.
# This ensures that any code relying on the STOCKFISH_EXECUTABLE environment variable uses the correct Windows path.
os.environ["STOCKFISH_EXECUTABLE"] = "C:\\stockfish\\stockfish-windows-x86-64-avx2.exe"

@pytest.fixture
def app_instance():
    """
    Creates a basic instance of ChessApp for testing its methods.
    The import is done here to ensure sys.path is modified first.
    """
    from src.main import ChessApp
    return ChessApp()