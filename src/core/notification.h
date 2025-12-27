/*
 * WoW Stat Tracker - Notification System
 * BSD 3-Clause License
 */

#ifndef WST_NOTIFICATION_H
#define WST_NOTIFICATION_H

#include "types.h"
#include "cJSON.h"

/* Notification type constants */
typedef enum {
    WST_NOTIFY_INFO = 0,
    WST_NOTIFY_SUCCESS,
    WST_NOTIFY_WARNING,
} WstNotifyType;

/* Maximum notifications to keep in history */
#define WST_MAX_NOTIFICATION_HISTORY 100000

/*
 * Notification data structure.
 */
struct Notification {
    char* id;               /* UUID */
    char* message;
    WstNotifyType type;
    char* timestamp;        /* ISO format */
};

/*
 * Notification store - manages notification history with JSON persistence.
 */
struct NotificationStore {
    Notification** notifications;
    size_t count;
    size_t capacity;
    char* file_path;
};

/*
 * Create a new notification with auto-generated ID and timestamp.
 * Returns NULL on allocation failure.
 */
Notification* notification_create(const char* message, WstNotifyType type);

/*
 * Free a notification.
 */
void notification_free(Notification* n);

/*
 * Format timestamp for display (e.g., "Dec 24, 4:30 PM").
 * Caller must free the returned string.
 */
char* notification_format_timestamp(const Notification* n);

/*
 * Convert notification to cJSON object.
 */
cJSON* notification_to_json(const Notification* n);

/*
 * Create notification from cJSON object.
 */
Notification* notification_from_json(const cJSON* json);

/*
 * Convert notification type to string.
 */
const char* notify_type_to_string(WstNotifyType type);

/*
 * Parse notification type from string.
 */
WstNotifyType notify_type_from_string(const char* str);

/* --- Notification Store --- */

/*
 * Create a new notification store.
 * Returns NULL on allocation failure.
 */
NotificationStore* notification_store_new(const char* file_path);

/*
 * Free the notification store and all notifications.
 */
void notification_store_free(NotificationStore* store);

/*
 * Load notifications from JSON file.
 */
WstResult notification_store_load(NotificationStore* store);

/*
 * Save notifications to JSON file atomically.
 */
WstResult notification_store_save(const NotificationStore* store);

/*
 * Add a notification (takes ownership, inserts at beginning).
 * Returns WST_OK on success.
 */
WstResult notification_store_add(NotificationStore* store, Notification* n);

/*
 * Remove a notification by ID.
 * Returns true if found and removed.
 */
bool notification_store_remove(NotificationStore* store, const char* id);

/*
 * Clear all notifications.
 */
void notification_store_clear_all(NotificationStore* store);

/*
 * Get notification at index.
 * Returns NULL if index is out of range.
 */
Notification* notification_store_get(const NotificationStore* store, size_t index);

/*
 * Get notification count.
 */
size_t notification_store_count(const NotificationStore* store);

#endif /* WST_NOTIFICATION_H */
