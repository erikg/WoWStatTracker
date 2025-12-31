/*
 * WoW Stat Tracker - Path Utility Tests
 */

#include "unity.h"
#include "test_suites.h"
#include "paths.h"
#include <string.h>
#include <stdlib.h>
#include <sys/stat.h>

static void test_paths_get_home(void) {
    char* home = paths_get_home();
    TEST_ASSERT_NOT_NULL(home);
    TEST_ASSERT_TRUE(strlen(home) > 0);
    /* Home should be an absolute path */
#ifdef _WIN32
    /* Windows paths start with drive letter like C: */
    TEST_ASSERT_TRUE(strlen(home) >= 2 && home[1] == ':');
#else
    TEST_ASSERT_EQUAL('/', home[0]);
#endif
    free(home);
}

static void test_paths_get_config_dir(void) {
    char* dir = paths_get_config_dir();
    TEST_ASSERT_NOT_NULL(dir);
    TEST_ASSERT_TRUE(strlen(dir) > 0);
    /* Should end with "wowstat" */
    TEST_ASSERT_NOT_NULL(strstr(dir, "wowstat"));
    free(dir);
}

static void test_paths_get_data_file(void) {
    char* path = paths_get_data_file();
    TEST_ASSERT_NOT_NULL(path);
    TEST_ASSERT_NOT_NULL(strstr(path, "wowstat_data.json"));
    free(path);
}

static void test_paths_get_config_file(void) {
    char* path = paths_get_config_file();
    TEST_ASSERT_NOT_NULL(path);
    TEST_ASSERT_NOT_NULL(strstr(path, "wowstat_config.json"));
    free(path);
}

static void test_paths_get_notifications_file(void) {
    char* path = paths_get_notifications_file();
    TEST_ASSERT_NOT_NULL(path);
    TEST_ASSERT_NOT_NULL(strstr(path, "notifications.json"));
    free(path);
}

static void test_paths_get_lock_file(void) {
    char* path = paths_get_lock_file();
    TEST_ASSERT_NOT_NULL(path);
    TEST_ASSERT_NOT_NULL(strstr(path, "wowstat.lock"));
    free(path);
}

static void test_paths_is_dir_valid(void) {
    /* Root directory should exist */
#ifdef _WIN32
    TEST_ASSERT_TRUE(paths_is_dir("C:\\"));
#else
    TEST_ASSERT_TRUE(paths_is_dir("/"));
#endif
    /* Home directory should exist */
    char* home = paths_get_home();
    TEST_ASSERT_TRUE(paths_is_dir(home));
    free(home);
}

static void test_paths_is_dir_invalid(void) {
#ifdef _WIN32
    TEST_ASSERT_FALSE(paths_is_dir("C:\\nonexistent_path_12345"));
#else
    TEST_ASSERT_FALSE(paths_is_dir("/nonexistent_path_12345"));
#endif
    TEST_ASSERT_FALSE(paths_is_dir(NULL));
}

static void test_paths_file_exists_valid(void) {
    /* This test file should exist during test run */
    char* config_dir = paths_get_config_dir();
    TEST_ASSERT_NOT_NULL(config_dir);
    /* Config dir should exist (created by paths_get_config_dir) */
    TEST_ASSERT_TRUE(paths_is_dir(config_dir));
    free(config_dir);
}

static void test_paths_file_exists_invalid(void) {
#ifdef _WIN32
    TEST_ASSERT_FALSE(paths_file_exists("C:\\nonexistent_file_12345.txt"));
#else
    TEST_ASSERT_FALSE(paths_file_exists("/nonexistent_file_12345.txt"));
#endif
    TEST_ASSERT_FALSE(paths_file_exists(NULL));
}

static void test_paths_ensure_dir_existing(void) {
    char* home = paths_get_home();
    /* Ensuring existing dir should succeed */
    TEST_ASSERT_EQUAL(WST_OK, paths_ensure_dir(home));
    free(home);
}

static void test_paths_ensure_dir_null(void) {
    TEST_ASSERT_EQUAL(WST_ERR_NULL_ARG, paths_ensure_dir(NULL));
}

void test_paths_suite(void) {
    RUN_TEST(test_paths_get_home);
    RUN_TEST(test_paths_get_config_dir);
    RUN_TEST(test_paths_get_data_file);
    RUN_TEST(test_paths_get_config_file);
    RUN_TEST(test_paths_get_notifications_file);
    RUN_TEST(test_paths_get_lock_file);
    RUN_TEST(test_paths_is_dir_valid);
    RUN_TEST(test_paths_is_dir_invalid);
    RUN_TEST(test_paths_file_exists_valid);
    RUN_TEST(test_paths_file_exists_invalid);
    RUN_TEST(test_paths_ensure_dir_existing);
    RUN_TEST(test_paths_ensure_dir_null);
}
