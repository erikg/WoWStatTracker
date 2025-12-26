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
import shutil
import sys
import threading
import time

from slpp import slpp as lua

from model import (
    Character,
    CharacterStore,
    Config,
    LockManager,
    get_config_dir,
    get_current_week_id,
    migrate_old_files,
    check_for_updates,
    __version__,
    THEME_AUTO,
    THEME_LIGHT,
    THEME_DARK,
    COL_VAULT_VISITED,
    COL_GEARING_UP,
    COL_QUESTS,
    WOW_DEFAULT_PATHS,
)

from view import (
    ThemeManager,
    CharacterTable,
    CharacterDialog,
    PropertiesDialog,
    ManualDialog,
    show_error,
    show_warning,
    show_info,
    show_folder_chooser,
    TOOLBAR_BOTH,
    TOOLBAR_ICONS,
    TOOLBAR_TEXT,
    TOOLBAR_HIDDEN,
)

from notification_model import (
    Notification,
    NotificationStore,
    NOTIFY_INFO,
    NOTIFY_SUCCESS,
    NOTIFY_WARNING,
)

from notification_view import (
    StatusBar,
    NotificationHistoryPopover,
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

        # Initialize notification store
        notifications_file = os.path.join(self.config_dir, "notifications.json")
        self.notification_store = NotificationStore(notifications_file)
        self.notification_store.load()

        self.debug_enabled = self.config.get("debug", False)

        # Check for weekly reset and auto-clear if needed
        self._weekly_reset_occurred = self._check_weekly_reset()

        # Timer and geometry tracking
        self._config_timer = None
        self._last_window_geometry = None
        self._last_import_time = 0  # For debouncing auto-import

        # Create main window
        self.window = Gtk.Window(title="WoW Character Stat Tracker")
        self.window.connect("destroy", self._on_destroy)
        self.window.connect("configure-event", self._on_window_configure)
        self.window.connect("window-state-event", self._on_window_state_event)
        self.window.connect("focus-in-event", self._on_focus_in)

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
        self.toolbar = self._create_toolbar()
        vbox.pack_start(self.toolbar, False, False, 0)
        self._apply_toolbar_style(self.config.get("toolbar_style", TOOLBAR_BOTH))

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

        # Create status bar at the bottom
        self.status_bar = StatusBar(on_history_clicked=self._on_history_clicked)
        vbox.pack_end(self.status_bar, False, False, 0)
        self._update_notification_badge()

    def _create_menu_bar(self) -> Gtk.MenuBar:
        """Create the application menu bar."""
        menubar = Gtk.MenuBar()

        # File menu
        file_menu_item = Gtk.MenuItem(label="File")
        file_menu = Gtk.Menu()
        file_menu_item.set_submenu(file_menu)
        menubar.append(file_menu_item)

        properties_item = Gtk.MenuItem(label="Properties")
        properties_item.connect("activate", self._on_properties)
        file_menu.append(properties_item)

        file_menu.append(Gtk.SeparatorMenuItem())

        quit_item = Gtk.MenuItem(label="Quit")
        quit_item.connect("activate", lambda w: self.window.close())
        file_menu.append(quit_item)

        # Characters menu
        chars_menu_item = Gtk.MenuItem(label="Characters")
        chars_menu = Gtk.Menu()
        chars_menu_item.set_submenu(chars_menu)
        menubar.append(chars_menu_item)

        add_item = Gtk.MenuItem(label="Add Character")
        add_item.connect("activate", self._on_add_character)
        chars_menu.append(add_item)

        chars_menu.append(Gtk.SeparatorMenuItem())

        reset_item = Gtk.MenuItem(label="Reset Weekly Data")
        reset_item.connect("activate", self._on_reset_weekly)
        chars_menu.append(reset_item)

        # Addon menu
        addon_menu_item = Gtk.MenuItem(label="Addon")
        addon_menu = Gtk.Menu()
        addon_menu_item.set_submenu(addon_menu)
        menubar.append(addon_menu_item)

        import_item = Gtk.MenuItem(label="Import from Addon")
        import_item.connect("activate", self._on_import_wow_addon)
        addon_menu.append(import_item)

        addon_menu.append(Gtk.SeparatorMenuItem())

        set_path_item = Gtk.MenuItem(label="Set WoW Location...")
        set_path_item.connect("activate", self._on_set_wow_path)
        addon_menu.append(set_path_item)

        install_addon_item = Gtk.MenuItem(label="Install Addon")
        install_addon_item.connect("activate", self._on_install_addon)
        addon_menu.append(install_addon_item)

        uninstall_addon_item = Gtk.MenuItem(label="Uninstall Addon")
        uninstall_addon_item.connect("activate", self._on_uninstall_addon)
        addon_menu.append(uninstall_addon_item)

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

        # Help menu
        help_menu_item = Gtk.MenuItem(label="Help")
        help_menu = Gtk.Menu()
        help_menu_item.set_submenu(help_menu)
        menubar.append(help_menu_item)

        manual_item = Gtk.MenuItem(label="Manual")
        manual_item.connect("activate", self._on_manual)
        help_menu.append(manual_item)

        check_updates_item = Gtk.MenuItem(label="Check for Updates...")
        check_updates_item.connect("activate", self._on_check_updates)
        help_menu.append(check_updates_item)

        help_menu.append(Gtk.SeparatorMenuItem())

        about_item = Gtk.MenuItem(label="About")
        about_item.connect("activate", self._on_about)
        help_menu.append(about_item)

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
        elif col_id == COL_GEARING_UP:
            character.gearing_up = new_value
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
            if hasattr(self, "table"):
                self.table.refresh_backgrounds()

    def _on_properties(self, widget):
        """Handle Properties menu item."""
        dialog = PropertiesDialog(self.window)
        result = dialog.show(
            wow_path=self.config.get("wow_path", ""),
            theme=self.config.get("theme", THEME_AUTO),
            toolbar_style=self.config.get("toolbar_style", TOOLBAR_BOTH),
            auto_import=self.config.get("auto_import", False),
            check_updates=self.config.get("check_updates", False),
            on_browse_path=self._on_invalid_wow_path,
        )

        if result:
            # Apply WoW path
            if result["wow_path"] != self.config.get("wow_path", ""):
                self.config.set("wow_path", result["wow_path"])

            # Apply theme
            if result["theme"] != self.config.get("theme", THEME_AUTO):
                self.theme_manager.set_preference(result["theme"])
                self.config.set("theme", result["theme"])
                if hasattr(self, "table"):
                    self.table.refresh_backgrounds()

            # Apply toolbar style
            if result["toolbar_style"] != self.config.get("toolbar_style", TOOLBAR_BOTH):
                self._apply_toolbar_style(result["toolbar_style"])
                self.config.set("toolbar_style", result["toolbar_style"])

            # Apply behavior settings
            self.config.set("auto_import", result["auto_import"])
            self.config.set("check_updates", result["check_updates"])

            self.config.save()

    def _on_invalid_wow_path(self, path):
        """Handle invalid WoW path selection in properties dialog."""
        show_warning(
            self.window,
            "Invalid Selection",
            "The selected folder must contain a '_retail_' directory.",
        )

    def _apply_toolbar_style(self, style: str):
        """Apply toolbar style setting."""
        if style == TOOLBAR_HIDDEN:
            self.toolbar.hide()
        else:
            self.toolbar.show()
            if style == TOOLBAR_BOTH:
                self.toolbar.set_style(Gtk.ToolbarStyle.BOTH)
            elif style == TOOLBAR_ICONS:
                self.toolbar.set_style(Gtk.ToolbarStyle.ICONS)
            elif style == TOOLBAR_TEXT:
                self.toolbar.set_style(Gtk.ToolbarStyle.TEXT)

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
                self.notify(f"WoW path set to: {path}", NOTIFY_SUCCESS)
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
            self.notify("Addon installed. Restart WoW to load.", NOTIFY_SUCCESS)
        except Exception as e:
            show_error(self.window, "Installation Failed", str(e))

    def _on_uninstall_addon(self, widget):
        """Uninstall WoW addon from WoW's AddOns folder."""
        wow_path = self.get_wow_path()
        if not wow_path:
            return

        addon_path = os.path.join(
            wow_path, "_retail_", "Interface", "AddOns", "WoWStatTracker_Addon"
        )

        if not os.path.exists(addon_path):
            show_warning(
                self.window,
                "Addon Not Installed",
                "The WoWStatTracker addon is not currently installed.",
            )
            return

        # Confirm uninstall
        dialog = Gtk.MessageDialog(
            parent=self.window,
            modal=True,
            message_type=Gtk.MessageType.WARNING,
            buttons=Gtk.ButtonsType.YES_NO,
            text="Uninstall WoWStatTracker Addon?",
        )
        dialog.format_secondary_text(
            "This will remove the addon from WoW.\n"
            "Your saved character data will not be affected."
        )
        response = dialog.run()
        dialog.destroy()

        if response != Gtk.ResponseType.YES:
            return

        try:
            shutil.rmtree(addon_path)
            self.notify("Addon uninstalled.", NOTIFY_SUCCESS)
        except Exception as e:
            show_error(self.window, "Uninstall Failed", str(e))

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

    def _on_focus_in(self, window, event):
        """Handle window focus gained - auto-import if enabled."""
        if not self.config.get("auto_import", False):
            return False

        # Debounce: don't import if we imported within the last 5 seconds
        now = time.time()
        if now - self._last_import_time < 5:
            return False

        self._last_import_time = now
        GLib.idle_add(self._auto_import_from_addon)
        return False

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
            print(
                f"[DEBUG] Weekly reset check: current={current_week}, last={last_week}"
            )

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
                print(
                    f"[DEBUG] Before save: {c.name} item_level={c.item_level} (type: {type(c.item_level).__name__})"
                )
        try:
            self.store.save()
            if self.debug_enabled:
                print(f"[DEBUG] Saved to {self.store.data_file}")
        except IOError as e:
            show_error(self.window, "Failed to save", str(e))
        self.table.populate(self.store.characters)

    # ==================== Import Methods ====================

    def update_from_wow_addon(self, widget, silent: bool = False):
        """Import character data from WoW Stat Tracker addon.

        Args:
            widget: The widget that triggered this (can be None)
            silent: If True, don't show notifications (used for auto-import)
        """
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
            addon_chars, addon_version = self.parse_wow_addon_data(addon_file)

            if not addon_chars:
                show_warning(
                    self.window,
                    "No data found",
                    "Could not parse character data from addon file.",
                )
                return

            # Check for version mismatch between addon and GUI
            if addon_version and addon_version != __version__:
                self._show_version_mismatch_warning(addon_version)

            # Update characters
            updated = 0
            added = 0
            stale_skipped = 0

            # Weekly fields to skip if data is from a different week
            weekly_fields = {
                "vault_visited",
                "delves",
                "gilded_stash",
                "gearing_up",
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
                    # Update existing - only count as updated if something changed
                    existing = self.store.characters[existing_idx]
                    changed = False
                    for key, value in addon_char.items():
                        # Skip week_id (internal tracking only)
                        if key == "week_id":
                            continue
                        # Skip weekly fields if data is stale
                        if not is_current_week and key in weekly_fields:
                            continue
                        if hasattr(existing, key) and value is not None:
                            old_value = getattr(existing, key)
                            if old_value != value:
                                setattr(existing, key, value)
                                changed = True
                    if changed:
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
                if not silent:
                    # Build concise message
                    if updated > 0 and added > 0:
                        char_word = "character" if updated + added == 1 else "characters"
                        msg = f"Updated {updated}, added {added} {char_word}."
                    elif updated > 0:
                        char_word = "character" if updated == 1 else "characters"
                        msg = f"Updated {updated} {char_word}."
                    else:
                        char_word = "character" if added == 1 else "characters"
                        msg = f"Added {added} {char_word}."
                    if stale_skipped > 0:
                        msg += f" ({stale_skipped} stale)"
                    self.notify(msg, NOTIFY_SUCCESS)
            elif not silent:
                self.notify("All characters up to date.", NOTIFY_INFO)

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
        """Parse WoW Stat Tracker addon SavedVariables file using slpp.

        Returns:
            tuple: (characters list, addon_version string or None)
        """
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                content = f.read()

            # Remove the "WoWStatTrackerDB = " prefix to get pure Lua table
            content = content.replace("WoWStatTrackerDB = ", "", 1)

            # Parse the Lua table
            data = lua.decode(content)
            if not data:
                return [], None

            # Extract addon version from metadata
            metadata = data.get("metadata", {})
            addon_version = metadata.get("version") if isinstance(metadata, dict) else None

            characters = []
            char_table = data.get("characters", {})

            for char_key, char_data in char_table.items():
                # char_key is "Name-Realm"
                if "-" not in char_key:
                    continue

                name, realm = char_key.rsplit("-", 1)

                # Build character dict with the fields we care about
                char = {
                    "name": name,
                    "realm": realm,
                    "guild": char_data.get("guild", ""),
                    "item_level": char_data.get("item_level", 0),
                    "heroic_items": char_data.get("heroic_items", 0),
                    "champion_items": char_data.get("champion_items", 0),
                    "veteran_items": char_data.get("veteran_items", 0),
                    "adventure_items": char_data.get("adventure_items", 0),
                    "old_items": char_data.get("old_items", 0),
                    "vault_visited": char_data.get("vault_visited", False),
                    "gearing_up": char_data.get("gearing_up", False),
                    "quests": char_data.get("quests", False),
                    "week_id": char_data.get("week_id", ""),
                }

                # Delves: vault_delves.count minus 1 if gearing_up was done
                vault_delves = char_data.get("vault_delves", {})
                delves_count = vault_delves.get("count", 0) if isinstance(vault_delves, dict) else 0
                char["delves"] = max(0, delves_count - (1 if char["gearing_up"] else 0))

                # Gilded stash
                gilded = char_data.get("gilded_stash", {})
                char["gilded_stash"] = gilded.get("claimed", 0) if isinstance(gilded, dict) else 0

                # Timewalking quest progress
                tw = char_data.get("timewalking_quest", {})
                char["timewalk"] = tw.get("progress", 0) if isinstance(tw, dict) else 0

                characters.append(char)

            return characters, addon_version

        except Exception as e:
            print(f"[VERBOSE] Error parsing addon data: {e}")
            return [], None

    # ==================== Notification System ====================

    def notify(self, message: str, notification_type: str = NOTIFY_INFO) -> None:
        """Show a notification and add to history."""
        notification = Notification.create(message, notification_type)
        self.notification_store.add(notification)
        self.notification_store.save()
        self.status_bar.show_notification(message, notification_type)
        self._update_notification_badge()

    def _on_history_clicked(self) -> None:
        """Handle history button click - show notification history popover."""
        popover = NotificationHistoryPopover(
            relative_to=self.status_bar.get_history_button(),
            on_clear_all=self._on_clear_all_notifications,
            on_remove=self._on_remove_notification,
        )
        popover.populate(self.notification_store.get_all())
        popover.popup()

    def _on_clear_all_notifications(self) -> None:
        """Clear all notification history."""
        self.notification_store.clear_all()
        self.notification_store.save()
        self._update_notification_badge()

    def _on_remove_notification(self, notification_id: str) -> None:
        """Remove a specific notification from history."""
        self.notification_store.remove(notification_id)
        self.notification_store.save()
        self._update_notification_badge()

    def _update_notification_badge(self) -> None:
        """Update the notification badge count on status bar."""
        count = self.notification_store.count()
        self.status_bar.update_badge(count)

    def _show_version_mismatch_warning(self, addon_version: str) -> None:
        """Show notification and dialog when addon and GUI versions don't match."""
        msg = f"Version mismatch: addon v{addon_version}, GUI v{__version__}"
        self.notify(msg, NOTIFY_WARNING)

        dialog = Gtk.MessageDialog(
            parent=self.window,
            modal=True,
            message_type=Gtk.MessageType.WARNING,
            buttons=Gtk.ButtonsType.OK,
            text="Addon Version Mismatch",
        )
        dialog.format_secondary_markup(
            f"The WoW addon version (<b>v{addon_version}</b>) does not match "
            f"the GUI version (<b>v{__version__}</b>).\n\n"
            "This may cause data import issues. Please update both components "
            "to the same version.\n\n"
            "You can reinstall the addon from:\n"
            "<b>Addon > Install Addon</b>"
        )
        dialog.run()
        dialog.destroy()

    # ==================== Update Check ====================

    def _on_check_updates(self, widget):
        """Handle Check for Updates menu item."""
        self._check_for_updates(show_no_update=True)

    def _check_for_updates(self, show_no_update: bool = False):
        """Check for updates and show notification if available."""
        result = check_for_updates()

        if result is None:
            if show_no_update:
                self.notify("Could not check for updates.", NOTIFY_WARNING)
            return

        if result["update_available"]:
            msg = f"Update available: v{result['latest_version']} (current: v{result['current_version']})"
            self.notify(msg, NOTIFY_INFO)
            # Show dialog with download link
            dialog = Gtk.MessageDialog(
                parent=self.window,
                modal=True,
                message_type=Gtk.MessageType.INFO,
                buttons=Gtk.ButtonsType.OK,
                text="Update Available",
            )
            dialog.format_secondary_markup(
                f"A new version is available: <b>v{result['latest_version']}</b>\n"
                f"Current version: v{result['current_version']}\n\n"
                f"Download from:\n{result['download_url']}"
            )
            dialog.run()
            dialog.destroy()
        elif show_no_update:
            self.notify(f"You're running the latest version (v{__version__}).", NOTIFY_SUCCESS)

    def _on_manual(self, widget):
        """Handle Manual menu item - show user manual dialog."""
        manual_path = self._find_manual_file()
        if manual_path and os.path.exists(manual_path):
            try:
                with open(manual_path, "r", encoding="utf-8") as f:
                    manual_text = f.read()
                dialog = ManualDialog(self.window)
                dialog.show(manual_text)
            except IOError:
                show_error(self.window, "Error", "Could not read manual file.")
        else:
            show_error(self.window, "Error", "Manual file not found.")

    def _find_manual_file(self) -> str | None:
        """Find the manual file (bundled or development)."""
        # Check if running from bundle (frozen)
        if getattr(sys, "frozen", False):
            # PyInstaller bundle - manual in Resources
            bundle_path = os.path.join(
                os.path.dirname(sys.executable),
                "..",
                "Resources",
                "MANUAL.txt",
            )
            if os.path.exists(bundle_path):
                return os.path.realpath(bundle_path)

        # Development mode - manual in project root
        dev_path = os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            "MANUAL.txt",
        )
        if os.path.exists(dev_path):
            return dev_path

        # Also check same directory as script
        script_path = os.path.join(
            os.path.dirname(os.path.abspath(__file__)),
            "MANUAL.txt",
        )
        if os.path.exists(script_path):
            return script_path

        return None

    def _on_about(self, widget):
        """Handle About menu item."""
        dialog = Gtk.AboutDialog(parent=self.window)
        dialog.set_program_name("WoW Stat Tracker")
        dialog.set_version(f"v{__version__}")
        dialog.set_comments("Track World of Warcraft character statistics and weekly progress.")
        dialog.set_website("https://github.com/erikg/WoWStatTracker")
        dialog.set_website_label("GitHub Repository")
        dialog.set_license_type(Gtk.License.BSD_3)
        dialog.run()
        dialog.destroy()

    def run(self):
        """Start the application."""
        self.window.show_all()

        # Re-apply toolbar style after show_all (needed for hidden state)
        toolbar_style = self.config.get("toolbar_style", TOOLBAR_BOTH)
        if toolbar_style == TOOLBAR_HIDDEN:
            self.toolbar.hide()

        # Show notification if weekly reset occurred
        if self._weekly_reset_occurred:
            GLib.idle_add(self._show_weekly_reset_notification)

        # Check for updates on startup if enabled
        if self.config.get("check_updates", False):
            GLib.idle_add(self._check_for_updates)

        Gtk.main()

    def _auto_import_from_addon(self):
        """Auto-import from addon when window gains focus."""
        try:
            addon_file = self.find_wow_addon_data()
            if addon_file:
                self.update_from_wow_addon(None, silent=True)
        except Exception:
            pass  # Silently fail on auto-import
        return False  # Don't repeat

    def _show_weekly_reset_notification(self):
        """Show notification that weekly data was auto-reset."""
        self.notify("Weekly data auto-reset for new WoW week.", NOTIFY_INFO)
        return False  # Don't repeat


# Import Gdk for window state constants
from gi.repository import Gdk


if __name__ == "__main__":
    app = WoWStatTracker()
    app.run()
