"""Tests for the notification model layer (notification_model.py)."""

import json
import os
import sys

import pytest

# Add src directory to path for imports
sys.path.insert(
    0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "src")
)

from notification_model import (
    Notification,
    NotificationStore,
    NOTIFY_INFO,
    NOTIFY_SUCCESS,
    NOTIFY_WARNING,
    MAX_HISTORY,
)


class TestNotification:
    """Tests for the Notification dataclass."""

    def test_default_values(self):
        """Test Notification has correct default values."""
        n = Notification()
        assert n.message == ""
        assert n.notification_type == NOTIFY_INFO
        assert n.timestamp == ""
        assert n.id == ""

    def test_create_with_values(self):
        """Test Notification creation with specific values."""
        n = Notification(
            message="Test message",
            notification_type=NOTIFY_SUCCESS,
            timestamp="2025-01-01T12:00:00",
            id="test-id-123",
        )
        assert n.message == "Test message"
        assert n.notification_type == NOTIFY_SUCCESS
        assert n.timestamp == "2025-01-01T12:00:00"
        assert n.id == "test-id-123"

    def test_create_factory_method(self):
        """Test Notification.create() generates id and timestamp."""
        n = Notification.create("Test message", NOTIFY_WARNING)
        assert n.message == "Test message"
        assert n.notification_type == NOTIFY_WARNING
        assert n.timestamp != ""
        assert n.id != ""
        # ID should be a valid UUID format
        assert len(n.id) == 36
        assert n.id.count("-") == 4

    def test_create_default_type(self):
        """Test Notification.create() defaults to info type."""
        n = Notification.create("Test message")
        assert n.notification_type == NOTIFY_INFO

    def test_to_dict(self):
        """Test conversion to dictionary."""
        n = Notification(
            message="Test",
            notification_type=NOTIFY_SUCCESS,
            timestamp="2025-01-01T12:00:00",
            id="abc123",
        )
        d = n.to_dict()
        assert d["message"] == "Test"
        assert d["notification_type"] == NOTIFY_SUCCESS
        assert d["timestamp"] == "2025-01-01T12:00:00"
        assert d["id"] == "abc123"

    def test_from_dict(self):
        """Test creation from dictionary."""
        data = {
            "message": "Test",
            "notification_type": NOTIFY_WARNING,
            "timestamp": "2025-01-01T12:00:00",
            "id": "xyz789",
        }
        n = Notification.from_dict(data)
        assert n.message == "Test"
        assert n.notification_type == NOTIFY_WARNING
        assert n.timestamp == "2025-01-01T12:00:00"
        assert n.id == "xyz789"

    def test_from_dict_with_missing_fields(self):
        """Test from_dict handles missing fields with defaults."""
        data = {"message": "Test"}
        n = Notification.from_dict(data)
        assert n.message == "Test"
        assert n.notification_type == NOTIFY_INFO
        assert n.timestamp == ""
        assert n.id == ""

    def test_from_dict_ignores_extra_fields(self):
        """Test from_dict ignores fields not in dataclass."""
        data = {
            "message": "Test",
            "notification_type": NOTIFY_INFO,
            "timestamp": "",
            "id": "",
            "extra_field": "should be ignored",
        }
        n = Notification.from_dict(data)
        assert n.message == "Test"
        assert not hasattr(n, "extra_field")

    def test_format_timestamp(self):
        """Test timestamp formatting for display."""
        n = Notification(timestamp="2025-01-15T14:30:00")
        formatted = n.format_timestamp()
        assert formatted == "2:30 PM"

    def test_format_timestamp_morning(self):
        """Test timestamp formatting for morning time."""
        n = Notification(timestamp="2025-01-15T09:05:00")
        formatted = n.format_timestamp()
        assert formatted == "9:05 AM"

    def test_format_timestamp_empty(self):
        """Test format_timestamp with empty timestamp."""
        n = Notification(timestamp="")
        assert n.format_timestamp() == ""

    def test_format_timestamp_invalid(self):
        """Test format_timestamp with invalid timestamp returns original."""
        n = Notification(timestamp="not-a-date")
        assert n.format_timestamp() == "not-a-date"

    def test_roundtrip_dict(self):
        """Test to_dict/from_dict roundtrip preserves data."""
        original = Notification.create("Test message", NOTIFY_SUCCESS)
        d = original.to_dict()
        restored = Notification.from_dict(d)
        assert restored.message == original.message
        assert restored.notification_type == original.notification_type
        assert restored.timestamp == original.timestamp
        assert restored.id == original.id


