#!/usr/bin/env python3
import gi

gi.require_version("Gtk", "3.0")
from gi.repository import Gtk, Gdk, Gio
import json
import os
import platform
import subprocess


class WoWStatTracker:
    # Column index constants to avoid magic numbers
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
    COL_GUNDARZ = 11
    COL_QUESTS = 12
    COL_TIMEWALK = 13
    COL_NOTES = 14
    COL_INDEX = 15  # Hidden column with original character index
    COL_COUNT = 16  # Total number of columns

    # Maximum values for validation
    MAX_ITEM_LEVEL = 1000
    MAX_ITEMS_PER_CATEGORY = 50  # Max items per gear category
    MAX_DELVES = 8  # Max weekly delves
    MAX_TIMEWALK = 5  # Max weekly timewalking dungeons

    # Theme constants
    THEME_AUTO = "auto"
    THEME_LIGHT = "light"
    THEME_DARK = "dark"

    def __init__(self):
        # Set up config directory
        self.config_dir = os.path.join(os.path.expanduser("~"), ".config", "wowstat")
        os.makedirs(self.config_dir, exist_ok=True)

        self.data_file = os.path.join(self.config_dir, "wowstat_data.json")
        self.config_file = os.path.join(self.config_dir, "wowstat_config.json")
        self.lock_file = os.path.join(self.config_dir, "wowstat.lock")
        self._config_timer = None  # Initialize timer reference
        self._last_window_geometry = None  # Track last known window geometry

        # Migrate old files from current directory to config directory
        self._migrate_old_files()

        # Check for another instance running
        if not self.acquire_lock():
            import sys

            print("Another instance is already running!")
            sys.exit(1)

        self.characters = self.load_data()
        self.config = self.load_config()
        self.debug_enabled = self.config.get("debug", False)

        # Initialize theme system
        self.setup_theme_system()

        self.window = Gtk.Window(title="WoW Character Stat Tracker")
        self.window.connect("destroy", self.on_destroy)
        self.window.connect("configure-event", self.on_window_configure)
        self.window.connect("window-state-event", self.on_window_state_event)
        self.restore_window_state()

        self.setup_ui()
        self.populate_table()
        self.restore_column_widths()
        self.restore_sort_order()

    def load_data(self):
        if os.path.exists(self.data_file):
            try:
                with open(self.data_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    # Ensure all characters have required fields with defaults
                    for char in data:
                        char.setdefault("guild", "")
                        char.setdefault("vault_visited", False)
                        char.setdefault("delves", 0)
                        char.setdefault("gundarz", False)
                        char.setdefault("quests", False)
                        char.setdefault("timewalk", 0)
                    return data
            except (json.JSONDecodeError, IOError, UnicodeDecodeError) as e:
                print(f"Warning: Failed to load data file: {e}")
                return []
        return []

    def save_data(self):
        try:
            # Atomic write with temporary file for safety
            temp_file = self.data_file + ".tmp"
            with open(temp_file, "w", encoding="utf-8") as f:
                json.dump(self.characters, f, indent=2)
            # Only replace original if write succeeded
            import shutil

            shutil.move(temp_file, self.data_file)
        except (IOError, OSError, UnicodeEncodeError) as e:
            # Show error dialog instead of silent failure
            if hasattr(self, "window"):
                error_dialog = Gtk.MessageDialog(
                    parent=self.window,
                    modal=True,
                    message_type=Gtk.MessageType.ERROR,
                    buttons=Gtk.ButtonsType.OK,
                    text="Failed to save character data",
                )
                error_dialog.format_secondary_text(f"Error: {str(e)}")
                error_dialog.run()
                error_dialog.destroy()

    def load_config(self):
        if os.path.exists(self.config_file):
            try:
                with open(self.config_file, "r", encoding="utf-8") as f:
                    return json.load(f)
            except (json.JSONDecodeError, IOError, UnicodeDecodeError) as e:
                print(f"Warning: Failed to load config file: {e}")
                return {}
        return {}

    def save_config(self):
        try:
            # Atomic write with temporary file for safety
            temp_file = self.config_file + ".tmp"
            with open(temp_file, "w", encoding="utf-8") as f:
                json.dump(self.config, f, indent=2)
            import shutil

            shutil.move(temp_file, self.config_file)
        except (IOError, OSError, UnicodeEncodeError) as e:
            # Don't show error dialog for config - less critical
            print(f"Warning: Failed to save config: {e}")

    def _migrate_old_files(self):
        """Migrate old config/data files from current directory to ~/.config/wowstat/"""
        import shutil

        old_files = [
            ("wowstat_data.json", self.data_file),
            ("wowstat_config.json", self.config_file),
        ]

        for old_name, new_path in old_files:
            old_path = os.path.join(os.path.dirname(__file__), old_name)
            if not os.path.isabs(old_path):
                old_path = os.path.abspath(old_name)

            # Only migrate if old file exists and new file doesn't
            if os.path.exists(old_path) and not os.path.exists(new_path):
                try:
                    shutil.move(old_path, new_path)
                    print(f"Migrated {old_name} to {new_path}")
                except (IOError, OSError) as e:
                    print(f"Warning: Failed to migrate {old_name}: {e}")

    def detect_system_theme(self):
        """Detect if system prefers dark mode"""
        system = platform.system().lower()

        try:
            if system == "darwin":  # macOS
                result = subprocess.run(
                    ["defaults", "read", "-g", "AppleInterfaceStyle"],
                    capture_output=True,
                    text=True,
                    timeout=5,
                )
                return result.returncode == 0 and "dark" in result.stdout.lower()

            elif system == "linux":
                # Try GNOME/GTK settings first
                try:
                    result = subprocess.run(
                        [
                            "gsettings",
                            "get",
                            "org.gnome.desktop.interface",
                            "gtk-theme",
                        ],
                        capture_output=True,
                        text=True,
                        timeout=5,
                    )
                    if result.returncode == 0:
                        theme = result.stdout.strip().strip("'\"").lower()
                        return "dark" in theme
                except:
                    pass

                # Fall back to checking environment variables
                current_theme = os.environ.get("GTK_THEME", "").lower()
                return "dark" in current_theme

            elif system == "windows":
                # Windows 10/11 theme detection
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
                except:
                    pass

        except (subprocess.TimeoutExpired, subprocess.SubprocessError, OSError):
            pass

        # Default to light theme if detection fails
        return False

    def setup_theme_system(self):
        """Initialize the theme system"""
        self.current_theme_preference = self.config.get("theme", self.THEME_AUTO)
        self.apply_theme()

    def apply_theme(self):
        """Apply the current theme to the application"""
        # Determine actual theme to use
        if self.current_theme_preference == self.THEME_AUTO:
            use_dark = self.detect_system_theme()
        elif self.current_theme_preference == self.THEME_DARK:
            use_dark = True
        else:  # THEME_LIGHT
            use_dark = False

        # Apply GTK theme
        settings = Gtk.Settings.get_default()
        if settings:
            # Set the theme preference - GTK will handle the dark variant automatically
            settings.set_property("gtk-application-prefer-dark-theme", use_dark)
            settings.set_property("gtk-theme-name", "Adwaita")

        # Apply custom CSS for better dark mode support
        self.apply_custom_css(use_dark)

    def apply_custom_css(self, use_dark):
        """Apply custom CSS styling for better theme support"""
        css_provider = Gtk.CssProvider()

        if use_dark:
            css_data = """
            window {
                background-color: #2d2d2d;
                color: #ffffff;
            }
            
            treeview {
                background-color: #3c3c3c;
                color: #ffffff;
            }
            
            treeview:selected {
                background-color: #4a90d9;
                color: #ffffff;
            }
            
            
            treeview header button {
                background-color: #404040;
                color: #ffffff;
                border-color: #555555;
            }
            
            entry {
                background-color: #404040;
                color: #ffffff;
                border-color: #555555;
            }
            
            button {
                background-color: #404040;
                color: #ffffff;
                border-color: #555555;
            }
            
            button:hover {
                background-color: #505050;
            }
            
            combobox {
                background-color: #404040;
                color: #ffffff;
            }
            
            dialog {
                background-color: #2d2d2d;
                color: #ffffff;
            }
            """
        else:
            css_data = """
            window {
                background-color: #ffffff;
                color: #000000;
            }
            
            treeview {
                background-color: #ffffff;
                color: #000000;
            }
            
            treeview:selected {
                background-color: #4a90d9;
                color: #ffffff;
            }
            """

        try:
            css_provider.load_from_data(css_data.encode("utf-8"))
            # Use the window's display to get screen for modern GTK
            if hasattr(self, "window") and self.window:
                display = self.window.get_display()
                if display:
                    screen = display.get_default_screen()
                    if screen:
                        Gtk.StyleContext.add_provider_for_screen(
                            screen,
                            css_provider,
                            Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION,
                        )
        except Exception as e:
            if self.debug_enabled:
                print(f"[DEBUG] Failed to apply CSS: {e}")

    def set_theme(self, theme_preference):
        """Set the theme preference and apply it"""
        self.current_theme_preference = theme_preference
        self.config["theme"] = theme_preference
        self.apply_theme()
        self.save_config()

    def restore_window_state(self):
        window_config = self.config.get("window", {})
        width = max(
            400, min(2000, window_config.get("width", 1200))
        )  # Reasonable bounds
        height = max(300, min(1500, window_config.get("height", 600)))
        x = window_config.get("x")
        y = window_config.get("y")
        is_maximized = window_config.get("maximized", False)

        if self.debug_enabled:
            print(
                f"[DEBUG] Restoring window: {width}x{height} at ({x},{y}) maximized={is_maximized}"
            )

        self.window.set_default_size(width, height)

        # Restore maximized state first
        if is_maximized:
            # Use idle_add for better macOS compatibility
            from gi.repository import GLib

            GLib.idle_add(self._delayed_maximize_window)
        elif x is not None and y is not None:
            # macOS-compatible window positioning for non-maximized windows
            # Try to get screen dimensions
            screen_width = 1920  # Default fallback
            screen_height = 1080

            try:
                # First try modern GTK API
                display = self.window.get_display()
                if display:
                    monitor = display.get_primary_monitor()
                    if monitor:
                        geometry = monitor.get_geometry()
                        screen_width = geometry.width
                        screen_height = geometry.height
                        if self.debug_enabled:
                            print(
                                f"[DEBUG] Screen dimensions: {screen_width}x{screen_height}"
                            )
            except AttributeError:
                # Fallback for older GTK or macOS issues
                try:
                    screen = self.window.get_screen()
                    if screen:
                        screen_width = screen.get_width()
                        screen_height = screen.get_height()
                        if self.debug_enabled:
                            print(
                                f"[DEBUG] Screen dimensions (fallback): {screen_width}x{screen_height}"
                            )
                except:
                    if self.debug_enabled:
                        print(f"[DEBUG] Using default screen dimensions")
                    pass  # Use defaults

            # Ensure at least 100px of window is visible
            x = max(0, min(screen_width - 100, x))
            y = max(0, min(screen_height - 100, y))

            # Use idle_add to delay positioning for better macOS compatibility
            from gi.repository import GLib

            GLib.idle_add(self._delayed_window_position, x, y)

    def _delayed_window_position(self, x, y):
        """Delayed window positioning for better macOS compatibility"""
        try:
            self.window.move(x, y)
            if self.debug_enabled:
                print(f"[DEBUG] Window positioned at ({x}, {y})")
        except Exception as e:
            if self.debug_enabled:
                print(f"[DEBUG] Failed to restore window position: {e}")
        return False  # Don't repeat

    def _delayed_maximize_window(self):
        """Delayed window maximizing for better macOS compatibility"""
        try:
            self.window.maximize()
            if self.debug_enabled:
                print(f"[DEBUG] Window maximized")
        except Exception as e:
            if self.debug_enabled:
                print(f"[DEBUG] Failed to maximize window: {e}")
        return False  # Don't repeat

    def on_window_configure(self, window, event):
        # Immediately cache the geometry (don't debounce this part)
        self._last_window_geometry = {
            "width": max(400, min(3840, event.width)),
            "height": max(300, min(2160, event.height)),
            "x": max(0, event.x),
            "y": max(0, event.y),
        }

        # Debounce the file write to prevent excessive disk I/O
        if self._config_timer is not None:
            self._config_timer.cancel()
            self._config_timer = None

        import threading

        def save_window_config():
            try:
                if not self.config.get("window"):
                    self.config["window"] = {}

                self.config["window"].update(self._last_window_geometry)
                self.save_config()
            finally:
                self._config_timer = None

        self._config_timer = threading.Timer(0.5, save_window_config)  # 500ms delay
        self._config_timer.daemon = True  # Dies with main thread
        self._config_timer.start()
        return False

    def on_window_state_event(self, window, event):
        """Handle window state changes (maximize, minimize, etc.)"""
        try:
            if not self.config.get("window"):
                self.config["window"] = {}

            # Save maximized state
            is_maximized = bool(event.new_window_state & Gdk.WindowState.MAXIMIZED)
            self.config["window"]["maximized"] = is_maximized

            if self.debug_enabled:
                print(f"[DEBUG] Window state changed - maximized: {is_maximized}")

            self.save_config()
        except Exception as e:
            if self.debug_enabled:
                print(f"[DEBUG] Error handling window state event: {e}")
        return False

    def save_column_widths(self):
        if not self.config.get("columns"):
            self.config["columns"] = {}

        for i, column in enumerate(self.treeview.get_columns()):
            self.config["columns"][str(i)] = column.get_width()

    def restore_column_widths(self):
        columns_config = self.config.get("columns", {})
        for i, column in enumerate(self.treeview.get_columns()):
            width = columns_config.get(str(i))
            if width and isinstance(width, (int, float)):
                # Validate width is reasonable (between 50 and 500 pixels)
                width = max(50, min(500, int(width)))
                column.set_fixed_width(width)

    def save_sort_order(self):
        sort_column_id, sort_order = self.store.get_sort_column_id()
        if sort_column_id is not None:
            if not self.config.get("sort"):
                self.config["sort"] = {}
            self.config["sort"]["column_id"] = sort_column_id
            self.config["sort"]["order"] = int(sort_order)  # Convert enum to int

    def restore_sort_order(self):
        sort_config = self.config.get("sort", {})
        if "column_id" in sort_config and "order" in sort_config:
            try:
                column_id = int(sort_config["column_id"])
                order_int = int(sort_config["order"])

                # Validate column_id is within valid range
                if 0 <= column_id < self.COL_COUNT - 1 and order_int in [
                    0,
                    1,
                ]:  # GTK sort types, exclude hidden column
                    sort_order = Gtk.SortType(order_int)
                    self.store.set_sort_column_id(column_id, sort_order)
            except (ValueError, TypeError) as e:
                print(f"Warning: Invalid sort config, using defaults: {e}")

    def setup_ui(self):
        vbox = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)
        self.window.add(vbox)

        # Create menu bar
        menubar = Gtk.MenuBar()
        vbox.pack_start(menubar, False, False, 0)

        # File menu
        file_menu_item = Gtk.MenuItem(label="File")
        file_menu = Gtk.Menu()
        file_menu_item.set_submenu(file_menu)
        menubar.append(file_menu_item)

        add_item = Gtk.MenuItem(label="Add Character")
        add_item.connect("activate", self.add_character)
        file_menu.append(add_item)

        file_menu.append(Gtk.SeparatorMenuItem())

        reset_item = Gtk.MenuItem(label="Reset Weekly Data")
        reset_item.connect("activate", self.reset_weekly_data)
        file_menu.append(reset_item)

        file_menu.append(Gtk.SeparatorMenuItem())

        altoholic_item = Gtk.MenuItem(label="Import from Altoholic")
        altoholic_item.connect("activate", self.update_from_altoholic)
        file_menu.append(altoholic_item)

        addon_item = Gtk.MenuItem(label="Import from WoW Addon")
        addon_item.connect("activate", self.update_from_wow_addon)
        file_menu.append(addon_item)

        file_menu.append(Gtk.SeparatorMenuItem())

        quit_item = Gtk.MenuItem(label="Quit")
        quit_item.connect("activate", self.on_quit_clicked)
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
        self.theme_group = None

        auto_theme_item = Gtk.RadioMenuItem(
            group=self.theme_group, label="Auto (System)"
        )
        auto_theme_item.connect(
            "activate", self.on_theme_menu_activate, self.THEME_AUTO
        )
        if self.current_theme_preference == self.THEME_AUTO:
            auto_theme_item.set_active(True)
        theme_submenu.append(auto_theme_item)
        self.theme_group = auto_theme_item

        light_theme_item = Gtk.RadioMenuItem(group=self.theme_group, label="Light")
        light_theme_item.connect(
            "activate", self.on_theme_menu_activate, self.THEME_LIGHT
        )
        if self.current_theme_preference == self.THEME_LIGHT:
            light_theme_item.set_active(True)
        theme_submenu.append(light_theme_item)

        dark_theme_item = Gtk.RadioMenuItem(group=self.theme_group, label="Dark")
        dark_theme_item.connect(
            "activate", self.on_theme_menu_activate, self.THEME_DARK
        )
        if self.current_theme_preference == self.THEME_DARK:
            dark_theme_item.set_active(True)
        theme_submenu.append(dark_theme_item)

        # Content area with margins
        content_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10)
        content_box.set_margin_start(10)
        content_box.set_margin_end(10)
        content_box.set_margin_top(10)
        content_box.set_margin_bottom(10)
        vbox.pack_start(content_box, True, True, 0)

        scrolled = Gtk.ScrolledWindow()
        scrolled.set_policy(Gtk.PolicyType.AUTOMATIC, Gtk.PolicyType.AUTOMATIC)
        content_box.pack_start(scrolled, True, True, 0)

        self.store = Gtk.ListStore(
            str,
            str,
            str,
            int,
            int,
            int,
            int,
            int,
            int,
            bool,
            int,
            bool,
            bool,
            int,
            str,
            int,
        )

        self.treeview = Gtk.TreeView(model=self.store)
        scrolled.add(self.treeview)

        columns = [
            ("Realm", str, 0),
            ("Name", str, 1),
            ("Guild", str, 2),
            ("Item Level", int, 3),
            ("Heroic Items", int, 4),
            ("Champion Items", int, 5),
            ("Veteran Items", int, 6),
            ("Adventure Items", int, 7),
            ("Old Items", int, 8),
            ("Vault Visited", bool, 9),
            ("Delves", int, 10),
            ("Gundarz", bool, 11),
            ("Quests", bool, 12),
            ("Timewalk", int, 13),
            ("Notes", str, 14),
            ("Index", int, 15),  # Hidden column for original character index
        ]

        for i, (title, data_type, col_id) in enumerate(columns):
            if data_type == bool and col_id in [
                9,
                11,
                12,
            ]:  # vault_visited, gundarz, quests (toggleable booleans)
                renderer = Gtk.CellRendererToggle()
                renderer.set_property("activatable", True)
                renderer.connect("toggled", self.on_boolean_toggled, col_id)
                column = Gtk.TreeViewColumn(title, renderer, active=col_id)
            else:
                renderer = Gtk.CellRendererText()
                if col_id == 14:  # Notes column - make it editable
                    renderer.set_property("editable", True)
                    renderer.connect("edited", self.on_notes_edited, col_id)
                column = Gtk.TreeViewColumn(title, renderer, text=col_id)

                # Apply cell data function for weekly columns with background coloring
                if col_id in [
                    8,
                    9,
                    10,
                    11,
                    12,
                    13,
                ]:  # vault_visited, delves, gundarz, quests, timewalk
                    column.set_cell_data_func(renderer, self.cell_data_func, col_id)
                elif col_id == 15:  # Hide the index column
                    column.set_visible(False)

            column.set_sort_column_id(col_id)
            column.set_clickable(True)
            column.set_resizable(True)
            self.treeview.append_column(column)

        self.treeview.connect("row-activated", self.on_row_activated)

    def cell_data_func(self, column, cell, model, iter, col_id):
        value = model[iter][col_id]

        delves = model[iter][10]
        gundarz = model[iter][11]
        quests = model[iter][12]
        timewalk = model[iter][13]
        vault_visited = model[iter][9]

        # Determine if we're in dark mode
        use_dark = False
        if self.current_theme_preference == self.THEME_AUTO:
            use_dark = self.detect_system_theme()
        elif self.current_theme_preference == self.THEME_DARK:
            use_dark = True

        # Set text color based on theme and background color
        def set_cell_colors(bg_color):
            cell.set_property("background", bg_color)
            if use_dark:
                # In dark mode, use black text on light colored backgrounds for readability
                if bg_color in [
                    "#90EE90",
                    "#FFFFE0",
                    "#F08080",
                ]:  # Light green, yellow, light red
                    cell.set_property("foreground", "#000000")
                else:
                    cell.set_property("foreground", "#ffffff")
            else:
                # In light mode, use default text color
                cell.set_property("foreground", None)

        if col_id == 9:  # vault_visited
            if vault_visited:
                set_cell_colors("#90EE90")
            else:
                set_cell_colors("#F08080")
        elif col_id == 10:  # delves
            if delves >= 8:
                set_cell_colors("#8080F0")
            elif delves >= 4:
                set_cell_colors("#90EE90")
            elif delves >= 2:
                set_cell_colors("#FFFFE0")
            else:
                set_cell_colors("#F08080")
        elif col_id == 11:  # gundarz
            if gundarz:
                set_cell_colors("#90EE90")
            else:
                set_cell_colors("#F08080")
        elif col_id == 12:  # quests
            if quests:
                set_cell_colors("#90EE90")
            else:
                set_cell_colors("#F08080")
        elif col_id == 13:  # timewalk
            if not self.all_timewalk_zero():
                if timewalk >= 5:
                    set_cell_colors("#90EE90")
                elif 1 <= timewalk <= 4:
                    set_cell_colors("#FFFFE0")
                else:
                    set_cell_colors("#F08080")
        else:
            # For non-colored columns, set appropriate text color for dark mode
            if use_dark:
                cell.set_property("foreground", "#ffffff")
                cell.set_property("background", None)
            else:
                cell.set_property("foreground", None)
                cell.set_property("background", None)

        if isinstance(value, bool):
            cell.set_property("text", "Yes" if value else "No")
        else:
            cell.set_property("text", str(value))

    def get_existing_realms(self):
        realms = set()
        for char in self.characters:
            realm = char.get("realm", "").strip()
            if realm:
                realms.add(realm)
        return sorted(list(realms))

    def all_timewalk_zero(self):
        # Handle empty character list edge case
        if not self.characters:
            return True  # If no characters, consider all timewalk as zero
        return all(char.get("timewalk", 0) == 0 for char in self.characters)

    def populate_table(self):
        self.store.clear()

        for i, char in enumerate(self.characters):
            self.store.append(
                [
                    char.get("realm", ""),
                    char.get("name", ""),
                    char.get("guild", ""),
                    char.get("item_level", 0),
                    char.get("heroic_items", 0),
                    char.get("champion_items", 0),
                    char.get("veteran_items", 0),
                    char.get("adventure_items", 0),
                    char.get("old_items", 0),
                    char.get("vault_visited", False),
                    char.get("delves", 0),
                    char.get("gundarz", False),
                    char.get("quests", False),
                    char.get("timewalk", 0),
                    char.get("notes", ""),
                    i,  # Store the original character index
                ]
            )

    def add_character(self, widget):
        self.edit_character_dialog()

    def on_row_activated(self, treeview, path, column):
        model = treeview.get_model()
        iter = model.get_iter(path)
        char_index = model[iter][self.COL_INDEX]  # Get the original character index

        # Validate char_index
        if char_index >= len(self.characters) or char_index < 0:
            print(f"Warning: Invalid character index {char_index}")
            return

        self.edit_character_dialog(char_index)

    def on_boolean_toggled(self, renderer, path, col_id):
        model = self.treeview.get_model()
        iter = model.get_iter(path)
        char_index = model[iter][self.COL_INDEX]  # Get the original character index

        # Validate char_index
        if char_index >= len(self.characters) or char_index < 0:
            print(f"Warning: Invalid character index {char_index}")
            return

        # Toggle the boolean value in both the model and character data
        current_value = model[iter][col_id]
        new_value = not current_value
        model[iter][col_id] = new_value

        # Update the character data
        field_map = {9: "vault_visited", 11: "gundarz", 12: "quests"}
        if col_id in field_map:
            self.characters[char_index][field_map[col_id]] = new_value
            self.save_data()

            # Update just this row's background instead of rebuilding entire table
            self.update_row_background(iter, self.characters[char_index])

    def on_notes_edited(self, renderer, path, new_text, col_id):
        model = self.treeview.get_model()
        iter = model.get_iter(path)
        char_index = model[iter][self.COL_INDEX]  # Get the original character index

        # Validate char_index
        if char_index >= len(self.characters) or char_index < 0:
            print(f"Warning: Invalid character index {char_index}")
            return

        # Update the model and character data
        model[iter][col_id] = new_text
        self.characters[char_index]["notes"] = new_text
        self.save_data()

    def update_row_background(self, iter, char_data):
        """Update background colors for a single row without rebuilding table"""
        # Trigger a redraw of the specific row by updating its data
        # This is more efficient than rebuilding the entire table
        try:
            model = self.treeview.get_model()
            if iter and model.iter_is_valid(iter):
                # Update the row data to trigger cell_data_func callbacks
                for col_id in [
                    self.COL_VAULT_VISITED,
                    self.COL_DELVES,
                    self.COL_GUNDARZ,
                    self.COL_QUESTS,
                    self.COL_TIMEWALK,
                ]:
                    # Force refresh by setting the same value (triggers cell_data_func)
                    current_value = model[iter][col_id]
                    model[iter][col_id] = current_value
        except Exception as e:
            print(f"Warning: Failed to update row background: {e}")
            # Fallback to full table refresh if row update fails
            self.populate_table()

    def edit_character_dialog(self, char_index=None):
        dialog = Gtk.Dialog(
            title="Edit Character" if char_index is not None else "Add Character",
            parent=self.window,
            modal=True,
        )
        dialog.set_default_size(400, 500)

        dialog.add_button("Cancel", Gtk.ResponseType.CANCEL)
        dialog.add_button("Save", Gtk.ResponseType.OK)
        if char_index is not None:
            dialog.add_button("Delete", Gtk.ResponseType.REJECT)

        content_area = dialog.get_content_area()
        content_area.set_spacing(10)
        content_area.set_margin_start(20)
        content_area.set_margin_end(20)
        content_area.set_margin_top(10)
        content_area.set_margin_bottom(10)

        char_data = self.characters[char_index] if char_index is not None else {}

        fields = {}

        grid = Gtk.Grid()
        grid.set_column_spacing(10)
        grid.set_row_spacing(5)
        content_area.add(grid)

        field_configs = [
            ("Realm", "realm", str, ""),
            ("Name", "name", str, ""),
            ("Guild", "guild", str, ""),
            ("Item Level", "item_level", int, 0),
            ("Heroic Items", "heroic_items", int, 0),
            ("Champion Items", "champion_items", int, 0),
            ("Veteran Items", "veteran_items", int, 0),
            ("Adventure Items", "adventure_items", int, 0),
            ("Old Items", "old_items", int, 0),
            ("Vault Visited", "vault_visited", bool, False),
            ("Delves Completed", "delves", int, 0),
            ("Gundarz", "gundarz", bool, False),
            ("Quests", "quests", bool, False),
            ("Timewalk", "timewalk", int, 0),
            ("Notes", "notes", str, ""),
        ]

        for i, (label_text, field_name, field_type, default_value) in enumerate(
            field_configs
        ):
            label = Gtk.Label(label=label_text + ":")
            label.set_halign(Gtk.Align.START)
            grid.attach(label, 0, i, 1, 1)

            if field_type == bool:
                widget = Gtk.CheckButton()
                widget.set_active(char_data.get(field_name, default_value))
                fields[field_name] = widget
            elif field_name == "realm":
                existing_realms = self.get_existing_realms()
                widget = Gtk.ComboBoxText.new_with_entry()

                for realm in existing_realms:
                    widget.append_text(realm)

                entry = widget.get_child()
                entry.set_text(str(char_data.get(field_name, default_value)))
                fields[field_name] = widget
            elif field_type == int:
                # Set reasonable upper limits using constants
                if field_name == "item_level":
                    upper_limit = self.MAX_ITEM_LEVEL
                elif field_name in [
                    "heroic_items",
                    "champion_items",
                    "veteran_items",
                    "adventure_items",
                    "old_items",
                ]:
                    upper_limit = self.MAX_ITEMS_PER_CATEGORY
                elif field_name == "delves":
                    upper_limit = self.MAX_DELVES
                elif field_name == "timewalk":
                    upper_limit = self.MAX_TIMEWALK
                else:
                    upper_limit = 999

                adjustment = Gtk.Adjustment(
                    value=char_data.get(field_name, default_value),
                    lower=0,
                    upper=upper_limit,
                    step_increment=1,
                    page_increment=10,
                )
                widget = Gtk.SpinButton()
                widget.set_adjustment(adjustment)
                widget.set_numeric(True)
                fields[field_name] = widget
            else:
                widget = Gtk.Entry()
                widget.set_text(str(char_data.get(field_name, default_value)))
                fields[field_name] = widget

            grid.attach(widget, 1, i, 1, 1)

        dialog.show_all()

        while True:
            response = dialog.run()

            if response == Gtk.ResponseType.OK:
                try:
                    new_char = {}
                    for field_name, widget in fields.items():
                        if isinstance(widget, Gtk.CheckButton):
                            new_char[field_name] = widget.get_active()
                        elif isinstance(widget, Gtk.ComboBoxText):
                            entry = widget.get_child()
                            text = entry.get_text()
                            new_char[field_name] = text
                        elif isinstance(widget, Gtk.SpinButton):
                            value = int(widget.get_value())
                            # Validate reasonable ranges using constants
                            if field_name == "item_level":
                                value = max(0, min(self.MAX_ITEM_LEVEL, value))
                            elif field_name in [
                                "heroic_items",
                                "champion_items",
                                "veteran_items",
                                "adventure_items",
                                "old_items",
                            ]:
                                value = max(0, min(self.MAX_ITEMS_PER_CATEGORY, value))
                            elif field_name == "delves":
                                value = max(0, min(self.MAX_DELVES, value))
                            elif field_name == "timewalk":
                                value = max(0, min(self.MAX_TIMEWALK, value))
                            new_char[field_name] = value
                        else:
                            text = widget.get_text().strip()
                            # Validate text fields
                            if field_name in ["name", "realm", "guild"]:
                                if len(text) > 50:  # Reasonable name length limit
                                    text = text[:50]
                                if field_name in ["name", "realm"] and not text:
                                    raise ValueError(
                                        f"{field_name.title()} cannot be empty"
                                    )
                            new_char[field_name] = text

                    if char_index is not None:
                        self.characters[char_index] = new_char
                    else:
                        self.characters.append(new_char)

                    self.save_data()
                    self.populate_table()
                    dialog.destroy()
                    break

                except (ValueError, TypeError, OverflowError) as e:
                    error_dialog = Gtk.MessageDialog(
                        parent=dialog,
                        modal=True,
                        message_type=Gtk.MessageType.ERROR,
                        buttons=Gtk.ButtonsType.OK,
                        text="Invalid input data",
                    )
                    error_dialog.format_secondary_text(f"Error: {str(e)}")
                    error_dialog.run()
                    error_dialog.destroy()
                except UnicodeError as e:
                    error_dialog = Gtk.MessageDialog(
                        parent=dialog,
                        modal=True,
                        message_type=Gtk.MessageType.ERROR,
                        buttons=Gtk.ButtonsType.OK,
                        text="Text encoding error",
                    )
                    error_dialog.format_secondary_text(f"Error: {str(e)}")
                    error_dialog.run()
                    error_dialog.destroy()

            elif response == Gtk.ResponseType.REJECT and char_index is not None:
                # Show confirmation dialog before deleting
                char_name = char_data.get("name", "Unknown")
                char_realm = char_data.get("realm", "Unknown")
                confirm_dialog = Gtk.MessageDialog(
                    parent=dialog,
                    modal=True,
                    message_type=Gtk.MessageType.WARNING,
                    buttons=Gtk.ButtonsType.YES_NO,
                    text=f"Delete {char_name} - {char_realm}?",
                )
                confirm_dialog.format_secondary_text("This action cannot be undone.")
                confirm_response = confirm_dialog.run()
                confirm_dialog.destroy()

                if confirm_response == Gtk.ResponseType.YES:
                    self.characters.pop(char_index)
                    self.save_data()
                    self.populate_table()  # This rebuilds indices correctly
                    dialog.destroy()
                    break
                # If user clicked No, continue showing the edit dialog

            else:
                dialog.destroy()
                break

    def reset_weekly_data(self, widget):
        for char in self.characters:
            char["vault_visited"] = False
            char["delves"] = 0
            char["gundarz"] = False
            char["quests"] = False
            char["timewalk"] = 0

        self.save_data()
        self.populate_table()

    def on_destroy(self, widget):
        # Cancel any pending config timer and clean up
        if self._config_timer is not None:
            self._config_timer.cancel()
            self._config_timer = None

        # Save cached window geometry before closing
        if not self.config.get("window"):
            self.config["window"] = {}

        # Use cached geometry if available and not maximized
        if self._last_window_geometry and not self.config.get("window", {}).get(
            "maximized", False
        ):
            self.config["window"].update(self._last_window_geometry)

        self.save_column_widths()
        self.save_sort_order()
        self.save_config()
        self.release_lock()
        Gtk.main_quit()

    def on_quit_clicked(self, widget):
        self.window.close()

    def on_theme_menu_activate(self, menu_item, theme_preference):
        """Handle theme menu selection"""
        if menu_item.get_active() and theme_preference != self.current_theme_preference:
            self.set_theme(theme_preference)

    def find_altoholic_data(self):
        """Find Altoholic SavedVariables file"""
        import platform

        system = platform.system()
        home = os.path.expanduser("~")

        print(f"[VERBOSE] Searching for Altoholic data on {system} system")
        print(f"[VERBOSE] Home directory: {home}")

        # Common WoW installation paths
        possible_paths = []

        if system == "Windows":
            # Use environment variables for better cross-installation compatibility
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

            # Add common alternative drive letters
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

        print(
            f"[VERBOSE] Checking {len(possible_paths)} possible WoW installation paths:"
        )
        for i, path in enumerate(possible_paths, 1):
            print(f"[VERBOSE]   {i}. {path}")

        # Look for Altoholic.lua files
        for base_path in possible_paths:
            abs_base_path = os.path.abspath(base_path)
            print(f"[VERBOSE] Checking base path: {abs_base_path}")
            if os.path.exists(abs_base_path):
                print(f"[VERBOSE]   ✓ Base path exists, listing account directories...")
                try:
                    account_dirs = os.listdir(abs_base_path)
                    print(
                        f"[VERBOSE]   Found {len(account_dirs)} directories: {account_dirs}"
                    )

                    for account_dir in account_dirs:
                        account_path = os.path.join(abs_base_path, account_dir)
                        abs_account_path = os.path.abspath(account_path)
                        print(
                            f"[VERBOSE]   Checking account directory: {abs_account_path}"
                        )

                        if os.path.isdir(abs_account_path):
                            sv_dir = os.path.join(abs_account_path, "SavedVariables")
                            abs_sv_dir = os.path.abspath(sv_dir)
                            print(
                                f"[VERBOSE]     Looking in SavedVariables directory: {abs_sv_dir}"
                            )

                            if os.path.exists(abs_sv_dir):
                                try:
                                    sv_files = os.listdir(abs_sv_dir)
                                    print(
                                        f"[VERBOSE]     Found {len(sv_files)} files in SavedVariables"
                                    )

                                    # Look for Altoholic and DataStore files (not .bak)
                                    target_files = []
                                    for filename in sv_files:
                                        if (
                                            (
                                                filename.startswith("Altoholic")
                                                or filename.startswith("DataStore")
                                            )
                                            and not filename.endswith(".bak")
                                            and filename.endswith(".lua")
                                        ):
                                            target_files.append(filename)

                                    print(
                                        f"[VERBOSE]     Found {len(target_files)} target files: {target_files}"
                                    )

                                    if target_files:
                                        # Store ALL target files for processing
                                        self._altoholic_files = [
                                            os.path.abspath(os.path.join(abs_sv_dir, f))
                                            for f in target_files
                                        ]
                                        print(
                                            f"[VERBOSE]     ✓ Found {len(target_files)} Altoholic/DataStore files:"
                                        )

                                        for i, target_file in enumerate(
                                            target_files, 1
                                        ):
                                            abs_file_path = os.path.abspath(
                                                os.path.join(abs_sv_dir, target_file)
                                            )
                                            file_size = os.path.getsize(abs_file_path)
                                            print(
                                                f"[VERBOSE]       {i}. {target_file} - {file_size:,} bytes"
                                            )
                                            print(
                                                f"[VERBOSE]          Path: {abs_file_path}"
                                            )

                                        # Return the first file as primary (for compatibility), but all will be processed
                                        priority_order = [
                                            "DataStore_Characters.lua",
                                            "Altoholic.lua",
                                            "DataStore.lua",
                                        ]
                                        primary_file = None

                                        # First check for priority files
                                        for priority_file in priority_order:
                                            if priority_file in target_files:
                                                primary_file = priority_file
                                                print(
                                                    f"[VERBOSE]     ✓ Using {priority_file} as primary file"
                                                )
                                                break

                                        # If no priority file, use the first one
                                        if not primary_file:
                                            primary_file = target_files[0]
                                            print(
                                                f"[VERBOSE]     ✓ Using {primary_file} as primary file"
                                            )

                                        primary_abs_path = os.path.abspath(
                                            os.path.join(abs_sv_dir, primary_file)
                                        )
                                        print(
                                            f"[VERBOSE]     ✓ Primary file path: {primary_abs_path}"
                                        )
                                        print(
                                            f"[VERBOSE]     ✓ ALL files will be processed during import"
                                        )

                                        return primary_abs_path
                                    else:
                                        print(
                                            f"[VERBOSE]     ✗ No Altoholic or DataStore .lua files found (excluding .bak)"
                                        )

                                except Exception as e:
                                    print(
                                        f"[VERBOSE]     ✗ Error reading SavedVariables directory: {e}"
                                    )
                            else:
                                print(
                                    f"[VERBOSE]     ✗ SavedVariables directory not found: {abs_sv_dir}"
                                )
                        else:
                            print(
                                f"[VERBOSE]     ✗ Not a directory: {abs_account_path}"
                            )
                except PermissionError as e:
                    print(
                        f"[VERBOSE]   ✗ Permission error accessing {abs_base_path}: {e}"
                    )
                except Exception as e:
                    print(f"[VERBOSE]   ✗ Error accessing {abs_base_path}: {e}")
            else:
                print(f"[VERBOSE]   ✗ Base path does not exist: {abs_base_path}")

        print(f"[VERBOSE] No Altoholic.lua file found in any location")
        return None

    def parse_altoholic_data(self, file_path):
        """Parse Altoholic/DataStore SavedVariables file for character data"""
        abs_file_path = os.path.abspath(file_path)
        print(f"[VERBOSE] Parsing data from absolute path: {abs_file_path}")

        # Verify file exists and show file info
        if not os.path.exists(abs_file_path):
            print(
                f"[VERBOSE] ✗ ERROR: File does not exist at absolute path: {abs_file_path}"
            )
            return []

        try:
            file_stat = os.stat(abs_file_path)
            import time

            mod_time = time.ctime(file_stat.st_mtime)
            print(
                f"[VERBOSE] File info - Size: {file_stat.st_size:,} bytes, Modified: {mod_time}"
            )
        except Exception as e:
            print(f"[VERBOSE] Warning: Could not get file stats: {e}")

        try:
            # Try different encodings for better compatibility
            encodings = ["utf-8", "utf-16", "latin-1", "cp1252"]
            content = None

            print(f"[VERBOSE] Attempting to read file with multiple encodings...")
            for encoding in encodings:
                try:
                    print(f"[VERBOSE]   Trying {encoding} encoding on: {abs_file_path}")
                    with open(
                        abs_file_path, "r", encoding=encoding, errors="replace"
                    ) as f:
                        content = f.read()
                    print(
                        f"[VERBOSE] ✓ Successfully read file with {encoding} encoding from: {abs_file_path}"
                    )
                    break
                except UnicodeDecodeError as e:
                    print(f"[VERBOSE] ✗ Failed with {encoding}: {e}")
                    continue
                except Exception as e:
                    print(f"[VERBOSE] ✗ Unexpected error with {encoding}: {e}")
                    continue

            if content is None:
                print(f"[VERBOSE] ✗ Failed to read file with any encoding")
                return []

            file_size = len(content)
            print(f"[VERBOSE] File content loaded, size: {file_size:,} characters")

            if file_size == 0:
                print(f"[VERBOSE] ✗ File is empty")
                return []

            # Show first 500 characters for better debugging
            preview = content[:500].replace("\n", "\\n").replace("\t", "\\t")
            print(f"[VERBOSE] File preview (first 500 chars): {preview}...")

            # Determine file type for specialized parsing
            filename = os.path.basename(abs_file_path).lower()
            print(f"[VERBOSE] File type detected: {filename}")

            characters = []

            # Use specialized parsers based on file type
            if filename == "datastore_characters.lua":
                characters = self.parse_datastore_characters(content)
                print(
                    f"[VERBOSE] DataStore_Characters parser returned {len(characters)} characters"
                )
            elif filename.startswith("datastore_inventory"):
                characters = self.parse_datastore_inventory(content)
                print(
                    f"[VERBOSE] DataStore_Inventory parser returned {len(characters)} characters"
                )
            else:
                # Fall back to general Altoholic parsing
                characters = self.parse_altoholic_general(content)
                print(
                    f"[VERBOSE] General Altoholic parser returned {len(characters)} characters"
                )

            print(
                f"[VERBOSE] Parsing complete. Returning {len(characters)} parsed characters"
            )

            if characters:
                print(f"[VERBOSE] Successfully parsed characters:")
                for i, char in enumerate(characters[:10], 1):  # Show first 10
                    print(
                        f"[VERBOSE]   {i}. {char['name']} ({char['realm']}) - iLevel {char.get('item_level', 0)}"
                    )
                if len(characters) > 10:
                    print(f"[VERBOSE]   ... and {len(characters) - 10} more characters")

            return characters

        except Exception as e:
            print(f"[VERBOSE] ✗ Error parsing data: {e}")
            import traceback

            print(f"[VERBOSE] Traceback: {traceback.format_exc()}")
            return []

    def parse_datastore_characters(self, content):
        """Parse DataStore_Characters.lua format"""
        import re

        characters = []

        print(f"[VERBOSE] Parsing DataStore_Characters format...")

        # Look for DataStore_Characters_Info table - need to handle nested braces properly
        # First, find where the table starts
        start_match = re.search(r"DataStore_Characters_Info\s*=\s*{", content)
        if not start_match:
            print(f"[VERBOSE] ✗ DataStore_Characters_Info table not found")
            return characters

        # Extract the table content by matching braces
        start_pos = start_match.end() - 1  # Position of opening brace
        brace_count = 0
        table_content = ""

        for i, char in enumerate(content[start_pos:], start_pos):
            table_content += char
            if char == "{":
                brace_count += 1
            elif char == "}":
                brace_count -= 1
                if brace_count == 0:
                    break

        # Remove the outer braces to get just the content
        info_content = (
            table_content[1:-1]
            if table_content.startswith("{") and table_content.endswith("}")
            else table_content
        )
        print(f"[VERBOSE] ✓ Found DataStore_Characters_Info table")

        # Parse individual character entries - need to handle nested structures
        # The character entries contain nested structures, so we need a more sophisticated approach
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
                    current_entry = ""
                else:
                    current_entry += char
            elif in_entry:
                current_entry += char

        print(f"[VERBOSE] Found {len(char_entries)} character entries")

        # Also get character ID mappings from DataStore_CharacterIDs
        char_ids = {}
        ids_match = re.search(
            r'DataStore_CharacterIDs\s*=\s*{[^}]*"List"\s*=\s*{([^}]+)}',
            content,
            re.DOTALL,
        )
        if ids_match:
            ids_content = ids_match.group(1)
            # Parse character ID list: "Default.Realm.Name"
            id_entries = re.findall(r'"([^"]+)"', ids_content)
            for i, char_id in enumerate(id_entries):
                if "." in char_id:
                    parts = char_id.split(".")
                    if len(parts) >= 3:
                        realm = parts[1]
                        name = parts[2]
                        char_ids[i] = {"name": name, "realm": realm}
                        print(f"[VERBOSE] Character ID {i}: {name} on {realm}")
        else:
            print(f"[VERBOSE] ⚠ DataStore_CharacterIDs not found in this file")

        for i, entry in enumerate(char_entries):
            try:
                character = {}

                # Get name and realm from character ID mapping or parse from entry
                if i in char_ids:
                    character["name"] = char_ids[i]["name"]
                    character["realm"] = char_ids[i]["realm"]
                else:
                    # Try to extract from entry itself
                    name_match = re.search(r'\["name"\]\s*=\s*"([^"]+)"', entry)
                    if name_match:
                        character["name"] = name_match.group(1)
                    else:
                        print(f"[VERBOSE] ✗ No name found for entry {i}")
                        print(f"[VERBOSE] Entry preview: {entry[:200]}")
                        continue

                    character["realm"] = "Unknown"  # Will try to get from other sources

                # Parse money (convert from copper to gold for display)
                money_match = re.search(r'\["money"\]\s*=\s*(\d+)', entry)
                if money_match:
                    copper = int(money_match.group(1))
                    # Store as copper but we could convert: gold = copper / 10000
                    character["money"] = copper

                # Parse playtime
                played_match = re.search(r'\["played"\]\s*=\s*(\d+)', entry)
                if played_match:
                    character["played_seconds"] = int(played_match.group(1))

                # Parse location
                zone_match = re.search(r'\["zone"\]\s*=\s*"([^"]*)"', entry)
                if zone_match:
                    character["zone"] = zone_match.group(1)

                # Parse guild rank (would need guild mapping for guild name)
                guild_rank_match = re.search(r'\["guildRankIndex"\]\s*=\s*(\d+)', entry)
                if guild_rank_match:
                    character["guild_rank"] = int(guild_rank_match.group(1))

                # Parse BaseInfo (packed race/class/gender/faction data)
                base_info_match = re.search(r'\["BaseInfo"\]\s*=\s*(\d+)', entry)
                if base_info_match:
                    character["base_info"] = int(base_info_match.group(1))

                # Set defaults for tracking fields
                character.setdefault("item_level", 0)
                character.setdefault("guild", "")
                character.setdefault("heroic_items", 0)
                character.setdefault("champion_items", 0)
                character.setdefault("veteran_items", 0)
                character.setdefault("adventure_items", 0)
                character.setdefault("old_items", 0)
                character.setdefault("vault_visited", False)
                character.setdefault("delves", 0)
                character.setdefault("gundarz", False)
                character.setdefault("quests", False)
                character.setdefault("timewalk", 0)

                if character.get("name"):
                    characters.append(character)
                    print(
                        f"[VERBOSE] ✓ Parsed character: {character['name']} on {character.get('realm', 'Unknown')}"
                    )

            except Exception as e:
                print(f"[VERBOSE] ✗ Error parsing character entry {i}: {e}")
                continue

        return characters

    def parse_datastore_inventory(self, content):
        """Parse DataStore_Inventory.lua format"""
        import re

        characters = []

        print(f"[VERBOSE] Parsing DataStore_Inventory format...")

        # Look for DataStore_Inventory_Characters table - handle nested braces properly
        start_match = re.search(r"DataStore_Inventory_Characters\s*=\s*{", content)
        if not start_match:
            print(f"[VERBOSE] ✗ DataStore_Inventory_Characters table not found")
            return characters

        # Extract the table content by matching braces
        start_pos = start_match.end() - 1  # Position of opening brace
        brace_count = 0
        table_content = ""

        for i, char in enumerate(content[start_pos:], start_pos):
            table_content += char
            if char == "{":
                brace_count += 1
            elif char == "}":
                brace_count -= 1
                if brace_count == 0:
                    break

        # Remove the outer braces to get just the content
        inv_content = (
            table_content[1:-1]
            if table_content.startswith("{") and table_content.endswith("}")
            else table_content
        )
        print(f"[VERBOSE] ✓ Found DataStore_Inventory_Characters table")

        # Parse individual inventory entries - need to handle nested structures properly
        inv_entries = []
        brace_count = 0
        current_entry = ""
        in_entry = False

        for char in inv_content:
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
                    inv_entries.append(current_entry)
                    in_entry = False
                    current_entry = ""
                else:
                    current_entry += char
            elif in_entry:
                current_entry += char

        print(f"[VERBOSE] Found {len(inv_entries)} inventory entries")

        for i, entry in enumerate(inv_entries):
            try:
                character = {}

                # Parse average item level
                ilvl_match = re.search(r'\["averageItemLvl"\]\s*=\s*([0-9.]+)', entry)
                if ilvl_match:
                    character["item_level"] = int(float(ilvl_match.group(1)))

                # Parse overall average item level
                overall_ilvl_match = re.search(
                    r'\["overallAIL"\]\s*=\s*([0-9.]+)', entry
                )
                if overall_ilvl_match:
                    # Use overall if available, otherwise use regular average
                    character["item_level"] = int(float(overall_ilvl_match.group(1)))

                # Parse inventory items to count by quality - need to handle nested structure
                inventory_match = re.search(
                    r'\["Inventory"\]\s*=\s*{(.+)}', entry, re.DOTALL
                )
                if inventory_match:
                    inventory_content = inventory_match.group(1)
                    # Count item qualities from item links
                    # Item link format: |cnIQ#:|Hitem:...
                    # IQ1 = Common (old), IQ2 = Uncommon (adventure), IQ3 = Rare (champion), IQ4 = Epic (heroic)

                    heroic_count = len(re.findall(r"\|cnIQ4:", inventory_content))
                    champion_count = len(re.findall(r"\|cnIQ3:", inventory_content))
                    adventure_count = len(re.findall(r"\|cnIQ2:", inventory_content))
                    old_count = len(re.findall(r"\|cnIQ1:", inventory_content))

                    character["heroic_items"] = heroic_count
                    character["champion_items"] = champion_count
                    character["adventure_items"] = adventure_count
                    character["old_items"] = old_count

                    # Count veteran items by item level (would need item level parsing)
                    character["veteran_items"] = 0

                # Set defaults for missing fields
                character.setdefault("name", f"Character_{i+1}")
                character.setdefault("realm", "Unknown")
                character.setdefault("guild", "")
                character.setdefault("item_level", 0)
                character.setdefault("heroic_items", 0)
                character.setdefault("champion_items", 0)
                character.setdefault("veteran_items", 0)
                character.setdefault("adventure_items", 0)
                character.setdefault("old_items", 0)
                character.setdefault("vault_visited", False)
                character.setdefault("delves", 0)
                character.setdefault("gundarz", False)
                character.setdefault("quests", False)
                character.setdefault("timewalk", 0)

                if character.get("item_level", 0) > 0:
                    characters.append(character)
                    print(
                        f"[VERBOSE] ✓ Parsed inventory: {character['name']} (iLevel {character['item_level']})"
                    )

            except Exception as e:
                print(f"[VERBOSE] ✗ Error parsing inventory entry {i}: {e}")
                continue

        return characters

    def parse_altoholic_general(self, content):
        """Parse general Altoholic format (fallback parser)"""
        import re

        characters = []

        print(f"[VERBOSE] Using general Altoholic parser...")

        # Add timeout protection for regex to prevent ReDoS (cross-platform)
        max_file_size = 50 * 1024 * 1024  # 50MB limit
        if len(content) > max_file_size:
            print(
                f"[VERBOSE] File too large ({len(content):,} bytes), truncating to {max_file_size:,} bytes"
            )
            content = content[:max_file_size]

        def safe_regex_search(pattern, text, timeout_seconds=5):
            """Cross-platform regex with timeout protection and proper thread cleanup"""
            import concurrent.futures

            # Use ThreadPoolExecutor for better thread management
            with concurrent.futures.ThreadPoolExecutor(max_workers=1) as executor:
                try:
                    # Submit the regex operation
                    future = executor.submit(re.findall, pattern, text)

                    # Wait for result with timeout
                    result = future.result(timeout=timeout_seconds)
                    return result

                except concurrent.futures.TimeoutError:
                    print(
                        f"[VERBOSE] Regex operation timed out after {timeout_seconds}s"
                    )
                    return []
                except Exception as e:
                    print(f"[VERBOSE] Regex operation failed: {e}")
                    return []

        # Try multiple patterns to find character data
        patterns_to_try = [
            # Original pattern - exact Altoholic format
            (
                r'\["([^"]+)\|([^"]+)"\]\s*=\s*{[^}]*"itemLevel"\s*=\s*(\d+)',
                "Original Altoholic format",
            ),
            # More flexible itemLevel pattern
            (
                r'\["([^"]+)\|([^"]+)"\]\s*=\s*{[^}]*itemLevel["\s]*=\s*(\d+)',
                "Flexible itemLevel format",
            ),
            # DataStore Characters pattern (general)
            (
                r'\["([^"]+)\|([^"]+)"\]\s*=\s*{[^}]*averageItemLevel["\s]*=\s*(\d+)',
                "DataStore averageItemLevel format",
            ),
            # Look for any character|realm pattern with item level numbers
            (
                r'\["([^"]+)\|([^"]+)"\]\s*=\s*{[^}]*(\d{3,4})',
                "Character|Realm with item level numbers",
            ),
            # Look for Characters table entries
            (
                r'Characters\s*=\s*{.*?\["([^"]+)\|([^"]+)"\]\s*=.*?itemLevel["\s]*=\s*(\d+)',
                "Characters table format",
            ),
            # Simple character name pattern in quotes
            (
                r'"([A-Za-z]{2,12})"\s*=\s*{[^}]*(?:itemLevel|averageItemLevel)["\s]*=\s*(\d+)',
                "Simple character name pattern",
            ),
            # Broader pattern for any character data with level info
            (
                r'\["?([A-Za-z]+)\|([A-Za-z\s\'-]+)"?\]?\s*=\s*{[^}]*(\d{3,4})',
                "Broad character|realm pattern",
            ),
        ]

        for pattern_info in patterns_to_try:
            pattern, description = pattern_info
            print(f"[VERBOSE] Trying pattern: {description}")

            matches = safe_regex_search(pattern, content)
            print(f"[VERBOSE]   Found {len(matches)} matches")

            if matches:
                print(f"[VERBOSE] ✓ Success with pattern: {description}")
                for i, match in enumerate(matches[:10], 1):  # Show first 10 matches
                    if len(match) >= 3:  # Has realm and item level
                        char_name, realm, item_level = match[0], match[1], match[2]
                    elif len(match) == 2:  # Only name and item level
                        char_name, item_level = match[0], match[1]
                        realm = "Unknown"
                    else:
                        continue

                    print(
                        f"[VERBOSE]     {i}. Character: {char_name} on {realm}, iLevel: {item_level}"
                    )

                    try:
                        characters.append(
                            {
                                "name": char_name,
                                "realm": realm,
                                "item_level": int(item_level),
                                "guild": "",  # Would need more complex parsing
                                "heroic_items": 0,
                                "champion_items": 0,
                                "veteran_items": 0,
                                "adventure_items": 0,
                                "old_items": 0,
                                "vault_visited": False,
                                "delves": 0,
                                "gundarz": False,
                                "quests": False,
                                "timewalk": 0,
                            }
                        )
                    except ValueError as e:
                        print(f"[VERBOSE]     ✗ Skipping invalid data: {e}")
                        continue

                # If we found characters, break out of pattern loop
                if characters:
                    break
            else:
                print(f"[VERBOSE]   ✗ No matches found with this pattern")

        return characters

    def merge_datastore_data(self, all_files):
        """Merge data from multiple DataStore files to create complete character records"""
        print(f"[VERBOSE] Merging data from {len(all_files)} DataStore files...")

        characters_data = {}  # Character index -> character data
        inventory_data = {}  # Character index -> inventory data
        guild_mappings = {}  # Guild ID -> Guild name
        character_guilds = {}  # Character index -> Guild ID
        character_mappings = {}  # Character index -> (name, realm)

        for file_path in all_files:
            filename = os.path.basename(file_path).lower()
            print(f"[VERBOSE] Processing {filename}...")

            try:
                with open(file_path, "r", encoding="utf-8", errors="replace") as f:
                    content = f.read()

                if filename == "datastore_characters.lua":
                    # Parse character info and mappings
                    chars = self.parse_datastore_characters(content)
                    for i, char in enumerate(chars):
                        characters_data[i] = char
                        character_mappings[i] = (char["name"], char["realm"])

                    # Parse character-guild relationships
                    import re

                    guild_rel_match = re.search(
                        r"DataStore_CharacterGuilds\s*=\s*{([^}]+)}", content
                    )
                    if guild_rel_match:
                        guild_numbers = re.findall(r"(\d+)", guild_rel_match.group(1))
                        for i, guild_id in enumerate(guild_numbers):
                            if guild_id != "nil":
                                character_guilds[i] = int(guild_id)

                elif filename == "datastore_inventory.lua":
                    # Parse inventory data (item levels, gear quality counts)
                    inv_chars = self.parse_datastore_inventory(content)
                    for i, inv_char in enumerate(inv_chars):
                        inventory_data[i] = inv_char

                elif filename == "datastore.lua":
                    # Parse guild mappings and character mappings
                    import re

                    guild_ids_match = re.search(
                        r"DataStore_GuildIDs\s*=\s*{.*?List.*?=\s*{([^}]+)}",
                        content,
                        re.DOTALL,
                    )
                    if guild_ids_match:
                        guild_list = re.findall(r'"([^"]+)"', guild_ids_match.group(1))
                        for i, guild_full_name in enumerate(guild_list):
                            # Extract guild name from "Default.Realm.GuildName" format
                            if "." in guild_full_name:
                                parts = guild_full_name.split(".")
                                if len(parts) >= 3:
                                    guild_name = parts[2]
                                    guild_mappings[i + 1] = (
                                        guild_name  # Guild IDs are 1-indexed
                                    )
                                    print(f"[VERBOSE] Guild {i + 1}: {guild_name}")
                    else:
                        print(
                            f"[VERBOSE] ⚠ DataStore_GuildIDs not found in datastore.lua"
                        )

                    # Parse character ID mappings to get realm information
                    char_ids_match = re.search(
                        r"DataStore_CharacterIDs\s*=\s*{.*?List.*?=\s*{([^}]+)}",
                        content,
                        re.DOTALL,
                    )
                    if char_ids_match:
                        char_list = re.findall(r'"([^"]+)"', char_ids_match.group(1))
                        for i, char_full_name in enumerate(char_list):
                            # Extract realm and name from "Default.Realm.Name" format
                            if "." in char_full_name:
                                parts = char_full_name.split(".")
                                if len(parts) >= 3:
                                    realm = parts[1]
                                    name = parts[2]
                                    character_mappings[i] = (name, realm)
                                    print(
                                        f"[VERBOSE] Character mapping {i}: {name} on {realm}"
                                    )

                    # Parse character-guild relationships
                    char_guilds_match = re.search(
                        r"DataStore_CharacterGuilds\s*=\s*{([^}]+)}", content
                    )
                    if char_guilds_match:
                        guild_numbers = re.findall(r"(\d+)", char_guilds_match.group(1))
                        for i, guild_id in enumerate(guild_numbers):
                            if guild_id != "nil":
                                character_guilds[i] = int(guild_id)
                                print(f"[VERBOSE] Character {i} -> Guild {guild_id}")

            except Exception as e:
                print(f"[VERBOSE] ✗ Error processing {filename}: {e}")
                continue

        # Merge all data together
        merged_characters = []

        print(f"[VERBOSE] Merging character data...")
        print(f"[VERBOSE] Characters data: {len(characters_data)} entries")
        print(f"[VERBOSE] Inventory data: {len(inventory_data)} entries")
        print(f"[VERBOSE] Guild mappings: {len(guild_mappings)} entries")
        print(f"[VERBOSE] Character guilds: {len(character_guilds)} entries")

        for char_index in characters_data:
            try:
                character = characters_data[char_index].copy()

                # Update realm from character mappings if available
                if char_index in character_mappings:
                    name, realm = character_mappings[char_index]
                    character["realm"] = realm
                    # Verify name matches
                    if character.get("name") != name:
                        print(
                            f"[VERBOSE] ⚠ Name mismatch for index {char_index}: parsed '{character.get('name')}' vs mapping '{name}'"
                        )

                # Add inventory data if available
                if char_index in inventory_data:
                    inv_data = inventory_data[char_index]
                    # Use inventory item level if character doesn't have one
                    if (
                        character.get("item_level", 0) == 0
                        and inv_data.get("item_level", 0) > 0
                    ):
                        character["item_level"] = inv_data["item_level"]

                    # Add gear quality counts
                    for key in [
                        "heroic_items",
                        "champion_items",
                        "veteran_items",
                        "adventure_items",
                        "old_items",
                    ]:
                        if key in inv_data:
                            character[key] = inv_data[key]

                # Add guild name if available
                if char_index in character_guilds:
                    guild_id = character_guilds[char_index]
                    if guild_id in guild_mappings:
                        character["guild"] = guild_mappings[guild_id]
                        print(
                            f"[VERBOSE] ✓ Added guild '{guild_mappings[guild_id]}' to {character['name']}"
                        )

                # Only add characters with names and known realms
                if character.get("name"):
                    if character.get("realm") == "Unknown":
                        print(
                            f"[VERBOSE] ⚠ Warning: Skipping character {character['name']} - realm is Unknown, not updating"
                        )
                        continue
                    merged_characters.append(character)
                    print(
                        f"[VERBOSE] ✓ Merged character: {character['name']} on {character['realm']} (iLevel: {character.get('item_level', 0)}, Guild: {character.get('guild', 'None')})"
                    )

            except Exception as e:
                print(f"[VERBOSE] ✗ Error merging character {char_index}: {e}")
                continue

        print(f"[VERBOSE] Merge complete: {len(merged_characters)} total characters")
        return merged_characters

    def update_from_altoholic(self, widget):
        """Update character data from Altoholic addon"""
        print(f"[VERBOSE] ========== Starting Altoholic Update ===========")
        print(f"[VERBOSE] Current working directory: {os.getcwd()}")
        print(f"[VERBOSE] Current character count: {len(self.characters)}")

        altoholic_file = self.find_altoholic_data()

        if not altoholic_file:
            print(f"[VERBOSE] ✗ No Altoholic file found")
            dialog = Gtk.MessageDialog(
                parent=self.window,
                modal=True,
                message_type=Gtk.MessageType.WARNING,
                buttons=Gtk.ButtonsType.OK,
                text="Altoholic data not found.",
            )
            dialog.format_secondary_text(
                "Could not locate Altoholic SavedVariables file. "
                "Make sure World of Warcraft and Altoholic addon are installed."
            )
            dialog.run()
            dialog.destroy()
            return

        print(f"[VERBOSE] ✓ Found Altoholic file: {altoholic_file}")

        # Process ALL matching files, not just the primary one
        altoholic_chars = []
        files_processed = 0

        if hasattr(self, "_altoholic_files") and self._altoholic_files:
            print(
                f"[VERBOSE] Processing ALL {len(self._altoholic_files)} Altoholic/DataStore files..."
            )

            # Check if we have DataStore files that can be merged
            datastore_files = [
                f
                for f in self._altoholic_files
                if "datastore" in os.path.basename(f).lower()
            ]
            other_files = [
                f
                for f in self._altoholic_files
                if "datastore" not in os.path.basename(f).lower()
            ]

            if len(datastore_files) > 1:
                print(
                    f"[VERBOSE] Found {len(datastore_files)} DataStore files - using merge strategy"
                )
                merged_chars = self.merge_datastore_data(datastore_files)
                if merged_chars:
                    altoholic_chars.extend(merged_chars)
                    print(
                        f"[VERBOSE] ✓ Merged {len(merged_chars)} characters from DataStore files"
                    )
                files_processed += len(datastore_files)

            # Process remaining files individually
            remaining_files = datastore_files if len(datastore_files) <= 1 else []
            remaining_files.extend(other_files)

            for file_path in remaining_files:
                files_processed += 1
                filename = os.path.basename(file_path)
                print(f"[VERBOSE] Processing individual file: {filename}")
                print(f"[VERBOSE]   Full path: {file_path}")

                chars_from_file = self.parse_altoholic_data(file_path)
                if chars_from_file:
                    altoholic_chars.extend(chars_from_file)
                    print(
                        f"[VERBOSE] ✓ Found {len(chars_from_file)} characters in {filename}"
                    )
                else:
                    print(f"[VERBOSE] ✗ No characters found in {filename}")
        else:
            # Fallback to single file processing if _altoholic_files not set
            print(f"[VERBOSE] Processing single file: {altoholic_file}")
            altoholic_chars = self.parse_altoholic_data(altoholic_file)
            files_processed = 1

        # Remove duplicate characters (same name + realm combination)
        if altoholic_chars:
            print(f"[VERBOSE] Deduplicating characters...")
            seen_characters = set()
            deduplicated_chars = []

            for char in altoholic_chars:
                # Skip characters with Unknown realm
                if char.get("realm") == "Unknown":
                    print(
                        f"[VERBOSE] ⚠ Warning: Skipping character {char.get('name', 'Unknown')} - realm is Unknown, not updating"
                    )
                    continue

                char_key = (
                    f"{char.get('name', '').lower()}|{char.get('realm', '').lower()}"
                )
                if char_key not in seen_characters:
                    seen_characters.add(char_key)
                    deduplicated_chars.append(char)
                else:
                    print(
                        f"[VERBOSE]   Skipping duplicate: {char.get('name', '')}-{char.get('realm', '')}"
                    )

            altoholic_chars = deduplicated_chars
            print(
                f"[VERBOSE] After deduplication: {len(altoholic_chars)} unique characters"
            )

        print(
            f"[VERBOSE] Summary: Processed {files_processed} files, found {len(altoholic_chars)} unique characters"
        )

        if not altoholic_chars:
            print(
                f"[VERBOSE] ✗ No character data parsed from any Altoholic/DataStore files"
            )
            dialog = Gtk.MessageDialog(
                parent=self.window,
                modal=True,
                message_type=Gtk.MessageType.WARNING,
                buttons=Gtk.ButtonsType.OK,
                text="No character data found in Altoholic files.",
            )
            dialog.format_secondary_text(
                "Altoholic/DataStore files were found but no character data could be parsed. "
                "This may be due to:\n"
                "• Different Altoholic/DataStore data format\n"
                "• Empty or corrupted files\n"
                "• Unsupported addon versions\n\n"
                "Check the console output for detailed parsing information."
            )
            dialog.run()
            dialog.destroy()
            return

        print(f"[VERBOSE] ✓ Parsed {len(altoholic_chars)} characters from Altoholic")

        # Update existing characters or add new ones
        updated_count = 0
        added_count = 0

        print(f"[VERBOSE] Processing character updates with validation...")

        for i, alt_char in enumerate(altoholic_chars, 1):
            # Validate altoholic character data
            if not isinstance(alt_char, dict):
                print(f"[VERBOSE]   Skipping invalid character data at index {i}")
                continue

            alt_name = str(alt_char.get("name", "")).strip()
            alt_realm = str(alt_char.get("realm", "")).strip()
            alt_ilevel = alt_char.get("item_level", 0)

            # Skip characters with invalid data
            if not alt_name or not alt_realm or alt_ilevel <= 0:
                print(
                    f"[VERBOSE]   Skipping character with invalid data: {alt_name}-{alt_realm} (iLvl: {alt_ilevel})"
                )
                continue

            print(
                f"[VERBOSE]   Processing {i}/{len(altoholic_chars)}: {alt_name}-{alt_realm} (iLvl: {alt_ilevel})"
            )

            # Look for existing character
            existing_char = None
            for j, char in enumerate(self.characters):
                char_name = char.get("name", "").lower()
                char_realm = char.get("realm", "").lower()

                # Consistent case-insensitive comparison for both name and realm
                if char_name == alt_name.lower() and char_realm == alt_realm.lower():
                    existing_char = char
                    print(f"[VERBOSE]     ✓ Found existing character at index {j}")
                    break

            if existing_char:
                current_ilevel = existing_char.get("item_level", 0)
                print(
                    f"[VERBOSE]     Current iLevel: {current_ilevel}, Altoholic iLevel: {alt_ilevel}"
                )

                # Update item level if Altoholic has newer data
                if alt_ilevel > current_ilevel:
                    existing_char["item_level"] = alt_ilevel
                    updated_count += 1
                    print(
                        f"[VERBOSE]     ✓ Updated iLevel from {current_ilevel} to {alt_ilevel}"
                    )
                else:
                    print(f"[VERBOSE]     ✗ No update needed (current >= altoholic)")
            else:
                # Add new character
                self.characters.append(alt_char)
                added_count += 1
                print(f"[VERBOSE]     ✓ Added new character")

        print(
            f"[VERBOSE] Update summary: Updated {updated_count} characters, added {added_count} new characters"
        )

        if updated_count > 0 or added_count > 0:
            print(f"[VERBOSE] Saving data and refreshing table...")
            self.save_data()
            self.populate_table()

            dialog = Gtk.MessageDialog(
                parent=self.window,
                modal=True,
                message_type=Gtk.MessageType.INFO,
                buttons=Gtk.ButtonsType.OK,
                text="Altoholic data imported successfully!",
            )
            dialog.format_secondary_text(
                f"Updated {updated_count} characters, added {added_count} new characters."
            )
            dialog.run()
            dialog.destroy()
            print(f"[VERBOSE] ✓ Update completed successfully")
        else:
            dialog = Gtk.MessageDialog(
                parent=self.window,
                modal=True,
                message_type=Gtk.MessageType.INFO,
                buttons=Gtk.ButtonsType.OK,
                text="No updates needed.",
            )
            dialog.format_secondary_text("All characters are already up to date.")
            dialog.run()
            dialog.destroy()
            print(f"[VERBOSE] ✓ No updates were necessary")

        print(f"[VERBOSE] ========== Altoholic Update Complete ===========")

    def update_from_wow_addon(self, widget):
        """Import character data from WoW Stat Tracker addon"""
        if self.debug_enabled:
            print(f"[DEBUG] ========== WoW Addon Update Started ===========")

        try:
            # Find WoW addon SavedVariables file
            addon_data_file = self.find_wow_addon_data()

            if not addon_data_file:
                dialog = Gtk.MessageDialog(
                    parent=self.window,
                    flags=0,
                    message_type=Gtk.MessageType.WARNING,
                    buttons=Gtk.ButtonsType.OK,
                    text="WoW Addon Data Not Found",
                )
                dialog.format_secondary_text(
                    "Could not find WoW Stat Tracker addon data.\n\n"
                    "Please ensure:\n"
                    "1. The WoW Stat Tracker addon is installed\n"
                    "2. You have logged in with your characters\n"
                    "3. The addon has exported data (/wst export)\n\n"
                    "The addon SavedVariables file should be located in:\n"
                    "WoW/_retail_/WTF/Account/ACCOUNT/SavedVariables/WoWStatTracker.lua"
                )
                dialog.run()
                dialog.destroy()
                return

            # Parse addon data
            addon_chars = self.parse_wow_addon_data(addon_data_file)

            if not addon_chars:
                dialog = Gtk.MessageDialog(
                    parent=self.window,
                    flags=0,
                    message_type=Gtk.MessageType.WARNING,
                    buttons=Gtk.ButtonsType.OK,
                    text="No Character Data Found",
                )
                dialog.format_secondary_text(
                    "The addon data file was found but contains no character data.\n\n"
                    "Please ensure you have:\n"
                    "1. Logged in with your characters\n"
                    "2. Run '/wst export' in-game to export data\n"
                    "3. The addon is actively collecting data"
                )
                dialog.run()
                dialog.destroy()
                return

            # Import the data
            imported_count = 0
            updated_count = 0

            for addon_char in addon_chars:
                char_name = addon_char.get("name", "Unknown")
                char_realm = addon_char.get("realm", "Unknown")
                char_key = f"{char_name}-{char_realm}"

                if self.debug_enabled:
                    print(f"[DEBUG] Processing {char_key} from addon data")

                # Find or create character
                existing_char = None
                for i, char in enumerate(self.characters):
                    if (
                        char.get("name") == char_name
                        and char.get("realm") == char_realm
                    ):
                        existing_char = i
                        break

                if existing_char is not None:
                    # Update existing character - preserve notes and other user data
                    preserved_notes = self.characters[existing_char].get("notes", "")
                    self.characters[existing_char].update(addon_char)
                    # Restore notes after update
                    if preserved_notes:
                        self.characters[existing_char]["notes"] = preserved_notes
                    updated_count += 1
                    if self.debug_enabled:
                        print(f"[DEBUG] Updated existing character: {char_key}")
                else:
                    # Add new character
                    self.characters.append(addon_char)
                    imported_count += 1
                    if self.debug_enabled:
                        print(f"[DEBUG] Added new character: {char_key}")

            # Save and refresh
            self.save_data()
            self.populate_table()

            # Show success dialog
            dialog = Gtk.MessageDialog(
                parent=self.window,
                flags=0,
                message_type=Gtk.MessageType.INFO,
                buttons=Gtk.ButtonsType.OK,
                text="WoW Addon Import Complete",
            )
            dialog.format_secondary_text(
                f"Successfully imported data from WoW Stat Tracker addon!\n\n"
                f"New characters: {imported_count}\n"
                f"Updated characters: {updated_count}\n"
                f"Total characters: {len(self.characters)}"
            )
            dialog.run()
            dialog.destroy()

        except Exception as e:
            if self.debug_enabled:
                print(f"[DEBUG] Error importing addon data: {e}")

            dialog = Gtk.MessageDialog(
                parent=self.window,
                flags=0,
                message_type=Gtk.MessageType.ERROR,
                buttons=Gtk.ButtonsType.OK,
                text="Import Error",
            )
            dialog.format_secondary_text(f"Failed to import addon data:\n{str(e)}")
            dialog.run()
            dialog.destroy()

        if self.debug_enabled:
            print(f"[DEBUG] ========== WoW Addon Update Complete ===========")

    def find_wow_addon_data(self):
        """Find the WoW Stat Tracker addon SavedVariables file"""
        import platform

        system = platform.system()
        home = os.path.expanduser("~")

        possible_paths = []

        if system == "Darwin":  # macOS
            possible_paths = [
                f"{home}/Applications/World of Warcraft/_retail_/WTF/Account",
                f"/Applications/World of Warcraft/_retail_/WTF/Account",
                f"{home}/Games/World of Warcraft/_retail_/WTF/Account",
            ]
        elif system == "Windows":
            possible_paths = [
                f"C:/Program Files (x86)/World of Warcraft/_retail_/WTF/Account",
                f"C:/Program Files/World of Warcraft/_retail_/WTF/Account",
            ]
        else:  # Linux
            possible_paths = [
                f"{home}/.wine/drive_c/Program Files (x86)/World of Warcraft/_retail_/WTF/Account",
                f"{home}/Games/World of Warcraft/_retail_/WTF/Account",
            ]

        if self.debug_enabled:
            print(
                f"[DEBUG] Searching for addon data in {len(possible_paths)} locations"
            )

        for base_path in possible_paths:
            if not os.path.exists(base_path):
                continue

            try:
                # Look through account folders
                for account_dir in os.listdir(base_path):
                    if account_dir.startswith("."):
                        continue

                    addon_file = os.path.join(
                        base_path, account_dir, "SavedVariables", "WoWStatTracker.lua"
                    )
                    if os.path.exists(addon_file):
                        if self.debug_enabled:
                            print(f"[DEBUG] Found addon data: {addon_file}")
                        return addon_file

            except (OSError, PermissionError) as e:
                if self.debug_enabled:
                    print(f"[DEBUG] Error accessing {base_path}: {e}")
                continue

        return None

    def parse_wow_addon_data(self, file_path):
        """Parse WoW addon SavedVariables file"""
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                content = f.read()

            # Look for the exportData table in the Lua file
            import re

            # Find the exportData section
            export_match = re.search(
                r"exportData\s*=\s*{(.+?)}(?=\s*[},])", content, re.DOTALL
            )
            if not export_match:
                return []

            export_content = export_match.group(1)

            # Look for characters array
            chars_match = re.search(
                r"characters\s*=\s*{(.+?)}", export_content, re.DOTALL
            )
            if not chars_match:
                return []

            chars_content = chars_match.group(1)

            # Parse character entries
            characters = []
            char_pattern = r"{([^{}]+)}"

            for match in re.finditer(char_pattern, chars_content):
                char_data = match.group(1)
                character = self.parse_lua_character_data(char_data)
                if character:
                    characters.append(character)

            if self.debug_enabled:
                print(f"[DEBUG] Parsed {len(characters)} characters from addon data")

            return characters

        except Exception as e:
            if self.debug_enabled:
                print(f"[DEBUG] Error parsing addon file: {e}")
            return []

    def parse_lua_character_data(self, char_data):
        """Parse individual character data from Lua format"""
        character = {}

        # Simple regex-based parsing for Lua table format
        import re

        patterns = {
            "name": r'name\s*=\s*"([^"]+)"',
            "realm": r'realm\s*=\s*"([^"]+)"',
            "guild": r'guild\s*=\s*"([^"]*)"',
            "item_level": r"item_level\s*=\s*(\d+)",
            "heroic_items": r"heroic_items\s*=\s*(\d+)",
            "champion_items": r"champion_items\s*=\s*(\d+)",
            "veteran_items": r"veteran_items\s*=\s*(\d+)",
            "adventure_items": r"adventure_items\s*=\s*(\d+)",
            "old_items": r"old_items\s*=\s*(\d+)",
            "vault_visited": r"vault_visited\s*=\s*(true|false)",
            "delves": r"delves\s*=\s*(\d+)",
            "gundarz": r"gundarz\s*=\s*(true|false)",
            "quests": r"quests\s*=\s*(true|false)",
            "timewalk": r"timewalk\s*=\s*(\d+)",
        }

        for key, pattern in patterns.items():
            match = re.search(pattern, char_data)
            if match:
                value = match.group(1)
                if key in [
                    "item_level",
                    "heroic_items",
                    "champion_items",
                    "veteran_items",
                    "adventure_items",
                    "old_items",
                    "delves",
                    "timewalk",
                ]:
                    character[key] = int(value)
                elif key in ["vault_visited", "gundarz", "quests"]:
                    character[key] = value.lower() == "true"
                else:
                    character[key] = value

        # Only return if we have essential data
        if character.get("name") and character.get("realm"):
            return character

        return None

    def _is_process_running(self, pid):
        """Cross-platform process existence check"""
        try:
            import platform

            if platform.system() == "Windows":
                # Windows-specific process check
                import subprocess

                try:
                    result = subprocess.run(
                        ["tasklist", "/FI", f"PID eq {pid}", "/FO", "CSV"],
                        capture_output=True,
                        text=True,
                        timeout=5,
                    )
                    return str(pid) in result.stdout
                except (subprocess.SubprocessError, subprocess.TimeoutExpired):
                    # Fallback to basic method if tasklist fails
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
            # If all else fails, assume process is not running
            return False

    def acquire_lock(self):
        """Acquire file lock to prevent multiple instances"""
        self._lock_fd = None
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
                except:
                    pass
                self._lock_fd = None

            # fcntl not available on Windows, or lock failed
            # Fallback to simple PID file check
            try:
                if os.path.exists(self.lock_file):
                    with open(self.lock_file, "r", encoding="utf-8") as f:
                        pid = int(f.read().strip())
                    # Check if process is still running (cross-platform)
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

    def release_lock(self):
        """Release file lock"""
        try:
            if hasattr(self, "_lock_fd") and self._lock_fd is not None:
                try:
                    self._lock_fd.close()
                except (IOError, OSError):
                    pass  # Ignore close errors
                finally:
                    self._lock_fd = None

            if os.path.exists(self.lock_file):
                os.remove(self.lock_file)
        except (IOError, OSError):
            pass  # Ignore errors during cleanup

    def run(self):
        self.window.show_all()
        Gtk.main()


if __name__ == "__main__":
    app = WoWStatTracker()
    app.run()
