/*
 * WoW Stat Tracker - Utility Function Tests
 */

#include "unity.h"
#include "util.h"
#include <string.h>
#include <stdlib.h>

static void test_wst_strdup_normal(void) {
    char* dup = wst_strdup("hello");
    TEST_ASSERT_NOT_NULL(dup);
    TEST_ASSERT_EQUAL_STRING("hello", dup);
    free(dup);
}

static void test_wst_strdup_null(void) {
    char* dup = wst_strdup(NULL);
    TEST_ASSERT_NULL(dup);
}

static void test_wst_strdup_empty(void) {
    char* dup = wst_strdup("");
    TEST_ASSERT_NOT_NULL(dup);
    TEST_ASSERT_EQUAL_STRING("", dup);
    free(dup);
}

static void test_wst_strndup_normal(void) {
    char* dup = wst_strndup("hello world", 5);
    TEST_ASSERT_NOT_NULL(dup);
    TEST_ASSERT_EQUAL_STRING("hello", dup);
    free(dup);
}

static void test_wst_strlcpy_normal(void) {
    char buf[10];
    size_t len = wst_strlcpy(buf, "hello", sizeof(buf));
    TEST_ASSERT_EQUAL_STRING("hello", buf);
    TEST_ASSERT_EQUAL(5, len);
}

static void test_wst_strlcpy_truncates(void) {
    char buf[4];
    size_t len = wst_strlcpy(buf, "hello", sizeof(buf));
    TEST_ASSERT_EQUAL_STRING("hel", buf);
    TEST_ASSERT_EQUAL(5, len);  /* Returns what would have been copied */
}

static void test_wst_str_empty_null(void) {
    TEST_ASSERT_TRUE(wst_str_empty(NULL));
}

static void test_wst_str_empty_empty(void) {
    TEST_ASSERT_TRUE(wst_str_empty(""));
}

static void test_wst_str_empty_nonempty(void) {
    TEST_ASSERT_FALSE(wst_str_empty("hello"));
}

static void test_wst_strcmp_equal(void) {
    TEST_ASSERT_EQUAL(0, wst_strcmp("hello", "hello"));
}

static void test_wst_strcmp_null(void) {
    TEST_ASSERT_TRUE(wst_strcmp(NULL, "hello") < 0);
    TEST_ASSERT_TRUE(wst_strcmp("hello", NULL) > 0);
    TEST_ASSERT_EQUAL(0, wst_strcmp(NULL, NULL));
}

static void test_wst_strcasecmp_case_insensitive(void) {
    TEST_ASSERT_EQUAL(0, wst_strcasecmp("Hello", "HELLO"));
    TEST_ASSERT_EQUAL(0, wst_strcasecmp("hello", "HELLO"));
}

static void test_wst_strtrim_both(void) {
    char buf[] = "  hello  ";
    char* result = wst_strtrim(buf);
    TEST_ASSERT_EQUAL_STRING("hello", result);
}

static void test_wst_strtrim_leading(void) {
    char buf[] = "  hello";
    char* result = wst_strtrim(buf);
    TEST_ASSERT_EQUAL_STRING("hello", result);
}

static void test_wst_strtrim_trailing(void) {
    char buf[] = "hello  ";
    char* result = wst_strtrim(buf);
    TEST_ASSERT_EQUAL_STRING("hello", result);
}

static void test_wst_path_join_normal(void) {
    char* path = wst_path_join("/home/user", "file.txt");
    TEST_ASSERT_NOT_NULL(path);
    TEST_ASSERT_EQUAL_STRING("/home/user/file.txt", path);
    free(path);
}

static void test_wst_path_join_trailing_slash(void) {
    char* path = wst_path_join("/home/user/", "file.txt");
    TEST_ASSERT_NOT_NULL(path);
    TEST_ASSERT_EQUAL_STRING("/home/user/file.txt", path);
    free(path);
}

void test_util_suite(void) {
    RUN_TEST(test_wst_strdup_normal);
    RUN_TEST(test_wst_strdup_null);
    RUN_TEST(test_wst_strdup_empty);
    RUN_TEST(test_wst_strndup_normal);
    RUN_TEST(test_wst_strlcpy_normal);
    RUN_TEST(test_wst_strlcpy_truncates);
    RUN_TEST(test_wst_str_empty_null);
    RUN_TEST(test_wst_str_empty_empty);
    RUN_TEST(test_wst_str_empty_nonempty);
    RUN_TEST(test_wst_strcmp_equal);
    RUN_TEST(test_wst_strcmp_null);
    RUN_TEST(test_wst_strcasecmp_case_insensitive);
    RUN_TEST(test_wst_strtrim_both);
    RUN_TEST(test_wst_strtrim_leading);
    RUN_TEST(test_wst_strtrim_trailing);
    RUN_TEST(test_wst_path_join_normal);
    RUN_TEST(test_wst_path_join_trailing_slash);
}
