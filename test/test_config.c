/*
 * WoW Stat Tracker - Config Tests
 */

#include "unity.h"
#include "config.h"
#include <stdlib.h>
#include <stdio.h>

static const char* TEST_FILE = "test_config.json";

static void test_config_new(void) {
    Config* cfg = config_new(TEST_FILE);
    TEST_ASSERT_NOT_NULL(cfg);
    config_free(cfg);
}

static void test_config_set_get_string(void) {
    Config* cfg = config_new(TEST_FILE);

    WstResult result = config_set_string(cfg, "key", "value");
    TEST_ASSERT_EQUAL(WST_OK, result);

    const char* value = config_get_string(cfg, "key", "default");
    TEST_ASSERT_EQUAL_STRING("value", value);

    config_free(cfg);
}

static void test_config_set_get_int(void) {
    Config* cfg = config_new(TEST_FILE);

    config_set_int(cfg, "count", 42);

    int value = config_get_int(cfg, "count", 0);
    TEST_ASSERT_EQUAL(42, value);

    config_free(cfg);
}

static void test_config_set_get_double(void) {
    Config* cfg = config_new(TEST_FILE);

    config_set_double(cfg, "ratio", 3.14159);

    double value = config_get_double(cfg, "ratio", 0.0);
    TEST_ASSERT_DOUBLE_WITHIN(0.0001, 3.14159, value);

    config_free(cfg);
}

static void test_config_set_get_bool(void) {
    Config* cfg = config_new(TEST_FILE);

    config_set_bool(cfg, "enabled", true);
    config_set_bool(cfg, "disabled", false);

    TEST_ASSERT_TRUE(config_get_bool(cfg, "enabled", false));
    TEST_ASSERT_FALSE(config_get_bool(cfg, "disabled", true));

    config_free(cfg);
}

static void test_config_get_default(void) {
    Config* cfg = config_new(TEST_FILE);

    TEST_ASSERT_EQUAL_STRING("default", config_get_string(cfg, "missing", "default"));
    TEST_ASSERT_EQUAL(99, config_get_int(cfg, "missing", 99));
    TEST_ASSERT_DOUBLE_WITHIN(0.001, 1.5, config_get_double(cfg, "missing", 1.5));
    TEST_ASSERT_TRUE(config_get_bool(cfg, "missing", true));

    config_free(cfg);
}

static void test_config_has_key(void) {
    Config* cfg = config_new(TEST_FILE);

    config_set_string(cfg, "exists", "value");

    TEST_ASSERT_TRUE(config_has_key(cfg, "exists"));
    TEST_ASSERT_FALSE(config_has_key(cfg, "notexists"));

    config_free(cfg);
}

static void test_config_delete_key(void) {
    Config* cfg = config_new(TEST_FILE);

    config_set_string(cfg, "key", "value");
    TEST_ASSERT_TRUE(config_has_key(cfg, "key"));

    config_delete_key(cfg, "key");
    TEST_ASSERT_FALSE(config_has_key(cfg, "key"));

    config_free(cfg);
}

static void test_config_overwrite(void) {
    Config* cfg = config_new(TEST_FILE);

    config_set_string(cfg, "key", "first");
    TEST_ASSERT_EQUAL_STRING("first", config_get_string(cfg, "key", ""));

    config_set_string(cfg, "key", "second");
    TEST_ASSERT_EQUAL_STRING("second", config_get_string(cfg, "key", ""));

    config_free(cfg);
}

static void test_config_save_load(void) {
    /* Save */
    {
        Config* cfg = config_new(TEST_FILE);
        config_set_string(cfg, "name", "test");
        config_set_int(cfg, "value", 123);
        config_set_bool(cfg, "flag", true);

        WstResult result = config_save(cfg);
        TEST_ASSERT_EQUAL(WST_OK, result);
        config_free(cfg);
    }

    /* Load */
    {
        Config* cfg = config_new(TEST_FILE);
        WstResult result = config_load(cfg);
        TEST_ASSERT_EQUAL(WST_OK, result);

        TEST_ASSERT_EQUAL_STRING("test", config_get_string(cfg, "name", ""));
        TEST_ASSERT_EQUAL(123, config_get_int(cfg, "value", 0));
        TEST_ASSERT_TRUE(config_get_bool(cfg, "flag", false));

        config_free(cfg);
    }

    /* Clean up */
    remove(TEST_FILE);
}

static void test_config_nested_object(void) {
    Config* cfg = config_new(TEST_FILE);

    cJSON* window = cJSON_CreateObject();
    cJSON_AddNumberToObject(window, "width", 1024);
    cJSON_AddNumberToObject(window, "height", 768);

    config_set_object(cfg, "window", window);

    cJSON* retrieved = config_get_object(cfg, "window");
    TEST_ASSERT_NOT_NULL(retrieved);

    cJSON* width = cJSON_GetObjectItem(retrieved, "width");
    TEST_ASSERT_TRUE(cJSON_IsNumber(width));
    TEST_ASSERT_EQUAL(1024, width->valueint);

    config_free(cfg);
}

void test_config_suite(void) {
    RUN_TEST(test_config_new);
    RUN_TEST(test_config_set_get_string);
    RUN_TEST(test_config_set_get_int);
    RUN_TEST(test_config_set_get_double);
    RUN_TEST(test_config_set_get_bool);
    RUN_TEST(test_config_get_default);
    RUN_TEST(test_config_has_key);
    RUN_TEST(test_config_delete_key);
    RUN_TEST(test_config_overwrite);
    RUN_TEST(test_config_save_load);
    RUN_TEST(test_config_nested_object);
}
