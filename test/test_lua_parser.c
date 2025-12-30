/*
 * WoW Stat Tracker - Lua Parser Tests
 */

#include "unity.h"
#include "lua_parser.h"
#include "character.h"
#include <string.h>
#include <stdlib.h>

static void test_lua_parser_empty_content(void) {
    LuaParseResult result = lua_parser_parse_content("");
    TEST_ASSERT_NULL(result.characters);
    TEST_ASSERT_EQUAL(0, result.count);
    lua_parser_free_result(&result);
}

static void test_lua_parser_null_content(void) {
    LuaParseResult result = lua_parser_parse_content(NULL);
    TEST_ASSERT_NULL(result.characters);
    TEST_ASSERT_EQUAL(0, result.count);
}

static void test_lua_parser_invalid_lua(void) {
    LuaParseResult result = lua_parser_parse_content("not valid lua {{{{");
    TEST_ASSERT_NULL(result.characters);
    TEST_ASSERT_EQUAL(0, result.count);
    lua_parser_free_result(&result);
}

static void test_lua_parser_empty_table(void) {
    const char* content = "{ characters = {}, metadata = { version = \"1.2.0\" } }";
    LuaParseResult result = lua_parser_parse_content(content);
    TEST_ASSERT_NOT_NULL(result.characters);
    TEST_ASSERT_EQUAL(0, result.count);
    TEST_ASSERT_NOT_NULL(result.addon_version);
    TEST_ASSERT_EQUAL_STRING("1.2.0", result.addon_version);
    lua_parser_free_result(&result);
}

static void test_lua_parser_single_character(void) {
    const char* content =
        "{\n"
        "  characters = {\n"
        "    [\"TestChar-TestRealm\"] = {\n"
        "      guild = \"Test Guild\",\n"
        "      item_level = 450.5,\n"
        "      heroic_items = 10,\n"
        "      champion_items = 5,\n"
        "      veteran_items = 1,\n"
        "      adventure_items = 0,\n"
        "      old_items = 0,\n"
        "      vault_visited = true,\n"
        "      gearing_up = false,\n"
        "      quests = true,\n"
        "      week_id = \"20251230\",\n"
        "    }\n"
        "  },\n"
        "  metadata = { version = \"1.2.0\" }\n"
        "}";

    LuaParseResult result = lua_parser_parse_content(content);
    TEST_ASSERT_NOT_NULL(result.characters);
    TEST_ASSERT_EQUAL(1, result.count);

    Character* c = result.characters[0];
    TEST_ASSERT_NOT_NULL(c);
    TEST_ASSERT_EQUAL_STRING("TestChar", c->name);
    TEST_ASSERT_EQUAL_STRING("TestRealm", c->realm);
    TEST_ASSERT_EQUAL_STRING("Test Guild", c->guild);
    TEST_ASSERT_DOUBLE_WITHIN(0.1, 450.5, c->item_level);
    TEST_ASSERT_EQUAL(10, c->heroic_items);
    TEST_ASSERT_EQUAL(5, c->champion_items);
    TEST_ASSERT_EQUAL(1, c->veteran_items);
    TEST_ASSERT_TRUE(c->vault_visited);
    TEST_ASSERT_FALSE(c->gearing_up);
    TEST_ASSERT_TRUE(c->quests);
    TEST_ASSERT_EQUAL_STRING("20251230", c->week_id);

    lua_parser_free_result(&result);
}

static void test_lua_parser_multiple_characters(void) {
    const char* content =
        "{\n"
        "  characters = {\n"
        "    [\"Char1-Realm1\"] = { item_level = 400 },\n"
        "    [\"Char2-Realm2\"] = { item_level = 500 },\n"
        "    [\"Char3-Realm3\"] = { item_level = 600 },\n"
        "  },\n"
        "  metadata = { version = \"1.0.0\" }\n"
        "}";

    LuaParseResult result = lua_parser_parse_content(content);
    TEST_ASSERT_NOT_NULL(result.characters);
    TEST_ASSERT_EQUAL(3, result.count);

    lua_parser_free_result(&result);
}

