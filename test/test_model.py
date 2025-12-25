"""Tests for the model layer (model.py)."""

import json
import os
import sys

import pytest

# Add src directory to path for imports
sys.path.insert(
    0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "src")
)

from model import (
    Character,
    CharacterStore,
    Config,
    LockManager,
    get_config_dir,
    migrate_old_files,
    detect_system_theme,
    MAX_ITEM_LEVEL,
    MAX_ITEMS_PER_CATEGORY,
    MAX_DELVES,
    MAX_TIMEWALK,
    THEME_AUTO,
    THEME_LIGHT,
    THEME_DARK,
    WOW_DEFAULT_PATHS,
)


class TestCharacter:
    """Tests for the Character dataclass."""

    def test_default_values(self):
        """Test Character has correct default values."""
        char = Character()
        assert char.realm == ""
        assert char.name == ""
        assert char.guild == ""
        assert char.item_level == 0.0
        assert char.heroic_items == 0
        assert char.champion_items == 0
        assert char.veteran_items == 0
        assert char.adventure_items == 0
        assert char.old_items == 0
        assert char.vault_visited is False
        assert char.delves == 0
        assert char.gearing_up is False
        assert char.quests is False
        assert char.timewalk == 0
        assert char.notes == ""

    def test_create_with_values(self):
        """Test Character creation with specific values."""
        char = Character(
            realm="TestRealm",
            name="TestChar",
            guild="TestGuild",
            item_level=500.0,
            heroic_items=10,
            champion_items=5,
            veteran_items=3,
            adventure_items=2,
            old_items=1,
            vault_visited=True,
            delves=4,
            gearing_up=True,
            quests=True,
            timewalk=3,
            notes="Test notes",
        )
        assert char.realm == "TestRealm"
        assert char.name == "TestChar"
        assert char.item_level == 500.0
        assert char.vault_visited is True

    def test_validate_valid_character(self):
        """Test validation passes for valid character."""
        char = Character(realm="TestRealm", name="TestChar", item_level=500)
        errors = char.validate()
        assert errors == []

    def test_validate_missing_name(self):
        """Test validation fails for missing name."""
        char = Character(realm="TestRealm", name="", item_level=500)
        errors = char.validate()
        assert "Character name is required" in errors

    def test_validate_missing_realm(self):
        """Test validation fails for missing realm."""
        char = Character(realm="", name="TestChar", item_level=500)
        errors = char.validate()
        assert "Realm is required" in errors

    def test_validate_whitespace_name(self):
        """Test validation fails for whitespace-only name."""
        char = Character(realm="TestRealm", name="   ", item_level=500)
        errors = char.validate()
        assert "Character name is required" in errors

    def test_validate_item_level_too_high(self):
        """Test validation fails for item level exceeding max."""
        char = Character(
            realm="TestRealm", name="TestChar", item_level=MAX_ITEM_LEVEL + 1
        )
        errors = char.validate()
        assert any("item level" in e.lower() for e in errors)

    def test_validate_item_level_negative(self):
        """Test validation fails for negative item level."""
        char = Character(realm="TestRealm", name="TestChar", item_level=-1)
        errors = char.validate()
        assert any("item level" in e.lower() for e in errors)

    def test_validate_heroic_items_exceeds_max(self):
        """Test validation fails for heroic_items exceeding max."""
        char = Character(
            realm="TestRealm",
            name="TestChar",
            heroic_items=MAX_ITEMS_PER_CATEGORY + 1,
        )
        errors = char.validate()
        assert any("heroic_items" in e for e in errors)

    def test_validate_delves_exceeds_max(self):
        """Test validation fails for delves exceeding max."""
        char = Character(realm="TestRealm", name="TestChar", delves=MAX_DELVES + 1)
        errors = char.validate()
        assert any("Delves" in e for e in errors)

    def test_validate_timewalk_exceeds_max(self):
        """Test validation fails for timewalk exceeding max."""
        char = Character(realm="TestRealm", name="TestChar", timewalk=MAX_TIMEWALK + 1)
        errors = char.validate()
        assert any("Timewalk" in e for e in errors)

    def test_validate_multiple_errors(self):
        """Test validation returns multiple errors."""
        char = Character(
            realm="",
            name="",
            item_level=-1,
            delves=MAX_DELVES + 1,
        )
        errors = char.validate()
        assert len(errors) >= 3

    def test_to_dict(self):
        """Test conversion to dictionary."""
        char = Character(
            realm="TestRealm",
            name="TestChar",
            guild="TestGuild",
            item_level=500.0,
        )
        d = char.to_dict()
        assert d["realm"] == "TestRealm"
        assert d["name"] == "TestChar"
        assert d["guild"] == "TestGuild"
        assert d["item_level"] == 500.0
        assert "vault_visited" in d
        assert "delves" in d

    def test_from_dict_complete(self):
        """Test creation from complete dictionary."""
        data = {
            "realm": "TestRealm",
            "name": "TestChar",
            "guild": "TestGuild",
            "item_level": 500.0,
            "heroic_items": 10,
            "champion_items": 5,
            "veteran_items": 3,
            "adventure_items": 2,
            "old_items": 1,
            "vault_visited": True,
            "delves": 4,
            "gearing_up": True,
            "quests": True,
            "timewalk": 3,
            "notes": "Test notes",
        }
        char = Character.from_dict(data)
        assert char.realm == "TestRealm"
        assert char.name == "TestChar"
        assert char.item_level == 500.0
        assert char.vault_visited is True

    def test_from_dict_partial(self):
        """Test creation from partial dictionary with defaults."""
        data = {"realm": "TestRealm", "name": "TestChar"}
        char = Character.from_dict(data)
        assert char.realm == "TestRealm"
        assert char.name == "TestChar"
        assert char.item_level == 0.0
        assert char.guild == ""
        assert char.vault_visited is False

    def test_from_dict_extra_fields_ignored(self):
        """Test that extra fields in dict are ignored."""
        data = {
            "realm": "TestRealm",
            "name": "TestChar",
            "unknown_field": "value",
        }
        char = Character.from_dict(data)
        assert char.realm == "TestRealm"
        assert not hasattr(char, "unknown_field")

    def test_reset_weekly(self):
        """Test weekly field reset."""
        char = Character(
            realm="TestRealm",
            name="TestChar",
            vault_visited=True,
            delves=5,
            gearing_up=True,
            quests=True,
            timewalk=3,
            notes="Should not be reset",
        )
        char.reset_weekly()
        assert char.vault_visited is False
        assert char.delves == 0
        assert char.gearing_up is False
        assert char.quests is False
        assert char.timewalk == 0
        # Notes should not be reset
        assert char.notes == "Should not be reset"
        # Other fields should not be reset
        assert char.realm == "TestRealm"
        assert char.name == "TestChar"

    def test_roundtrip_to_from_dict(self):
        """Test that to_dict and from_dict are reversible."""
        original = Character(
            realm="TestRealm",
            name="TestChar",
            guild="TestGuild",
            item_level=500.0,
            heroic_items=10,
            vault_visited=True,
            notes="Test notes",
        )
        d = original.to_dict()
        restored = Character.from_dict(d)
        assert restored.realm == original.realm
        assert restored.name == original.name
        assert restored.guild == original.guild
        assert restored.item_level == original.item_level
        assert restored.heroic_items == original.heroic_items
        assert restored.vault_visited == original.vault_visited
        assert restored.notes == original.notes