class TestNotificationStore:
    """Tests for the NotificationStore class."""

    def test_init_empty(self, tmp_path):
        """Test store initialization with no existing file."""
        data_file = tmp_path / "notifications.json"
        store = NotificationStore(str(data_file))
        assert store.notifications == []
        assert store.data_file == str(data_file)

    def test_load_nonexistent_file(self, tmp_path):
        """Test loading from nonexistent file."""
        data_file = tmp_path / "notifications.json"
        store = NotificationStore(str(data_file))
        store.load()
        assert store.notifications == []

    def test_load_existing_file(self, tmp_path):
        """Test loading from existing file."""
        data_file = tmp_path / "notifications.json"
        data = [
            {"message": "Test1", "notification_type": "info", "timestamp": "", "id": "1"},
            {"message": "Test2", "notification_type": "success", "timestamp": "", "id": "2"},
        ]
        with open(data_file, "w") as f:
            json.dump(data, f)

        store = NotificationStore(str(data_file))
        store.load()
        assert len(store.notifications) == 2
        assert store.notifications[0].message == "Test1"
        assert store.notifications[1].message == "Test2"

    def test_load_invalid_json(self, tmp_path):
        """Test loading from file with invalid JSON."""
        data_file = tmp_path / "notifications.json"
        with open(data_file, "w") as f:
            f.write("not valid json")

        store = NotificationStore(str(data_file))
        store.load()
        assert store.notifications == []

    def test_save_creates_file(self, tmp_path):
        """Test saving creates a new file."""
        data_file = tmp_path / "notifications.json"
        store = NotificationStore(str(data_file))
        store.notifications = [Notification.create("Test", NOTIFY_INFO)]
        store.save()

        assert data_file.exists()
        with open(data_file) as f:
            data = json.load(f)
        assert len(data) == 1
        assert data[0]["message"] == "Test"

    def test_save_overwrites_file(self, tmp_path):
        """Test saving overwrites existing file."""
        data_file = tmp_path / "notifications.json"
        with open(data_file, "w") as f:
            json.dump([{"message": "Old"}], f)

        store = NotificationStore(str(data_file))
        store.notifications = [Notification.create("New", NOTIFY_INFO)]
        store.save()

        with open(data_file) as f:
            data = json.load(f)
        assert len(data) == 1
        assert data[0]["message"] == "New"

    def test_add_notification(self, tmp_path):
        """Test adding a notification."""
        data_file = tmp_path / "notifications.json"
        store = NotificationStore(str(data_file))
        n = Notification.create("Test", NOTIFY_INFO)
        store.add(n)
        assert len(store.notifications) == 1
        assert store.notifications[0].message == "Test"

    def test_add_inserts_at_beginning(self, tmp_path):
        """Test add inserts at beginning (most recent first)."""
        data_file = tmp_path / "notifications.json"
        store = NotificationStore(str(data_file))
        store.add(Notification.create("First", NOTIFY_INFO))
        store.add(Notification.create("Second", NOTIFY_INFO))
        store.add(Notification.create("Third", NOTIFY_INFO))

        assert store.notifications[0].message == "Third"
        assert store.notifications[1].message == "Second"
        assert store.notifications[2].message == "First"

    def test_remove_notification(self, tmp_path):
        """Test removing a notification by ID."""
        data_file = tmp_path / "notifications.json"
        store = NotificationStore(str(data_file))
        n1 = Notification(message="Test1", id="id1")
        n2 = Notification(message="Test2", id="id2")
        store.notifications = [n1, n2]

        result = store.remove("id1")
        assert result is True
        assert len(store.notifications) == 1
        assert store.notifications[0].id == "id2"

    def test_remove_nonexistent_id(self, tmp_path):
        """Test removing with invalid ID returns False."""
        data_file = tmp_path / "notifications.json"
        store = NotificationStore(str(data_file))
        store.notifications = [Notification(message="Test", id="id1")]

        result = store.remove("nonexistent")
        assert result is False
        assert len(store.notifications) == 1

    def test_clear_all(self, tmp_path):
        """Test clearing all notifications."""
        data_file = tmp_path / "notifications.json"
        store = NotificationStore(str(data_file))
        store.notifications = [
            Notification.create("Test1", NOTIFY_INFO),
            Notification.create("Test2", NOTIFY_INFO),
        ]
        store.clear_all()
        assert store.notifications == []

    def test_get_all(self, tmp_path):
        """Test getting all notifications."""
        data_file = tmp_path / "notifications.json"
        store = NotificationStore(str(data_file))
        n1 = Notification.create("Test1", NOTIFY_INFO)
        n2 = Notification.create("Test2", NOTIFY_INFO)
        store.notifications = [n1, n2]

        result = store.get_all()
        assert len(result) == 2
        assert result[0] == n1
        assert result[1] == n2

    def test_count(self, tmp_path):
        """Test counting notifications."""
        data_file = tmp_path / "notifications.json"
        store = NotificationStore(str(data_file))
        assert store.count() == 0

        store.add(Notification.create("Test1", NOTIFY_INFO))
        assert store.count() == 1

        store.add(Notification.create("Test2", NOTIFY_INFO))
        assert store.count() == 2

    def test_roundtrip_save_load(self, tmp_path):
        """Test save/load roundtrip preserves data."""
        data_file = tmp_path / "notifications.json"

        store1 = NotificationStore(str(data_file))
        store1.add(Notification.create("Test1", NOTIFY_SUCCESS))
        store1.add(Notification.create("Test2", NOTIFY_WARNING))
        store1.save()

        store2 = NotificationStore(str(data_file))
        store2.load()

        assert len(store2.notifications) == 2
        assert store2.notifications[0].message == "Test2"
        assert store2.notifications[0].notification_type == NOTIFY_WARNING
        assert store2.notifications[1].message == "Test1"
        assert store2.notifications[1].notification_type == NOTIFY_SUCCESS

    def test_atomic_save_cleans_temp_on_success(self, tmp_path):
        """Test atomic write pattern cleans up temp file on success."""
        data_file = tmp_path / "notifications.json"
        temp_file = tmp_path / "notifications.json.tmp"

        store = NotificationStore(str(data_file))
        store.add(Notification.create("Test", NOTIFY_INFO))
        store.save()

        assert data_file.exists()
        assert not temp_file.exists()
