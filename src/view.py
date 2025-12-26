"""
View layer for WoW Stat Tracker.
Contains GTK UI components, theming, and display logic.
"""

import gi
import os

gi.require_version("Gtk", "3.0")
from gi.repository import Gtk, GLib

from model import (
    Character,
    COL_REALM,
    COL_NAME,
    COL_GUILD,
    COL_ITEM_LEVEL,
    COL_HEROIC_ITEMS,
    COL_CHAMPION_ITEMS,
    COL_VETERAN_ITEMS,
    COL_ADVENTURE_ITEMS,
    COL_OLD_ITEMS,
    COL_VAULT_VISITED,
    COL_DELVES,
    COL_GILDED_STASH,
    COL_GEARING_UP,
    COL_QUESTS,
    COL_TIMEWALK,
    COL_NOTES,
    COL_INDEX,
    THEME_AUTO,
    THEME_LIGHT,
    THEME_DARK,
    detect_system_theme,
    MAX_ITEM_LEVEL,
    MAX_ITEMS_PER_CATEGORY,
    MAX_DELVES,
    MAX_GILDED_STASH,
    MAX_TIMEWALK,
)


# CSS for dark theme
DARK_CSS = """
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

.notification-badge {
    background-color: #cc3333;
    color: #ffffff;
    border-radius: 8px;
    padding: 1px 5px;
    font-size: 10px;
    font-weight: bold;
    min-width: 14px;
}
"""

# CSS for light theme
LIGHT_CSS = """
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

.notification-badge {
    background-color: #cc3333;
    color: #ffffff;
    border-radius: 8px;
    padding: 1px 5px;
    font-size: 10px;
    font-weight: bold;
    min-width: 14px;
}
"""


class ThemeManager:
    """Manages application theming and CSS."""

    def __init__(self, window: Gtk.Window, theme_preference: str = THEME_AUTO):
        self.window = window
        self.current_preference = theme_preference
        self._css_provider = Gtk.CssProvider()

    @property
    def is_dark(self) -> bool:
        """Check if current theme is dark."""
        if self.current_preference == THEME_AUTO:
            return detect_system_theme()
        return self.current_preference == THEME_DARK

    def apply(self) -> None:
        """Apply the current theme."""
        use_dark = self.is_dark

        # Apply GTK theme preference
        settings = Gtk.Settings.get_default()
        if settings:
            settings.set_property("gtk-application-prefer-dark-theme", use_dark)
            settings.set_property("gtk-theme-name", "Adwaita")

        # Apply custom CSS
        css_data = DARK_CSS if use_dark else LIGHT_CSS

        try:
            self._css_provider.load_from_data(css_data.encode("utf-8"))
            if self.window:
                display = self.window.get_display()
                if display:
                    screen = display.get_default_screen()
                    if screen:
                        Gtk.StyleContext.add_provider_for_screen(
                            screen,
                            self._css_provider,
                            Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION,
                        )
        except Exception as e:
            print(f"[DEBUG] Failed to apply CSS: {e}")

    def set_preference(self, preference: str) -> None:
        """Set theme preference and apply."""
        self.current_preference = preference
        self.apply()


