/*
 * WoW Stat Tracker - Config Tests
 */

#include "unity.h"
#include "test_suites.h"
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

static void test_config_save_overwrite(void) {
    /* First save */
    {
        Config* cfg = config_new(TEST_FILE);
        config_set_string(cfg, "key", "first");
        TEST_ASSERT_EQUAL(WST_OK, config_save(cfg));
        config_free(cfg);
    }

    /* Second save (overwrite) */
    {
        Config* cfg = config_new(TEST_FILE);
        config_set_string(cfg, "key", "second");
        config_set_int(cfg, "new_key", 42);
        TEST_ASSERT_EQUAL(WST_OK, config_save(cfg));
        config_free(cfg);
    }

    /* Verify overwrite */
    {
        Config* cfg = config_new(TEST_FILE);
        TEST_ASSERT_EQUAL(WST_OK, config_load(cfg));
        TEST_ASSERT_EQUAL_STRING("second", config_get_string(cfg, "key", ""));
        TEST_ASSERT_EQUAL(42, config_get_int(cfg, "new_key", 0));
        config_free(cfg);
    }

    remove(TEST_FILE);
}

static void test_config_save_empty(void) {
    /* Save empty config */
    {
        Config* cfg = config_new(TEST_FILE);
        TEST_ASSERT_EQUAL(WST_OK, config_save(cfg));
        config_free(cfg);
    }

    /* Load empty config */
    {
        Config* cfg = config_new(TEST_FILE);
        TEST_ASSERT_EQUAL(WST_OK, config_load(cfg));
        /* Should have no keys */
        TEST_ASSERT_FALSE(config_has_key(cfg, "anything"));
        config_free(cfg);
    }

    remove(TEST_FILE);
}

static void test_config_save_load_all_types(void) {
    /* Save all types */
    {
        Config* cfg = config_new(TEST_FILE);
        config_set_string(cfg, "str", "hello world");
        config_set_int(cfg, "int_pos", 12345);
        config_set_int(cfg, "int_neg", -9999);
        config_set_double(cfg, "double", 3.14159);
        config_set_bool(cfg, "bool_true", true);
        config_set_bool(cfg, "bool_false", false);
        TEST_ASSERT_EQUAL(WST_OK, config_save(cfg));
        config_free(cfg);
    }

    /* Load and verify all types */
    {
        Config* cfg = config_new(TEST_FILE);
        TEST_ASSERT_EQUAL(WST_OK, config_load(cfg));

        TEST_ASSERT_EQUAL_STRING("hello world", config_get_string(cfg, "str", ""));
        TEST_ASSERT_EQUAL(12345, config_get_int(cfg, "int_pos", 0));
        TEST_ASSERT_EQUAL(-9999, config_get_int(cfg, "int_neg", 0));
        TEST_ASSERT_DOUBLE_WITHIN(0.0001, 3.14159, config_get_double(cfg, "double", 0.0));
        TEST_ASSERT_TRUE(config_get_bool(cfg, "bool_true", false));
        TEST_ASSERT_FALSE(config_get_bool(cfg, "bool_false", true));

        config_free(cfg);
    }

    remove(TEST_FILE);
}

static void test_config_multiple_save_load_cycles(void) {
    /* Multiple save/load cycles */
    for (int i = 0; i < 5; i++) {
        Config* cfg = config_new(TEST_FILE);
        if (i > 0) {
            TEST_ASSERT_EQUAL(WST_OK, config_load(cfg));
            TEST_ASSERT_EQUAL(i - 1, config_get_int(cfg, "iteration", -1));
        }
        config_set_int(cfg, "iteration", i);
        TEST_ASSERT_EQUAL(WST_OK, config_save(cfg));
        config_free(cfg);
    }

    /* Final verify */
    {
        Config* cfg = config_new(TEST_FILE);
        TEST_ASSERT_EQUAL(WST_OK, config_load(cfg));
        TEST_ASSERT_EQUAL(4, config_get_int(cfg, "iteration", -1));
        config_free(cfg);
    }

    remove(TEST_FILE);
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
    RUN_TEST(test_config_save_overwrite);
    RUN_TEST(test_config_save_empty);
    RUN_TEST(test_config_save_load_all_types);
    RUN_TEST(test_config_multiple_save_load_cycles);
}
