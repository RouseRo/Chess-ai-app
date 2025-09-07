from src.player_factory import PlayerFactory
from src.human_player import HumanPlayer
from src.ai_player import AIPlayer

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
    assert "Robert" in player.model_name
    # Assert that our mock was called correctly
    mock_ui.get_human_player_name.assert_called_once_with("White")

def test_create_ai_player(mocker):
    """Tests creating an AI player from config."""
    mock_ui = mocker.MagicMock()
    ai_models_config = {"m1": "openai/gpt-4o"}
    
    factory = PlayerFactory(ui=mock_ui, ai_models=ai_models_config, stockfish_configs={}, stockfish_path="")
    
    player = factory.create_player('m1')
    
    assert isinstance(player, AIPlayer)
    assert player.model_name == "openai/gpt-4o"