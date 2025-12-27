/*
 * WoW Stat Tracker - Character Store Tests
 */

#include "unity.h"
#include "character_store.h"
#include <stdlib.h>
#include <stdio.h>

static const char* TEST_FILE = "test_characters.json";

static void test_character_store_new(void) {
    CharacterStore* store = character_store_new(TEST_FILE);
    TEST_ASSERT_NOT_NULL(store);
    TEST_ASSERT_EQUAL(0, character_store_count(store));
    character_store_free(store);
}

static void test_character_store_add(void) {
    CharacterStore* store = character_store_new(TEST_FILE);
    Character* c = character_create("Realm", "Name");

    WstResult result = character_store_add(store, c);
    TEST_ASSERT_EQUAL(WST_OK, result);
    TEST_ASSERT_EQUAL(1, character_store_count(store));

    Character* retrieved = character_store_get(store, 0);
    TEST_ASSERT_NOT_NULL(retrieved);
    TEST_ASSERT_EQUAL_STRING("Name", retrieved->name);

    character_store_free(store);
}

static void test_character_store_update(void) {
    CharacterStore* store = character_store_new(TEST_FILE);
    character_store_add(store, character_create("Realm", "Original"));

    Character* updated = character_create("Realm", "Updated");
    WstResult result = character_store_update(store, 0, updated);
    TEST_ASSERT_EQUAL(WST_OK, result);

    Character* retrieved = character_store_get(store, 0);
    TEST_ASSERT_EQUAL_STRING("Updated", retrieved->name);

    character_store_free(store);
}

static void test_character_store_delete(void) {
    CharacterStore* store = character_store_new(TEST_FILE);
    character_store_add(store, character_create("Realm", "One"));
    character_store_add(store, character_create("Realm", "Two"));
    character_store_add(store, character_create("Realm", "Three"));

    TEST_ASSERT_EQUAL(3, character_store_count(store));

    WstResult result = character_store_delete(store, 1);  /* Delete "Two" */
    TEST_ASSERT_EQUAL(WST_OK, result);
    TEST_ASSERT_EQUAL(2, character_store_count(store));

    /* "One" should still be at index 0, "Three" should now be at index 1 */
    TEST_ASSERT_EQUAL_STRING("One", character_store_get(store, 0)->name);
    TEST_ASSERT_EQUAL_STRING("Three", character_store_get(store, 1)->name);

    character_store_free(store);
}

static void test_character_store_find(void) {
    CharacterStore* store = character_store_new(TEST_FILE);
    character_store_add(store, character_create("Realm1", "Char1"));
    character_store_add(store, character_create("Realm2", "Char2"));
    character_store_add(store, character_create("Realm1", "Char3"));

    int idx = character_store_find(store, "Realm2", "Char2");
    TEST_ASSERT_EQUAL(1, idx);

    idx = character_store_find(store, "Realm1", "Char3");
    TEST_ASSERT_EQUAL(2, idx);

    idx = character_store_find(store, "NoRealm", "NoChar");
    TEST_ASSERT_EQUAL(-1, idx);

    character_store_free(store);
}

static void test_character_store_reset_weekly_all(void) {
    CharacterStore* store = character_store_new(TEST_FILE);

    Character* c1 = character_create("Realm", "One");
    c1->vault_visited = true;
    c1->delves = 5;
    character_store_add(store, c1);

    Character* c2 = character_create("Realm", "Two");
    c2->gearing_up = true;
    c2->timewalk = 3;
    character_store_add(store, c2);

    character_store_reset_weekly_all(store);

    TEST_ASSERT_FALSE(character_store_get(store, 0)->vault_visited);
    TEST_ASSERT_EQUAL(0, character_store_get(store, 0)->delves);
    TEST_ASSERT_FALSE(character_store_get(store, 1)->gearing_up);
    TEST_ASSERT_EQUAL(0, character_store_get(store, 1)->timewalk);

    character_store_free(store);
}

static void test_character_store_save_load(void) {
    /* Save */
    {
        CharacterStore* store = character_store_new(TEST_FILE);
        Character* c = character_create("SaveRealm", "SaveChar");
        c->item_level = 500.5;
        c->heroic_items = 10;
        character_store_add(store, c);

        WstResult result = character_store_save(store);
        TEST_ASSERT_EQUAL(WST_OK, result);
        character_store_free(store);
    }

    /* Load */
    {
        CharacterStore* store = character_store_new(TEST_FILE);
        WstResult result = character_store_load(store);
        TEST_ASSERT_EQUAL(WST_OK, result);
        TEST_ASSERT_EQUAL(1, character_store_count(store));

        Character* c = character_store_get(store, 0);
        TEST_ASSERT_EQUAL_STRING("SaveRealm", c->realm);
        TEST_ASSERT_EQUAL_STRING("SaveChar", c->name);
        TEST_ASSERT_EQUAL_DOUBLE(500.5, c->item_level);
        TEST_ASSERT_EQUAL(10, c->heroic_items);

        character_store_free(store);
    }

    /* Clean up */
    remove(TEST_FILE);
}

static void test_character_store_out_of_range(void) {
    CharacterStore* store = character_store_new(TEST_FILE);
    character_store_add(store, character_create("Realm", "Name"));

    TEST_ASSERT_NULL(character_store_get(store, 5));
    TEST_ASSERT_EQUAL(WST_ERR_OUT_OF_RANGE, character_store_delete(store, 5));
    TEST_ASSERT_EQUAL(WST_ERR_OUT_OF_RANGE,
                      character_store_update(store, 5, character_create("R", "N")));

    character_store_free(store);
}

void test_character_store_suite(void) {
    RUN_TEST(test_character_store_new);
    RUN_TEST(test_character_store_add);
    RUN_TEST(test_character_store_update);
    RUN_TEST(test_character_store_delete);
    RUN_TEST(test_character_store_find);
    RUN_TEST(test_character_store_reset_weekly_all);
    RUN_TEST(test_character_store_save_load);
    RUN_TEST(test_character_store_out_of_range);
}
