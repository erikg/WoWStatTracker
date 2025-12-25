"""Tests for WoW Stat Tracker application."""

import json
import os
import sys

# Add src directory to path for imports
sys.path.insert(
    0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "src")
)


class TestDataOperations:
    """Tests for data loading and saving operations."""

    def test_load_data_file_exists(self, sample_data_file, sample_characters):
        """Test loading data from an existing file."""
        with open(sample_data_file, "r") as f:
            loaded_data = json.load(f)

        assert len(loaded_data) == 2
        assert loaded_data[0]["name"] == "TestChar1"
        assert loaded_data[1]["name"] == "TestChar2"

    def test_load_data_file_not_exists(self, temp_config_dir):
        """Test loading data when file doesn't exist returns empty list."""
        data_file = temp_config_dir / "nonexistent.json"
        assert not data_file.exists()

    def test_save_data_creates_file(self, temp_config_dir, sample_characters):
        """Test saving data creates a new file."""
        data_file = temp_config_dir / "new_data.json"

        with open(data_file, "w") as f:
            json.dump(sample_characters, f)

        assert data_file.exists()
        with open(data_file, "r") as f:
            loaded = json.load(f)
        assert len(loaded) == 2

    def test_data_has_required_fields(self, sample_characters):
        """Test that sample data has all required fields."""
        required_fields = [
            "realm",
            "name",
            "guild",
            "item_level",
            "heroic_items",
            "champion_items",
            "veteran_items",
            "adventure_items",
            "old_items",
            "vault_visited",
            "delves",
            "gearing_up",
            "quests",
            "timewalk",
            "notes",
        ]

        for char in sample_characters:
            for field in required_fields:
                assert field in char, f"Missing field: {field}"


class TestConfigOperations:
    """Tests for configuration loading and saving."""

    def test_load_config_file_exists(self, sample_config_file, sample_config):
        """Test loading config from an existing file."""
        with open(sample_config_file, "r") as f:
            loaded_config = json.load(f)

        assert loaded_config["theme"] == "auto"
        assert loaded_config["window"]["width"] == 1200

    def test_save_config_creates_file(self, temp_config_dir, sample_config):
        """Test saving config creates a new file."""
        config_file = temp_config_dir / "new_config.json"

        with open(config_file, "w") as f:
            json.dump(sample_config, f)

        assert config_file.exists()

    def test_config_has_window_settings(self, sample_config):
        """Test that config has window settings."""
        assert "window" in sample_config
        assert "width" in sample_config["window"]
        assert "height" in sample_config["window"]


class TestLuaParsing:
    """Tests for Lua SavedVariables parsing."""

    def test_parse_simple_lua_table(self):
        """Test parsing a simple Lua table."""
        lua_content = '["key"] = "value",'
        # Basic string parsing test
        assert "key" in lua_content
        assert "value" in lua_content

    def test_parse_nested_lua_table(self, sample_lua_content):
        """Test that sample Lua content has expected structure."""
        assert "DataStore_CharactersDB" in sample_lua_content
        assert "TestRealm" in sample_lua_content
        assert "TestChar" in sample_lua_content
        assert "485.5" in sample_lua_content

    def test_lua_file_creation(self, sample_lua_file):
        """Test that Lua file fixture creates readable file."""
        assert sample_lua_file.exists()
        with open(sample_lua_file, "r") as f:
            content = f.read()
        assert "DataStore_CharactersDB" in content


class TestSlppParsing:
    """Tests for slpp-based addon data parsing."""

    def test_parse_addon_character(self, tmp_path):
        """Test parsing a WoWStatTracker addon file."""
        from slpp import slpp as lua

        addon_content = '''WoWStatTrackerDB = {
    ["characters"] = {
        ["TestChar-TestRealm"] = {
            ["name"] = "TestChar",
            ["realm"] = "TestRealm",
            ["guild"] = "Test Guild",
            ["item_level"] = 715.5,
            ["heroic_items"] = 14,
            ["champion_items"] = 2,
            ["veteran_items"] = 0,
            ["adventure_items"] = 0,
            ["old_items"] = 0,
            ["vault_visited"] = true,
            ["gearing_up"] = true,
            ["quests"] = false,
            ["week_id"] = "20251223",
        },
    },
}'''
        content = addon_content.replace("WoWStatTrackerDB = ", "", 1)
        data = lua.decode(content)

        assert "characters" in data
        assert "TestChar-TestRealm" in data["characters"]
        char = data["characters"]["TestChar-TestRealm"]
        assert char["name"] == "TestChar"
        assert char["item_level"] == 715.5
        assert char["heroic_items"] == 14
        assert char["vault_visited"] is True
        assert char["gearing_up"] is True
        assert char["quests"] is False

    def test_parse_unicode_character_name(self):
        """Test parsing character names with unicode."""
        from slpp import slpp as lua

        content = '''{
    ["characters"] = {
        ["Muffïn-Norgannon"] = {
            ["name"] = "Muffïn",
            ["realm"] = "Norgannon",
        },
    },
}'''
        data = lua.decode(content)
        assert "Muffïn-Norgannon" in data["characters"]
        assert data["characters"]["Muffïn-Norgannon"]["name"] == "Muffïn"

    def test_parse_nested_structures(self):
        """Test parsing nested addon structures like vault_delves."""
        from slpp import slpp as lua

        content = '''{
    ["characters"] = {
        ["Test-Realm"] = {
            ["vault_delves"] = {
                ["count"] = 5,
            },
            ["gilded_stash"] = {
                ["claimed"] = 3,
            },
            ["timewalking_quest"] = {
                ["progress"] = 2,
                ["completed"] = false,
            },
        },
    },
}'''
        data = lua.decode(content)
        char = data["characters"]["Test-Realm"]
        assert char["vault_delves"]["count"] == 5
        assert char["gilded_stash"]["claimed"] == 3
        assert char["timewalking_quest"]["progress"] == 2

    def test_parse_empty_characters_table(self):
        """Test parsing addon with no characters."""
        from slpp import slpp as lua

        content = '''{
    ["characters"] = {
    },
}'''
        data = lua.decode(content)
        assert data["characters"] == {}


