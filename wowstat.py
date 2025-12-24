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
import shutil
import sys
import threading

from model import (
    Character,
    CharacterStore,
    Config,
    LockManager,
    get_config_dir,
    get_current_week_id,
    migrate_old_files,
    THEME_AUTO,
    THEME_LIGHT,
    THEME_DARK,
    COL_VAULT_VISITED,
    COL_GUNDARZ,
    COL_QUESTS,
    WOW_DEFAULT_PATHS,
)

from view import (
    ThemeManager,
    CharacterTable,
    CharacterDialog,
    show_error,
    show_warning,
    show_info,
    show_folder_chooser,
)


class WoWStatTracker:
    """Main application controller."""

    def __init__(self):
        # Set up config directory (platform-specific)
        self.config_dir = get_config_dir()
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

        # Check for weekly reset and auto-clear if needed
        self._weekly_reset_occurred = self._check_weekly_reset()

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

        # Create toolbar
        toolbar = self._create_toolbar()
        vbox.pack_start(toolbar, False, False, 0)

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

        addon_item = Gtk.MenuItem(label="Import from WoW Addon")
        addon_item.connect("activate", self._on_import_wow_addon)
        file_menu.append(addon_item)

        set_path_item = Gtk.MenuItem(label="Set WoW Location...")
        set_path_item.connect("activate", self._on_set_wow_path)
        file_menu.append(set_path_item)

        install_addon_item = Gtk.MenuItem(label="Install Addon to WoW")
        install_addon_item.connect("activate", self._on_install_addon)
        file_menu.append(install_addon_item)

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

    def _create_toolbar(self) -> Gtk.Toolbar:
        """Create the application toolbar."""
        toolbar = Gtk.Toolbar()
        toolbar.set_style(Gtk.ToolbarStyle.BOTH)

        # Add Character button
        add_btn = Gtk.ToolButton()
        add_btn.set_label("Add Character")
        add_btn.set_icon_name("list-add")
        add_btn.set_tooltip_text("Add a new character")
        add_btn.connect("clicked", self._on_add_character)
        toolbar.insert(add_btn, -1)

        # Import from Addon button
        import_btn = Gtk.ToolButton()
        import_btn.set_label("Import")
        import_btn.set_icon_name("document-open")
        import_btn.set_tooltip_text("Import data from WoW addon")
        import_btn.connect("clicked", self._on_import_wow_addon)
        toolbar.insert(import_btn, -1)

        # Reset Weekly button
        reset_btn = Gtk.ToolButton()
        reset_btn.set_label("Reset Weekly")
        reset_btn.set_icon_name("view-refresh")
        reset_btn.set_tooltip_text("Reset all weekly activity data")
        reset_btn.connect("clicked", self._on_reset_weekly)
        toolbar.insert(reset_btn, -1)

        # Update Addon button (Install Addon to WoW)
        update_addon_btn = Gtk.ToolButton()
        update_addon_btn.set_label("Update Addon")
        update_addon_btn.set_icon_name("system-software-install")
        update_addon_btn.set_tooltip_text("Install/update addon in WoW")
        update_addon_btn.connect("clicked", self._on_install_addon)
        toolbar.insert(update_addon_btn, -1)

        # Separator before Exit
        separator = Gtk.SeparatorToolItem()
        separator.set_draw(True)
        toolbar.insert(separator, -1)

        # Exit button
        exit_btn = Gtk.ToolButton()
        exit_btn.set_label("Exit")
        exit_btn.set_icon_name("application-exit")
        exit_btn.set_tooltip_text("Exit the application")
        exit_btn.connect("clicked", lambda w: self.window.close())
        toolbar.insert(exit_btn, -1)

        return toolbar

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
            if hasattr(self, 'table'):
                self.table.refresh_backgrounds()

    def _on_import_wow_addon(self, widget):
        """Handle Import from WoW Addon menu item."""
        self.update_from_wow_addon(widget)

    def _on_set_wow_path(self, widget):
        """Allow user to manually set WoW installation path."""
        current = self.config.get("wow_path", "")
        path = show_folder_chooser(
            self.window,
            "Select World of Warcraft Folder",
            initial_folder=current if current and os.path.exists(current) else None,
        )
        if path:
            if os.path.exists(os.path.join(path, "_retail_")):
                self.config.set("wow_path", path)
                self.config.save()
                show_info(self.window, "Path Updated", f"WoW path set to:\n{path}")
            else:
                show_warning(
                    self.window,
                    "Invalid Selection",
                    "The selected folder must contain a '_retail_' directory.",
                )

    def _on_install_addon(self, widget):
        """Install WoW addon to WoW's AddOns folder."""
        wow_path = self.get_wow_path()
        if not wow_path:
            return

        addons_path = os.path.join(wow_path, "_retail_", "Interface", "AddOns")

        # Create AddOns folder if it doesn't exist
        os.makedirs(addons_path, exist_ok=True)

        # Find addon source (bundled or local)
        addon_source = self._find_addon_source()
        if not addon_source:
            show_error(
                self.window,
                "Addon Not Found",
                "Could not find the WoWStatTracker addon to install.",
            )
            return

        # Copy addon
        dest_path = os.path.join(addons_path, "WoWStatTracker_Addon")
        try:
            if os.path.exists(dest_path):
                shutil.rmtree(dest_path)
            shutil.copytree(addon_source, dest_path)
            show_info(
                self.window,
                "Addon Installed",
                f"WoWStatTracker addon installed to:\n{dest_path}\n\n"
                "Restart WoW to load the addon.",
            )
        except Exception as e:
            show_error(self.window, "Installation Failed", str(e))

    def _find_addon_source(self) -> str | None:
        """Find the addon source directory (bundled or development)."""
        # Check if running from bundle (frozen)
        if getattr(sys, "frozen", False):
            # PyInstaller bundle - addon in Resources
            bundle_path = os.path.join(
                os.path.dirname(sys.executable),
                "..",
                "Resources",
                "WoWStatTracker_Addon",
            )
            if os.path.exists(bundle_path):
                return os.path.realpath(bundle_path)

        # Development mode - addon in same directory as script
        dev_path = os.path.join(
            os.path.dirname(os.path.abspath(__file__)),
            "WoWStatTracker_Addon",
        )
        if os.path.exists(dev_path):
            return dev_path

        return None

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

    def _check_weekly_reset(self) -> bool:
        """Check if weekly reset has occurred and auto-clear data if needed.

        Returns True if a reset was performed.
        """
        current_week = get_current_week_id()
        last_week = self.config.get("last_week_id")

        if self.debug_enabled:
            print(f"[DEBUG] Weekly reset check: current={current_week}, last={last_week}")

        if last_week is None:
            # First run - just record the current week
            self.config.set("last_week_id", current_week)
            self.config.save()
            return False

        if current_week != last_week:
            # Week has changed - reset weekly data
            if self.debug_enabled:
                print(f"[DEBUG] Weekly reset detected! Clearing weekly data.")
            self.store.reset_weekly_all()
            self.store.save()
            self.config.set("last_week_id", current_week)
            self.config.save()
            return True

        return False

    def _save_and_refresh(self):
        """Save data and refresh the table."""
        if self.debug_enabled:
            for c in self.store.characters[:3]:
                print(f"[DEBUG] Before save: {c.name} item_level={c.item_level} (type: {type(c.item_level).__name__})")
        try:
            self.store.save()
            if self.debug_enabled:
                print(f"[DEBUG] Saved to {self.store.data_file}")
        except IOError as e:
            show_error(self.window, "Failed to save", str(e))
        self.table.populate(self.store.characters)

    # ==================== Import Methods ====================

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
            stale_skipped = 0

            # Weekly fields to skip if data is from a different week
            weekly_fields = {
                "vault_visited",
                "delves",
                "gilded_stash",
                "gundarz",
                "quests",
                "timewalk",
            }

            current_week = get_current_week_id()

            for addon_char in addon_chars:
                name = addon_char.get("name", "").strip()
                realm = addon_char.get("realm", "").strip()

                if not name or not realm:
                    continue

                # Check if addon data is from the current week
                addon_week = addon_char.get("week_id")
                is_current_week = addon_week == current_week

                if not is_current_week and addon_week:
                    stale_skipped += 1
                    if self.debug_enabled:
                        print(
                            f"[DEBUG] {name}: Stale weekly data (addon week {addon_week} != current {current_week})"
                        )

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
                    old_ilevel = existing.item_level if self.debug_enabled else None
                    new_ilevel = addon_char.get("item_level") if self.debug_enabled else None
                    for key, value in addon_char.items():
                        # Skip week_id (internal tracking only)
                        if key == "week_id":
                            continue
                        # Skip weekly fields if data is stale
                        if not is_current_week and key in weekly_fields:
                            continue
                        if hasattr(existing, key) and value:
                            setattr(existing, key, value)
                    if self.debug_enabled:
                        print(
                            f"[DEBUG] {name}: item_level {old_ilevel} -> {existing.item_level} "
                            f"(addon had: {new_ilevel}, type: {type(new_ilevel).__name__ if new_ilevel else 'None'})"
                        )
                    updated += 1
                else:
                    # Add new - filter weekly fields if stale
                    char_data = {
                        k: v
                        for k, v in addon_char.items()
                        if hasattr(Character, k)
                        and k != "week_id"
                        and (is_current_week or k not in weekly_fields)
                    }
                    new_char = Character(**char_data)
                    self.store.add(new_char)
                    added += 1

            if updated > 0 or added > 0:
                self._save_and_refresh()
                msg = f"Updated {updated} characters, added {added} new characters."
                if stale_skipped > 0:
                    msg += f"\n\n{stale_skipped} character(s) had stale weekly data (not logged in since reset) - only gear info was imported."
                show_info(
                    self.window,
                    "Successfully imported data from WoW Stat Tracker addon!",
                    msg,
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

    def get_wow_path(self) -> str | None:
        """Get the WoW installation path, detecting or prompting if needed."""
        # Check if already configured and valid
        wow_path = self.config.get("wow_path")
        if wow_path and os.path.exists(wow_path):
            return wow_path

        # Try to auto-detect from defaults
        detected = self._detect_wow_path()
        if detected:
            self.config.set("wow_path", detected)
            self.config.save()
            return detected

        # Prompt user to select
        return self._prompt_wow_path()

    def _detect_wow_path(self) -> str | None:
        """Try to detect WoW installation from default paths."""
        system = platform.system()
        defaults = WOW_DEFAULT_PATHS.get(system, [])

        for path in defaults:
            # Check for _retail_ subdirectory as validation
            retail_path = os.path.join(path, "_retail_")
            if os.path.exists(retail_path):
                return path
        return None

    def _prompt_wow_path(self) -> str | None:
        """Prompt user to select WoW installation folder."""
        show_info(
            self.window,
            "WoW Installation Not Found",
            "Please select your World of Warcraft installation folder.",
        )

        system = platform.system()
        if system == "Darwin":
            initial = "/Applications"
        elif system == "Windows":
            initial = "C:/"
        else:
            initial = os.path.expanduser("~")

        path = show_folder_chooser(
            self.window,
            "Select World of Warcraft Folder",
            initial_folder=initial,
        )

        if path:
            # Validate it looks like a WoW installation
            if os.path.exists(os.path.join(path, "_retail_")):
                self.config.set("wow_path", path)
                self.config.save()
                return path
            else:
                show_warning(
                    self.window,
                    "Invalid Selection",
                    "The selected folder doesn't appear to be a WoW installation.\n\n"
                    "Please select the folder containing '_retail_'.",
                )
        return None

    def find_wow_addon_data(self) -> str | None:
        """Find WoW Stat Tracker addon SavedVariables file."""
        wow_path = self.get_wow_path()
        if not wow_path:
            return None

        wtf_account_path = os.path.join(wow_path, "_retail_", "WTF", "Account")
        if not os.path.exists(wtf_account_path):
            return None

        try:
            for account_dir in os.listdir(wtf_account_path):
                if account_dir.startswith("."):
                    continue

                addon_file = os.path.join(
                    wtf_account_path,
                    account_dir,
                    "SavedVariables",
                    "WoWStatTracker_Addon.lua",
                )
                if os.path.exists(addon_file):
                    return addon_file
        except Exception:
            pass

        return None

    def parse_wow_addon_data(self, file_path):
        """Parse WoW Stat Tracker addon SavedVariables file."""
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                content = f.read()

            characters = []
            # Find all character header positions using position-based matching
            # This handles nested tables correctly
            header_pattern = r'\["([^"]+)-([^"]+)"\]\s*=\s*\{'
            headers = list(re.finditer(header_pattern, content))

            for i, match in enumerate(headers):
                name, realm = match.groups()
                start = match.end()
                # End is either next header or a reasonable boundary
                if i + 1 < len(headers):
                    end = headers[i + 1].start()
                else:
                    end = start + 2000  # reasonable limit for last character

                data = content[start:end]
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

        # Float field (item_level supports decimals)
        ilevel_match = re.search(r'\["item_level"\]\s*=\s*([\d.]+)', lua_data)
        if ilevel_match:
            result["item_level"] = float(ilevel_match.group(1))

        # Integer fields
        int_patterns = [
            ("heroic_items", r'\["heroic_items"\]\s*=\s*(\d+)'),
            ("champion_items", r'\["champion_items"\]\s*=\s*(\d+)'),
            ("veteran_items", r'\["veteran_items"\]\s*=\s*(\d+)'),
            ("adventure_items", r'\["adventure_items"\]\s*=\s*(\d+)'),
            ("old_items", r'\["old_items"\]\s*=\s*(\d+)'),
            ("timewalk", r'\["timewalking_quest"\]\s*=\s*\{[^}]*\["progress"\]\s*=\s*(\d+)'),
        ]

        # Get delve count from vault (World activities)
        # vault_delves.count includes both delves AND world boss kills
        vault_delves_match = re.search(r'\["vault_delves"\]\s*=\s*\{[^}]*\["count"\]\s*=\s*(\d+)', lua_data)
        vault_delves_count = int(vault_delves_match.group(1)) if vault_delves_match else 0

        # Check if gundarz (world boss) was killed - if so, subtract 1 from vault count
        gundarz_match = re.search(r'\["gundarz"\]\s*=\s*(true|false)', lua_data)
        gundarz_done = gundarz_match and gundarz_match.group(1) == "true"

        # Actual delves = vault count minus world boss if applicable
        result["delves"] = max(0, vault_delves_count - (1 if gundarz_done else 0))

        # Gilded stash is a table with claimed field
        gilded_match = re.search(
            r'\["gilded_stash"\]\s*=\s*\{[^}]*\["claimed"\]\s*=\s*(\d+)', lua_data
        )
        if gilded_match:
            result["gilded_stash"] = int(gilded_match.group(1))

        for field, pattern in int_patterns:
            match = re.search(pattern, lua_data)
            if match:
                result[field] = int(match.group(1))

        bool_patterns = [
            ("vault_visited", r'\["vault_visited"\]\s*=\s*(true|false)'),
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

        # Week ID for staleness detection
        week_id_match = re.search(r'\["week_id"\]\s*=\s*"(\d+)"', lua_data)
        if week_id_match:
            result["week_id"] = week_id_match.group(1)

        return result

    def run(self):
        """Start the application."""
        self.window.show_all()

        # Show notification if weekly reset occurred
        if self._weekly_reset_occurred:
            GLib.idle_add(self._show_weekly_reset_notification)

        Gtk.main()

    def _show_weekly_reset_notification(self):
        """Show notification that weekly data was auto-reset."""
        show_info(
            self.window,
            "Weekly Reset",
            "A new WoW week has started. Weekly tracking data has been automatically reset.",
        )
        return False  # Don't repeat


# Import Gdk for window state constants
from gi.repository import Gdk


if __name__ == "__main__":
    app = WoWStatTracker()
    app.run()
