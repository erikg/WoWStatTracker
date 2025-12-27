/*
 * WoW Stat Tracker - Character Tests
 */

#include "unity.h"
#include "character.h"
#include <stdlib.h>

static void test_character_new(void) {
    Character* c = character_new();
    TEST_ASSERT_NOT_NULL(c);
    TEST_ASSERT_NOT_NULL(c->realm);
    TEST_ASSERT_NOT_NULL(c->name);
    TEST_ASSERT_EQUAL_STRING("", c->realm);
    TEST_ASSERT_EQUAL_STRING("", c->name);
    TEST_ASSERT_EQUAL_DOUBLE(0.0, c->item_level);
    TEST_ASSERT_FALSE(c->vault_visited);
    character_free(c);
}

static void test_character_create(void) {
    Character* c = character_create("TestRealm", "TestChar");
    TEST_ASSERT_NOT_NULL(c);
    TEST_ASSERT_EQUAL_STRING("TestRealm", c->realm);
    TEST_ASSERT_EQUAL_STRING("TestChar", c->name);
    character_free(c);
}

static void test_character_copy(void) {
    Character* c1 = character_create("Realm", "Name");
    c1->item_level = 500.5;
    c1->heroic_items = 10;
    c1->vault_visited = true;
    character_set_guild(c1, "Test Guild");

    Character* c2 = character_copy(c1);
    TEST_ASSERT_NOT_NULL(c2);
    TEST_ASSERT_EQUAL_STRING("Realm", c2->realm);
    TEST_ASSERT_EQUAL_STRING("Name", c2->name);
    TEST_ASSERT_EQUAL_STRING("Test Guild", c2->guild);
    TEST_ASSERT_EQUAL_DOUBLE(500.5, c2->item_level);
    TEST_ASSERT_EQUAL(10, c2->heroic_items);
    TEST_ASSERT_TRUE(c2->vault_visited);

    /* Ensure deep copy - modifying one doesn't affect the other */
    character_set_name(c1, "Changed");
    TEST_ASSERT_EQUAL_STRING("Name", c2->name);

    character_free(c1);
    character_free(c2);
}

static void test_character_validate_valid(void) {
    Character* c = character_create("Realm", "Name");
    c->item_level = 500.0;
    c->delves = 4;

    char** errors = NULL;
    size_t error_count = 0;
    WstResult result = character_validate(c, &errors, &error_count);

    TEST_ASSERT_EQUAL(WST_OK, result);
    TEST_ASSERT_EQUAL(0, error_count);

    character_free(c);
}

static void test_character_validate_missing_name(void) {
    Character* c = character_new();
    character_set_realm(c, "Realm");

    char** errors = NULL;
    size_t error_count = 0;
    WstResult result = character_validate(c, &errors, &error_count);

    TEST_ASSERT_EQUAL(WST_ERR_VALIDATION, result);
    TEST_ASSERT_TRUE(error_count > 0);

    character_free_errors(errors, error_count);
    character_free(c);
}

static void test_character_validate_item_level_range(void) {
    Character* c = character_create("Realm", "Name");
    c->item_level = 2000.0;  /* Over max */

    char** errors = NULL;
    size_t error_count = 0;
    WstResult result = character_validate(c, &errors, &error_count);

    TEST_ASSERT_EQUAL(WST_ERR_VALIDATION, result);

    character_free_errors(errors, error_count);
    character_free(c);
}

static void test_character_validate_delves_range(void) {
    Character* c = character_create("Realm", "Name");
    c->delves = 100;  /* Over max */

    char** errors = NULL;
    size_t error_count = 0;
    WstResult result = character_validate(c, &errors, &error_count);

    TEST_ASSERT_EQUAL(WST_ERR_VALIDATION, result);

    character_free_errors(errors, error_count);
    character_free(c);
}

