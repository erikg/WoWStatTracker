/*
 * WoW Stat Tracker - Lua Parser Tests
 */

#include "unity.h"
#include "test_suites.h"
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

static void test_lua_parser_all_fields(void) {
    /* Test all character fields with proper nested structures */
    const char* content =
        "{\n"
        "  characters = {\n"
        "    [\"TestChar-Misha\"] = {\n"
        "      name = \"TestChar\",\n"
        "      realm = \"Misha\",\n"
        "      guild = \"Test Guild\",\n"
        "      item_level = 625,\n"
        "      heroic_items = 3,\n"
        "      champion_items = 5,\n"
        "      veteran_items = 2,\n"
        "      adventure_items = 1,\n"
        "      old_items = 0,\n"
        "      vault_visited = true,\n"
        "      vault_delves = { count = 5 },\n"
        "      gilded_stash = { claimed = 2 },\n"
        "      gearing_up = true,\n"
        "      quests = false,\n"
        "      timewalking_quest = { completed = false, progress = 3 },\n"
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
    TEST_ASSERT_EQUAL_STRING("Misha", c->realm);
    TEST_ASSERT_EQUAL_STRING("Test Guild", c->guild);
    TEST_ASSERT_DOUBLE_WITHIN(0.1, 625.0, c->item_level);
    TEST_ASSERT_EQUAL(3, c->heroic_items);
    TEST_ASSERT_EQUAL(5, c->champion_items);
    TEST_ASSERT_EQUAL(2, c->veteran_items);
    TEST_ASSERT_EQUAL(1, c->adventure_items);
    TEST_ASSERT_EQUAL(0, c->old_items);
    TEST_ASSERT_TRUE(c->vault_visited);
    /* vault_delves.count=5 minus 1 for gearing_up=true */
    TEST_ASSERT_EQUAL(4, c->delves);
    TEST_ASSERT_EQUAL(2, c->gilded_stash);
    TEST_ASSERT_TRUE(c->gearing_up);
    TEST_ASSERT_FALSE(c->quests);
    TEST_ASSERT_EQUAL(3, c->timewalk);
    /* notes are not imported from addon, they're user-entered */

    lua_parser_free_result(&result);
}

static void test_lua_parser_leading_whitespace(void) {
    /* WoW sometimes adds leading newline to SavedVariables files */
    const char* content =
        "\n"
        "WoWStatTrackerDB = {\n"
        "[\"characters\"] = {\n"
        "[\"Hero-Server\"] = {\n"
        "[\"item_level\"] = 700,\n"
        "[\"guild\"] = \"Test\",\n"
        "},\n"
        "},\n"
        "}";

    LuaParseResult result = lua_parser_parse_content(content);
    TEST_ASSERT_NOT_NULL(result.characters);
    TEST_ASSERT_EQUAL(1, result.count);
    TEST_ASSERT_EQUAL_STRING("Hero", result.characters[0]->name);
    TEST_ASSERT_DOUBLE_WITHIN(0.1, 700.0, result.characters[0]->item_level);

    lua_parser_free_result(&result);
}

static void test_lua_parser_wow_bracket_format(void) {
    /* Test the actual WoW SavedVariables format with ["key"] = syntax */
    const char* content =
        "WoWStatTrackerDB = {\n"
        "[\"settings\"] = {\n"
        "[\"exportOnLogout\"] = true,\n"
        "},\n"
        "[\"characters\"] = {\n"
        "[\"Magella-Cairne\"] = {\n"
        "[\"guild\"] = \"MENACE\",\n"
        "[\"item_level\"] = 715,\n"
        "[\"heroic_items\"] = 5,\n"
        "[\"vault_visited\"] = true,\n"
        "},\n"
        "},\n"
        "[\"metadata\"] = {\n"
        "[\"version\"] = \"1.2.0\",\n"
        "},\n"
        "}";

    LuaParseResult result = lua_parser_parse_content(content);
    TEST_ASSERT_NOT_NULL(result.characters);
    TEST_ASSERT_EQUAL(1, result.count);

    Character* c = result.characters[0];
    TEST_ASSERT_EQUAL_STRING("Magella", c->name);
    TEST_ASSERT_EQUAL_STRING("Cairne", c->realm);
    TEST_ASSERT_EQUAL_STRING("MENACE", c->guild);
    TEST_ASSERT_DOUBLE_WITHIN(0.1, 715.0, c->item_level);
    TEST_ASSERT_EQUAL(5, c->heroic_items);
    TEST_ASSERT_TRUE(c->vault_visited);
    TEST_ASSERT_EQUAL_STRING("1.2.0", result.addon_version);

    lua_parser_free_result(&result);
}