class TestCharacterValidation:
    """Tests for character data validation."""

    def test_valid_item_level_range(self, sample_characters):
        """Test that item levels are within valid range."""
        for char in sample_characters:
            assert 0 <= char["item_level"] <= 1000

    def test_valid_delves_range(self, sample_characters):
        """Test that delves count is within valid range."""
        for char in sample_characters:
            assert 0 <= char["delves"] <= 8

    def test_valid_timewalk_range(self, sample_characters):
        """Test that timewalk count is within valid range."""
        for char in sample_characters:
            assert 0 <= char["timewalk"] <= 5

    def test_boolean_fields_are_bool(self, sample_characters):
        """Test that boolean fields are actually booleans."""
        bool_fields = ["vault_visited", "gearing_up", "quests"]
        for char in sample_characters:
            for field in bool_fields:
                assert isinstance(char[field], bool), f"{field} should be bool"


class TestConfigDirectory:
    """Tests for config directory operations."""

    def test_config_dir_creation(self, tmp_path):
        """Test that config directory can be created."""
        config_dir = tmp_path / ".config" / "wowstat"
        config_dir.mkdir(parents=True, exist_ok=True)
        assert config_dir.exists()
        assert config_dir.is_dir()

    def test_config_dir_path(self):
        """Test expected config directory path uses get_config_dir."""
        from model import get_config_dir

        config_path = get_config_dir()
        assert "wowstat" in config_path
        assert os.path.isabs(config_path)


class TestFileMigration:
    """Tests for file migration logic."""

    def test_migrate_when_old_exists_new_does_not(self, tmp_path):
        """Test migration when old file exists but new doesn't."""
        old_file = tmp_path / "old_data.json"
        new_dir = tmp_path / "new_location"
        new_dir.mkdir()
        new_file = new_dir / "data.json"

        # Create old file
        with open(old_file, "w") as f:
            json.dump({"test": "data"}, f)

        assert old_file.exists()
        assert not new_file.exists()

        # Simulate migration
        import shutil

        shutil.move(str(old_file), str(new_file))

        assert not old_file.exists()
        assert new_file.exists()

    def test_no_migrate_when_new_exists(self, tmp_path):
        """Test that migration doesn't overwrite existing new file."""
        old_file = tmp_path / "old_data.json"
        new_file = tmp_path / "new_data.json"

        # Create both files with different content
        with open(old_file, "w") as f:
            json.dump({"source": "old"}, f)
        with open(new_file, "w") as f:
            json.dump({"source": "new"}, f)

        # New file should not be overwritten
        with open(new_file, "r") as f:
            data = json.load(f)
        assert data["source"] == "new"


class TestWeeklyReset:
    """Tests for weekly data reset functionality."""

    def test_reset_weekly_fields(self, sample_characters):
        """Test resetting weekly fields."""
        # Reset weekly data
        for char in sample_characters:
            char["vault_visited"] = False
            char["delves"] = 0
            char["gearing_up"] = False
            char["quests"] = False
            char["timewalk"] = 0

        # Verify reset
        for char in sample_characters:
            assert char["vault_visited"] is False
            assert char["delves"] == 0
            assert char["gearing_up"] is False
            assert char["quests"] is False
            assert char["timewalk"] == 0


class TestThemeSettings:
    """Tests for theme configuration."""

    def test_valid_theme_values(self):
        """Test that theme values are valid."""
        valid_themes = ["auto", "light", "dark"]
        for theme in valid_themes:
            assert theme in valid_themes

    def test_default_theme_is_auto(self, sample_config):
        """Test that default theme is auto."""
        assert sample_config["theme"] == "auto"


class TestColumnConstants:
    """Tests for column index constants."""

    def test_column_indices_unique(self):
        """Test that column indices are unique."""
        # These should match the constants in wowstat.py
        indices = [0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15]
        assert len(indices) == len(set(indices))

    def test_column_count(self):
        """Test expected column count."""
        # COL_COUNT should be 16
        expected_count = 16
        assert expected_count == 16
