"""
Data model layer for WoW Stat Tracker.
Contains data structures, persistence, and parsing logic with no GTK dependencies.
"""

import json
import os
import platform
import shutil
import subprocess
from dataclasses import dataclass, asdict
from datetime import datetime, timezone, timedelta


# Application name for config directories
APP_NAME = "wowstat"

# Validation constants
MAX_ITEM_LEVEL = 1000
MAX_ITEMS_PER_CATEGORY = 50
MAX_DELVES = 8
MAX_GILDED_STASH = 3
MAX_TIMEWALK = 5

# Theme constants
THEME_AUTO = "auto"
THEME_LIGHT = "light"
THEME_DARK = "dark"

# Column index constants (shared with view)
COL_REALM = 0
COL_NAME = 1
COL_GUILD = 2
COL_ITEM_LEVEL = 3
COL_HEROIC_ITEMS = 4
COL_CHAMPION_ITEMS = 5
COL_VETERAN_ITEMS = 6
COL_ADVENTURE_ITEMS = 7
COL_OLD_ITEMS = 8
COL_VAULT_VISITED = 9
COL_DELVES = 10
COL_GILDED_STASH = 11
COL_GUNDARZ = 12
COL_QUESTS = 13
COL_TIMEWALK = 14
COL_NOTES = 15
COL_INDEX = 16
COL_COUNT = 17

# Default WoW installation paths by platform
WOW_DEFAULT_PATHS = {
    "Darwin": [  # macOS
        "/Applications/World of Warcraft",
        "/Applications/Games/World of Warcraft",
        os.path.expanduser("~/Applications/World of Warcraft"),
    ],
    "Windows": [
        "C:/Program Files (x86)/World of Warcraft",
        "C:/Program Files/World of Warcraft",
        "D:/World of Warcraft",
        "D:/Games/World of Warcraft",
    ],
    "Linux": [
        os.path.expanduser("~/.wine/drive_c/Program Files (x86)/World of Warcraft"),
        os.path.expanduser(
            "~/Games/world-of-warcraft/drive_c/Program Files (x86)/World of Warcraft"
        ),
    ],
}


@dataclass
class Character:
    """Data class representing a WoW character."""

    realm: str = ""
    name: str = ""
    guild: str = ""
    item_level: float = 0.0
    heroic_items: int = 0
    champion_items: int = 0
    veteran_items: int = 0
    adventure_items: int = 0
    old_items: int = 0
    vault_visited: bool = False
    delves: int = 0
    gilded_stash: int = 0
    gundarz: bool = False
    quests: bool = False
    timewalk: int = 0
    notes: str = ""

    def validate(self) -> list[str]:
        """Validate character data. Returns list of error messages."""
        errors = []

        if not self.name.strip():
            errors.append("Character name is required")
        if not self.realm.strip():
            errors.append("Realm is required")

        if self.item_level < 0 or self.item_level > MAX_ITEM_LEVEL:
            errors.append(f"Item level must be between 0 and {MAX_ITEM_LEVEL}")

        for field_name in [
            "heroic_items",
            "champion_items",
            "veteran_items",
            "adventure_items",
            "old_items",
        ]:
            value = getattr(self, field_name)
            if value < 0 or value > MAX_ITEMS_PER_CATEGORY:
                errors.append(
                    f"{field_name} must be between 0 and {MAX_ITEMS_PER_CATEGORY}"
                )

        if self.delves < 0 or self.delves > MAX_DELVES:
            errors.append(f"Delves must be between 0 and {MAX_DELVES}")

        if self.timewalk < 0 or self.timewalk > MAX_TIMEWALK:
            errors.append(f"Timewalk must be between 0 and {MAX_TIMEWALK}")

        return errors

    def to_dict(self) -> dict:
        """Convert to dictionary for JSON serialization."""
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict) -> "Character":
        """Create a Character from a dictionary."""
        # Set defaults for any missing fields
        defaults = {
            "realm": "",
            "name": "",
            "guild": "",
            "item_level": 0.0,
            "heroic_items": 0,
            "champion_items": 0,
            "veteran_items": 0,
            "adventure_items": 0,
            "old_items": 0,
            "vault_visited": False,
            "delves": 0,
            "gilded_stash": 0,
            "gundarz": False,
            "quests": False,
            "timewalk": 0,
            "notes": "",
        }
        defaults.update(data)
        # Ensure item_level is always a float
        defaults["item_level"] = float(defaults["item_level"])
        return cls(
            **{k: v for k, v in defaults.items() if k in cls.__dataclass_fields__}
        )

    def reset_weekly(self) -> None:
        """Reset weekly tracking fields."""
        self.vault_visited = False
        self.delves = 0
        self.gilded_stash = 0
        self.gundarz = False
        self.quests = False
        self.timewalk = 0