class CharacterTable:
    """GTK TreeView for displaying character data."""

    # Column definitions: (title, data_type, col_id)
    COLUMNS = [
        ("Realm", str, COL_REALM),
        ("Name", str, COL_NAME),
        ("Guild", str, COL_GUILD),
        ("Item Level", int, COL_ITEM_LEVEL),
        ("Heroic Items", int, COL_HEROIC_ITEMS),
        ("Champion Items", int, COL_CHAMPION_ITEMS),
        ("Veteran Items", int, COL_VETERAN_ITEMS),
        ("Adventure Items", int, COL_ADVENTURE_ITEMS),
        ("Old Items", int, COL_OLD_ITEMS),
        ("Vault Visited", bool, COL_VAULT_VISITED),
        ("Delves", int, COL_DELVES),
        ("Gilded", int, COL_GILDED_STASH),
        ("Gearing Up", bool, COL_GEARING_UP),
        ("Quests", bool, COL_QUESTS),
        ("Timewalk", int, COL_TIMEWALK),
        ("Notes", str, COL_NOTES),
        ("Index", int, COL_INDEX),  # Hidden column
    ]

    # Columns with toggleable boolean values
    TOGGLE_COLUMNS = [COL_VAULT_VISITED, COL_GEARING_UP, COL_QUESTS]

    # Weekly activity columns (colored backgrounds)
    WEEKLY_COLUMNS = [
        COL_OLD_ITEMS,
        COL_VAULT_VISITED,
        COL_DELVES,
        COL_GILDED_STASH,
        COL_GEARING_UP,
        COL_QUESTS,
        COL_TIMEWALK,
    ]

    def __init__(
        self,
        theme_manager: ThemeManager,
        on_row_activated=None,
        on_toggle=None,
        on_notes_edited=None,
    ):
        self.theme_manager = theme_manager
        self._on_row_activated = on_row_activated
        self._on_toggle = on_toggle
        self._on_notes_edited = on_notes_edited

        # Create list store
        self.store = Gtk.ListStore(
            str,  # realm
            str,  # name
            str,  # guild
            float,  # item_level
            int,  # heroic_items
            int,  # champion_items
            int,  # veteran_items
            int,  # adventure_items
            int,  # old_items
            bool,  # vault_visited
            int,  # delves
            int,  # gilded_stash
            bool,  # gearing_up
            bool,  # quests
            int,  # timewalk
            str,  # notes
            int,  # index (hidden)
        )

        # Create tree view
        self.treeview = Gtk.TreeView(model=self.store)
        # External dict tracks visual sort order (keyed by "name-realm")
        # This avoids modifying the model which would trigger recursive sorts
        self._sort_indices = {}
        self._setup_sort_functions()
        self._setup_columns()

        if on_row_activated:
            self.treeview.connect("row-activated", self._handle_row_activated)

    def _setup_sort_functions(self) -> None:
        """Set up stable sort functions for all columns."""
        for _, _, col_id in self.COLUMNS:
            if col_id == COL_INDEX:
                continue  # Don't set sort func for index column
            self.store.set_sort_func(col_id, self._stable_sort_func, col_id)
        # Update sort indices after each sort to enable true stable sorting
        self.store.connect("sort-column-changed", self._on_sort_changed)

    def _on_sort_changed(self, model) -> None:
        """Update sort indices after sort completes."""
        # Defer to after sort completes
        GLib.idle_add(self._update_sort_indices)

    def _update_sort_indices(self) -> bool:
        """Update external sort indices dict to reflect current visual order."""
        for i, row in enumerate(self.store):
            key = f"{row[COL_NAME]}-{row[COL_REALM]}"
            self._sort_indices[key] = i
        return False  # Don't repeat

    def _stable_sort_func(self, model, iter1, iter2, col_id) -> int:
        """Compare two rows by column value, using previous sort order as tiebreaker."""
        val1 = model[iter1][col_id]
        val2 = model[iter2][col_id]

        # Primary comparison
        if val1 < val2:
            return -1
        elif val1 > val2:
            return 1
        else:
            # Tiebreaker: use sort indices dict to preserve previous order
            key1 = f"{model[iter1][COL_NAME]}-{model[iter1][COL_REALM]}"
            key2 = f"{model[iter2][COL_NAME]}-{model[iter2][COL_REALM]}"
            idx1 = self._sort_indices.get(key1, 0)
            idx2 = self._sort_indices.get(key2, 0)
            return idx1 - idx2

    def _setup_columns(self) -> None:
        """Create and configure all columns."""
        for title, data_type, col_id in self.COLUMNS:
            if data_type == bool and col_id in self.TOGGLE_COLUMNS:
                renderer = Gtk.CellRendererToggle()
                renderer.set_property("activatable", True)
                renderer.connect("toggled", self._handle_toggle, col_id)
                column = Gtk.TreeViewColumn(title, renderer, active=col_id)
            else:
                renderer = Gtk.CellRendererText()
                if col_id == COL_NOTES:
                    renderer.set_property("editable", True)
                    renderer.connect("edited", self._handle_notes_edited, col_id)
                column = Gtk.TreeViewColumn(title, renderer, text=col_id)

                # Apply cell data function for weekly columns and item level
                if col_id in self.WEEKLY_COLUMNS:
                    column.set_cell_data_func(renderer, self._cell_data_func, col_id)
                elif col_id == COL_ITEM_LEVEL:
                    column.set_cell_data_func(
                        renderer, self._item_level_cell_func, col_id
                    )
                elif col_id == COL_INDEX:
                    column.set_visible(False)

            column.set_sort_column_id(col_id)
            column.set_clickable(True)
            column.set_resizable(True)
            self.treeview.append_column(column)

    def _cell_data_func(self, column, cell, model, iter, col_id):
        """Color cells based on weekly activity status."""
        delves = model[iter][COL_DELVES]
        gearing_up = model[iter][COL_GEARING_UP]
        quests = model[iter][COL_QUESTS]
        timewalk = model[iter][COL_TIMEWALK]
        vault_visited = model[iter][COL_VAULT_VISITED]

        use_dark = self.theme_manager.is_dark

        def set_cell_colors(bg_color):
            cell.set_property("background", bg_color)
            if use_dark:
                # Use black text on light backgrounds for readability
                if bg_color in ["#90EE90", "#FFFFE0", "#F08080"]:
                    cell.set_property("foreground", "#000000")
                else:
                    cell.set_property("foreground", "#ffffff")
            else:
                cell.set_property("foreground", "#000000")

        # Determine completion for weekly items
        delves_done = delves >= 4  # 4+ delves = completed
        all_weeklies_done = gearing_up and quests and delves_done

        if col_id == COL_VAULT_VISITED:
            # Vault column: green if visited, red if not visited but weeklies done
            if vault_visited:
                set_cell_colors("#90EE90")  # Light green
            elif all_weeklies_done:
                set_cell_colors("#F08080")  # Light red - should visit vault
            else:
                set_cell_colors(
                    "#FFFFE0" if not use_dark else "#3c3c3c"
                )  # Light yellow or dark bg

        elif col_id == COL_DELVES:
            # Delves: green if 4+, yellow if partial, default otherwise
            if delves >= 4:
                set_cell_colors("#90EE90")  # Light green
            elif delves > 0:
                set_cell_colors("#FFFFE0")  # Light yellow
            else:
                set_cell_colors("#ffffff" if not use_dark else "#3c3c3c")

        elif col_id == COL_GILDED_STASH:
            # Gilded stash: green if 3, yellow if 1-2, red if 0
            gilded = model[iter][COL_GILDED_STASH]
            if gilded >= 3:
                set_cell_colors("#90EE90")  # Light green
            elif gilded > 0:
                set_cell_colors("#FFFFE0")  # Light yellow
            else:
                set_cell_colors("#F08080")  # Light red

        elif col_id in [COL_GEARING_UP, COL_QUESTS]:
            # Boolean weeklies: green if done, yellow if not
            value = model[iter][col_id]
            if value:
                set_cell_colors("#90EE90")  # Light green
            else:
                set_cell_colors("#FFFFE0" if not use_dark else "#3c3c3c")

        elif col_id == COL_TIMEWALK:
            # Timewalk: green if 5, yellow if partial
            if timewalk >= 5:
                set_cell_colors("#90EE90")  # Light green
            elif timewalk > 0:
                set_cell_colors("#FFFFE0")  # Light yellow
            else:
                set_cell_colors("#ffffff" if not use_dark else "#3c3c3c")

        elif col_id == COL_OLD_ITEMS:
            # Old items: just use default background
            set_cell_colors("#ffffff" if not use_dark else "#3c3c3c")

    def _item_level_cell_func(self, column, cell, model, iter, col_id):
        """Format item level with one decimal place."""
        value = model[iter][col_id]
        cell.set_property("text", f"{value:.1f}")

    def _handle_row_activated(self, treeview, path, column):
        """Handle row double-click."""
        if self._on_row_activated:
            iter = self.store.get_iter(path)
            index = self.store[iter][COL_INDEX]
            self._on_row_activated(index)

    def _handle_toggle(self, widget, path, col_id):
        """Handle toggle click."""
        if self._on_toggle:
            iter = self.store.get_iter(path)
            index = self.store[iter][COL_INDEX]
            current_value = self.store[iter][col_id]
            self._on_toggle(index, col_id, not current_value)

    def _handle_notes_edited(self, widget, path, new_text, col_id):
        """Handle notes cell edited."""
        if self._on_notes_edited:
            iter = self.store.get_iter(path)
            index = self.store[iter][COL_INDEX]
            self._on_notes_edited(index, new_text)

    def populate(self, characters: list[Character]) -> None:
        """Populate table with character data."""
        self.store.clear()
        self._sort_indices.clear()
        for i, char in enumerate(characters):
            self.store.append(
                [
                    char.realm,
                    char.name,
                    char.guild,
                    char.item_level,
                    char.heroic_items,
                    char.champion_items,
                    char.veteran_items,
                    char.adventure_items,
                    char.old_items,
                    char.vault_visited,
                    char.delves,
                    char.gilded_stash,
                    char.gearing_up,
                    char.quests,
                    char.timewalk,
                    char.notes,
                    i,  # Store original index for data store lookup
                ]
            )
            # Initialize sort index for stable sorting
            key = f"{char.name}-{char.realm}"
            self._sort_indices[key] = i

    def update_row(self, index: int, char: Character) -> None:
        """Update a single row."""
        for row in self.store:
            if row[COL_INDEX] == index:
                row[COL_REALM] = char.realm
                row[COL_NAME] = char.name
                row[COL_GUILD] = char.guild
                row[COL_ITEM_LEVEL] = char.item_level
                row[COL_HEROIC_ITEMS] = char.heroic_items
                row[COL_CHAMPION_ITEMS] = char.champion_items
                row[COL_VETERAN_ITEMS] = char.veteran_items
                row[COL_ADVENTURE_ITEMS] = char.adventure_items
                row[COL_OLD_ITEMS] = char.old_items
                row[COL_VAULT_VISITED] = char.vault_visited
                row[COL_DELVES] = char.delves
                row[COL_GILDED_STASH] = char.gilded_stash
                row[COL_GEARING_UP] = char.gearing_up
                row[COL_QUESTS] = char.quests
                row[COL_TIMEWALK] = char.timewalk
                row[COL_NOTES] = char.notes
                break

    def refresh_backgrounds(self) -> None:
        """Refresh cell backgrounds (e.g., after theme change)."""
        # Force redraw by emitting row-changed for each row
        for row in self.store:
            path = row.path
            iter = self.store.get_iter(path)
            self.store.row_changed(path, iter)

    def get_column_widths(self) -> dict:
        """Get current column widths."""
        widths = {}
        for i, column in enumerate(self.treeview.get_columns()):
            widths[str(i)] = column.get_width()
        return widths

    def set_column_widths(self, widths: dict) -> None:
        """Set column widths from config."""
        columns = self.treeview.get_columns()
        for col_id_str, width in widths.items():
            try:
                col_id = int(col_id_str)
                if 0 <= col_id < len(columns) and width > 0:
                    columns[col_id].set_fixed_width(width)
            except (ValueError, IndexError):
                pass

    def get_sort_order(self) -> tuple:
        """Get current sort column and order."""
        sort_col, sort_order = self.store.get_sort_column_id()
        return (sort_col, sort_order)

    def set_sort_order(self, column_id: int, order: Gtk.SortType) -> None:
        """Set sort column and order."""
        if column_id is not None:
            self.store.set_sort_column_id(column_id, order)


