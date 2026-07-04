/*
 * WoW Stat Tracker - Gem/Enchant Recommendations Tests
 */

#include "unity.h"
#include "test_suites.h"
#include "gem_recs.h"

#ifndef WST_GEM_RECS_PATH
#define WST_GEM_RECS_PATH "gem_enchant_recs.json"
#endif

static void test_gem_recs_load_and_lookup(void) {
    GemRecs* recs = gem_recs_load(WST_GEM_RECS_PATH);
    TEST_ASSERT_NOT_NULL(recs);

    /* Known class/spec present in the data file */
    const cJSON* node = gem_recs_lookup(recs, "Priest", "Holy");
    TEST_ASSERT_NOT_NULL(node);
    TEST_ASSERT_NOT_NULL(cJSON_GetObjectItemCaseSensitive(node, "enchants"));
    TEST_ASSERT_NOT_NULL(cJSON_GetObjectItemCaseSensitive(node, "gems"));

    gem_recs_free(recs);
}

static void test_gem_recs_lookup_missing(void) {
    GemRecs* recs = gem_recs_load(WST_GEM_RECS_PATH);
    TEST_ASSERT_NOT_NULL(recs);

    /* Absent class/spec and empty/NULL args return NULL */
    TEST_ASSERT_NULL(gem_recs_lookup(recs, "Priest", "Nonexistent"));
    TEST_ASSERT_NULL(gem_recs_lookup(recs, "BogusClass", "Holy"));
    TEST_ASSERT_NULL(gem_recs_lookup(recs, "", ""));
    TEST_ASSERT_NULL(gem_recs_lookup(recs, NULL, NULL));

    gem_recs_free(recs);
}

static void test_gem_recs_load_missing_file(void) {
    TEST_ASSERT_NULL(gem_recs_load("/nonexistent/path/gem_enchant_recs.json"));
    TEST_ASSERT_NULL(gem_recs_load(NULL));
    /* Freeing NULL is a no-op */
    gem_recs_free(NULL);
}

void test_gem_recs_suite(void) {
    RUN_TEST(test_gem_recs_load_and_lookup);
    RUN_TEST(test_gem_recs_lookup_missing);
    RUN_TEST(test_gem_recs_load_missing_file);
}
