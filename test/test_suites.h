/*
 * WoW Stat Tracker - Test Suite Declarations
 */

#ifndef TEST_SUITES_H
#define TEST_SUITES_H

void test_util_suite(void);
void test_character_suite(void);
void test_character_store_suite(void);
void test_config_suite(void);
void test_week_id_suite(void);
void test_paths_suite(void);
void test_lua_parser_suite(void);
void test_notification_suite(void);

#ifdef WST_BUILD_PLATFORM
void test_platform_suite(void);
#endif

#endif /* TEST_SUITES_H */