class CharacterDialog:
    """Dialog for editing or adding a character."""

    # Field configuration: (key, label, type, default, max_value or None)
    FIELD_CONFIGS = [
        ("realm", "Realm", str, "", None),
        ("name", "Name", str, "", None),
        ("guild", "Guild", str, "", None),
        ("item_level", "Item Level", float, 0.0, MAX_ITEM_LEVEL),
        ("heroic_items", "Heroic Items", int, 0, MAX_ITEMS_PER_CATEGORY),
        ("champion_items", "Champion Items", int, 0, MAX_ITEMS_PER_CATEGORY),
        ("veteran_items", "Veteran Items", int, 0, MAX_ITEMS_PER_CATEGORY),
        ("adventure_items", "Adventure Items", int, 0, MAX_ITEMS_PER_CATEGORY),
        ("old_items", "Old Items", int, 0, MAX_ITEMS_PER_CATEGORY),
        ("vault_visited", "Vault Visited", bool, False, None),
        ("delves", "Delves (0-8)", int, 0, MAX_DELVES),
        ("gilded_stash", "Gilded Stash (0-3)", int, 0, MAX_GILDED_STASH),
        ("gearing_up", "Gearing Up for Trouble", bool, False, None),
        ("quests", "World Quests", bool, False, None),
        ("timewalk", "Timewalk (0-5)", int, 0, MAX_TIMEWALK),
        ("notes", "Notes", str, "", None),
    ]

    def __init__(self, parent: Gtk.Window):
        self.parent = parent
        self.entries = {}

    def show_edit(self, character: Character = None) -> Character | None:
        """Show dialog to edit or add a character. Returns updated Character or None."""
        is_new = character is None
        if is_new:
            character = Character()

        dialog = Gtk.Dialog(
            title="Add Character" if is_new else "Edit Character",
            parent=self.parent,
            modal=True,
        )
        dialog.add_button("Cancel", Gtk.ResponseType.CANCEL)
        dialog.add_button("Save", Gtk.ResponseType.OK)

        if not is_new:
            delete_button = dialog.add_button("Delete", Gtk.ResponseType.REJECT)
            delete_button.get_style_context().add_class("destructive-action")

        content = dialog.get_content_area()
        content.set_spacing(10)
        content.set_margin_start(10)
        content.set_margin_end(10)
        content.set_margin_top(10)
        content.set_margin_bottom(10)

        grid = Gtk.Grid()
        grid.set_column_spacing(10)
        grid.set_row_spacing(5)
        content.add(grid)

        self.entries = {}

        for row, (key, label, field_type, default, max_val) in enumerate(
            self.FIELD_CONFIGS
        ):
            lbl = Gtk.Label(label=label + ":")
            lbl.set_halign(Gtk.Align.END)
            grid.attach(lbl, 0, row, 1, 1)

            current_value = getattr(character, key, default)

            if field_type == bool:
                entry = Gtk.CheckButton()
                entry.set_active(current_value)
            elif field_type == int:
                entry = Gtk.SpinButton()
                entry.set_adjustment(
                    Gtk.Adjustment(
                        value=current_value,
                        lower=0,
                        upper=max_val or 9999,
                        step_increment=1,
                    )
                )
                entry.set_value(current_value)
            elif field_type == float:
                entry = Gtk.SpinButton()
                entry.set_adjustment(
                    Gtk.Adjustment(
                        value=current_value,
                        lower=0,
                        upper=max_val or 9999,
                        step_increment=0.1,
                    )
                )
                entry.set_digits(1)
                entry.set_value(current_value)
            else:
                entry = Gtk.Entry()
                entry.set_text(str(current_value))
                entry.set_hexpand(True)

            grid.attach(entry, 1, row, 1, 1)
            self.entries[key] = (entry, field_type)

        dialog.show_all()
        response = dialog.run()

        result = None
        if response == Gtk.ResponseType.OK:
            # Collect values
            result = Character()
            for key, (entry, field_type) in self.entries.items():
                if field_type == bool:
                    value = entry.get_active()
                elif field_type == int:
                    value = int(entry.get_value())
                elif field_type == float:
                    value = entry.get_value()
                else:
                    value = entry.get_text()
                setattr(result, key, value)

            # Validate
            errors = result.validate()
            if errors:
                self._show_validation_errors(dialog, errors)
                dialog.destroy()
                return None

        elif response == Gtk.ResponseType.REJECT:
            # Delete requested
            if self.show_delete_confirm(character):
                result = "DELETE"
            else:
                result = None

        dialog.destroy()
        return result

    def show_delete_confirm(self, character: Character) -> bool:
        """Show delete confirmation dialog. Returns True if confirmed."""
        dialog = Gtk.MessageDialog(
            parent=self.parent,
            modal=True,
            message_type=Gtk.MessageType.WARNING,
            buttons=Gtk.ButtonsType.YES_NO,
            text=f"Delete {character.name} ({character.realm})?",
        )
        dialog.format_secondary_text("This action cannot be undone.")
        response = dialog.run()
        dialog.destroy()
        return response == Gtk.ResponseType.YES

    def _show_validation_errors(self, parent: Gtk.Widget, errors: list[str]) -> None:
        """Show validation error dialog."""
        dialog = Gtk.MessageDialog(
            parent=parent,
            modal=True,
            message_type=Gtk.MessageType.ERROR,
            buttons=Gtk.ButtonsType.OK,
            text="Validation Error",
        )
        dialog.format_secondary_text("\n".join(errors))
        dialog.run()
        dialog.destroy()


