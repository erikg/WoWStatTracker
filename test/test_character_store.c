/*
 * WoW Stat Tracker - Character Store Tests
 */

#include "unity.h"
#include "test_suites.h"
#include "character_store.h"
#include "util.h"
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

static void test_character_store_save_overwrite(void) {
    /* First save */
    {
        CharacterStore* store = character_store_new(TEST_FILE);
        Character* c = character_create("Realm1", "Char1");
        character_store_add(store, c);
        TEST_ASSERT_EQUAL(WST_OK, character_store_save(store));
        character_store_free(store);
    }

    /* Second save (overwrite with different data) */
    {
        CharacterStore* store = character_store_new(TEST_FILE);
        Character* c = character_create("Realm2", "Char2");
        c->item_level = 600.0;
        character_store_add(store, c);
        TEST_ASSERT_EQUAL(WST_OK, character_store_save(store));
        character_store_free(store);
    }

    /* Verify overwrite */
    {
        CharacterStore* store = character_store_new(TEST_FILE);
        TEST_ASSERT_EQUAL(WST_OK, character_store_load(store));
        TEST_ASSERT_EQUAL(1, character_store_count(store));

        Character* c = character_store_get(store, 0);
        TEST_ASSERT_EQUAL_STRING("Realm2", c->realm);
        TEST_ASSERT_EQUAL_STRING("Char2", c->name);
        TEST_ASSERT_EQUAL_DOUBLE(600.0, c->item_level);

        character_store_free(store);
    }

    remove(TEST_FILE);
}

static void test_character_store_save_empty(void) {
    /* Save empty store */
    {
        CharacterStore* store = character_store_new(TEST_FILE);
        TEST_ASSERT_EQUAL(WST_OK, character_store_save(store));
        character_store_free(store);
    }

    /* Load empty store */
    {
        CharacterStore* store = character_store_new(TEST_FILE);
        TEST_ASSERT_EQUAL(WST_OK, character_store_load(store));
        TEST_ASSERT_EQUAL(0, character_store_count(store));
        character_store_free(store);
    }

    remove(TEST_FILE);
}

static void test_character_store_save_multiple_characters(void) {
    /* Save multiple characters */
    {
        CharacterStore* store = character_store_new(TEST_FILE);

        for (int i = 0; i < 10; i++) {
            char name[32];
            snprintf(name, sizeof(name), "Char%d", i);
            Character* c = character_create("TestRealm", name);
            c->item_level = 400.0 + i * 10;
            c->heroic_items = i;
            c->delves = i % 5;
            character_store_add(store, c);
        }

        TEST_ASSERT_EQUAL(WST_OK, character_store_save(store));
        character_store_free(store);
    }

    /* Load and verify */
    {
        CharacterStore* store = character_store_new(TEST_FILE);
        TEST_ASSERT_EQUAL(WST_OK, character_store_load(store));
        TEST_ASSERT_EQUAL(10, character_store_count(store));

        for (int i = 0; i < 10; i++) {
            char expected_name[32];
            snprintf(expected_name, sizeof(expected_name), "Char%d", i);

            Character* c = character_store_get(store, i);
            TEST_ASSERT_EQUAL_STRING("TestRealm", c->realm);
            TEST_ASSERT_EQUAL_STRING(expected_name, c->name);
            TEST_ASSERT_EQUAL_DOUBLE(400.0 + i * 10, c->item_level);
            TEST_ASSERT_EQUAL(i, c->heroic_items);
            TEST_ASSERT_EQUAL(i % 5, c->delves);
        }

        character_store_free(store);
    }

    remove(TEST_FILE);
}

static void test_character_store_save_all_fields(void) {
    /* Save character with all fields populated */
    {
        CharacterStore* store = character_store_new(TEST_FILE);
        Character* c = character_create("TestRealm", "TestChar");

        c->guild = wst_strdup("Test Guild");
        c->item_level = 525.5;
        c->heroic_items = 5;
        c->champion_items = 3;
        c->veteran_items = 2;
        c->adventure_items = 1;
        c->old_items = 0;
        c->vault_visited = true;
        c->delves = 4;
        c->gilded_stash = 3;
        c->gearing_up = true;
        c->quests = true;
        c->timewalk = 5;
        c->notes = wst_strdup("Test notes here");

        character_store_add(store, c);
        TEST_ASSERT_EQUAL(WST_OK, character_store_save(store));
        character_store_free(store);
    }

    /* Load and verify all fields */
    {
        CharacterStore* store = character_store_new(TEST_FILE);
        TEST_ASSERT_EQUAL(WST_OK, character_store_load(store));
        TEST_ASSERT_EQUAL(1, character_store_count(store));

        Character* c = character_store_get(store, 0);
        TEST_ASSERT_EQUAL_STRING("TestRealm", c->realm);
        TEST_ASSERT_EQUAL_STRING("TestChar", c->name);
        TEST_ASSERT_EQUAL_STRING("Test Guild", c->guild);
        TEST_ASSERT_EQUAL_DOUBLE(525.5, c->item_level);
        TEST_ASSERT_EQUAL(5, c->heroic_items);
        TEST_ASSERT_EQUAL(3, c->champion_items);
        TEST_ASSERT_EQUAL(2, c->veteran_items);
        TEST_ASSERT_EQUAL(1, c->adventure_items);
        TEST_ASSERT_EQUAL(0, c->old_items);
        TEST_ASSERT_TRUE(c->vault_visited);
        TEST_ASSERT_EQUAL(4, c->delves);
        TEST_ASSERT_EQUAL(3, c->gilded_stash);
        TEST_ASSERT_TRUE(c->gearing_up);
        TEST_ASSERT_TRUE(c->quests);
        TEST_ASSERT_EQUAL(5, c->timewalk);
        TEST_ASSERT_EQUAL_STRING("Test notes here", c->notes);

        character_store_free(store);
    }

    remove(TEST_FILE);
}

static void test_character_store_multiple_save_load_cycles(void) {
    /* Multiple save/load cycles with modifications */
    for (int cycle = 0; cycle < 3; cycle++) {
        CharacterStore* store = character_store_new(TEST_FILE);

        if (cycle > 0) {
            TEST_ASSERT_EQUAL(WST_OK, character_store_load(store));
            TEST_ASSERT_EQUAL((size_t)cycle, character_store_count(store));
        }

        char name[32];
        snprintf(name, sizeof(name), "Cycle%d", cycle);
        Character* c = character_create("Realm", name);
        character_store_add(store, c);

        TEST_ASSERT_EQUAL(WST_OK, character_store_save(store));
        character_store_free(store);
    }

    /* Final verify */
    {
        CharacterStore* store = character_store_new(TEST_FILE);
        TEST_ASSERT_EQUAL(WST_OK, character_store_load(store));
        TEST_ASSERT_EQUAL(3, character_store_count(store));

        for (int i = 0; i < 3; i++) {
            char expected_name[32];
            snprintf(expected_name, sizeof(expected_name), "Cycle%d", i);
            Character* c = character_store_get(store, i);
            TEST_ASSERT_EQUAL_STRING(expected_name, c->name);
        }

        character_store_free(store);
    }

    remove(TEST_FILE);
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
    RUN_TEST(test_character_store_save_overwrite);
    RUN_TEST(test_character_store_save_empty);
    RUN_TEST(test_character_store_save_multiple_characters);
    RUN_TEST(test_character_store_save_all_fields);
    RUN_TEST(test_character_store_multiple_save_load_cycles);
}