class CharacterStore:
    """Manages character data persistence and CRUD operations."""

    def __init__(self, data_file: str):
        self.data_file = data_file
        self.characters: list[Character] = []

    def load(self) -> None:
        """Load characters from JSON file."""
        if os.path.exists(self.data_file):
            try:
                with open(self.data_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    self.characters = [Character.from_dict(char) for char in data]
            except (json.JSONDecodeError, IOError, UnicodeDecodeError) as e:
                print(f"Warning: Failed to load data file: {e}")
                self.characters = []
        else:
            self.characters = []

    def save(self) -> None:
        """Save characters to JSON file atomically."""
        temp_file = self.data_file + ".tmp"
        try:
            with open(temp_file, "w", encoding="utf-8") as f:
                json.dump([char.to_dict() for char in self.characters], f, indent=2)
            shutil.move(temp_file, self.data_file)
        except (IOError, OSError, UnicodeEncodeError) as e:
            # Remove temp file if it exists
            if os.path.exists(temp_file):
                try:
                    os.remove(temp_file)
                except OSError:
                    pass
            raise IOError(f"Failed to save character data: {e}") from e

    def add(self, character: Character) -> None:
        """Add a new character."""
        self.characters.append(character)

    def update(self, index: int, character: Character) -> None:
        """Update an existing character."""
        if 0 <= index < len(self.characters):
            self.characters[index] = character
        else:
            raise IndexError(f"Character index {index} out of range")

    def delete(self, index: int) -> None:
        """Delete a character by index."""
        if 0 <= index < len(self.characters):
            del self.characters[index]
        else:
            raise IndexError(f"Character index {index} out of range")

    def get(self, index: int) -> Character:
        """Get a character by index."""
        if 0 <= index < len(self.characters):
            return self.characters[index]
        raise IndexError(f"Character index {index} out of range")

    def reset_weekly_all(self) -> None:
        """Reset weekly data for all characters."""
        for char in self.characters:
            char.reset_weekly()


class Config:
    """Manages application configuration."""

    def __init__(self, config_file: str):
        self.config_file = config_file
        self._data: dict = {}

    def load(self) -> None:
        """Load configuration from JSON file."""
        if os.path.exists(self.config_file):
            try:
                with open(self.config_file, "r", encoding="utf-8") as f:
                    self._data = json.load(f)
            except (json.JSONDecodeError, IOError, UnicodeDecodeError) as e:
                print(f"Warning: Failed to load config file: {e}")
                self._data = {}
        else:
            self._data = {}

    def save(self) -> None:
        """Save configuration to JSON file atomically."""
        temp_file = self.config_file + ".tmp"
        try:
            with open(temp_file, "w", encoding="utf-8") as f:
                json.dump(self._data, f, indent=2)
            shutil.move(temp_file, self.config_file)
        except (IOError, OSError, UnicodeEncodeError) as e:
            print(f"Warning: Failed to save config: {e}")

    def get(self, key: str, default=None):
        """Get a config value."""
        return self._data.get(key, default)

    def set(self, key: str, value) -> None:
        """Set a config value."""
        self._data[key] = value

    def update(self, updates: dict) -> None:
        """Update multiple config values."""
        self._data.update(updates)

    @property
    def data(self) -> dict:
        """Get the raw config data dict."""
        return self._data


class LockManager:
    """Manages single-instance lock file."""

    def __init__(self, lock_file: str):
        self.lock_file = lock_file
        self._lock_fd = None

    def acquire(self) -> bool:
        """Acquire file lock to prevent multiple instances. Returns True if acquired."""
        try:
            import fcntl

            self._lock_fd = open(self.lock_file, "w", encoding="utf-8")
            fcntl.flock(self._lock_fd.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
            self._lock_fd.write(str(os.getpid()))
            self._lock_fd.flush()
            return True
        except (ImportError, IOError, OSError):
            # Close file handle if opened but locking failed
            if self._lock_fd:
                try:
                    self._lock_fd.close()
                except Exception:
                    pass
                self._lock_fd = None

            # fcntl not available on Windows, or lock failed
            # Fallback to simple PID file check
            return self._acquire_fallback()

    def _acquire_fallback(self) -> bool:
        """Fallback lock acquisition using PID file."""
        try:
            if os.path.exists(self.lock_file):
                with open(self.lock_file, "r", encoding="utf-8") as f:
                    pid = int(f.read().strip())
                if self._is_process_running(pid):
                    return False  # Process exists, don't start
                else:
                    # Process doesn't exist, remove stale lock
                    try:
                        os.remove(self.lock_file)
                    except OSError:
                        pass

            # Create new lock file
            with open(self.lock_file, "w", encoding="utf-8") as f:
                f.write(str(os.getpid()))
            return True
        except (IOError, ValueError, UnicodeError):
            return True  # If we can't check, allow startup

    def _is_process_running(self, pid: int) -> bool:
        """Cross-platform process existence check."""
        try:
            if platform.system() == "Windows":
                try:
                    result = subprocess.run(
                        ["tasklist", "/FI", f"PID eq {pid}", "/FO", "CSV"],
                        capture_output=True,
                        text=True,
                        timeout=5,
                    )
                    return str(pid) in result.stdout
                except (subprocess.SubprocessError, subprocess.TimeoutExpired):
                    try:
                        os.kill(pid, 0)
                        return True
                    except (OSError, ProcessLookupError):
                        return False
            else:
                # Unix-like systems
                try:
                    os.kill(pid, 0)  # Signal 0 checks existence without killing
                    return True
                except (OSError, ProcessLookupError):
                    return False
        except Exception:
            return False

    def release(self) -> None:
        """Release file lock."""
        try:
            if self._lock_fd is not None:
                try:
                    self._lock_fd.close()
                except (IOError, OSError):
                    pass
                finally:
                    self._lock_fd = None

            if os.path.exists(self.lock_file):
                os.remove(self.lock_file)
        except (IOError, OSError):
            pass


def get_config_dir() -> str:
    """Get the platform-specific config directory for the application.

    Returns:
        macOS: ~/Library/Application Support/wowstat
        Linux: ~/.config/wowstat (or $XDG_CONFIG_HOME/wowstat)
        Windows: %APPDATA%/wowstat
    """
    system = platform.system().lower()
    home = os.path.expanduser("~")

    if system == "darwin":
        # macOS: use Application Support
        return os.path.join(home, "Library", "Application Support", APP_NAME)
    elif system == "windows":
        # Windows: use APPDATA
        appdata = os.environ.get("APPDATA")
        if appdata:
            return os.path.join(appdata, APP_NAME)
        # Fallback if APPDATA not set
        return os.path.join(home, "AppData", "Roaming", APP_NAME)
    else:
        # Linux and other Unix-like: use XDG_CONFIG_HOME or ~/.config
        xdg_config = os.environ.get("XDG_CONFIG_HOME")
        if xdg_config:
            return os.path.join(xdg_config, APP_NAME)
        return os.path.join(home, ".config", APP_NAME)


def migrate_old_files(config_dir: str, data_file: str, config_file: str) -> None:
    """Migrate old config/data files from current directory to config directory."""
    old_files = [
        ("wowstat_data.json", data_file),
        ("wowstat_config.json", config_file),
    ]

    for old_name, new_path in old_files:
        old_path = os.path.abspath(old_name)

        # Only migrate if old file exists and new file doesn't
        if os.path.exists(old_path) and not os.path.exists(new_path):
            try:
                shutil.move(old_path, new_path)
                print(f"Migrated {old_name} to {new_path}")
            except (IOError, OSError) as e:
                print(f"Warning: Failed to migrate {old_name}: {e}")


def detect_system_theme() -> bool:
    """Detect if system prefers dark mode. Returns True for dark mode."""
    system = platform.system().lower()

    try:
        if system == "darwin":  # macOS
            try:
                result = subprocess.run(
                    ["defaults", "read", "-g", "AppleInterfaceStyle"],
                    capture_output=True,
                    text=True,
                    timeout=5,
                )
                return result.returncode == 0 and "dark" in result.stdout.lower()
            except Exception:
                pass

        elif system == "linux":
            try:
                result = subprocess.run(
                    ["gsettings", "get", "org.gnome.desktop.interface", "gtk-theme"],
                    capture_output=True,
                    text=True,
                    timeout=5,
                )
                if result.returncode == 0:
                    theme = result.stdout.strip().strip("'\"").lower()
                    return "dark" in theme
            except Exception:
                pass

            # Fall back to checking environment variables
            current_theme = os.environ.get("GTK_THEME", "").lower()
            return "dark" in current_theme

        elif system == "windows":
            try:
                result = subprocess.run(
                    [
                        "reg",
                        "query",
                        "HKEY_CURRENT_USER\\Software\\Microsoft\\Windows\\CurrentVersion\\Themes\\Personalize",
                        "/v",
                        "AppsUseLightTheme",
                    ],
                    capture_output=True,
                    text=True,
                    timeout=5,
                )
                if result.returncode == 0 and "0x0" in result.stdout:
                    return True  # 0x0 means dark mode is enabled
            except Exception:
                pass

    except (subprocess.TimeoutExpired, subprocess.SubprocessError, OSError):
        pass

    # Default to light theme if detection fails
    return False


def get_current_week_id() -> str:
    """Calculate the current WoW week ID based on Tuesday 15:00 UTC reset.

    Returns a string in YYYYMMDD format representing the reset date for the
    current week. This matches the logic used in the WoW addon.
    """
    # WoW resets on Tuesday at 15:00 UTC (7:00 AM PST)
    RESET_WEEKDAY = 1  # Tuesday (Monday=0 in Python)
    RESET_HOUR = 15  # 15:00 UTC

    now = datetime.now(timezone.utc)

    # Calculate days since last Tuesday reset
    days_since_reset = (now.weekday() - RESET_WEEKDAY) % 7

    # If it's Tuesday but before reset time, count as previous week
    if now.weekday() == RESET_WEEKDAY and now.hour < RESET_HOUR:
        days_since_reset = 7

    # Get the last reset timestamp
    last_reset = now - timedelta(days=days_since_reset)
    # Normalize to reset hour
    last_reset = last_reset.replace(hour=RESET_HOUR, minute=0, second=0, microsecond=0)

    return last_reset.strftime("%Y%m%d")
