import pytest
from src.player_factory import PlayerFactory
from src.human_player import HumanPlayer
from src.ai_player import AIPlayer


def test_create_human_player(mocker):
    """Tests creating a human player, mocking the UI prompt."""
    mock_ui = mocker.MagicMock()
    mocker.patch.object(mock_ui, 'get_human_player_name', return_value="Robert")

    factory = PlayerFactory(ui=mock_ui, ai_models={}, stockfish_configs={}, stockfish_path="")
    player = factory.create_player('hu', color_label="White")

    assert isinstance(player, HumanPlayer)
    assert "Robert" in player.name
    mock_ui.get_human_player_name.assert_called_once_with("White")


def test_create_ai_player(mocker):
    """Tests creating an AI player from config."""
    mock_ui = mocker.MagicMock()
    ai_models_config = {"m1": "openai/gpt-4o"}

    mocker.patch("src.ai_player.openai.OpenAI", autospec=True)

    factory = PlayerFactory(ui=mock_ui, ai_models=ai_models_config, stockfish_configs={}, stockfish_path="")
    player = factory.create_player('m1')

    assert player is not None
    assert isinstance(player, AIPlayer)


def test_create_stockfish_player(mocker):
    """Tests creating a Stockfish player from config."""
    stockfish_path = "C:\\stockfish\\stockfish-windows-x86-64-avx2.exe"
    mock_ui = mocker.MagicMock()
    stockfish_configs = {
        "s1": {
            "name": "Quick, Casual",
            "parameters": {"Skill Level": 5, "UCI_LimitStrength": "false"}
        }
    }

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

    mocker.patch(
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


def test_create_player_invalid_type(mocker):
    """Tests that creating a player with an invalid type raises an error."""
    mock_ui = mocker.MagicMock()
    factory = PlayerFactory(ui=mock_ui, ai_models={}, stockfish_configs={}, stockfish_path="")

    with pytest.raises((KeyError, ValueError)):
        factory.create_player('invalid_type')