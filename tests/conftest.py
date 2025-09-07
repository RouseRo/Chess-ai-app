import sys
import os
import pytest

# Add the project root directory to the Python path
# This allows tests to import modules from the 'src' directory
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

@pytest.fixture
def app_instance():
    """Creates a basic instance of ChessApp for testing its methods."""
    # We import here to ensure sys.path is modified first
    from src.main import ChessApp
    return ChessApp()