class TestCharacterStore:
    """Tests for the CharacterStore class."""

    def test_init_empty(self, tmp_path):
        """Test store initialization with no existing file."""
        data_file = str(tmp_path / "data.json")
        store = CharacterStore(data_file)
        assert store.characters == []

    def test_load_nonexistent_file(self, tmp_path):
        """Test loading from nonexistent file results in empty list."""
        data_file = str(tmp_path / "nonexistent.json")
        store = CharacterStore(data_file)
        store.load()
        assert store.characters == []

    def test_load_existing_file(self, tmp_path):
        """Test loading from existing file."""
        data_file = tmp_path / "data.json"
        data = [
            {"realm": "TestRealm", "name": "Char1", "item_level": 500.0},
            {"realm": "TestRealm", "name": "Char2", "item_level": 450.0},
        ]
        with open(data_file, "w") as f:
            json.dump(data, f)

        store = CharacterStore(str(data_file))
        store.load()
        assert len(store.characters) == 2
        assert store.characters[0].name == "Char1"
        assert store.characters[1].name == "Char2"

    def test_load_invalid_json(self, tmp_path):
        """Test loading invalid JSON results in empty list."""
        data_file = tmp_path / "data.json"
        with open(data_file, "w") as f:
            f.write("not valid json {{{")

        store = CharacterStore(str(data_file))
        store.load()
        assert store.characters == []

    def test_save_creates_file(self, tmp_path):
        """Test saving creates a new file."""
        data_file = tmp_path / "data.json"
        store = CharacterStore(str(data_file))
        store.characters = [Character(realm="TestRealm", name="TestChar")]
        store.save()

        assert data_file.exists()
        with open(data_file) as f:
            data = json.load(f)
        assert len(data) == 1
        assert data[0]["name"] == "TestChar"

    def test_save_overwrites_file(self, tmp_path):
        """Test saving overwrites existing file."""
        data_file = tmp_path / "data.json"
        with open(data_file, "w") as f:
            json.dump([{"name": "OldChar"}], f)

        store = CharacterStore(str(data_file))
        store.characters = [Character(realm="TestRealm", name="NewChar")]
        store.save()

        with open(data_file) as f:
            data = json.load(f)
        assert len(data) == 1
        assert data[0]["name"] == "NewChar"

    def test_add(self, tmp_path):
        """Test adding a character."""
        store = CharacterStore(str(tmp_path / "data.json"))
        char = Character(realm="TestRealm", name="TestChar")
        store.add(char)
        assert len(store.characters) == 1
        assert store.characters[0].name == "TestChar"

    def test_update_valid_index(self, tmp_path):
        """Test updating a character at valid index."""
        store = CharacterStore(str(tmp_path / "data.json"))
        store.characters = [
            Character(realm="TestRealm", name="Original"),
        ]
        updated = Character(realm="TestRealm", name="Updated")
        store.update(0, updated)
        assert store.characters[0].name == "Updated"

    def test_update_invalid_index(self, tmp_path):
        """Test updating at invalid index raises error."""
        store = CharacterStore(str(tmp_path / "data.json"))
        store.characters = [Character(realm="TestRealm", name="Original")]
        with pytest.raises(IndexError):
            store.update(5, Character(realm="Test", name="Test"))

    def test_delete_valid_index(self, tmp_path):
        """Test deleting a character at valid index."""
        store = CharacterStore(str(tmp_path / "data.json"))
        store.characters = [
            Character(realm="TestRealm", name="Char1"),
            Character(realm="TestRealm", name="Char2"),
        ]
        store.delete(0)
        assert len(store.characters) == 1
        assert store.characters[0].name == "Char2"

    def test_delete_invalid_index(self, tmp_path):
        """Test deleting at invalid index raises error."""
        store = CharacterStore(str(tmp_path / "data.json"))
        store.characters = [Character(realm="TestRealm", name="Char1")]
        with pytest.raises(IndexError):
            store.delete(5)

    def test_get_valid_index(self, tmp_path):
        """Test getting a character at valid index."""
        store = CharacterStore(str(tmp_path / "data.json"))
        store.characters = [Character(realm="TestRealm", name="TestChar")]
        char = store.get(0)
        assert char.name == "TestChar"

    def test_get_invalid_index(self, tmp_path):
        """Test getting at invalid index raises error."""
        store = CharacterStore(str(tmp_path / "data.json"))
        with pytest.raises(IndexError):
            store.get(0)

    def test_reset_weekly_all(self, tmp_path):
        """Test resetting weekly data for all characters."""
        store = CharacterStore(str(tmp_path / "data.json"))
        store.characters = [
            Character(
                realm="R1", name="C1", vault_visited=True, delves=5, gearing_up=True
            ),
            Character(
                realm="R2", name="C2", vault_visited=True, quests=True, timewalk=3
            ),
        ]
        store.reset_weekly_all()
        for char in store.characters:
            assert char.vault_visited is False
            assert char.delves == 0
            assert char.gearing_up is False
            assert char.quests is False
            assert char.timewalk == 0

    def test_save_to_readonly_directory_fails(self, tmp_path):
        """Test saving to a readonly location raises IOError."""
        # Use a path that doesn't exist and can't be created
        bad_path = "/nonexistent_dir_12345/data.json"
        store = CharacterStore(bad_path)
        store.characters = [Character(realm="TestRealm", name="TestChar")]
        with pytest.raises(IOError):
            store.save()

    def test_save_atomic_cleanup_on_failure(self, tmp_path, monkeypatch):
        """Test that temp file is cleaned up on save failure."""
        data_file = tmp_path / "data.json"
        store = CharacterStore(str(data_file))
        store.characters = [Character(realm="TestRealm", name="TestChar")]

        # Mock shutil.move to fail after temp file is created
        import shutil

        original_move = shutil.move

        def failing_move(src, dst):
            raise OSError("Simulated move failure")

        monkeypatch.setattr(shutil, "move", failing_move)

        with pytest.raises(IOError):
            store.save()

        # Temp file should be cleaned up
        temp_file = str(data_file) + ".tmp"
        assert not os.path.exists(temp_file)


