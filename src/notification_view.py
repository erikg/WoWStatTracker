"""
Notification view layer for WoW Stat Tracker.
Contains StatusBar and NotificationHistoryPopover GTK widgets.
"""

import gi

gi.require_version("Gtk", "3.0")
gi.require_version("PangoCairo", "1.0")
from gi.repository import Gtk, GLib, Pango, PangoCairo

from notification_model import (
    Notification,
    NOTIFY_INFO,
    NOTIFY_SUCCESS,
    NOTIFY_WARNING,
)


# Status bar configuration
AUTO_DISMISS_MS = 5000  # 5 seconds
SCROLL_INTERVAL_MS = 50  # Chyron scroll speed
SCROLL_STEP_PX = 2  # Pixels per scroll step
MAX_LABEL_WIDTH = 500  # Threshold for chyron mode


class StatusBar(Gtk.Box):
    """Status bar widget displaying notifications with auto-dismiss and scrolling."""

    def __init__(self, on_history_clicked=None):
        super().__init__(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        self._on_history_clicked = on_history_clicked

        # Animation state
        self._scroll_offset = 0
        self._scroll_timer_id = None
        self._dismiss_timer_id = None
        self._notification_queue = []
        self._current_message = None
        self._text_width = 0
        self._is_scrolling = False

        self._setup_ui()

    def _setup_ui(self) -> None:
        """Set up the status bar UI layout."""
        self.set_margin_start(6)
        self.set_margin_end(6)
        self.set_margin_top(0)
        self.set_margin_bottom(0)

        # Left: Icon for notification type
        self._icon = Gtk.Image()
        self._icon.set_from_icon_name("dialog-information", Gtk.IconSize.MENU)
        self._icon.set_no_show_all(True)
        self.pack_start(self._icon, False, False, 0)

        # Center: Message label in a clipped container for scrolling
        self._scroll_container = Gtk.DrawingArea()
        self._scroll_container.set_hexpand(True)
        self._scroll_container.set_size_request(-1, 10)
        self._scroll_container.connect("draw", self._on_draw)
        self._scroll_container.set_no_show_all(True)
        self.pack_start(self._scroll_container, True, True, 0)

        # Right side container for history button
        right_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=2)
        self.pack_end(right_box, False, False, 0)

        # History button with badge overlay
        self._history_button = Gtk.Button()
        self._history_button.set_relief(Gtk.ReliefStyle.NONE)
        self._history_button.set_tooltip_text("Notification History")
        self._history_button.set_size_request(-1, 16)
        self._history_button.connect("clicked", self._on_history_button_clicked)

        # Button content: icon and badge
        button_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=1)
        history_icon = Gtk.Image.new_from_icon_name("document-open-recent", Gtk.IconSize.MENU)
        button_box.pack_start(history_icon, False, False, 0)

        # Badge for unread count
        self._badge = Gtk.Label()
        self._badge.set_no_show_all(True)
        self._badge.get_style_context().add_class("notification-badge")
        button_box.pack_start(self._badge, False, False, 0)

        self._history_button.add(button_box)
        right_box.pack_start(self._history_button, False, False, 0)

        # Store message text and layout for drawing
        self._message_text = ""
        self._pango_layout = None

    def _on_draw(self, widget, cr) -> bool:
        """Draw the scrolling notification text."""
        if not self._message_text:
            return False

        allocation = widget.get_allocation()

        # Get Pango layout for text measurement and drawing
        if self._pango_layout is None:
            self._pango_layout = widget.create_pango_layout(self._message_text)
            self._pango_layout.set_font_description(
                Pango.FontDescription.from_string("Sans 10")
            )
            self._text_width, text_height = self._pango_layout.get_pixel_size()

        # Get text color from style context
        style = widget.get_style_context()
        color = style.get_color(Gtk.StateFlags.NORMAL)
        cr.set_source_rgba(color.red, color.green, color.blue, color.alpha)

        # Calculate vertical centering
        _, text_height = self._pango_layout.get_pixel_size()
        y = (allocation.height - text_height) / 2

        # Draw text with scroll offset
        cr.move_to(-self._scroll_offset, y)
        PangoCairo.show_layout(cr, self._pango_layout)

        return False

    def show_notification(self, message: str, notification_type: str = NOTIFY_INFO) -> None:
        """Display a notification, queuing if one is already showing."""
        if self._current_message is not None:
            # Queue this notification
            self._notification_queue.append((message, notification_type))
            return

        self._display_notification(message, notification_type)

    def _display_notification(self, message: str, notification_type: str) -> None:
        """Actually display a notification."""
        self._stop_animations()

        self._current_message = message
        self._message_text = message
        self._pango_layout = None  # Reset layout for new text
        self._scroll_offset = 0

        # Set icon based on type
        self._set_icon_for_type(notification_type)

        # Show the notification elements
        self._icon.show()
        self._scroll_container.show()
        self._scroll_container.queue_draw()

        # Measure text width after layout is created
        GLib.idle_add(self._check_scroll_needed)

        # Start auto-dismiss timer
        self._dismiss_timer_id = GLib.timeout_add(
            AUTO_DISMISS_MS, self._on_dismiss_timeout
        )

    def _check_scroll_needed(self) -> bool:
        """Check if scrolling is needed and start if so."""
        if self._pango_layout is None:
            # Create layout to measure
            self._pango_layout = self._scroll_container.create_pango_layout(self._message_text)
            self._pango_layout.set_font_description(
                Pango.FontDescription.from_string("Sans 10")
            )
            self._text_width, _ = self._pango_layout.get_pixel_size()

        allocation = self._scroll_container.get_allocation()
        if self._text_width > allocation.width and allocation.width > 0:
            self._start_chyron_scroll()

        return False  # Don't repeat

    def _start_chyron_scroll(self) -> None:
        """Start chyron scrolling for long messages."""
        if self._scroll_timer_id is not None:
            return  # Already scrolling

        self._is_scrolling = True
        self._scroll_timer_id = GLib.timeout_add(
            SCROLL_INTERVAL_MS, self._on_scroll_tick
        )

    def _on_scroll_tick(self) -> bool:
        """Handle scroll animation tick."""
        if not self._is_scrolling:
            return False

        allocation = self._scroll_container.get_allocation()
        max_scroll = self._text_width - allocation.width + 50  # Extra padding

        self._scroll_offset += SCROLL_STEP_PX

        # Reset to beginning when we've scrolled past the end
        if self._scroll_offset > max_scroll:
            self._scroll_offset = -allocation.width  # Start from right side

        self._scroll_container.queue_draw()
        return True  # Continue animation

    def _on_dismiss_timeout(self) -> bool:
        """Handle auto-dismiss timeout."""
        self._dismiss_timer_id = None
        self._hide_notification()
        return False  # Don't repeat

    def _hide_notification(self) -> None:
        """Hide the current notification and show next if queued."""
        self._stop_animations()
        self._current_message = None
        self._message_text = ""
        self._pango_layout = None

        self._icon.hide()
        self._scroll_container.hide()

        # Show next queued notification if any
        if self._notification_queue:
            message, notification_type = self._notification_queue.pop(0)
            # Use idle_add to avoid recursion issues
            GLib.idle_add(lambda: self._display_notification(message, notification_type))

    def _stop_animations(self) -> None:
        """Stop all running timers."""
        if self._scroll_timer_id is not None:
            GLib.source_remove(self._scroll_timer_id)
            self._scroll_timer_id = None

        if self._dismiss_timer_id is not None:
            GLib.source_remove(self._dismiss_timer_id)
            self._dismiss_timer_id = None

        self._is_scrolling = False
        self._scroll_offset = 0

    def _set_icon_for_type(self, notification_type: str) -> None:
        """Set the status bar icon based on notification type."""
        if notification_type == NOTIFY_SUCCESS:
            icon_name = "emblem-ok-symbolic"
        elif notification_type == NOTIFY_WARNING:
            icon_name = "dialog-warning-symbolic"
        else:
            icon_name = "dialog-information-symbolic"

        self._icon.set_from_icon_name(icon_name, Gtk.IconSize.SMALL_TOOLBAR)

    def update_badge(self, count: int) -> None:
        """Update the unread notification badge."""
        if count > 0:
            self._badge.set_text(str(min(count, 99)))  # Cap at 99
            self._badge.show()
        else:
            self._badge.hide()

    def _on_history_button_clicked(self, button) -> None:
        """Handle history button click."""
        if self._on_history_clicked:
            self._on_history_clicked()

    def get_history_button(self) -> Gtk.Button:
        """Get the history button widget for popover positioning."""
        return self._history_button

    def cleanup(self) -> None:
        """Clean up timers on destruction."""
        self._stop_animations()