def show_message(
    parent: Gtk.Window,
    message_type: Gtk.MessageType,
    title: str,
    secondary: str = None,
) -> None:
    """Show a message dialog."""
    dialog = Gtk.MessageDialog(
        parent=parent,
        modal=True,
        message_type=message_type,
        buttons=Gtk.ButtonsType.OK,
        text=title,
    )
    if secondary:
        dialog.format_secondary_text(secondary)
    dialog.run()
    dialog.destroy()


def show_error(parent: Gtk.Window, title: str, message: str) -> None:
    """Show an error dialog."""
    show_message(parent, Gtk.MessageType.ERROR, title, message)


def show_warning(parent: Gtk.Window, title: str, message: str) -> None:
    """Show a warning dialog."""
    show_message(parent, Gtk.MessageType.WARNING, title, message)


def show_info(parent: Gtk.Window, title: str, message: str) -> None:
    """Show an info dialog."""
    show_message(parent, Gtk.MessageType.INFO, title, message)


def show_folder_chooser(
    parent: Gtk.Window,
    title: str,
    initial_folder: str = None,
) -> str | None:
    """Show a folder chooser dialog. Returns selected path or None if cancelled."""
    dialog = Gtk.FileChooserDialog(
        title=title,
        parent=parent,
        action=Gtk.FileChooserAction.SELECT_FOLDER,
    )
    dialog.add_button("Cancel", Gtk.ResponseType.CANCEL)
    dialog.add_button("Select", Gtk.ResponseType.OK)

    if initial_folder and os.path.exists(initial_folder):
        dialog.set_current_folder(initial_folder)

    response = dialog.run()
    result = dialog.get_filename() if response == Gtk.ResponseType.OK else None
    dialog.destroy()
    return result


