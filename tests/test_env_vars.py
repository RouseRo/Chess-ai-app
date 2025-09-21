import os
import pytest
import json
from src.stockfish_utils import load_stockfish_config

def test_windows_env_vars():
    # Windows-specific variables
    print("USERPROFILE:", os.environ.get('USERPROFILE'))
    assert os.environ.get('USERPROFILE'), "USERPROFILE not set"
    print("APPDATA:", os.environ.get('APPDATA'))
    assert os.environ.get('APPDATA'), "APPDATA not set"
    print("LOCALAPPDATA:", os.environ.get('LOCALAPPDATA'))
    assert os.environ.get('LOCALAPPDATA'), "LOCALAPPDATA not set"
    print("TEMP:", os.environ.get('TEMP'))
    assert os.environ.get('TEMP'), "TEMP not set"
    print("TMP:", os.environ.get('TMP'))
    assert os.environ.get('TMP'), "TMP not set"
    print("COMPUTERNAME:", os.environ.get('COMPUTERNAME'))
    assert os.environ.get('COMPUTERNAME'), "COMPUTERNAME not set"
    print("USERNAME:", os.environ.get('USERNAME'))
    assert os.environ.get('USERNAME'), "USERNAME not set"
    print("USERDOMAIN:", os.environ.get('USERDOMAIN'))
    assert os.environ.get('USERDOMAIN'), "USERDOMAIN not set"
    print("OS:", os.environ.get('OS'))
    assert os.environ.get('OS'), "OS not set"
    print("COMSPEC:", os.environ.get('COMSPEC'))
    assert os.environ.get('COMSPEC'), "COMSPEC not set"
    print("SYSTEMROOT:", os.environ.get('SYSTEMROOT'))
    assert os.environ.get('SYSTEMROOT'), "SYSTEMROOT not set"
    print("WINDIR:", os.environ.get('WINDIR'))
    assert os.environ.get('WINDIR'), "WINDIR not set"
    print("HOMEDRIVE:", os.environ.get('HOMEDRIVE'))
    assert os.environ.get('HOMEDRIVE'), "HOMEDRIVE not set"
    print("HOMEPATH:", os.environ.get('HOMEPATH'))
    assert os.environ.get('HOMEPATH'), "HOMEPATH not set"
    print("STOCKFISH_EXECUTABLE:", os.environ.get('STOCKFISH_EXECUTABLE'))
    # No assert for STOCKFISH_EXECUTABLE, as it may not always be set

def test_path_variables():
    # System paths
    path = os.environ.get('PATH')
    print("PATH:", path)
    assert path and 'Windows' in path, "PATH does not contain 'Windows'"
    assert path and 'System32' in path, "PATH does not contain 'System32'"
    
    # Python-specific
    python_path = os.environ.get('PYTHONPATH')  # May be None
    print("PYTHONPATH:", python_path)
    
    # Common program paths
    print("PROGRAMFILES:", os.environ.get('PROGRAMFILES'))
    assert os.environ.get('PROGRAMFILES'), "PROGRAMFILES not set"
    print("PROGRAMFILES(X86):", os.environ.get('PROGRAMFILES(X86)'))
    assert os.environ.get('PROGRAMFILES(X86)'), "PROGRAMFILES(X86) not set"
    print("PROGRAMDATA:", os.environ.get('PROGRAMDATA'))
    assert os.environ.get('PROGRAMDATA'), "PROGRAMDATA not set"

def test_pytest_env_vars():
    # These may not all be set, but we can check if they exist without raising
    print("PYTEST_CURRENT_TEST:", os.environ.get('PYTEST_CURRENT_TEST'))
    _ = os.environ.get('PYTEST_CURRENT_TEST')
    print("PYTEST_ADDOPTS:", os.environ.get('PYTEST_ADDOPTS'))
    _ = os.environ.get('PYTEST_ADDOPTS')
    print("PYTEST_PLUGINS:", os.environ.get('PYTEST_PLUGINS'))
    _ = os.environ.get('PYTEST_PLUGINS')
    print("PYTEST_DISABLE_PLUGIN_AUTOLOAD:", os.environ.get('PYTEST_DISABLE_PLUGIN_AUTOLOAD'))
    _ = os.environ.get('PYTEST_DISABLE_PLUGIN_AUTOLOAD')
    print("PYTEST_DEBUG:", os.environ.get('PYTEST_DEBUG'))
    _ = os.environ.get('PYTEST_DEBUG')
    print("COVERAGE_FILE:", os.environ.get('COVERAGE_FILE'))
    _ = os.environ.get('COVERAGE_FILE')
    print("COVERAGE_CORE:", os.environ.get('COVERAGE_CORE'))
    _ = os.environ.get('COVERAGE_CORE')
    print("PYTEST_TERMINAL_WIDTH:", os.environ.get('PYTEST_TERMINAL_WIDTH'))
    _ = os.environ.get('PYTEST_TERMINAL_WIDTH')
    print("NO_COLOR:", os.environ.get('NO_COLOR'))
    _ = os.environ.get('NO_COLOR')
    print("FORCE_COLOR:", os.environ.get('FORCE_COLOR'))
    _ = os.environ.get('FORCE_COLOR')

def test_stockfish_env_var_matches_config():
    """
    Verify that STOCKFISH_EXECUTABLE env var is set to the value in config.json after calling load_stockfish_config.
    """
    stockfish_path, _ = load_stockfish_config()
    with open("src/config.json", "r") as f:
        config = json.load(f)
    config_exe = config.get("stockfish_executable")
    if config_exe:
        assert os.environ.get("STOCKFISH_EXECUTABLE") == config_exe, (
            f"STOCKFISH_EXECUTABLE env var should match config value: {config_exe}"
        )
        assert stockfish_path == config_exe or stockfish_path == os.environ.get("STOCKFISH_EXECUTABLE")