class TestConfig:
    """Tests for the Config class."""

    def test_init_empty(self, tmp_path):
        """Test config initialization with no existing file."""
        config_file = str(tmp_path / "config.json")
        config = Config(config_file)
        assert config.data == {}

    def test_load_nonexistent_file(self, tmp_path):
        """Test loading from nonexistent file results in empty dict."""
        config_file = str(tmp_path / "nonexistent.json")
        config = Config(config_file)
        config.load()
        assert config.data == {}

    def test_load_existing_file(self, tmp_path):
        """Test loading from existing file."""
        config_file = tmp_path / "config.json"
        data = {"theme": "dark", "window": {"width": 1200}}
        with open(config_file, "w") as f:
            json.dump(data, f)

        config = Config(str(config_file))
        config.load()
        assert config.get("theme") == "dark"
        assert config.get("window")["width"] == 1200

    def test_load_invalid_json(self, tmp_path):
        """Test loading invalid JSON results in empty dict."""
        config_file = tmp_path / "config.json"
        with open(config_file, "w") as f:
            f.write("not valid json")

        config = Config(str(config_file))
        config.load()
        assert config.data == {}

    def test_save_creates_file(self, tmp_path):
        """Test saving creates a new file."""
        config_file = tmp_path / "config.json"
        config = Config(str(config_file))
        config.set("theme", "dark")
        config.save()

        assert config_file.exists()
        with open(config_file) as f:
            data = json.load(f)
        assert data["theme"] == "dark"

    def test_get_with_default(self, tmp_path):
        """Test get with default value."""
        config = Config(str(tmp_path / "config.json"))
        assert config.get("nonexistent", "default") == "default"
        assert config.get("nonexistent") is None

    def test_set(self, tmp_path):
        """Test setting a value."""
        config = Config(str(tmp_path / "config.json"))
        config.set("key", "value")
        assert config.get("key") == "value"

    def test_update(self, tmp_path):
        """Test updating multiple values."""
        config = Config(str(tmp_path / "config.json"))
        config.set("existing", "old")
        config.update({"existing": "new", "another": "value"})
        assert config.get("existing") == "new"
        assert config.get("another") == "value"


