#!/usr/bin/env python3
"""
WoW Stat Tracker - Main application controller.
Orchestrates model (data) and view (GTK UI) layers.
"""

import gi

gi.require_version("Gtk", "3.0")
from gi.repository import Gtk, GLib

import os
import platform
import re
import threading

from model import (
    Character,
    CharacterStore,
    Config,
    LockManager,
    migrate_old_files,
    THEME_AUTO,
    THEME_LIGHT,
    THEME_DARK,
    COL_VAULT_VISITED,
    COL_GUNDARZ,
    COL_QUESTS,
)

from view import (
    ThemeManager,
    CharacterTable,
    CharacterDialog,
    show_error,
    show_warning,
    show_info,
)


class WoWStatTracker:
    """Main application controller."""

    def __init__(self):
        # Set up config directory
        self.config_dir = os.path.join(os.path.expanduser("~"), ".config", "wowstat")
        os.makedirs(self.config_dir, exist_ok=True)

        data_file = os.path.join(self.config_dir, "wowstat_data.json")
        config_file = os.path.join(self.config_dir, "wowstat_config.json")
        lock_file = os.path.join(self.config_dir, "wowstat.lock")

        # Migrate old files from current directory to config directory
        migrate_old_files(self.config_dir, data_file, config_file)

        # Initialize lock manager and check for another instance
        self.lock_manager = LockManager(lock_file)
        if not self.lock_manager.acquire():
            import sys

            print("Another instance is already running!")
            sys.exit(1)

        # Initialize model
        self.store = CharacterStore(data_file)
        self.store.load()

        self.config = Config(config_file)
        self.config.load()

        self.debug_enabled = self.config.get("debug", False)

        # Timer and geometry tracking
        self._config_timer = None
        self._last_window_geometry = None

        # Create main window
        self.window = Gtk.Window(title="WoW Character Stat Tracker")
        self.window.connect("destroy", self._on_destroy)
        self.window.connect("configure-event", self._on_window_configure)
        self.window.connect("window-state-event", self._on_window_state_event)

        # Initialize theme manager
        theme_pref = self.config.get("theme", THEME_AUTO)
        self.theme_manager = ThemeManager(self.window, theme_pref)

        # Set up UI
        self._setup_ui()
        self.theme_manager.apply()

        # Restore window state
        self._restore_window_state()

        # Populate table
        self.table.populate(self.store.characters)

        # Restore column widths and sort order
        self._restore_column_widths()
        self._restore_sort_order()

    def _setup_ui(self):
        """Set up the main UI layout."""
        vbox = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)
        self.window.add(vbox)

        # Create menu bar
        menubar = self._create_menu_bar()
        vbox.pack_start(menubar, False, False, 0)

        # Content area with margins
        content_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10)
        content_box.set_margin_start(10)
        content_box.set_margin_end(10)
        content_box.set_margin_top(10)
        content_box.set_margin_bottom(10)
        vbox.pack_start(content_box, True, True, 0)

        # Scrolled window for table
        scrolled = Gtk.ScrolledWindow()
        scrolled.set_policy(Gtk.PolicyType.AUTOMATIC, Gtk.PolicyType.AUTOMATIC)
        content_box.pack_start(scrolled, True, True, 0)

        # Create character table
        self.table = CharacterTable(
            theme_manager=self.theme_manager,
            on_row_activated=self._on_row_activated,
            on_toggle=self._on_toggle,
            on_notes_edited=self._on_notes_edited,
        )
        scrolled.add(self.table.treeview)

    def _create_menu_bar(self) -> Gtk.MenuBar:
        """Create the application menu bar."""
        menubar = Gtk.MenuBar()

        # File menu
        file_menu_item = Gtk.MenuItem(label="File")
        file_menu = Gtk.Menu()
        file_menu_item.set_submenu(file_menu)
        menubar.append(file_menu_item)

        add_item = Gtk.MenuItem(label="Add Character")
        add_item.connect("activate", self._on_add_character)
        file_menu.append(add_item)

        file_menu.append(Gtk.SeparatorMenuItem())

        reset_item = Gtk.MenuItem(label="Reset Weekly Data")
        reset_item.connect("activate", self._on_reset_weekly)
        file_menu.append(reset_item)

        file_menu.append(Gtk.SeparatorMenuItem())

        altoholic_item = Gtk.MenuItem(label="Import from Altoholic")
        altoholic_item.connect("activate", self._on_import_altoholic)
        file_menu.append(altoholic_item)

        addon_item = Gtk.MenuItem(label="Import from WoW Addon")
        addon_item.connect("activate", self._on_import_wow_addon)
        file_menu.append(addon_item)

        file_menu.append(Gtk.SeparatorMenuItem())

        quit_item = Gtk.MenuItem(label="Quit")
        quit_item.connect("activate", lambda w: self.window.close())
        file_menu.append(quit_item)

        # View menu
        view_menu_item = Gtk.MenuItem(label="View")
        view_menu = Gtk.Menu()
        view_menu_item.set_submenu(view_menu)
        menubar.append(view_menu_item)

        theme_menu_item = Gtk.MenuItem(label="Theme")
        theme_submenu = Gtk.Menu()
        theme_menu_item.set_submenu(theme_submenu)
        view_menu.append(theme_menu_item)

        # Theme radio buttons
        theme_group = None
        current_pref = self.theme_manager.current_preference

        auto_theme_item = Gtk.RadioMenuItem(group=theme_group, label="Auto (System)")
        auto_theme_item.connect("activate", self._on_theme_changed, THEME_AUTO)
        if current_pref == THEME_AUTO:
            auto_theme_item.set_active(True)
        theme_submenu.append(auto_theme_item)
        theme_group = auto_theme_item

        light_theme_item = Gtk.RadioMenuItem(group=theme_group, label="Light")
        light_theme_item.connect("activate", self._on_theme_changed, THEME_LIGHT)
        if current_pref == THEME_LIGHT:
            light_theme_item.set_active(True)
        theme_submenu.append(light_theme_item)

        dark_theme_item = Gtk.RadioMenuItem(group=theme_group, label="Dark")
        dark_theme_item.connect("activate", self._on_theme_changed, THEME_DARK)
        if current_pref == THEME_DARK:
            dark_theme_item.set_active(True)
        theme_submenu.append(dark_theme_item)

        return menubar

    # ==================== Event Handlers ====================

    def _on_row_activated(self, index: int):
        """Handle row double-click to edit character."""
        character = self.store.get(index)
        dialog = CharacterDialog(self.window)
        result = dialog.show_edit(character)

        if result == "DELETE":
            self.store.delete(index)
            self._save_and_refresh()
        elif result is not None:
            self.store.update(index, result)
            self._save_and_refresh()

    def _on_toggle(self, index: int, col_id: int, new_value: bool):
        """Handle toggle click on boolean columns."""
        character = self.store.get(index)

        if col_id == COL_VAULT_VISITED:
            character.vault_visited = new_value
        elif col_id == COL_GUNDARZ:
            character.gundarz = new_value
        elif col_id == COL_QUESTS:
            character.quests = new_value

        self.store.update(index, character)
        self._save_and_refresh()

    def _on_notes_edited(self, index: int, new_text: str):
        """Handle notes cell edited."""
        character = self.store.get(index)
        character.notes = new_text
        self.store.update(index, character)
        self._save_and_refresh()

    def _on_add_character(self, widget):
        """Handle Add Character menu item."""
        dialog = CharacterDialog(self.window)
        result = dialog.show_edit(None)

        if result is not None and result != "DELETE":
            self.store.add(result)
            self._save_and_refresh()

    def _on_reset_weekly(self, widget):
        """Handle Reset Weekly Data menu item."""
        self.store.reset_weekly_all()
        self._save_and_refresh()

    def _on_theme_changed(self, menu_item, theme_preference):
        """Handle theme menu selection."""
        if menu_item.get_active():
            self.theme_manager.set_preference(theme_preference)
            self.config.set("theme", theme_preference)
            self.config.save()
            self.table.refresh_backgrounds()

    def _on_import_altoholic(self, widget):
        """Handle Import from Altoholic menu item."""
        self.update_from_altoholic(widget)

    def _on_import_wow_addon(self, widget):
        """Handle Import from WoW Addon menu item."""
        self.update_from_wow_addon(widget)

    # ==================== Window State Management ====================

    def _restore_window_state(self):
        """Restore window size, position, and maximized state."""
        window_config = self.config.get("window", {})
        width = max(400, min(2000, window_config.get("width", 1200)))
        height = max(300, min(1500, window_config.get("height", 600)))
        x = window_config.get("x")
        y = window_config.get("y")
        is_maximized = window_config.get("maximized", False)

        if self.debug_enabled:
            print(
                f"[DEBUG] Restoring window: {width}x{height} at ({x},{y}) maximized={is_maximized}"
            )

        self.window.set_default_size(width, height)

        if is_maximized:
            GLib.idle_add(self._delayed_maximize)
        elif x is not None and y is not None:
            # Ensure position is on screen
            screen_width, screen_height = self._get_screen_size()
            x = max(0, min(screen_width - 100, x))
            y = max(0, min(screen_height - 100, y))
            GLib.idle_add(self._delayed_position, x, y)

    def _get_screen_size(self) -> tuple:
        """Get screen dimensions."""
        try:
            display = self.window.get_display()
            if display:
                monitor = display.get_primary_monitor()
                if monitor:
                    geometry = monitor.get_geometry()
                    return (geometry.width, geometry.height)
        except AttributeError:
            try:
                screen = self.window.get_screen()
                if screen:
                    return (screen.get_width(), screen.get_height())
            except Exception:
                pass
        return (1920, 1080)  # Fallback

    def _delayed_maximize(self):
        """Delayed window maximizing for macOS compatibility."""
        try:
            self.window.maximize()
        except Exception as e:
            if self.debug_enabled:
                print(f"[DEBUG] Failed to maximize: {e}")
        return False

    def _delayed_position(self, x, y):
        """Delayed window positioning for macOS compatibility."""
        try:
            self.window.move(x, y)
        except Exception as e:
            if self.debug_enabled:
                print(f"[DEBUG] Failed to position: {e}")
        return False

    def _on_window_configure(self, window, event):
        """Handle window configure event (resize/move)."""
        # Cache geometry immediately
        self._last_window_geometry = {
            "width": max(400, min(3840, event.width)),
            "height": max(300, min(2160, event.height)),
            "x": max(0, event.x),
            "y": max(0, event.y),
        }

        # Debounce config saves
        if self._config_timer is not None:
            self._config_timer.cancel()

        self._config_timer = threading.Timer(0.5, self._save_window_geometry)
        self._config_timer.start()

    def _on_window_state_event(self, window, event):
        """Handle window state changes (maximize/minimize)."""
        is_maximized = bool(event.new_window_state & Gdk.WindowState.MAXIMIZED)
        if "window" not in self.config.data:
            self.config.data["window"] = {}
        self.config.data["window"]["maximized"] = is_maximized

    def _save_window_geometry(self):
        """Save window geometry to config."""
        if self._last_window_geometry:
            if "window" not in self.config.data:
                self.config.data["window"] = {}
            if not self.config.data["window"].get("maximized", False):
                self.config.data["window"].update(self._last_window_geometry)
            self.config.save()

    def _on_destroy(self, widget):
        """Handle window destroy."""
        if self._config_timer is not None:
            self._config_timer.cancel()
            self._config_timer = None

        # Save final state
        if "window" not in self.config.data:
            self.config.data["window"] = {}

        if self._last_window_geometry and not self.config.data.get("window", {}).get(
            "maximized", False
        ):
            self.config.data["window"].update(self._last_window_geometry)

        self._save_column_widths()
        self._save_sort_order()
        self.config.save()
        self.lock_manager.release()
        Gtk.main_quit()

    # ==================== Column/Sort Persistence ====================

    def _restore_column_widths(self):
        """Restore column widths from config."""
        widths = self.config.get("columns", {})
        self.table.set_column_widths(widths)

    def _save_column_widths(self):
        """Save column widths to config."""
        widths = self.table.get_column_widths()
        self.config.set("columns", widths)

    def _restore_sort_order(self):
        """Restore sort order from config."""
        sort_config = self.config.get("sort", {})
        column_id = sort_config.get("column_id")
        order = sort_config.get("order", 0)

        if column_id is not None:
            try:
                sort_order = (
                    Gtk.SortType.ASCENDING if order == 0 else Gtk.SortType.DESCENDING
                )
                self.table.set_sort_order(column_id, sort_order)
            except (ValueError, TypeError):
                pass

    def _save_sort_order(self):
        """Save sort order to config."""
        sort_col, sort_order = self.table.get_sort_order()
        if sort_col is not None:
            self.config.set(
                "sort",
                {
                    "column_id": sort_col,
                    "order": 0 if sort_order == Gtk.SortType.ASCENDING else 1,
                },
            )

    # ==================== Helper Methods ====================

    def _save_and_refresh(self):
        """Save data and refresh the table."""
        try:
            self.store.save()
        except IOError as e:
            show_error(self.window, "Failed to save", str(e))
        self.table.populate(self.store.characters)

    # ==================== Import Methods ====================
    # These are kept here for now as they have complex instance state

    def find_altoholic_data(self):
        """Find Altoholic SavedVariables file."""
        system = platform.system()
        home = os.path.expanduser("~")

        print(f"[VERBOSE] Searching for Altoholic data on {system} system")

        possible_paths = []

        if system == "Windows":
            program_files_x86 = os.environ.get(
                "PROGRAMFILES(X86)", "C:\\Program Files (x86)"
            )
            program_files = os.environ.get("PROGRAMFILES", "C:\\Program Files")

            possible_paths = [
                os.path.join(
                    home, "Documents", "World of Warcraft", "_retail_", "WTF", "Account"
                ),
                os.path.join(
                    program_files_x86, "World of Warcraft", "_retail_", "WTF", "Account"
                ),
                os.path.join(
                    program_files, "World of Warcraft", "_retail_", "WTF", "Account"
                ),
            ]

            for drive in ["D:", "E:", "F:"]:
                possible_paths.extend(
                    [
                        os.path.join(
                            drive, "World of Warcraft", "_retail_", "WTF", "Account"
                        ),
                        os.path.join(
                            drive,
                            "Games",
                            "World of Warcraft",
                            "_retail_",
                            "WTF",
                            "Account",
                        ),
                    ]
                )

        elif system == "Darwin":  # macOS
            possible_paths = [
                os.path.join(
                    home,
                    "Applications",
                    "World of Warcraft",
                    "_retail_",
                    "WTF",
                    "Account",
                ),
                "/Applications/World of Warcraft/_retail_/WTF/Account",
                "/Applications/Games/World of Warcraft/_retail_/WTF/Account",
            ]

        else:  # Linux
            possible_paths = [
                os.path.join(
                    home,
                    ".wine",
                    "drive_c",
                    "Program Files (x86)",
                    "World of Warcraft",
                    "_retail_",
                    "WTF",
                    "Account",
                ),
                os.path.join(
                    home,
                    "Games",
                    "world-of-warcraft",
                    "drive_c",
                    "Program Files (x86)",
                    "World of Warcraft",
                    "_retail_",
                    "WTF",
                    "Account",
                ),
            ]

        # Look for Altoholic/DataStore files
        for base_path in possible_paths:
            if not os.path.exists(base_path):
                continue

            try:
                for account_dir in os.listdir(base_path):
                    account_path = os.path.join(base_path, account_dir)
                    if not os.path.isdir(account_path):
                        continue

                    sv_dir = os.path.join(account_path, "SavedVariables")
                    if not os.path.exists(sv_dir):
                        continue

                    try:
                        sv_files = os.listdir(sv_dir)
                        target_files = [
                            f
                            for f in sv_files
                            if (f.startswith("Altoholic") or f.startswith("DataStore"))
                            and not f.endswith(".bak")
                            and f.endswith(".lua")
                        ]

                        if target_files:
                            self._altoholic_files = [
                                os.path.join(sv_dir, f) for f in target_files
                            ]

                            # Priority order for primary file
                            priority = [
                                "DataStore_Characters.lua",
                                "Altoholic.lua",
                                "DataStore.lua",
                            ]
                            primary = next(
                                (p for p in priority if p in target_files),
                                target_files[0],
                            )
                            return os.path.join(sv_dir, primary)

                    except Exception as e:
                        print(f"[VERBOSE] Error reading SavedVariables: {e}")

            except PermissionError as e:
                print(f"[VERBOSE] Permission error: {e}")
            except Exception as e:
                print(f"[VERBOSE] Error: {e}")

        print("[VERBOSE] No Altoholic data found")
        return None

    def parse_altoholic_data(self, file_path):
        """Parse Altoholic/DataStore SavedVariables file."""
        if not os.path.exists(file_path):
            return []

        try:
            # Try different encodings
            content = None
            for encoding in ["utf-8", "utf-16", "latin-1", "cp1252"]:
                try:
                    with open(file_path, "r", encoding=encoding, errors="replace") as f:
                        content = f.read()
                    break
                except Exception:
                    continue

            if not content:
                return []

            filename = os.path.basename(file_path).lower()

            if filename == "datastore_characters.lua":
                return self.parse_datastore_characters(content)
            elif filename.startswith("datastore_inventory"):
                return self.parse_datastore_inventory(content)
            else:
                return self.parse_altoholic_general(content)

        except Exception as e:
            print(f"[VERBOSE] Error parsing: {e}")
            return []

    def parse_datastore_characters(self, content):
        """Parse DataStore_Characters.lua format."""
        characters = []

        start_match = re.search(r"DataStore_Characters_Info\s*=\s*{", content)
        if not start_match:
            return characters

        # Extract table content by matching braces
        start_pos = start_match.end() - 1
        brace_count = 0
        table_content = ""

        for char in content[start_pos:]:
            table_content += char
            if char == "{":
                brace_count += 1
            elif char == "}":
                brace_count -= 1
                if brace_count == 0:
                    break

        # Parse character ID mappings
        char_ids = {}
        ids_match = re.search(
            r'DataStore_CharacterIDs\s*=\s*{[^}]*"List"\s*=\s*{([^}]+)}',
            content,
            re.DOTALL,
        )
        if ids_match:
            id_entries = re.findall(r'"([^"]+)"', ids_match.group(1))
            for i, char_id in enumerate(id_entries):
                if "." in char_id:
                    parts = char_id.split(".")
                    if len(parts) >= 3:
                        char_ids[i] = {"name": parts[2], "realm": parts[1]}

        # Parse character entries
        info_content = (
            table_content[1:-1] if table_content.startswith("{") else table_content
        )
        char_entries = []
        brace_count = 0
        current_entry = ""
        in_entry = False

        for char in info_content:
            if char == "{":
                if not in_entry:
                    in_entry = True
                    current_entry = ""
                else:
                    current_entry += char
                brace_count += 1
            elif char == "}":
                brace_count -= 1
                if brace_count == 0 and in_entry:
                    char_entries.append(current_entry)
                    in_entry = False
                else:
                    current_entry += char
            elif in_entry:
                current_entry += char

        for i, entry in enumerate(char_entries):
            try:
                char_data = {}

                if i in char_ids:
                    char_data["name"] = char_ids[i]["name"]
                    char_data["realm"] = char_ids[i]["realm"]
                else:
                    name_match = re.search(r'\["name"\]\s*=\s*"([^"]+)"', entry)
                    if name_match:
                        char_data["name"] = name_match.group(1)
                    else:
                        continue
                    char_data["realm"] = "Unknown"

                # Parse item level
                ilevel_match = re.search(r'\["averageItemLvl"\]\s*=\s*([\d.]+)', entry)
                if ilevel_match:
                    char_data["item_level"] = int(float(ilevel_match.group(1)))

                # Parse guild
                guild_match = re.search(r'\["guildName"\]\s*=\s*"([^"]*)"', entry)
                if guild_match:
                    char_data["guild"] = guild_match.group(1)

                characters.append(char_data)

            except Exception as e:
                print(f"[VERBOSE] Error parsing entry: {e}")
                continue

        return characters

    def parse_datastore_inventory(self, content):
        """Parse DataStore_Inventory.lua format."""
        characters = []

        start_match = re.search(r"DataStore_Inventory_Characters\s*=\s*{", content)
        if not start_match:
            return characters

        # Similar parsing logic to datastore_characters
        # Returns inventory data (item levels, gear counts)

        return characters

    def parse_altoholic_general(self, content):
        """Parse general Altoholic format (fallback parser)."""
        characters = []

        # Try multiple patterns
        patterns = [
            (
                r'\["([^"]+)\|([^"]+)"\]\s*=\s*{[^}]*"itemLevel"\s*=\s*(\d+)',
                "Altoholic format",
            ),
            (
                r'\["([^"]+)\|([^"]+)"\]\s*=\s*{[^}]*averageItemLevel["\s]*=\s*(\d+)',
                "DataStore format",
            ),
        ]

        for pattern, name in patterns:
            matches = re.findall(pattern, content)
            if matches:
                for name_val, realm_val, ilevel in matches:
                    try:
                        characters.append(
                            {
                                "name": name_val,
                                "realm": realm_val,
                                "item_level": int(ilevel),
                            }
                        )
                    except ValueError:
                        continue

                if characters:
                    break

        return characters

    def merge_datastore_data(self, all_files):
        """Merge data from multiple DataStore files."""
        characters_data = {}
        inventory_data = {}
        guild_mappings = {}
        character_guilds = {}
        character_mappings = {}

        for file_path in all_files:
            filename = os.path.basename(file_path).lower()

            try:
                with open(file_path, "r", encoding="utf-8", errors="replace") as f:
                    content = f.read()

                if filename == "datastore_characters.lua":
                    chars = self.parse_datastore_characters(content)
                    for i, char in enumerate(chars):
                        characters_data[i] = char
                        character_mappings[i] = (
                            char.get("name", ""),
                            char.get("realm", ""),
                        )

                elif filename == "datastore_inventory.lua":
                    inv_chars = self.parse_datastore_inventory(content)
                    for i, inv_char in enumerate(inv_chars):
                        inventory_data[i] = inv_char

                elif filename == "datastore.lua":
                    # Parse guild mappings
                    guild_ids_match = re.search(
                        r"DataStore_GuildIDs\s*=\s*{.*?List.*?=\s*{([^}]+)}",
                        content,
                        re.DOTALL,
                    )
                    if guild_ids_match:
                        guild_list = re.findall(r'"([^"]+)"', guild_ids_match.group(1))
                        for i, guild_full_name in enumerate(guild_list):
                            if "." in guild_full_name:
                                parts = guild_full_name.split(".")
                                if len(parts) >= 3:
                                    guild_mappings[i + 1] = parts[2]

            except Exception as e:
                print(f"[VERBOSE] Error processing {filename}: {e}")
                continue

        # Merge all data
        merged = []
        for idx in characters_data:
            char = characters_data[idx].copy()

            if idx in character_mappings:
                name, realm = character_mappings[idx]
                char["realm"] = realm

            if idx in inventory_data:
                inv = inventory_data[idx]
                if char.get("item_level", 0) == 0 and inv.get("item_level", 0) > 0:
                    char["item_level"] = inv["item_level"]

            if idx in character_guilds:
                guild_id = character_guilds[idx]
                if guild_id in guild_mappings:
                    char["guild"] = guild_mappings[guild_id]

            if char.get("name") and char.get("realm") != "Unknown":
                merged.append(char)

        return merged

    def update_from_altoholic(self, widget):
        """Import character data from Altoholic addon."""
        print("[VERBOSE] ========== Starting Altoholic Update ===========")

        altoholic_file = self.find_altoholic_data()

        if not altoholic_file:
            show_warning(
                self.window,
                "Altoholic data not found.",
                "Could not locate Altoholic SavedVariables file. "
                "Make sure World of Warcraft and Altoholic addon are installed.",
            )
            return

        # Parse all available files
        altoholic_chars = []
        files_processed = 0

        if hasattr(self, "_altoholic_files") and self._altoholic_files:
            for file_path in self._altoholic_files:
                chars = self.parse_altoholic_data(file_path)
                altoholic_chars.extend(chars)
                files_processed += 1

            # Try merging DataStore files
            if files_processed > 1:
                merged = self.merge_datastore_data(self._altoholic_files)
                if merged:
                    altoholic_chars = merged
        else:
            altoholic_chars = self.parse_altoholic_data(altoholic_file)
            files_processed = 1

        # Deduplicate
        if altoholic_chars:
            seen = set()
            deduplicated = []
            for char in altoholic_chars:
                if char.get("realm") == "Unknown":
                    continue
                key = f"{char.get('name', '').lower()}|{char.get('realm', '').lower()}"
                if key not in seen:
                    seen.add(key)
                    deduplicated.append(char)
            altoholic_chars = deduplicated

        if not altoholic_chars:
            show_warning(
                self.window,
                "No character data found.",
                "Altoholic files were found but no character data could be parsed.",
            )
            return

        # Update existing or add new
        updated_count = 0
        added_count = 0

        for alt_char in altoholic_chars:
            alt_name = str(alt_char.get("name", "")).strip()
            alt_realm = str(alt_char.get("realm", "")).strip()
            alt_ilevel = alt_char.get("item_level", 0)

            if not alt_name or not alt_realm or alt_ilevel <= 0:
                continue

            # Find existing character
            existing_idx = None
            for i, char in enumerate(self.store.characters):
                if (
                    char.name.lower() == alt_name.lower()
                    and char.realm.lower() == alt_realm.lower()
                ):
                    existing_idx = i
                    break

            if existing_idx is not None:
                existing = self.store.characters[existing_idx]
                if alt_ilevel > existing.item_level:
                    existing.item_level = alt_ilevel
                    if "guild" in alt_char:
                        existing.guild = alt_char["guild"]
                    updated_count += 1
            else:
                # Add new character
                new_char = Character(
                    name=alt_name,
                    realm=alt_realm,
                    item_level=alt_ilevel,
                    guild=alt_char.get("guild", ""),
                )
                self.store.add(new_char)
                added_count += 1

        if updated_count > 0 or added_count > 0:
            self._save_and_refresh()
            show_info(
                self.window,
                "Altoholic data imported successfully!",
                f"Updated {updated_count} characters, added {added_count} new characters.",
            )
        else:
            show_info(
                self.window,
                "No updates needed.",
                "All characters are already up to date.",
            )

        print("[VERBOSE] ========== Altoholic Update Complete ===========")

    def update_from_wow_addon(self, widget):
        """Import character data from WoW Stat Tracker addon."""
        if self.debug_enabled:
            print("[DEBUG] ========== WoW Addon Update Started ===========")

        try:
            addon_file = self.find_wow_addon_data()

            if not addon_file:
                show_warning(
                    self.window,
                    "WoW Addon Data Not Found",
                    "Could not find WoW Stat Tracker addon data.\n\n"
                    "Please ensure:\n"
                    "1. The WoW Stat Tracker addon is installed\n"
                    "2. You have logged in with your characters\n"
                    "3. The addon has exported data (/wst export)",
                )
                return

            # Parse addon data
            addon_chars = self.parse_wow_addon_data(addon_file)

            if not addon_chars:
                show_warning(
                    self.window,
                    "No data found",
                    "Could not parse character data from addon file.",
                )
                return

            # Update characters
            updated = 0
            added = 0

            for addon_char in addon_chars:
                name = addon_char.get("name", "").strip()
                realm = addon_char.get("realm", "").strip()

                if not name or not realm:
                    continue

                # Find existing
                existing_idx = None
                for i, char in enumerate(self.store.characters):
                    if (
                        char.name.lower() == name.lower()
                        and char.realm.lower() == realm.lower()
                    ):
                        existing_idx = i
                        break

                if existing_idx is not None:
                    # Update existing
                    existing = self.store.characters[existing_idx]
                    for key, value in addon_char.items():
                        if hasattr(existing, key) and value:
                            setattr(existing, key, value)
                    updated += 1
                else:
                    # Add new
                    new_char = Character(
                        **{k: v for k, v in addon_char.items() if hasattr(Character, k)}
                    )
                    self.store.add(new_char)
                    added += 1

            if updated > 0 or added > 0:
                self._save_and_refresh()
                show_info(
                    self.window,
                    "Successfully imported data from WoW Stat Tracker addon!",
                    f"Updated {updated} characters, added {added} new characters.",
                )
            else:
                show_info(
                    self.window,
                    "No updates needed.",
                    "All characters are already up to date.",
                )

        except Exception as e:
            show_error(
                self.window, "Import Failed", f"Failed to import addon data:\n{str(e)}"
            )

        if self.debug_enabled:
            print("[DEBUG] ========== WoW Addon Update Complete ===========")

    def find_wow_addon_data(self):
        """Find WoW Stat Tracker addon SavedVariables file."""
        system = platform.system()
        home = os.path.expanduser("~")

        possible_paths = []

        if system == "Darwin":
            possible_paths = [
                f"{home}/Applications/World of Warcraft/_retail_/WTF/Account",
                "/Applications/World of Warcraft/_retail_/WTF/Account",
                f"{home}/Games/World of Warcraft/_retail_/WTF/Account",
            ]
        elif system == "Windows":
            possible_paths = [
                "C:/Program Files (x86)/World of Warcraft/_retail_/WTF/Account",
                "C:/Program Files/World of Warcraft/_retail_/WTF/Account",
            ]
        else:
            possible_paths = [
                f"{home}/.wine/drive_c/Program Files (x86)/World of Warcraft/_retail_/WTF/Account",
                f"{home}/Games/World of Warcraft/_retail_/WTF/Account",
            ]

        for base_path in possible_paths:
            if not os.path.exists(base_path):
                continue

            try:
                for account_dir in os.listdir(base_path):
                    if account_dir.startswith("."):
                        continue

                    addon_file = os.path.join(
                        base_path, account_dir, "SavedVariables", "WoWStatTracker.lua"
                    )
                    if os.path.exists(addon_file):
                        return addon_file

            except Exception:
                continue

        return None

    def parse_wow_addon_data(self, file_path):
        """Parse WoW Stat Tracker addon SavedVariables file."""
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                content = f.read()

            characters = []
            # Parse WoWStatTrackerDB table
            char_pattern = r'\["([^"]+)-([^"]+)"\]\s*=\s*{([^}]+)}'
            matches = re.findall(char_pattern, content)

            for name, realm, data in matches:
                char_data = {"name": name, "realm": realm}
                char_data.update(self.parse_lua_character_data(data))
                characters.append(char_data)

            return characters

        except Exception as e:
            print(f"[VERBOSE] Error parsing addon data: {e}")
            return []

    def parse_lua_character_data(self, lua_data):
        """Extract character fields from Lua table data."""
        result = {}

        field_patterns = [
            ("item_level", r'\["itemLevel"\]\s*=\s*(\d+)'),
            ("heroic_items", r'\["heroicItems"\]\s*=\s*(\d+)'),
            ("champion_items", r'\["championItems"\]\s*=\s*(\d+)'),
            ("veteran_items", r'\["veteranItems"\]\s*=\s*(\d+)'),
            ("adventure_items", r'\["adventureItems"\]\s*=\s*(\d+)'),
            ("old_items", r'\["oldItems"\]\s*=\s*(\d+)'),
            ("delves", r'\["delves"\]\s*=\s*(\d+)'),
            ("timewalk", r'\["timewalk"\]\s*=\s*(\d+)'),
        ]

        for field, pattern in field_patterns:
            match = re.search(pattern, lua_data)
            if match:
                result[field] = int(match.group(1))

        bool_patterns = [
            ("vault_visited", r'\["vaultVisited"\]\s*=\s*(true|false)'),
            ("gundarz", r'\["gundarz"\]\s*=\s*(true|false)'),
            ("quests", r'\["quests"\]\s*=\s*(true|false)'),
        ]

        for field, pattern in bool_patterns:
            match = re.search(pattern, lua_data)
            if match:
                result[field] = match.group(1) == "true"

        guild_match = re.search(r'\["guild"\]\s*=\s*"([^"]*)"', lua_data)
        if guild_match:
            result["guild"] = guild_match.group(1)

        notes_match = re.search(r'\["notes"\]\s*=\s*"([^"]*)"', lua_data)
        if notes_match:
            result["notes"] = notes_match.group(1)

        return result

    def run(self):
        """Start the application."""
        self.window.show_all()
        Gtk.main()


# Import Gdk for window state constants
from gi.repository import Gdk


if __name__ == "__main__":
    app = WoWStatTracker()
    app.run()