# Toolbar style constants
TOOLBAR_BOTH = "both"
TOOLBAR_ICONS = "icons"
TOOLBAR_TEXT = "text"
TOOLBAR_HIDDEN = "hidden"


class ManualDialog:
    """Dialog for displaying the user manual."""

    def __init__(self, parent: Gtk.Window):
        self.parent = parent

    def show(self, manual_text: str) -> None:
        """Show the manual dialog."""
        dialog = Gtk.Dialog(
            title="User Manual",
            parent=self.parent,
            modal=False,
        )
        dialog.add_button("Close", Gtk.ResponseType.CLOSE)
        dialog.set_default_size(600, 500)

        content = dialog.get_content_area()
        content.set_margin_start(10)
        content.set_margin_end(10)
        content.set_margin_top(10)
        content.set_margin_bottom(10)

        # Scrolled window for the text
        scrolled = Gtk.ScrolledWindow()
        scrolled.set_policy(Gtk.PolicyType.AUTOMATIC, Gtk.PolicyType.AUTOMATIC)
        scrolled.set_vexpand(True)
        scrolled.set_hexpand(True)
        content.pack_start(scrolled, True, True, 0)

        # Text view with monospace font for nice formatting
        textview = Gtk.TextView()
        textview.set_editable(False)
        textview.set_cursor_visible(False)
        textview.set_wrap_mode(Gtk.WrapMode.WORD)
        textview.set_left_margin(10)
        textview.set_right_margin(10)
        textview.set_top_margin(10)
        textview.set_bottom_margin(10)

        # Use monospace font for consistent formatting
        font_desc = textview.get_pango_context().get_font_description()
        font_desc.set_family("monospace")
        textview.override_font(font_desc)

        buffer = textview.get_buffer()
        buffer.set_text(manual_text)

        scrolled.add(textview)

        dialog.show_all()
        dialog.run()
        dialog.destroy()


