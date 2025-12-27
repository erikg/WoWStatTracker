/*
 * WoW Stat Tracker - Test Runner
 */

#include "unity.h"

/* Test declarations */
void test_util_suite(void);
void test_character_suite(void);
void test_character_store_suite(void);
void test_config_suite(void);
void test_week_id_suite(void);

void setUp(void) {
    /* Called before each test */
}

void tearDown(void) {
    /* Called after each test */
}

int main(void) {
    UNITY_BEGIN();

    test_util_suite();
    test_character_suite();
    test_character_store_suite();
    test_config_suite();
    test_week_id_suite();

    return UNITY_END();
}