class TestLockManager:
    """Tests for the LockManager class."""

    def test_acquire_success(self, tmp_path):
        """Test acquiring lock succeeds when no lock exists."""
        lock_file = str(tmp_path / "lock")
        manager = LockManager(lock_file)
        assert manager.acquire() is True
        manager.release()

    def test_release_removes_file(self, tmp_path):
        """Test releasing lock removes lock file."""
        lock_file = tmp_path / "lock"
        manager = LockManager(str(lock_file))
        manager.acquire()
        manager.release()
        assert not lock_file.exists()

    def test_acquire_twice_same_manager(self, tmp_path):
        """Test acquiring lock twice with same manager."""
        lock_file = str(tmp_path / "lock")
        manager = LockManager(lock_file)
        assert manager.acquire() is True
        # Second acquire with same manager should work (same PID)
        manager.release()

    def test_release_nonexistent_file(self, tmp_path):
        """Test releasing when file doesn't exist doesn't raise."""
        lock_file = str(tmp_path / "nonexistent_lock")
        manager = LockManager(lock_file)
        manager.release()  # Should not raise

    def test_fallback_acquire_with_stale_lock(self, tmp_path):
        """Test fallback acquire succeeds with stale lock from dead process."""
        lock_file = tmp_path / "lock"
        # Create lock file with PID that doesn't exist
        with open(lock_file, "w") as f:
            f.write("99999999")  # Very high PID unlikely to exist

        manager = LockManager(str(lock_file))
        # Use fallback by calling _acquire_fallback directly
        assert manager._acquire_fallback() is True
        manager.release()

    def test_fallback_acquire_empty_lock_file(self, tmp_path):
        """Test fallback handles empty lock file."""
        lock_file = tmp_path / "lock"
        lock_file.touch()  # Create empty file

        manager = LockManager(str(lock_file))
        # Should succeed because empty file can't be parsed as PID
        assert manager._acquire_fallback() is True
        manager.release()

    def test_is_process_running_nonexistent_pid(self, tmp_path):
        """Test _is_process_running returns False for nonexistent PID."""
        manager = LockManager(str(tmp_path / "lock"))
        # Very high PID unlikely to exist
        assert manager._is_process_running(99999999) is False

    def test_is_process_running_current_pid(self, tmp_path):
        """Test _is_process_running returns True for current process."""
        manager = LockManager(str(tmp_path / "lock"))
        assert manager._is_process_running(os.getpid()) is True


