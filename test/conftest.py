"""Pytest configuration and fixtures for WoW Stat Tracker tests."""

import json

import pytest


@pytest.fixture
def temp_config_dir(tmp_path):
    """Create a temporary config directory for testing."""
    config_dir = tmp_path / ".config" / "wowstat"
    config_dir.mkdir(parents=True)
    return config_dir


@pytest.fixture
def sample_characters():
    """Sample character data for testing."""
    return [
        {
            "realm": "TestRealm",
            "name": "TestChar1",
            "guild": "TestGuild",
            "item_level": 480.5,
            "heroic_items": 5,
            "champion_items": 3,
            "veteran_items": 2,
            "adventure_items": 1,
            "old_items": 0,
            "vault_visited": True,
            "delves": 4,
            "gundarz": False,
            "quests": True,
            "timewalk": 0,
            "notes": "Main character",
        },
        {
            "realm": "TestRealm",
            "name": "TestChar2",
            "guild": "",
            "item_level": 450.0,
            "heroic_items": 0,
            "champion_items": 1,
            "veteran_items": 5,
            "adventure_items": 3,
            "old_items": 2,
            "vault_visited": False,
            "delves": 0,
            "gundarz": False,
            "quests": False,
            "timewalk": 5,
            "notes": "",
        },
    ]


@pytest.fixture
def sample_data_file(temp_config_dir, sample_characters):
    """Create a sample data file with test characters."""
    data_file = temp_config_dir / "wowstat_data.json"
    with open(data_file, "w") as f:
        json.dump(sample_characters, f)
    return data_file


@pytest.fixture
def sample_config():
    """Sample configuration data for testing."""
    return {
        "window": {
            "width": 1200,
            "height": 600,
            "x": 100,
            "y": 100,
            "maximized": False,
        },
        "columns": {"0": 80, "1": 100, "2": 150},
        "sort": {"column_id": 0, "order": 0},
        "theme": "auto",
    }


@pytest.fixture
def sample_config_file(temp_config_dir, sample_config):
    """Create a sample config file."""
    config_file = temp_config_dir / "wowstat_config.json"
    with open(config_file, "w") as f:
        json.dump(sample_config, f)
    return config_file


@pytest.fixture
def sample_lua_content():
    """Sample Altoholic Lua SavedVariables content."""
    return """
DataStore_CharactersDB = {
    ["global"] = {
        ["Characters"] = {
            ["Default.TestRealm.TestChar"] = {
                ["averageItemLvl"] = 485.5,
                ["guildName"] = "Test Guild",
            },
        },
    },
}
"""


@pytest.fixture
def sample_lua_file(tmp_path, sample_lua_content):
    """Create a sample Lua file."""
    lua_file = tmp_path / "DataStore_Characters.lua"
    with open(lua_file, "w") as f:
        f.write(sample_lua_content)
    return lua_file
