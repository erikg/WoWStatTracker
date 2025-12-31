/*
 * WoW Stat Tracker - Test Runner
 */

#include "unity.h"
#include "test_suites.h"

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
    test_paths_suite();
    test_lua_parser_suite();
    test_notification_suite();

#ifdef WST_BUILD_PLATFORM
    test_platform_suite();
#endif

    return UNITY_END();
}