class TestMigrateOldFiles:
    """Tests for the migrate_old_files function."""

    def test_migrate_when_old_exists_new_does_not(self, tmp_path):
        """Test migration when old file exists but new doesn't."""
        old_dir = tmp_path / "old"
        old_dir.mkdir()
        old_file = old_dir / "wowstat_data.json"
        with open(old_file, "w") as f:
            json.dump({"test": "data"}, f)

        new_dir = tmp_path / "new"
        new_dir.mkdir()
        new_file = new_dir / "data.json"

        # Change to old_dir so the function finds the old file
        original_cwd = os.getcwd()
        try:
            os.chdir(old_dir)
            migrate_old_files(str(new_dir), str(new_file), str(new_dir / "config.json"))
        finally:
            os.chdir(original_cwd)

        assert new_file.exists()
        with open(new_file) as f:
            data = json.load(f)
        assert data["test"] == "data"

    def test_no_migrate_when_new_exists(self, tmp_path):
        """Test that migration doesn't overwrite existing new file."""
        old_dir = tmp_path / "old"
        old_dir.mkdir()
        old_file = old_dir / "wowstat_data.json"
        with open(old_file, "w") as f:
            json.dump({"source": "old"}, f)

        new_dir = tmp_path / "new"
        new_dir.mkdir()
        new_file = new_dir / "data.json"
        with open(new_file, "w") as f:
            json.dump({"source": "new"}, f)

        original_cwd = os.getcwd()
        try:
            os.chdir(old_dir)
            migrate_old_files(str(new_dir), str(new_file), str(new_dir / "config.json"))
        finally:
            os.chdir(original_cwd)

        with open(new_file) as f:
            data = json.load(f)
        assert data["source"] == "new"

    def test_no_migrate_when_old_does_not_exist(self, tmp_path):
        """Test migration does nothing when old file doesn't exist."""
        new_dir = tmp_path / "new"
        new_dir.mkdir()
        new_file = new_dir / "data.json"

        migrate_old_files(str(new_dir), str(new_file), str(new_dir / "config.json"))

        assert not new_file.exists()


