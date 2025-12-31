/*
 * WoW Stat Tracker - Notification Tests
 */

#include "unity.h"
#include "test_suites.h"
#include "notification.h"
#include "paths.h"
#include <string.h>
#include <stdlib.h>
#include <stdio.h>

static char* test_notify_file = NULL;

static void setup_test_file(void) {
    char* config_dir = paths_get_config_dir();
    size_t len = strlen(config_dir) + 32;
    test_notify_file = malloc(len);
    snprintf(test_notify_file, len, "%s/test_notifications.json", config_dir);
    free(config_dir);
    /* Remove any existing test file */
    remove(test_notify_file);
}

static void cleanup_test_file(void) {
    if (test_notify_file) {
        remove(test_notify_file);
        free(test_notify_file);
        test_notify_file = NULL;
    }
}

/* --- Notification Tests --- */

static void test_notification_create(void) {
    Notification* n = notification_create("Test message", WST_NOTIFY_INFO);
    TEST_ASSERT_NOT_NULL(n);
    TEST_ASSERT_NOT_NULL(n->id);
    TEST_ASSERT_EQUAL_STRING("Test message", n->message);
    TEST_ASSERT_EQUAL(WST_NOTIFY_INFO, n->type);
    TEST_ASSERT_NOT_NULL(n->timestamp);
    notification_free(n);
}

static void test_notification_create_success_type(void) {
    Notification* n = notification_create("Success!", WST_NOTIFY_SUCCESS);
    TEST_ASSERT_NOT_NULL(n);
    TEST_ASSERT_EQUAL(WST_NOTIFY_SUCCESS, n->type);
    notification_free(n);
}

static void test_notification_create_warning_type(void) {
    Notification* n = notification_create("Warning!", WST_NOTIFY_WARNING);
    TEST_ASSERT_NOT_NULL(n);
    TEST_ASSERT_EQUAL(WST_NOTIFY_WARNING, n->type);
    notification_free(n);
}

static void test_notification_free_null(void) {
    /* Should not crash */
    notification_free(NULL);
}

static void test_notify_type_to_string(void) {
    TEST_ASSERT_EQUAL_STRING("info", notify_type_to_string(WST_NOTIFY_INFO));
    TEST_ASSERT_EQUAL_STRING("success", notify_type_to_string(WST_NOTIFY_SUCCESS));
    TEST_ASSERT_EQUAL_STRING("warning", notify_type_to_string(WST_NOTIFY_WARNING));
}

static void test_notify_type_from_string(void) {
    TEST_ASSERT_EQUAL(WST_NOTIFY_INFO, notify_type_from_string("info"));
    TEST_ASSERT_EQUAL(WST_NOTIFY_SUCCESS, notify_type_from_string("success"));
    TEST_ASSERT_EQUAL(WST_NOTIFY_WARNING, notify_type_from_string("warning"));
    TEST_ASSERT_EQUAL(WST_NOTIFY_INFO, notify_type_from_string("unknown"));
    TEST_ASSERT_EQUAL(WST_NOTIFY_INFO, notify_type_from_string(NULL));
}

static void test_notification_to_json(void) {
    Notification* n = notification_create("JSON test", WST_NOTIFY_SUCCESS);
    TEST_ASSERT_NOT_NULL(n);
    cJSON* json = notification_to_json(n);
    TEST_ASSERT_NOT_NULL(json);

    cJSON* msg = cJSON_GetObjectItem(json, "message");
    TEST_ASSERT_NOT_NULL(msg);
    TEST_ASSERT_EQUAL_STRING("JSON test", msg->valuestring);

    cJSON* type = cJSON_GetObjectItem(json, "notification_type");
    TEST_ASSERT_NOT_NULL(type);
    TEST_ASSERT_EQUAL_STRING("success", type->valuestring);

    cJSON_Delete(json);
    notification_free(n);
}

static void test_notification_from_json(void) {
    cJSON* json = cJSON_CreateObject();
    cJSON_AddStringToObject(json, "id", "test-id-123");
    cJSON_AddStringToObject(json, "message", "From JSON");
    cJSON_AddStringToObject(json, "notification_type", "warning");
    cJSON_AddStringToObject(json, "timestamp", "2025-01-01T00:00:00Z");

    Notification* n = notification_from_json(json);
    TEST_ASSERT_NOT_NULL(n);
    TEST_ASSERT_EQUAL_STRING("test-id-123", n->id);
    TEST_ASSERT_EQUAL_STRING("From JSON", n->message);
    TEST_ASSERT_EQUAL(WST_NOTIFY_WARNING, n->type);

    cJSON_Delete(json);
    notification_free(n);
}

static void test_notification_from_json_null(void) {
    Notification* n = notification_from_json(NULL);
    TEST_ASSERT_NULL(n);
}

