import pytest
from src.player_factory import PlayerFactory
from src.human_player import HumanPlayer
from src.ai_player import AIPlayer

# @pytest.mark.skip(reason="Skipping until fixed")
def test_create_human_player(mocker):
    """Tests creating a human player, mocking the UI prompt."""
    # 1. Setup the mock
    mock_ui = mocker.MagicMock()
    mocker.patch.object(mock_ui, 'get_human_player_name', return_value="Robert")

    # 2. Create the factory with the mock UI and dummy configs
    factory = PlayerFactory(ui=mock_ui, ai_models={}, stockfish_configs={}, stockfish_path="")
    
    # 3. Call the method to be tested
    player = factory.create_player('hu', color_label="White")
    
    # 4. Assert the results
    assert isinstance(player, HumanPlayer)
    assert "Robert" in player.name  # Updated to use the correct attribute
    # Assert that our mock was called correctly
    mock_ui.get_human_player_name.assert_called_once_with("White")

def test_create_ai_player(mocker):
    """Tests creating an AI player from config."""
    mock_ui = mocker.MagicMock()
    ai_models_config = {"m1": "openai/gpt-4o"}

    # Mock OpenAI client to avoid real API calls
    mocker.patch("src.ai_player.openai.OpenAI", autospec=True)

    factory = PlayerFactory(ui=mock_ui, ai_models=ai_models_config, stockfish_configs={}, stockfish_path="")
    player = factory.create_player('m1')
    assert player is not None

def test_create_stockfish_player(mocker):
    """Tests creating a Stockfish player from config."""
    import json
    # Load the Stockfish path from config_pytest.json
    with open("src/config_pytest.json", "r") as f:
        config = json.load(f)
    stockfish_path = config.get("stockfish_executable", "")

    mock_ui = mocker.MagicMock()
    stockfish_configs = {
        "s1": {
            "name": "Quick, Casual",
            "parameters": {"Skill Level": 5, "UCI_LimitStrength": "false"}
        }
    }
    # Patch StockfishPlayer to avoid launching the real engine
    mock_stockfish_player = mocker.patch("src.player_factory.StockfishPlayer", autospec=True)
    factory = PlayerFactory(
        ui=mock_ui,
        ai_models={},
        stockfish_configs=stockfish_configs,
        stockfish_path=stockfish_path
    )
    player = factory.create_player('s1')
    assert player is not None
    mock_stockfish_player.assert_called_once_with(
        stockfish_path,
        parameters=stockfish_configs["s1"]["parameters"]
    )

def test_create_stockfish_player_invalid_path(mocker):
    """Tests creating a Stockfish player with an invalid path and expects an error."""
    mock_ui = mocker.MagicMock()
    stockfish_configs = {
        "s1": {
            "name": "Quick, Casual",
            "parameters": {"Skill Level": 5, "UCI_LimitStrength": "false"}
        }
    }
    # Patch StockfishPlayer to raise FileNotFoundError when called with an invalid path
    mock_stockfish_player = mocker.patch(
        "src.player_factory.StockfishPlayer",
        side_effect=FileNotFoundError("Stockfish binary not found")
    )
    factory = PlayerFactory(
        ui=mock_ui,
        ai_models={},
        stockfish_configs=stockfish_configs,
        stockfish_path="Z:\\invalid\\path\\stockfish.exe"
    )
    with pytest.raises(FileNotFoundError, match="Stockfish binary not found"):
        factory.create_player('s1')