static void test_lua_parser_import_updates_existing(void) {
    /* Test that parsing multiple times works correctly (simulating re-import) */
    const char* content1 =
        "{ characters = { [\"Test-Realm\"] = { item_level = 600 } } }";
    const char* content2 =
        "{ characters = { [\"Test-Realm\"] = { item_level = 650 } } }";

    LuaParseResult result1 = lua_parser_parse_content(content1);
    TEST_ASSERT_EQUAL(1, result1.count);
    TEST_ASSERT_DOUBLE_WITHIN(0.1, 600.0, result1.characters[0]->item_level);

    LuaParseResult result2 = lua_parser_parse_content(content2);
    TEST_ASSERT_EQUAL(1, result2.count);
    TEST_ASSERT_DOUBLE_WITHIN(0.1, 650.0, result2.characters[0]->item_level);

    /* Original result should be unchanged */
    TEST_ASSERT_DOUBLE_WITHIN(0.1, 600.0, result1.characters[0]->item_level);

    lua_parser_free_result(&result1);
    lua_parser_free_result(&result2);
}

static void test_lua_parser_many_characters(void) {
    /* Test importing many characters at once */
    const char* content =
        "{\n"
        "  characters = {\n"
        "    [\"Char1-Realm\"] = { item_level = 600 },\n"
        "    [\"Char2-Realm\"] = { item_level = 610 },\n"
        "    [\"Char3-Realm\"] = { item_level = 620 },\n"
        "    [\"Char4-Realm\"] = { item_level = 630 },\n"
        "    [\"Char5-Realm\"] = { item_level = 640 },\n"
        "    [\"Char6-Realm\"] = { item_level = 650 },\n"
        "    [\"Char7-Realm\"] = { item_level = 660 },\n"
        "    [\"Char8-Realm\"] = { item_level = 670 },\n"
        "    [\"Char9-Realm\"] = { item_level = 680 },\n"
        "    [\"Char10-Realm\"] = { item_level = 690 },\n"
        "  }\n"
        "}";

    LuaParseResult result = lua_parser_parse_content(content);
    TEST_ASSERT_NOT_NULL(result.characters);
    TEST_ASSERT_EQUAL(10, result.count);

    /* Verify all characters are unique */
    for (size_t i = 0; i < result.count; i++) {
        TEST_ASSERT_NOT_NULL(result.characters[i]);
        TEST_ASSERT_NOT_NULL(result.characters[i]->name);
    }

    lua_parser_free_result(&result);
}

static void test_lua_parser_new_gear_fields(void) {
    /* Test parsing upgrade_current, upgrade_max, socket_info, enchant_info */
    const char* content =
        "{\n"
        "  characters = {\n"
        "    [\"TestChar-Realm\"] = {\n"
        "      item_level = 630,\n"
        "      upgrade_current = 111,\n"
        "      upgrade_max = 120,\n"
        "      socket_info = {\n"
        "        socketable_count = 3,\n"
        "        socketed_count = 1,\n"
        "        empty_count = 2,\n"
        "        missing_sockets = { 1, 6 },\n"
        "        empty_sockets = { 9 },\n"
        "      },\n"
        "      enchant_info = {\n"
        "        enchantable_count = 8,\n"
        "        enchant_count = 5,\n"
        "        missing_enchants = { 5, 7, 8 },\n"
        "      },\n"
        "    }\n"
        "  },\n"
        "  metadata = { version = \"1.2.0\" }\n"
        "}";

    LuaParseResult result = lua_parser_parse_content(content);
    TEST_ASSERT_NOT_NULL(result.characters);
    TEST_ASSERT_EQUAL(1, result.count);

    Character* c = result.characters[0];
    TEST_ASSERT_NOT_NULL(c);

    /* Verify aggregate counts */
    TEST_ASSERT_EQUAL(111, c->upgrade_current);
    TEST_ASSERT_EQUAL(120, c->upgrade_max);

    /* socket_missing = socketable_count - socketed_count = 3 - 1 = 2 */
    TEST_ASSERT_EQUAL(2, c->socket_missing_count);
    TEST_ASSERT_EQUAL(2, c->socket_empty_count);

    /* enchant_missing = enchantable_count - enchant_count = 8 - 5 = 3 */
    TEST_ASSERT_EQUAL(3, c->enchant_missing_count);

    /* Verify JSON string fields exist */
    TEST_ASSERT_NOT_NULL(c->missing_sockets_json);
    TEST_ASSERT_NOT_NULL(c->empty_sockets_json);
    TEST_ASSERT_NOT_NULL(c->missing_enchants_json);

    /* The JSON strings should contain the slot arrays */
    TEST_ASSERT_TRUE(strstr(c->missing_sockets_json, "1") != NULL);
    TEST_ASSERT_TRUE(strstr(c->missing_sockets_json, "6") != NULL);
    TEST_ASSERT_TRUE(strstr(c->empty_sockets_json, "9") != NULL);
    TEST_ASSERT_TRUE(strstr(c->missing_enchants_json, "5") != NULL);
    TEST_ASSERT_TRUE(strstr(c->missing_enchants_json, "7") != NULL);
    TEST_ASSERT_TRUE(strstr(c->missing_enchants_json, "8") != NULL);

    lua_parser_free_result(&result);
}

