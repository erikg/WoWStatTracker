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
    COL_INDEX = 14  # Hidden column with original character index
    COL_COUNT = 15  # Total number of columns
    
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
        self.data_file = "wowstat_data.json"
        self.config_file = "wowstat_config.json"
        self.lock_file = "wowstat.lock"
        self._config_timer = None  # Initialize timer reference

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
        self.restore_window_state()
        self.window.connect("destroy", self.on_destroy)
        self.window.connect("configure-event", self.on_window_configure)

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

    def detect_system_theme(self):
        """Detect if system prefers dark mode"""
        system = platform.system().lower()
        
        try:
            if system == "darwin":  # macOS
                result = subprocess.run(
                    ["defaults", "read", "-g", "AppleInterfaceStyle"], 
                    capture_output=True, text=True, timeout=5
                )
                return result.returncode == 0 and "dark" in result.stdout.lower()
            
            elif system == "linux":
                # Try GNOME/GTK settings first
                try:
                    result = subprocess.run(
                        ["gsettings", "get", "org.gnome.desktop.interface", "gtk-theme"],
                        capture_output=True, text=True, timeout=5
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
                    result = subprocess.run([
                        "reg", "query", 
                        "HKEY_CURRENT_USER\\Software\\Microsoft\\Windows\\CurrentVersion\\Themes\\Personalize",
                        "/v", "AppsUseLightTheme"
                    ], capture_output=True, text=True, timeout=5)
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
            css_provider.load_from_data(css_data.encode('utf-8'))
            # Use the window's display to get screen for modern GTK
            if hasattr(self, 'window') and self.window:
                display = self.window.get_display()
                if display:
                    screen = display.get_default_screen()
                    if screen:
                        Gtk.StyleContext.add_provider_for_screen(
                            screen, css_provider, Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION
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

        self.window.set_default_size(width, height)

        # Validate window position is on screen
        if x is not None and y is not None:
            # Get screen dimensions using modern GTK API
            display = self.window.get_display()
            if display:
                monitor = display.get_primary_monitor()
                if monitor:
                    geometry = monitor.get_geometry()
                    screen_width = geometry.width
                    screen_height = geometry.height
                    # Ensure at least 100px of window is visible
                    x = max(0, min(screen_width - 100, x))
                    y = max(0, min(screen_height - 100, y))
            self.window.move(x, y)

    def on_window_configure(self, window, event):
        # Debounce rapid configure events to prevent race conditions
        if self._config_timer is not None:
            self._config_timer.cancel()
            self._config_timer = None

        import threading

        def save_window_config():
            try:
                if not self.config.get("window"):
                    self.config["window"] = {}

                self.config["window"]["width"] = max(
                    400, min(3840, event.width)
                )  # Reasonable bounds
                self.config["window"]["height"] = max(300, min(2160, event.height))
                self.config["window"]["x"] = max(0, event.x)  # Don't go off-screen
                self.config["window"]["y"] = max(0, event.y)

                # Save config with error handling
                self.save_config()
            finally:
                self._config_timer = None

        self._config_timer = threading.Timer(0.5, save_window_config)  # 500ms delay
        self._config_timer.daemon = True  # Dies with main thread
        self._config_timer.start()
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
        vbox = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10)
        vbox.set_margin_start(10)
        vbox.set_margin_end(10)
        vbox.set_margin_top(10)
        vbox.set_margin_bottom(10)
        self.window.add(vbox)

        button_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=5)
        vbox.pack_start(button_box, False, False, 0)

        add_button = Gtk.Button(label="Add Character")
        add_button.connect("clicked", self.add_character)
        button_box.pack_start(add_button, False, False, 0)

        reset_button = Gtk.Button(label="Reset Weekly Data")
        reset_button.connect("clicked", self.reset_weekly_data)
        button_box.pack_start(reset_button, False, False, 0)

        altoholic_button = Gtk.Button(label="Update from Altoholic")
        altoholic_button.connect("clicked", self.update_from_altoholic)
        button_box.pack_start(altoholic_button, False, False, 0)

        addon_button = Gtk.Button(label="Update from WoW Addon")
        addon_button.connect("clicked", self.update_from_wow_addon)
        button_box.pack_start(addon_button, False, False, 0)

        # Theme selection dropdown
        theme_label = Gtk.Label(label="Theme:")
        button_box.pack_start(theme_label, False, False, 10)
        
        self.theme_combo = Gtk.ComboBoxText()
        self.theme_combo.append(self.THEME_AUTO, "Auto (System)")
        self.theme_combo.append(self.THEME_LIGHT, "Light")
        self.theme_combo.append(self.THEME_DARK, "Dark")
        self.theme_combo.set_active_id(self.current_theme_preference)
        self.theme_combo.connect("changed", self.on_theme_changed)
        button_box.pack_start(self.theme_combo, False, False, 0)

        quit_button = Gtk.Button(label="Quit")
        quit_button.connect("clicked", self.on_quit_clicked)
        button_box.pack_end(quit_button, False, False, 0)

        scrolled = Gtk.ScrolledWindow()
        scrolled.set_policy(Gtk.PolicyType.AUTOMATIC, Gtk.PolicyType.AUTOMATIC)
        vbox.pack_start(scrolled, True, True, 0)

        self.store = Gtk.ListStore(
            str, str, str, int, int, int, int, int, int, bool, int, bool, bool, int, int
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
            ("Index", int, 14),  # Hidden column for original character index
        ]

        for i, (title, data_type, col_id) in enumerate(columns):
            if data_type == bool and col_id in [
                8,
                10,
                11,
            ]:  # vault_visited, gundarz, quests (toggleable booleans)
                renderer = Gtk.CellRendererToggle()
                renderer.set_property("activatable", True)
                renderer.connect("toggled", self.on_boolean_toggled, col_id)
                column = Gtk.TreeViewColumn(title, renderer, active=col_id)
            else:
                renderer = Gtk.CellRendererText()
                column = Gtk.TreeViewColumn(title, renderer, text=col_id)

                # Apply cell data function for weekly columns with background coloring
                if col_id in [
                    8,
                    9,
                    10,
                    11,
                    12,
                ]:  # vault_visited, delves, gundarz, quests, timewalk
                    column.set_cell_data_func(renderer, self.cell_data_func, col_id)
                elif col_id == 13:  # Hide the index column
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
                if bg_color in ["#90EE90", "#FFFFE0", "#F08080"]:  # Light green, yellow, light red
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
            if delves >= 4:
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
                self.characters.pop(char_index)
                self.save_data()
                self.populate_table()  # This rebuilds indices correctly
                dialog.destroy()
                break

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

        self.save_column_widths()
        self.save_sort_order()
        self.save_config()
        self.release_lock()
        Gtk.main_quit()

    def on_quit_clicked(self, widget):
        self.window.close()

    def on_theme_changed(self, combo):
        """Handle theme selection change"""
        selected_theme = combo.get_active_id()
        if selected_theme and selected_theme != self.current_theme_preference:
            self.set_theme(selected_theme)

    def find_altoholic_data(self):
        """Find Altoholic SavedVariables file"""
        import platform

        system = platform.system()
        home = os.path.expanduser("~")

        if self.debug_enabled:
            print(f"[DEBUG] Searching for Altoholic data on {system} system")
            print(f"[DEBUG] Home directory: {home}")

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

        if self.debug_enabled:
            print(
                f"[DEBUG] Checking {len(possible_paths)} possible WoW installation paths:"
            )
            for i, path in enumerate(possible_paths, 1):
                print(f"[DEBUG]   {i}. {path}")

        # Look for Altoholic.lua files
        for base_path in possible_paths:
            if self.debug_enabled:
                print(f"[DEBUG] Checking base path: {base_path}")
            if os.path.exists(base_path):
                if self.debug_enabled:
                    print(f"[DEBUG]   Base path exists, listing account directories...")
                try:
                    account_dirs = os.listdir(base_path)
                    if self.debug_enabled:
                        print(
                            f"[DEBUG]   Found {len(account_dirs)} directories: {account_dirs}"
                        )

                    for account_dir in account_dirs:
                        account_path = os.path.join(base_path, account_dir)
                        if self.debug_enabled:
                            print(
                                f"[DEBUG]   Checking account directory: {account_path}"
                            )

                        if os.path.isdir(account_path):
                            sv_path = os.path.join(
                                account_path, "SavedVariables", "Altoholic.lua"
                            )
                            if self.debug_enabled:
                                print(f"[DEBUG]     Looking for: {sv_path}")

                            if os.path.exists(sv_path):
                                file_size = os.path.getsize(sv_path)
                                if self.debug_enabled:
                                    print(
                                        f"[DEBUG]     ✓ Found Altoholic.lua! Size: {file_size} bytes"
                                    )
                                return sv_path
                            else:
                                if self.debug_enabled:
                                    print(f"[DEBUG]     ✗ Altoholic.lua not found")
                        else:
                            if self.debug_enabled:
                                print(f"[DEBUG]     ✗ Not a directory")
                except PermissionError as e:
                    if self.debug_enabled:
                        print(
                            f"[DEBUG]   ✗ Permission error accessing {base_path}: {e}"
                        )
                except Exception as e:
                    if self.debug_enabled:
                        print(f"[DEBUG]   ✗ Error accessing {base_path}: {e}")
            else:
                if self.debug_enabled:
                    print(f"[DEBUG]   ✗ Base path does not exist")

        if self.debug_enabled:
            print(f"[DEBUG] No Altoholic.lua file found in any location")
        return None

    def parse_altoholic_data(self, file_path):
        """Parse Altoholic SavedVariables file for character data"""
        if self.debug_enabled:
            print(f"[DEBUG] Parsing Altoholic data from: {file_path}")

        try:
            # Try different encodings for better compatibility
            encodings = ["utf-8", "utf-16", "latin-1", "cp1252"]
            content = None

            for encoding in encodings:
                try:
                    with open(file_path, "r", encoding=encoding, errors="replace") as f:
                        content = f.read()
                    if self.debug_enabled:
                        print(
                            f"[DEBUG] Successfully read file with {encoding} encoding"
                        )
                    break
                except UnicodeDecodeError:
                    continue

            if content is None:
                if self.debug_enabled:
                    print(f"[DEBUG] Failed to read file with any encoding")
                return []

            file_size = len(content)
            if self.debug_enabled:
                print(f"[DEBUG] File content loaded, size: {file_size} characters")

            if file_size == 0:
                if self.debug_enabled:
                    print(f"[DEBUG] ✗ File is empty")
                return []

            # Show first 200 characters for debugging
            preview = content[:200].replace("\n", "\\n").replace("\t", "\\t")
            if self.debug_enabled:
                print(f"[DEBUG] File preview (first 200 chars): {preview}...")

            characters = []

            # Simple regex patterns to extract character data
            import re

            # Look for character entries in the Altoholic data structure
            # This is a basic implementation - Altoholic data structure is complex
            char_pattern = r'\["([^"]+)\|([^"]+)"\]\s*=\s*{[^}]*"itemLevel"\s*=\s*(\d+)'
            if self.debug_enabled:
                print(f"[DEBUG] Using regex pattern: {char_pattern}")

            # Add timeout protection for regex to prevent ReDoS (cross-platform)
            # Limit file size to prevent memory issues
            max_file_size = 50 * 1024 * 1024  # 50MB limit
            if len(content) > max_file_size:
                if self.debug_enabled:
                    print(
                        f"[DEBUG] File too large ({len(content)} bytes), truncating to {max_file_size} bytes"
                    )
                content = content[:max_file_size]

            def safe_regex_search(pattern, text, timeout_seconds=5):
                """Cross-platform regex with timeout protection and proper thread cleanup"""
                import concurrent.futures
                import threading
                import time

                # Use ThreadPoolExecutor for better thread management
                with concurrent.futures.ThreadPoolExecutor(max_workers=1) as executor:
                    try:
                        # Submit the regex operation
                        future = executor.submit(re.findall, pattern, text)

                        # Wait for result with timeout
                        result = future.result(timeout=timeout_seconds)
                        return result

                    except concurrent.futures.TimeoutError:
                        if self.debug_enabled:
                            print(
                                f"[DEBUG] Regex operation timed out after {timeout_seconds}s"
                            )
                        return []
                    except Exception as e:
                        if self.debug_enabled:
                            print(f"[DEBUG] Regex operation failed: {e}")
                        return []

            matches = safe_regex_search(char_pattern, content)
            if self.debug_enabled:
                print(f"[DEBUG] Found {len(matches)} character matches")

            for i, match in enumerate(matches, 1):
                char_name, realm, item_level = match
                if self.debug_enabled:
                    print(
                        f"[DEBUG]   {i}. Character: {char_name} on {realm}, iLevel: {item_level}"
                    )

                characters.append(
                    {
                        "name": char_name,
                        "realm": realm,
                        "item_level": int(item_level),
                        "guild": "",  # Would need more complex parsing
                        "heroic_items": 0,
                        "champion_items": 0,
                        "adventure_items": 0,
                        "old_items": 0,
                        "vault_visited": False,
                        "delves": 0,
                        "gundarz": False,
                        "quests": False,
                        "timewalk": 0,
                    }
                )

            # Try alternative patterns if no matches found
            if len(matches) == 0:
                if self.debug_enabled:
                    print(
                        f"[DEBUG] No matches with primary pattern, trying alternative patterns..."
                    )

                # Look for any character-like entries
                alt_patterns = [
                    r'"([^"]+)"\s*=\s*{[^}]*item[Ll]evel[^}]*(\d+)',
                    r'\["([^|"]+)\|([^"]+)"\]',
                    r'characters.*"([^"]+)".*"([^"]+)"',
                ]

                for j, pattern in enumerate(alt_patterns, 1):
                    if self.debug_enabled:
                        print(f"[DEBUG]   Trying pattern {j}: {pattern}")
                    alt_matches = re.findall(pattern, content, re.IGNORECASE)
                    if self.debug_enabled:
                        print(
                            f"[DEBUG]   Found {len(alt_matches)} matches with pattern {j}"
                        )

                    if alt_matches:
                        for match in alt_matches[:5]:  # Show first 5 matches
                            if self.debug_enabled:
                                print(f"[DEBUG]     Match: {match}")

            if self.debug_enabled:
                print(f"[DEBUG] Returning {len(characters)} parsed characters")
            return characters

        except Exception as e:
            if self.debug_enabled:
                print(f"[DEBUG] ✗ Error parsing Altoholic data: {e}")
            import traceback

            if self.debug_enabled:
                print(f"[DEBUG] Traceback: {traceback.format_exc()}")
            return []

    def update_from_altoholic(self, widget):
        """Update character data from Altoholic addon"""
        if self.debug_enabled:
            print(f"[DEBUG] ========== Starting Altoholic Update ===========")
            print(f"[DEBUG] Current working directory: {os.getcwd()}")
            print(f"[DEBUG] Current character count: {len(self.characters)}")

        altoholic_file = self.find_altoholic_data()

        if not altoholic_file:
            if self.debug_enabled:
                print(f"[DEBUG] ✗ No Altoholic file found")
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

        if self.debug_enabled:
            print(f"[DEBUG] ✓ Found Altoholic file: {altoholic_file}")

        altoholic_chars = self.parse_altoholic_data(altoholic_file)

        if not altoholic_chars:
            if self.debug_enabled:
                print(f"[DEBUG] ✗ No character data parsed from Altoholic file")
            dialog = Gtk.MessageDialog(
                parent=self.window,
                modal=True,
                message_type=Gtk.MessageType.WARNING,
                buttons=Gtk.ButtonsType.OK,
                text="No character data found in Altoholic file.",
            )
            dialog.run()
            dialog.destroy()
            return

        if self.debug_enabled:
            print(f"[DEBUG] ✓ Parsed {len(altoholic_chars)} characters from Altoholic")

        # Update existing characters or add new ones
        updated_count = 0
        added_count = 0

        if self.debug_enabled:
            print(f"[DEBUG] Processing character updates with validation...")

        for i, alt_char in enumerate(altoholic_chars, 1):
            # Validate altoholic character data
            if not isinstance(alt_char, dict):
                if self.debug_enabled:
                    print(f"[DEBUG]   Skipping invalid character data at index {i}")
                continue

            alt_name = str(alt_char.get("name", "")).strip()
            alt_realm = str(alt_char.get("realm", "")).strip()
            alt_ilevel = alt_char.get("item_level", 0)

            # Skip characters with invalid data
            if not alt_name or not alt_realm or alt_ilevel <= 0:
                if self.debug_enabled:
                    print(
                        f"[DEBUG]   Skipping character with invalid data: {alt_name}-{alt_realm} (iLvl: {alt_ilevel})"
                    )
                continue

            if self.debug_enabled:
                print(
                    f"[DEBUG]   Processing {i}/{len(altoholic_chars)}: {alt_name}-{alt_realm} (iLvl: {alt_ilevel})"
                )

            # Look for existing character
            existing_char = None
            for j, char in enumerate(self.characters):
                char_name = char.get("name", "").lower()
                char_realm = char.get("realm", "").lower()

                # Consistent case-insensitive comparison for both name and realm
                if char_name == alt_name.lower() and char_realm == alt_realm.lower():
                    existing_char = char
                    if self.debug_enabled:
                        print(f"[DEBUG]     ✓ Found existing character at index {j}")
                    break

            if existing_char:
                current_ilevel = existing_char.get("item_level", 0)
                if self.debug_enabled:
                    print(
                        f"[DEBUG]     Current iLevel: {current_ilevel}, Altoholic iLevel: {alt_ilevel}"
                    )

                # Update item level if Altoholic has newer data
                if alt_ilevel > current_ilevel:
                    existing_char["item_level"] = alt_ilevel
                    updated_count += 1
                    if self.debug_enabled:
                        print(
                            f"[DEBUG]     ✓ Updated iLevel from {current_ilevel} to {alt_ilevel}"
                        )
                else:
                    if self.debug_enabled:
                        print(f"[DEBUG]     ✗ No update needed (current >= altoholic)")
            else:
                # Add new character
                self.characters.append(alt_char)
                added_count += 1
                if self.debug_enabled:
                    print(f"[DEBUG]     ✓ Added new character")

        if self.debug_enabled:
            print(
                f"[DEBUG] Update summary: Updated {updated_count} characters, added {added_count} new characters"
            )

        if updated_count > 0 or added_count > 0:
            if self.debug_enabled:
                print(f"[DEBUG] Saving data and refreshing table...")
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
            if self.debug_enabled:
                print(f"[DEBUG] ✓ Update completed successfully")
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
            if self.debug_enabled:
                print(f"[DEBUG] ✓ No updates were necessary")

        if self.debug_enabled:
            print(f"[DEBUG] ========== Altoholic Update Complete ===========")

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
                    text="WoW Addon Data Not Found"
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
                    text="No Character Data Found"
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
                    if (char.get("name") == char_name and 
                        char.get("realm") == char_realm):
                        existing_char = i
                        break

                if existing_char is not None:
                    # Update existing character
                    self.characters[existing_char].update(addon_char)
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
            self.populate_treeview()

            # Show success dialog
            dialog = Gtk.MessageDialog(
                parent=self.window,
                flags=0,
                message_type=Gtk.MessageType.INFO,
                buttons=Gtk.ButtonsType.OK,
                text="WoW Addon Import Complete"
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
                text="Import Error"
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
            print(f"[DEBUG] Searching for addon data in {len(possible_paths)} locations")

        for base_path in possible_paths:
            if not os.path.exists(base_path):
                continue
                
            try:
                # Look through account folders
                for account_dir in os.listdir(base_path):
                    if account_dir.startswith("."):
                        continue
                        
                    addon_file = os.path.join(base_path, account_dir, "SavedVariables", "WoWStatTracker.lua")
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
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()

            # Look for the exportData table in the Lua file
            import re
            
            # Find the exportData section
            export_match = re.search(r'exportData\s*=\s*{(.+?)}(?=\s*[},])', content, re.DOTALL)
            if not export_match:
                return []

            export_content = export_match.group(1)
            
            # Look for characters array
            chars_match = re.search(r'characters\s*=\s*{(.+?)}', export_content, re.DOTALL)
            if not chars_match:
                return []

            chars_content = chars_match.group(1)
            
            # Parse character entries
            characters = []
            char_pattern = r'{([^{}]+)}'
            
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
            'name': r'name\s*=\s*"([^"]+)"',
            'realm': r'realm\s*=\s*"([^"]+)"',
            'guild': r'guild\s*=\s*"([^"]*)"',
            'item_level': r'item_level\s*=\s*(\d+)',
            'heroic_items': r'heroic_items\s*=\s*(\d+)',
            'champion_items': r'champion_items\s*=\s*(\d+)',
            'veteran_items': r'veteran_items\s*=\s*(\d+)',
            'adventure_items': r'adventure_items\s*=\s*(\d+)',
            'old_items': r'old_items\s*=\s*(\d+)',
            'vault_visited': r'vault_visited\s*=\s*(true|false)',
            'delves': r'delves\s*=\s*(\d+)',
            'gundarz': r'gundarz\s*=\s*(true|false)',
            'quests': r'quests\s*=\s*(true|false)',
            'timewalk': r'timewalk\s*=\s*(\d+)',
        }
        
        for key, pattern in patterns.items():
            match = re.search(pattern, char_data)
            if match:
                value = match.group(1)
                if key in ['item_level', 'heroic_items', 'champion_items', 'veteran_items', 'adventure_items', 'old_items', 'delves', 'timewalk']:
                    character[key] = int(value)
                elif key in ['vault_visited', 'gundarz', 'quests']:
                    character[key] = value.lower() == 'true'
                else:
                    character[key] = value

        # Only return if we have essential data
        if character.get('name') and character.get('realm'):
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