static void test_character_reset_weekly(void) {
    Character* c = character_create("Realm", "Name");
    c->vault_visited = true;
    c->delves = 5;
    c->gilded_stash = 2;
    c->gearing_up = true;
    c->quests = true;
    c->timewalk = 3;

    character_reset_weekly(c);

    TEST_ASSERT_FALSE(c->vault_visited);
    TEST_ASSERT_EQUAL(0, c->delves);
    TEST_ASSERT_EQUAL(0, c->gilded_stash);
    TEST_ASSERT_FALSE(c->gearing_up);
    TEST_ASSERT_FALSE(c->quests);
    TEST_ASSERT_EQUAL(0, c->timewalk);

    character_free(c);
}

static void test_character_to_json(void) {
    Character* c = character_create("TestRealm", "TestChar");
    c->item_level = 485.5;
    c->heroic_items = 12;
    c->vault_visited = true;
    character_set_guild(c, "Test Guild");

    cJSON* json = character_to_json(c);
    TEST_ASSERT_NOT_NULL(json);

    cJSON* name = cJSON_GetObjectItem(json, "name");
    TEST_ASSERT_TRUE(cJSON_IsString(name));
    TEST_ASSERT_EQUAL_STRING("TestChar", name->valuestring);

    cJSON* item_level = cJSON_GetObjectItem(json, "item_level");
    TEST_ASSERT_TRUE(cJSON_IsNumber(item_level));
    TEST_ASSERT_EQUAL_DOUBLE(485.5, item_level->valuedouble);

    cJSON* visited = cJSON_GetObjectItem(json, "vault_visited");
    TEST_ASSERT_TRUE(cJSON_IsTrue(visited));

    cJSON_Delete(json);
    character_free(c);
}

static void test_character_from_json(void) {
    cJSON* json = cJSON_CreateObject();
    cJSON_AddStringToObject(json, "realm", "JsonRealm");
    cJSON_AddStringToObject(json, "name", "JsonChar");
    cJSON_AddStringToObject(json, "guild", "Json Guild");
    cJSON_AddNumberToObject(json, "item_level", 520.25);
    cJSON_AddNumberToObject(json, "heroic_items", 8);
    cJSON_AddBoolToObject(json, "vault_visited", true);
    cJSON_AddBoolToObject(json, "gearing_up", false);

    Character* c = character_from_json(json);
    TEST_ASSERT_NOT_NULL(c);
    TEST_ASSERT_EQUAL_STRING("JsonRealm", c->realm);
    TEST_ASSERT_EQUAL_STRING("JsonChar", c->name);
    TEST_ASSERT_EQUAL_STRING("Json Guild", c->guild);
    TEST_ASSERT_EQUAL_DOUBLE(520.25, c->item_level);
    TEST_ASSERT_EQUAL(8, c->heroic_items);
    TEST_ASSERT_TRUE(c->vault_visited);
    TEST_ASSERT_FALSE(c->gearing_up);

    cJSON_Delete(json);
    character_free(c);
}

static void test_character_set_fields(void) {
    Character* c = character_new();

    TEST_ASSERT_EQUAL(WST_OK, character_set_realm(c, "NewRealm"));
    TEST_ASSERT_EQUAL_STRING("NewRealm", c->realm);

    TEST_ASSERT_EQUAL(WST_OK, character_set_name(c, "NewName"));
    TEST_ASSERT_EQUAL_STRING("NewName", c->name);

    TEST_ASSERT_EQUAL(WST_OK, character_set_guild(c, "NewGuild"));
    TEST_ASSERT_EQUAL_STRING("NewGuild", c->guild);

    TEST_ASSERT_EQUAL(WST_OK, character_set_notes(c, "Some notes"));
    TEST_ASSERT_EQUAL_STRING("Some notes", c->notes);

    character_free(c);
}

void test_character_suite(void) {
    RUN_TEST(test_character_new);
    RUN_TEST(test_character_create);
    RUN_TEST(test_character_copy);
    RUN_TEST(test_character_validate_valid);
    RUN_TEST(test_character_validate_missing_name);
    RUN_TEST(test_character_validate_item_level_range);
    RUN_TEST(test_character_validate_delves_range);
    RUN_TEST(test_character_reset_weekly);
    RUN_TEST(test_character_to_json);
    RUN_TEST(test_character_from_json);
    RUN_TEST(test_character_set_fields);
}