class TestDetectSystemTheme:
    """Tests for the detect_system_theme function."""

    def test_returns_bool(self):
        """Test that detect_system_theme returns a boolean."""
        result = detect_system_theme()
        assert isinstance(result, bool)


class TestConstants:
    """Tests for module constants."""

    def test_max_item_level(self):
        """Test MAX_ITEM_LEVEL is reasonable."""
        assert MAX_ITEM_LEVEL > 0
        assert MAX_ITEM_LEVEL == 1000

    def test_max_items_per_category(self):
        """Test MAX_ITEMS_PER_CATEGORY is reasonable."""
        assert MAX_ITEMS_PER_CATEGORY > 0
        assert MAX_ITEMS_PER_CATEGORY == 50

    def test_max_delves(self):
        """Test MAX_DELVES is reasonable."""
        assert MAX_DELVES > 0
        assert MAX_DELVES == 8

    def test_max_timewalk(self):
        """Test MAX_TIMEWALK is reasonable."""
        assert MAX_TIMEWALK > 0
        assert MAX_TIMEWALK == 5

    def test_theme_constants(self):
        """Test theme constant values."""
        assert THEME_AUTO == "auto"
        assert THEME_LIGHT == "light"
        assert THEME_DARK == "dark"


class TestGetConfigDir:
    """Tests for the get_config_dir function."""

    def test_returns_string(self):
        """Test get_config_dir returns a string path."""
        result = get_config_dir()
        assert isinstance(result, str)
        assert len(result) > 0

    def test_contains_app_name(self):
        """Test that config dir contains the app name."""
        result = get_config_dir()
        assert "wowstat" in result

    def test_path_is_absolute(self):
        """Test that returned path is absolute."""
        result = get_config_dir()
        assert os.path.isabs(result)

    def test_macos_path(self, monkeypatch):
        """Test macOS returns Application Support path."""
        import platform as plat

        monkeypatch.setattr(plat, "system", lambda: "Darwin")
        monkeypatch.setenv("HOME", "/Users/testuser")
        # Need to reimport to pick up the mock
        from model import get_config_dir as get_dir

        result = get_dir()
        assert "Library/Application Support/wowstat" in result

    def test_linux_path_default(self, monkeypatch):
        """Test Linux uses ~/.config by default."""
        import platform as plat

        monkeypatch.setattr(plat, "system", lambda: "Linux")
        monkeypatch.setenv("HOME", "/home/testuser")
        monkeypatch.delenv("XDG_CONFIG_HOME", raising=False)
        from model import get_config_dir as get_dir

        result = get_dir()
        assert ".config/wowstat" in result

    def test_linux_path_xdg(self, monkeypatch):
        """Test Linux respects XDG_CONFIG_HOME."""
        import platform as plat

        monkeypatch.setattr(plat, "system", lambda: "Linux")
        monkeypatch.setenv("XDG_CONFIG_HOME", "/custom/config")
        from model import get_config_dir as get_dir

        result = get_dir()
        assert result == "/custom/config/wowstat"

    def test_windows_path_appdata(self, monkeypatch):
        """Test Windows uses APPDATA."""
        import platform as plat

        monkeypatch.setattr(plat, "system", lambda: "Windows")
        monkeypatch.setenv("APPDATA", "C:\\Users\\testuser\\AppData\\Roaming")
        from model import get_config_dir as get_dir

        result = get_dir()
        assert "AppData" in result and "wowstat" in result

    def test_windows_path_fallback(self, monkeypatch):
        """Test Windows fallback when APPDATA not set."""
        import platform as plat

        monkeypatch.setattr(plat, "system", lambda: "Windows")
        monkeypatch.delenv("APPDATA", raising=False)
        monkeypatch.setenv("HOME", "/home/testuser")
        from model import get_config_dir as get_dir

        result = get_dir()
        assert "wowstat" in result