/* --- NotificationStore Tests --- */

static void test_notification_store_new(void) {
    setup_test_file();
    NotificationStore* store = notification_store_new(test_notify_file);
    TEST_ASSERT_NOT_NULL(store);
    TEST_ASSERT_EQUAL(0, notification_store_count(store));
    notification_store_free(store);
    cleanup_test_file();
}

static void test_notification_store_add(void) {
    setup_test_file();
    NotificationStore* store = notification_store_new(test_notify_file);
    Notification* n = notification_create("Added notification", WST_NOTIFY_INFO);

    WstResult result = notification_store_add(store, n);
    TEST_ASSERT_EQUAL(WST_OK, result);
    TEST_ASSERT_EQUAL(1, notification_store_count(store));

    notification_store_free(store);
    cleanup_test_file();
}

static void test_notification_store_get(void) {
    setup_test_file();
    NotificationStore* store = notification_store_new(test_notify_file);
    notification_store_add(store, notification_create("First", WST_NOTIFY_INFO));
    notification_store_add(store, notification_create("Second", WST_NOTIFY_SUCCESS));

    /* Notifications are inserted at beginning, so "Second" is at index 0 */
    Notification* n = notification_store_get(store, 0);
    TEST_ASSERT_NOT_NULL(n);
    TEST_ASSERT_EQUAL_STRING("Second", n->message);

    n = notification_store_get(store, 1);
    TEST_ASSERT_NOT_NULL(n);
    TEST_ASSERT_EQUAL_STRING("First", n->message);

    /* Out of range */
    TEST_ASSERT_NULL(notification_store_get(store, 100));

    notification_store_free(store);
    cleanup_test_file();
}

static void test_notification_store_remove(void) {
    setup_test_file();
    NotificationStore* store = notification_store_new(test_notify_file);
    Notification* n = notification_create("To remove", WST_NOTIFY_INFO);
    char* id = strdup(n->id);
    notification_store_add(store, n);

    TEST_ASSERT_EQUAL(1, notification_store_count(store));
    TEST_ASSERT_TRUE(notification_store_remove(store, id));
    TEST_ASSERT_EQUAL(0, notification_store_count(store));

    /* Remove non-existent */
    TEST_ASSERT_FALSE(notification_store_remove(store, "nonexistent-id"));

    free(id);
    notification_store_free(store);
    cleanup_test_file();
}

static void test_notification_store_clear_all(void) {
    setup_test_file();
    NotificationStore* store = notification_store_new(test_notify_file);
    notification_store_add(store, notification_create("One", WST_NOTIFY_INFO));
    notification_store_add(store, notification_create("Two", WST_NOTIFY_INFO));
    notification_store_add(store, notification_create("Three", WST_NOTIFY_INFO));

    TEST_ASSERT_EQUAL(3, notification_store_count(store));
    notification_store_clear_all(store);
    TEST_ASSERT_EQUAL(0, notification_store_count(store));

    notification_store_free(store);
    cleanup_test_file();
}

static void test_notification_store_save_load(void) {
    setup_test_file();

    /* Create and save */
    NotificationStore* store1 = notification_store_new(test_notify_file);
    notification_store_add(store1, notification_create("Persisted", WST_NOTIFY_SUCCESS));
    notification_store_save(store1);
    notification_store_free(store1);

    /* Load in new store */
    NotificationStore* store2 = notification_store_new(test_notify_file);
    notification_store_load(store2);
    TEST_ASSERT_EQUAL(1, notification_store_count(store2));

    Notification* n = notification_store_get(store2, 0);
    TEST_ASSERT_EQUAL_STRING("Persisted", n->message);
    TEST_ASSERT_EQUAL(WST_NOTIFY_SUCCESS, n->type);

    notification_store_free(store2);
    cleanup_test_file();
}

static void test_notification_store_free_null(void) {
    /* Should not crash */
    notification_store_free(NULL);
}

void test_notification_suite(void) {
    /* Notification tests */
    RUN_TEST(test_notification_create);
    RUN_TEST(test_notification_create_success_type);
    RUN_TEST(test_notification_create_warning_type);
    RUN_TEST(test_notification_free_null);
    RUN_TEST(test_notify_type_to_string);
    RUN_TEST(test_notify_type_from_string);
    RUN_TEST(test_notification_to_json);
    RUN_TEST(test_notification_from_json);
    RUN_TEST(test_notification_from_json_null);

    /* NotificationStore tests */
    RUN_TEST(test_notification_store_new);
    RUN_TEST(test_notification_store_add);
    RUN_TEST(test_notification_store_get);
    RUN_TEST(test_notification_store_remove);
    RUN_TEST(test_notification_store_clear_all);
    RUN_TEST(test_notification_store_save_load);
    RUN_TEST(test_notification_store_free_null);
}
