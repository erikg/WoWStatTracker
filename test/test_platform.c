/*
 * WoW Stat Tracker - Platform Layer Tests
 */

#include "unity.h"
#include "platform.h"
#include "util.h"
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

static const char* TEST_LOCK_FILE = "test_lock.lock";
static const char* TEST_WRITE_FILE = "test_atomic.txt";

static void test_platform_is_dark_theme(void) {
    /* Just verify it doesn't crash - result depends on system settings */
    bool result = platform_is_dark_theme();
    /* Result can be true or false depending on system settings */
    TEST_ASSERT_TRUE(result == true || result == false);
}

static void test_platform_write_atomic_basic(void) {
    const char* data = "Hello, World!";
    size_t len = strlen(data);

    WstResult result = platform_write_atomic(TEST_WRITE_FILE, data, len);
    TEST_ASSERT_EQUAL(WST_OK, result);

    /* Verify contents */
    FILE* f = fopen(TEST_WRITE_FILE, "r");
    TEST_ASSERT_NOT_NULL(f);

    char buffer[64];
    size_t read = fread(buffer, 1, sizeof(buffer) - 1, f);
    fclose(f);

    buffer[read] = '\0';
    TEST_ASSERT_EQUAL_STRING(data, buffer);

    /* Cleanup */
    remove(TEST_WRITE_FILE);
}

static void test_platform_write_atomic_overwrite(void) {
    const char* data1 = "First write";
    const char* data2 = "Second write with more data";

    /* Write first version */
    platform_write_atomic(TEST_WRITE_FILE, data1, strlen(data1));

    /* Overwrite with second version */
    WstResult result = platform_write_atomic(TEST_WRITE_FILE, data2, strlen(data2));
    TEST_ASSERT_EQUAL(WST_OK, result);

    /* Verify second version */
    FILE* f = fopen(TEST_WRITE_FILE, "r");
    TEST_ASSERT_NOT_NULL(f);

    char buffer[128];
    size_t read = fread(buffer, 1, sizeof(buffer) - 1, f);
    fclose(f);

    buffer[read] = '\0';
    TEST_ASSERT_EQUAL_STRING(data2, buffer);

    /* Cleanup */
    remove(TEST_WRITE_FILE);
}

static void test_platform_write_atomic_null_args(void) {
    WstResult result = platform_write_atomic(NULL, "data", 4);
    TEST_ASSERT_EQUAL(WST_ERR_NULL_ARG, result);

    result = platform_write_atomic(TEST_WRITE_FILE, NULL, 4);
    TEST_ASSERT_EQUAL(WST_ERR_NULL_ARG, result);
}

static void test_platform_lock_acquire_release(void) {
    /* Acquire lock */
    WstResult result = platform_lock_acquire(TEST_LOCK_FILE);
    TEST_ASSERT_EQUAL(WST_OK, result);

    /* Acquiring again should succeed (same process) */
    result = platform_lock_acquire(TEST_LOCK_FILE);
    TEST_ASSERT_EQUAL(WST_OK, result);

    /* Release lock */
    platform_lock_release(TEST_LOCK_FILE);

    /* Cleanup - lock file should be removed */
    /* Note: file might be removed by platform_lock_release */
}

static void test_platform_lock_null_arg(void) {
    WstResult result = platform_lock_acquire(NULL);
    TEST_ASSERT_EQUAL(WST_ERR_NULL_ARG, result);
}

static void test_platform_open_url_null(void) {
    /* Should not crash with NULL */
    platform_open_url(NULL);
    TEST_PASS();
}

/* Note: We don't test platform_http_get here as it requires network access
   and could make tests flaky. It would be better tested in integration tests. */

void test_platform_suite(void) {
    RUN_TEST(test_platform_is_dark_theme);
    RUN_TEST(test_platform_write_atomic_basic);
    RUN_TEST(test_platform_write_atomic_overwrite);
    RUN_TEST(test_platform_write_atomic_null_args);
    RUN_TEST(test_platform_lock_acquire_release);
    RUN_TEST(test_platform_lock_null_arg);
    RUN_TEST(test_platform_open_url_null);
}