class NotificationHistoryPopover(Gtk.Popover):
    """Popover showing notification history with clear/delete options."""

    def __init__(self, relative_to: Gtk.Widget, on_clear_all=None, on_remove=None):
        super().__init__()
        self.set_relative_to(relative_to)
        self._on_clear_all = on_clear_all
        self._on_remove = on_remove
        self._notifications = []

        self._setup_ui()

    def _setup_ui(self) -> None:
        """Set up the popover UI."""
        self.set_size_request(450, -1)

        main_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
        main_box.set_margin_start(8)
        main_box.set_margin_end(8)
        main_box.set_margin_top(8)
        main_box.set_margin_bottom(8)

        # Header with title and clear button
        header_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)

        title = Gtk.Label(label="Notifications")
        title.set_xalign(0)
        title.get_style_context().add_class("title")
        header_box.pack_start(title, True, True, 0)

        self._clear_button = Gtk.Button(label="Clear All")
        self._clear_button.connect("clicked", self._on_clear_clicked)
        header_box.pack_end(self._clear_button, False, False, 0)

        main_box.pack_start(header_box, False, False, 0)

        # Separator
        separator = Gtk.Separator(orientation=Gtk.Orientation.HORIZONTAL)
        main_box.pack_start(separator, False, False, 0)

        # Scrolled list of notifications
        scrolled = Gtk.ScrolledWindow()
        scrolled.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        scrolled.set_min_content_height(150)
        scrolled.set_max_content_height(400)

        self._list_box = Gtk.ListBox()
        self._list_box.set_selection_mode(Gtk.SelectionMode.NONE)
        scrolled.add(self._list_box)

        main_box.pack_start(scrolled, True, True, 0)

        # Empty state label
        self._empty_label = Gtk.Label(label="No notifications")
        self._empty_label.set_sensitive(False)
        self._empty_label.set_margin_top(20)
        self._empty_label.set_margin_bottom(20)
        main_box.pack_start(self._empty_label, True, True, 0)

        self.add(main_box)
        main_box.show_all()

    def populate(self, notifications: list) -> None:
        """Populate the list with notifications."""
        self._notifications = notifications

        # Clear existing rows
        for child in self._list_box.get_children():
            self._list_box.remove(child)

        if not notifications:
            self._empty_label.show()
            self._list_box.hide()
            self._clear_button.set_sensitive(False)
        else:
            self._empty_label.hide()
            self._list_box.show()
            self._clear_button.set_sensitive(True)

            for notification in notifications:
                row = self._create_notification_row(notification)
                self._list_box.add(row)

            self._list_box.show_all()

    def _create_notification_row(self, notification: Notification) -> Gtk.ListBoxRow:
        """Create a row widget for a notification."""
        row = Gtk.ListBoxRow()
        row.set_activatable(False)

        box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        box.set_margin_top(4)
        box.set_margin_bottom(4)

        # Type icon
        if notification.notification_type == NOTIFY_SUCCESS:
            icon_name = "emblem-ok-symbolic"
        elif notification.notification_type == NOTIFY_WARNING:
            icon_name = "dialog-warning-symbolic"
        else:
            icon_name = "dialog-information-symbolic"

        icon = Gtk.Image.new_from_icon_name(icon_name, Gtk.IconSize.SMALL_TOOLBAR)
        box.pack_start(icon, False, False, 0)

        # Time and message
        content_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=2)

        time_label = Gtk.Label(label=notification.format_timestamp())
        time_label.set_xalign(0)
        time_label.set_sensitive(False)
        time_label.get_style_context().add_class("dim-label")
        content_box.pack_start(time_label, False, False, 0)

        message_label = Gtk.Label(label=notification.message)
        message_label.set_xalign(0)
        message_label.set_line_wrap(True)
        message_label.set_max_width_chars(40)
        content_box.pack_start(message_label, False, False, 0)

        box.pack_start(content_box, True, True, 0)

        # Delete button
        delete_button = Gtk.Button()
        delete_button.set_relief(Gtk.ReliefStyle.NONE)
        delete_icon = Gtk.Image.new_from_icon_name("window-close-symbolic", Gtk.IconSize.SMALL_TOOLBAR)
        delete_button.add(delete_icon)
        delete_button.set_tooltip_text("Remove this notification")
        delete_button.connect("clicked", self._on_delete_clicked, notification.id, row)
        box.pack_end(delete_button, False, False, 0)

        row.add(box)
        return row

    def _on_clear_clicked(self, button) -> None:
        """Handle Clear All button click."""
        if self._on_clear_all:
            self._on_clear_all()
        self.popdown()

    def _on_delete_clicked(self, button, notification_id: str, row: Gtk.ListBoxRow) -> None:
        """Handle individual delete button click."""
        if self._on_remove:
            self._on_remove(notification_id)

        # Remove the row from the list
        self._list_box.remove(row)

        # Check if list is now empty
        if not self._list_box.get_children():
            self._empty_label.show()
            self._list_box.hide()
            self._clear_button.set_sensitive(False)