class PropertiesDialog:
    """Dialog for application properties/settings."""

    THEME_OPTIONS = [
        (THEME_AUTO, "Auto (System)"),
        (THEME_LIGHT, "Light"),
        (THEME_DARK, "Dark"),
    ]

    TOOLBAR_OPTIONS = [
        (TOOLBAR_BOTH, "Icons and Text"),
        (TOOLBAR_ICONS, "Icons Only"),
        (TOOLBAR_TEXT, "Text Only"),
        (TOOLBAR_HIDDEN, "Hidden"),
    ]

    def __init__(self, parent: Gtk.Window):
        self.parent = parent
        self.result = None

    def show(
        self,
        wow_path: str = "",
        theme: str = THEME_AUTO,
        toolbar_style: str = TOOLBAR_BOTH,
        auto_import: bool = False,
        check_updates: bool = False,
        on_browse_path=None,
    ) -> dict | None:
        """Show properties dialog. Returns dict of settings or None if cancelled."""
        dialog = Gtk.Dialog(
            title="Properties",
            parent=self.parent,
            modal=True,
        )
        dialog.add_button("Cancel", Gtk.ResponseType.CANCEL)
        dialog.add_button("OK", Gtk.ResponseType.OK)
        dialog.set_default_size(450, -1)

        content = dialog.get_content_area()
        content.set_spacing(15)
        content.set_margin_start(15)
        content.set_margin_end(15)
        content.set_margin_top(15)
        content.set_margin_bottom(15)

        # Game Location section
        location_frame = Gtk.Frame(label=" Game Location ")
        location_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)
        location_box.set_margin_start(10)
        location_box.set_margin_end(10)
        location_box.set_margin_top(10)
        location_box.set_margin_bottom(10)
        location_frame.add(location_box)

        self.path_entry = Gtk.Entry()
        self.path_entry.set_text(wow_path)
        self.path_entry.set_hexpand(True)
        self.path_entry.set_placeholder_text("World of Warcraft installation path")
        location_box.pack_start(self.path_entry, True, True, 0)

        browse_btn = Gtk.Button(label="Browse...")
        browse_btn.connect("clicked", self._on_browse_clicked, on_browse_path)
        location_box.pack_start(browse_btn, False, False, 0)

        content.pack_start(location_frame, False, False, 0)

        # Appearance section
        appearance_frame = Gtk.Frame(label=" Appearance ")
        appearance_grid = Gtk.Grid()
        appearance_grid.set_column_spacing(15)
        appearance_grid.set_row_spacing(10)
        appearance_grid.set_margin_start(10)
        appearance_grid.set_margin_end(10)
        appearance_grid.set_margin_top(10)
        appearance_grid.set_margin_bottom(10)
        appearance_frame.add(appearance_grid)

        # Theme
        theme_label = Gtk.Label(label="Theme:")
        theme_label.set_halign(Gtk.Align.END)
        appearance_grid.attach(theme_label, 0, 0, 1, 1)

        self.theme_combo = Gtk.ComboBoxText()
        for value, label in self.THEME_OPTIONS:
            self.theme_combo.append(value, label)
        self.theme_combo.set_active_id(theme)
        self.theme_combo.set_hexpand(True)
        appearance_grid.attach(self.theme_combo, 1, 0, 1, 1)

        # Toolbar style
        toolbar_label = Gtk.Label(label="Toolbar:")
        toolbar_label.set_halign(Gtk.Align.END)
        appearance_grid.attach(toolbar_label, 0, 1, 1, 1)

        self.toolbar_combo = Gtk.ComboBoxText()
        for value, label in self.TOOLBAR_OPTIONS:
            self.toolbar_combo.append(value, label)
        self.toolbar_combo.set_active_id(toolbar_style)
        appearance_grid.attach(self.toolbar_combo, 1, 1, 1, 1)

        content.pack_start(appearance_frame, False, False, 0)

        # Behavior section
        behavior_frame = Gtk.Frame(label=" Behavior ")
        behavior_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
        behavior_box.set_margin_start(10)
        behavior_box.set_margin_end(10)
        behavior_box.set_margin_top(10)
        behavior_box.set_margin_bottom(10)
        behavior_frame.add(behavior_box)

        self.auto_import_check = Gtk.CheckButton(label="Auto-import when window is focused")
        self.auto_import_check.set_active(auto_import)
        behavior_box.pack_start(self.auto_import_check, False, False, 0)

        self.check_updates_check = Gtk.CheckButton(label="Check for updates on startup")
        self.check_updates_check.set_active(check_updates)
        behavior_box.pack_start(self.check_updates_check, False, False, 0)

        content.pack_start(behavior_frame, False, False, 0)

        dialog.show_all()
        response = dialog.run()

        result = None
        if response == Gtk.ResponseType.OK:
            result = {
                "wow_path": self.path_entry.get_text().strip(),
                "theme": self.theme_combo.get_active_id(),
                "toolbar_style": self.toolbar_combo.get_active_id(),
                "auto_import": self.auto_import_check.get_active(),
                "check_updates": self.check_updates_check.get_active(),
            }

        dialog.destroy()
        return result

    def _on_browse_clicked(self, button, callback):
        """Handle browse button click."""
        current = self.path_entry.get_text().strip()
        path = show_folder_chooser(
            self.parent,
            "Select World of Warcraft Folder",
            initial_folder=current if current and os.path.exists(current) else None,
        )
        if path:
            # Validate it looks like a WoW installation
            if os.path.exists(os.path.join(path, "_retail_")):
                self.path_entry.set_text(path)
            elif callback:
                callback(path)  # Let caller handle validation message
