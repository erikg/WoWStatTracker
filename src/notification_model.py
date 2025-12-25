"""
Notification model layer for WoW Stat Tracker.
Contains notification data structures and persistence with no GTK dependencies.
"""

import json
import os
import shutil
import uuid
from dataclasses import dataclass, asdict
from datetime import datetime


# Notification type constants
NOTIFY_INFO = "info"
NOTIFY_SUCCESS = "success"
NOTIFY_WARNING = "warning"

# Maximum notifications to keep in history
MAX_HISTORY = 100000


@dataclass
class Notification:
    """Data class representing a notification."""

    message: str = ""
    notification_type: str = NOTIFY_INFO
    timestamp: str = ""  # ISO format for JSON serialization
    id: str = ""  # UUID for unique identification

    def to_dict(self) -> dict:
        """Convert to dictionary for JSON serialization."""
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict) -> "Notification":
        """Create a Notification from a dictionary."""
        defaults = {
            "message": "",
            "notification_type": NOTIFY_INFO,
            "timestamp": "",
            "id": "",
        }
        defaults.update(data)
        # Only include fields that exist in the dataclass
        return cls(**{k: v for k, v in defaults.items() if k in cls.__dataclass_fields__})

    @classmethod
    def create(cls, message: str, notification_type: str = NOTIFY_INFO) -> "Notification":
        """Factory method to create a notification with auto-generated id and timestamp."""
        return cls(
            message=message,
            notification_type=notification_type,
            timestamp=datetime.now().isoformat(),
            id=str(uuid.uuid4()),
        )

    def format_timestamp(self) -> str:
        """Format timestamp for display (e.g., 'Dec 24, 4:30 PM')."""
        if not self.timestamp:
            return ""
        try:
            dt = datetime.fromisoformat(self.timestamp)
            return dt.strftime("%b %-d, %-I:%M %p")
        except ValueError:
            return self.timestamp


class NotificationStore:
    """Manages notification data persistence and CRUD operations."""

    def __init__(self, data_file: str):
        self.data_file = data_file
        self.notifications: list[Notification] = []

    def load(self) -> None:
        """Load notifications from JSON file."""
        if os.path.exists(self.data_file):
            try:
                with open(self.data_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    self.notifications = [Notification.from_dict(n) for n in data]
            except (json.JSONDecodeError, IOError, UnicodeDecodeError) as e:
                print(f"Warning: Failed to load notifications file: {e}")
                self.notifications = []
        else:
            self.notifications = []

    def save(self) -> None:
        """Save notifications to JSON file atomically."""
        temp_file = self.data_file + ".tmp"
        try:
            with open(temp_file, "w", encoding="utf-8") as f:
                json.dump([n.to_dict() for n in self.notifications], f, indent=2)
            shutil.move(temp_file, self.data_file)
        except (IOError, OSError, UnicodeEncodeError) as e:
            # Remove temp file if it exists
            if os.path.exists(temp_file):
                try:
                    os.remove(temp_file)
                except OSError:
                    pass
            print(f"Warning: Failed to save notifications: {e}")

    def add(self, notification: Notification) -> None:
        """Add a new notification at the beginning (most recent first)."""
        self.notifications.insert(0, notification)
        # Trim old notifications if over limit
        if len(self.notifications) > MAX_HISTORY:
            self.notifications = self.notifications[:MAX_HISTORY]

    def remove(self, notification_id: str) -> bool:
        """Remove a notification by ID. Returns True if found and removed."""
        for i, n in enumerate(self.notifications):
            if n.id == notification_id:
                del self.notifications[i]
                return True
        return False

    def clear_all(self) -> None:
        """Remove all notifications."""
        self.notifications = []

    def get_all(self) -> list[Notification]:
        """Get all notifications."""
        return self.notifications

    def count(self) -> int:
        """Get the number of notifications."""
        return len(self.notifications)
