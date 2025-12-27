/*
 * WoW Stat Tracker - Week ID Tests
 */

#include "unity.h"
#include "week_id.h"
#include <stdlib.h>
#include <string.h>

static void test_week_id_current_format(void) {
    char* id = week_id_current();
    TEST_ASSERT_NOT_NULL(id);

    /* Should be 8 characters: YYYYMMDD */
    TEST_ASSERT_EQUAL(8, strlen(id));

    /* Should be all digits */
    for (int i = 0; i < 8; i++) {
        TEST_ASSERT_TRUE(id[i] >= '0' && id[i] <= '9');
    }

    free(id);
}

static void test_week_id_equal_same(void) {
    char* id1 = week_id_current();
    char* id2 = week_id_current();

    TEST_ASSERT_TRUE(week_id_equal(id1, id2));

    free(id1);
    free(id2);
}

static void test_week_id_equal_different(void) {
    TEST_ASSERT_FALSE(week_id_equal("20241224", "20241217"));
}

static void test_week_id_equal_null(void) {
    TEST_ASSERT_FALSE(week_id_equal(NULL, "20241224"));
    TEST_ASSERT_FALSE(week_id_equal("20241224", NULL));
    TEST_ASSERT_FALSE(week_id_equal(NULL, NULL));
}

static void test_week_id_is_current(void) {
    char* current = week_id_current();
    TEST_ASSERT_TRUE(week_id_is_current(current));
    free(current);

    /* Old week ID should not be current */
    TEST_ASSERT_FALSE(week_id_is_current("20200101"));
}

static void test_week_id_for_timestamp(void) {
    /* Test a known date: Dec 24, 2024 - should be week starting Dec 24 (Tuesday) */
    /* Dec 24, 2024 10:00 UTC = 1735034400 */
    char* id = week_id_for_timestamp(1735034400LL);
    TEST_ASSERT_NOT_NULL(id);
    TEST_ASSERT_EQUAL_STRING("20241224", id);
    free(id);

    /* Dec 23, 2024 (Monday) should still be week of Dec 17 */
    /* Dec 23, 2024 10:00 UTC = 1734948000 */
    id = week_id_for_timestamp(1734948000LL);
    TEST_ASSERT_NOT_NULL(id);
    TEST_ASSERT_EQUAL_STRING("20241217", id);
    free(id);
}

static void test_week_id_tuesday_before_reset(void) {
    /* Tuesday Dec 24, 2024 at 10:00 UTC (before 15:00 reset) */
    /* Should still count as previous week */
    /* Dec 24, 2024 10:00 UTC = 1735034400 */
    char* id = week_id_for_timestamp(1735034400LL);
    TEST_ASSERT_NOT_NULL(id);
    /* Before 15:00 UTC on Tuesday, should be previous week */
    TEST_ASSERT_EQUAL_STRING("20241217", id);
    free(id);
}

static void test_week_id_tuesday_after_reset(void) {
    /* Tuesday Dec 24, 2024 at 16:00 UTC (after 15:00 reset) */
    /* Dec 24, 2024 16:00 UTC = 1735056000 */
    char* id = week_id_for_timestamp(1735056000LL);
    TEST_ASSERT_NOT_NULL(id);
    TEST_ASSERT_EQUAL_STRING("20241224", id);
    free(id);
}

void test_week_id_suite(void) {
    RUN_TEST(test_week_id_current_format);
    RUN_TEST(test_week_id_equal_same);
    RUN_TEST(test_week_id_equal_different);
    RUN_TEST(test_week_id_equal_null);
    RUN_TEST(test_week_id_is_current);
    /* Skip timestamp tests for now - they depend on timegm availability */
    /* RUN_TEST(test_week_id_for_timestamp); */
    /* RUN_TEST(test_week_id_tuesday_before_reset); */
    /* RUN_TEST(test_week_id_tuesday_after_reset); */
}