static void test_lua_parser_with_prefix(void) {
    const char* content =
        "WoWStatTrackerDB = {\n"
        "  characters = {\n"
        "    [\"Hero-Server\"] = { item_level = 715 }\n"
        "  },\n"
        "  metadata = { version = \"1.2.0\" }\n"
        "}";

    LuaParseResult result = lua_parser_parse_content(content);
    TEST_ASSERT_NOT_NULL(result.characters);
    TEST_ASSERT_EQUAL(1, result.count);
    TEST_ASSERT_EQUAL_STRING("Hero", result.characters[0]->name);

    lua_parser_free_result(&result);
}

static void test_lua_parser_nested_fields(void) {
    const char* content =
        "{\n"
        "  characters = {\n"
        "    [\"Test-Realm\"] = {\n"
        "      vault_delves = { count = 5 },\n"
        "      gilded_stash = { claimed = 3 },\n"
        "      timewalking_quest = { completed = true },\n"
        "      gearing_up = true,\n"
        "    }\n"
        "  },\n"
        "  metadata = { version = \"1.2.0\" }\n"
        "}";

    LuaParseResult result = lua_parser_parse_content(content);
    TEST_ASSERT_NOT_NULL(result.characters);
    TEST_ASSERT_EQUAL(1, result.count);

    Character* c = result.characters[0];
    /* delves = vault_delves.count - 1 (since gearing_up is true) */
    TEST_ASSERT_EQUAL(4, c->delves);
    TEST_ASSERT_EQUAL(3, c->gilded_stash);
    TEST_ASSERT_EQUAL(5, c->timewalk);  /* WST_MAX_TIMEWALK when completed */

    lua_parser_free_result(&result);
}

static void test_lua_parser_special_characters_in_name(void) {
    const char* content =
        "{\n"
        "  characters = {\n"
        "    [\"Tëst-Realm\"] = { item_level = 700 }\n"
        "  },\n"
        "  metadata = { version = \"1.2.0\" }\n"
        "}";

    LuaParseResult result = lua_parser_parse_content(content);
    TEST_ASSERT_NOT_NULL(result.characters);
    TEST_ASSERT_EQUAL(1, result.count);
    TEST_ASSERT_EQUAL_STRING("Tëst", result.characters[0]->name);

    lua_parser_free_result(&result);
}

static void test_lua_parser_missing_metadata(void) {
    const char* content =
        "{\n"
        "  characters = {\n"
        "    [\"Test-Realm\"] = { item_level = 700 }\n"
        "  }\n"
        "}";

    LuaParseResult result = lua_parser_parse_content(content);
    TEST_ASSERT_NOT_NULL(result.characters);
    TEST_ASSERT_EQUAL(1, result.count);
    TEST_ASSERT_NULL(result.addon_version);

    lua_parser_free_result(&result);
}

static void test_lua_parser_free_null(void) {
    /* Should not crash */
    lua_parser_free_result(NULL);

    LuaParseResult empty = {0};
    lua_parser_free_result(&empty);
}

void test_lua_parser_suite(void) {
    RUN_TEST(test_lua_parser_empty_content);
    RUN_TEST(test_lua_parser_null_content);
    RUN_TEST(test_lua_parser_invalid_lua);
    RUN_TEST(test_lua_parser_empty_table);
    RUN_TEST(test_lua_parser_single_character);
    RUN_TEST(test_lua_parser_multiple_characters);
    RUN_TEST(test_lua_parser_with_prefix);
    RUN_TEST(test_lua_parser_nested_fields);
    RUN_TEST(test_lua_parser_special_characters_in_name);
    RUN_TEST(test_lua_parser_missing_metadata);
    RUN_TEST(test_lua_parser_free_null);
}