static void test_lua_parser_slot_upgrades(void) {
    /* Test parsing slot_upgrades with per-slot data */
    const char* content =
        "{\n"
        "  characters = {\n"
        "    [\"TestChar-Realm\"] = {\n"
        "      item_level = 630,\n"
        "      slot_upgrades = {\n"
        "        [1] = { slot = 1, slot_name = \"Head\", track = \"Hero\", current = 5, max = 8 },\n"
        "        [6] = { slot = 6, slot_name = \"Waist\", track = \"Champion\", current = 3, max = 8 },\n"
        "      },\n"
        "    }\n"
        "  },\n"
        "  metadata = { version = \"1.2.0\" }\n"
        "}";

    LuaParseResult result = lua_parser_parse_content(content);
    TEST_ASSERT_NOT_NULL(result.characters);
    TEST_ASSERT_EQUAL(1, result.count);

    Character* c = result.characters[0];
    TEST_ASSERT_NOT_NULL(c);

    /* slot_upgrades_json should be populated */
    TEST_ASSERT_NOT_NULL(c->slot_upgrades_json);

    /* Verify JSON contains expected slot data */
    TEST_ASSERT_TRUE(strstr(c->slot_upgrades_json, "slot") != NULL);
    TEST_ASSERT_TRUE(strstr(c->slot_upgrades_json, "Hero") != NULL ||
                     strstr(c->slot_upgrades_json, "Champion") != NULL);

    lua_parser_free_result(&result);
}

static void test_lua_parser_gear_fields_missing(void) {
    /* Test that missing gear fields default to 0/NULL */
    const char* content =
        "{\n"
        "  characters = {\n"
        "    [\"TestChar-Realm\"] = {\n"
        "      item_level = 600,\n"
        "    }\n"
        "  }\n"
        "}";

    LuaParseResult result = lua_parser_parse_content(content);
    TEST_ASSERT_NOT_NULL(result.characters);
    TEST_ASSERT_EQUAL(1, result.count);

    Character* c = result.characters[0];
    TEST_ASSERT_NOT_NULL(c);

    /* All new fields should be 0/NULL when not present */
    TEST_ASSERT_EQUAL(0, c->upgrade_current);
    TEST_ASSERT_EQUAL(0, c->upgrade_max);
    TEST_ASSERT_EQUAL(0, c->socket_missing_count);
    TEST_ASSERT_EQUAL(0, c->socket_empty_count);
    TEST_ASSERT_EQUAL(0, c->enchant_missing_count);
    TEST_ASSERT_NULL(c->slot_upgrades_json);
    TEST_ASSERT_NULL(c->missing_sockets_json);
    TEST_ASSERT_NULL(c->empty_sockets_json);
    TEST_ASSERT_NULL(c->missing_enchants_json);

    lua_parser_free_result(&result);
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
    RUN_TEST(test_lua_parser_all_fields);
    RUN_TEST(test_lua_parser_leading_whitespace);
    RUN_TEST(test_lua_parser_wow_bracket_format);
    RUN_TEST(test_lua_parser_import_updates_existing);
    RUN_TEST(test_lua_parser_many_characters);
    RUN_TEST(test_lua_parser_new_gear_fields);
    RUN_TEST(test_lua_parser_slot_upgrades);
    RUN_TEST(test_lua_parser_gear_fields_missing);
}