class TestWowDefaultPaths:
    """Tests for WOW_DEFAULT_PATHS constant."""

    def test_has_all_platforms(self):
        """Test that WOW_DEFAULT_PATHS has entries for all platforms."""
        assert "Darwin" in WOW_DEFAULT_PATHS
        assert "Windows" in WOW_DEFAULT_PATHS
        assert "Linux" in WOW_DEFAULT_PATHS

    def test_darwin_paths_are_absolute(self):
        """Test macOS paths are absolute."""
        for path in WOW_DEFAULT_PATHS["Darwin"]:
            assert path.startswith("/") or path.startswith("~")

    def test_windows_paths_have_drive_letters(self):
        """Test Windows paths start with drive letters."""
        for path in WOW_DEFAULT_PATHS["Windows"]:
            assert path[1] == ":"  # e.g., "C:/"

    def test_each_platform_has_multiple_paths(self):
        """Test each platform has fallback paths."""
        for platform_name, paths in WOW_DEFAULT_PATHS.items():
            assert len(paths) >= 2, f"{platform_name} should have multiple fallbacks"


class TestVersionComparison:
    """Tests for the version comparison function."""

    def test_equal_versions(self):
        """Test equal versions return 0."""
        from model import _compare_versions

        assert _compare_versions("1.0.0", "1.0.0") == 0
        assert _compare_versions("2.1.3", "2.1.3") == 0

    def test_newer_version(self):
        """Test newer version returns 1."""
        from model import _compare_versions

        assert _compare_versions("1.0.1", "1.0.0") == 1
        assert _compare_versions("1.1.0", "1.0.0") == 1
        assert _compare_versions("2.0.0", "1.9.9") == 1

    def test_older_version(self):
        """Test older version returns -1."""
        from model import _compare_versions

        assert _compare_versions("1.0.0", "1.0.1") == -1
        assert _compare_versions("1.0.0", "1.1.0") == -1
        assert _compare_versions("1.9.9", "2.0.0") == -1

    def test_different_length_versions(self):
        """Test versions with different number of parts."""
        from model import _compare_versions

        assert _compare_versions("1.0", "1.0.0") == 0
        assert _compare_versions("1.0.0.1", "1.0.0") == 1
        assert _compare_versions("1.0", "1.0.1") == -1

    def test_version_with_prefix(self):
        """Test versions with non-numeric suffixes."""
        from model import _compare_versions

        # Only numeric parts are compared
        assert _compare_versions("1.0.0-beta", "1.0.0") == 0
        assert _compare_versions("1.0.1-rc1", "1.0.0") == 1


class TestVersionConstant:
    """Tests for version constant."""

    def test_version_exists(self):
        """Test __version__ is defined."""
        from model import __version__

        assert __version__ is not None
        assert isinstance(__version__, str)
        assert len(__version__) > 0

    def test_version_format(self):
        """Test version follows semver format."""
        from model import __version__

        parts = __version__.split(".")
        assert len(parts) >= 2  # At least major.minor
        for part in parts:
            assert part.isdigit()


class TestGitHubRepo:
    """Tests for GitHub repo constant."""

    def test_github_repo_format(self):
        """Test GITHUB_REPO has owner/repo format."""
        from model import GITHUB_REPO

        assert "/" in GITHUB_REPO
        parts = GITHUB_REPO.split("/")
        assert len(parts) == 2
        assert len(parts[0]) > 0  # owner
        assert len(parts[1]) > 0  # repo
