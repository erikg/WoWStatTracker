/*
 * WoW Stat Tracker - Character Tests
 */

#define _POSIX_C_SOURCE 200809L
#include "unity.h"
#include "test_suites.h"
#include "character.h"
#include <stdlib.h>
#include <string.h>

static void test_character_new(void) {
    Character* c = character_new();
    TEST_ASSERT_NOT_NULL(c);
    TEST_ASSERT_NOT_NULL(c->realm);
    TEST_ASSERT_NOT_NULL(c->name);
    TEST_ASSERT_EQUAL_STRING("", c->realm);
    TEST_ASSERT_EQUAL_STRING("", c->name);
    TEST_ASSERT_EQUAL_DOUBLE(0.0, c->item_level);
    TEST_ASSERT_FALSE(c->vault_visited);

    /* New fields should be initialized to 0/NULL */
    TEST_ASSERT_EQUAL(0, c->upgrade_current);
    TEST_ASSERT_EQUAL(0, c->upgrade_max);
    TEST_ASSERT_EQUAL(0, c->socket_missing_count);
    TEST_ASSERT_EQUAL(0, c->socket_empty_count);
    TEST_ASSERT_EQUAL(0, c->enchant_missing_count);
    TEST_ASSERT_NULL(c->slot_upgrades_json);
    TEST_ASSERT_NULL(c->missing_sockets_json);
    TEST_ASSERT_NULL(c->empty_sockets_json);
    TEST_ASSERT_NULL(c->missing_enchants_json);

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

static void test_character_copy_new_fields(void) {
    Character* c1 = character_create("Realm", "Name");
    c1->upgrade_current = 111;
    c1->upgrade_max = 120;
    c1->socket_missing_count = 2;
    c1->socket_empty_count = 1;
    c1->enchant_missing_count = 3;
    c1->slot_upgrades_json = strdup("[{\"slot\":1}]");
    c1->missing_sockets_json = strdup("[1,6]");
    c1->empty_sockets_json = strdup("[9]");
    c1->missing_enchants_json = strdup("[5,7,8]");

    Character* c2 = character_copy(c1);
    TEST_ASSERT_NOT_NULL(c2);

    /* Verify new fields are copied */
    TEST_ASSERT_EQUAL(111, c2->upgrade_current);
    TEST_ASSERT_EQUAL(120, c2->upgrade_max);
    TEST_ASSERT_EQUAL(2, c2->socket_missing_count);
    TEST_ASSERT_EQUAL(1, c2->socket_empty_count);
    TEST_ASSERT_EQUAL(3, c2->enchant_missing_count);
    TEST_ASSERT_NOT_NULL(c2->slot_upgrades_json);
    TEST_ASSERT_EQUAL_STRING("[{\"slot\":1}]", c2->slot_upgrades_json);
    TEST_ASSERT_EQUAL_STRING("[1,6]", c2->missing_sockets_json);
    TEST_ASSERT_EQUAL_STRING("[9]", c2->empty_sockets_json);
    TEST_ASSERT_EQUAL_STRING("[5,7,8]", c2->missing_enchants_json);

    /* Ensure deep copy of strings */
    TEST_ASSERT_NOT_EQUAL(c1->slot_upgrades_json, c2->slot_upgrades_json);

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

static void test_character_to_json_new_fields(void) {
    Character* c = character_create("Realm", "Name");
    c->upgrade_current = 111;
    c->upgrade_max = 120;
    c->socket_missing_count = 2;
    c->socket_empty_count = 1;
    c->enchant_missing_count = 3;
    c->slot_upgrades_json = strdup("[{\"slot\":1,\"track\":\"Hero\",\"current\":5,\"max\":8}]");
    c->missing_sockets_json = strdup("[1,6]");
    c->empty_sockets_json = strdup("[9]");
    c->missing_enchants_json = strdup("[5,7,8]");

    cJSON* json = character_to_json(c);
    TEST_ASSERT_NOT_NULL(json);

    /* Verify aggregate counts */
    cJSON* upgrade_current = cJSON_GetObjectItem(json, "upgrade_current");
    TEST_ASSERT_TRUE(cJSON_IsNumber(upgrade_current));
    TEST_ASSERT_EQUAL(111, upgrade_current->valueint);

    cJSON* upgrade_max = cJSON_GetObjectItem(json, "upgrade_max");
    TEST_ASSERT_TRUE(cJSON_IsNumber(upgrade_max));
    TEST_ASSERT_EQUAL(120, upgrade_max->valueint);

    cJSON* socket_missing = cJSON_GetObjectItem(json, "socket_missing_count");
    TEST_ASSERT_TRUE(cJSON_IsNumber(socket_missing));
    TEST_ASSERT_EQUAL(2, socket_missing->valueint);

    cJSON* socket_empty = cJSON_GetObjectItem(json, "socket_empty_count");
    TEST_ASSERT_TRUE(cJSON_IsNumber(socket_empty));
    TEST_ASSERT_EQUAL(1, socket_empty->valueint);

    cJSON* enchant_missing = cJSON_GetObjectItem(json, "enchant_missing_count");
    TEST_ASSERT_TRUE(cJSON_IsNumber(enchant_missing));
    TEST_ASSERT_EQUAL(3, enchant_missing->valueint);

    /* Verify JSON string fields */
    cJSON* slot_upgrades = cJSON_GetObjectItem(json, "slot_upgrades_json");
    TEST_ASSERT_TRUE(cJSON_IsString(slot_upgrades));
    TEST_ASSERT_EQUAL_STRING("[{\"slot\":1,\"track\":\"Hero\",\"current\":5,\"max\":8}]",
                             slot_upgrades->valuestring);

    cJSON* missing_sockets = cJSON_GetObjectItem(json, "missing_sockets_json");
    TEST_ASSERT_TRUE(cJSON_IsString(missing_sockets));
    TEST_ASSERT_EQUAL_STRING("[1,6]", missing_sockets->valuestring);

    cJSON* empty_sockets = cJSON_GetObjectItem(json, "empty_sockets_json");
    TEST_ASSERT_TRUE(cJSON_IsString(empty_sockets));
    TEST_ASSERT_EQUAL_STRING("[9]", empty_sockets->valuestring);

    cJSON* missing_enchants = cJSON_GetObjectItem(json, "missing_enchants_json");
    TEST_ASSERT_TRUE(cJSON_IsString(missing_enchants));
    TEST_ASSERT_EQUAL_STRING("[5,7,8]", missing_enchants->valuestring);

    cJSON_Delete(json);
    character_free(c);
}

static void test_character_from_json_new_fields(void) {
    cJSON* json = cJSON_CreateObject();
    cJSON_AddStringToObject(json, "realm", "JsonRealm");
    cJSON_AddStringToObject(json, "name", "JsonChar");
    cJSON_AddNumberToObject(json, "upgrade_current", 105);
    cJSON_AddNumberToObject(json, "upgrade_max", 120);
    cJSON_AddNumberToObject(json, "socket_missing_count", 1);
    cJSON_AddNumberToObject(json, "socket_empty_count", 2);
    cJSON_AddNumberToObject(json, "enchant_missing_count", 4);
    cJSON_AddStringToObject(json, "slot_upgrades_json", "[{\"slot\":6}]");
    cJSON_AddStringToObject(json, "missing_sockets_json", "[1]");
    cJSON_AddStringToObject(json, "empty_sockets_json", "[6,9]");
    cJSON_AddStringToObject(json, "missing_enchants_json", "[5,7,8,11]");

    Character* c = character_from_json(json);
    TEST_ASSERT_NOT_NULL(c);

    /* Verify aggregate counts */
    TEST_ASSERT_EQUAL(105, c->upgrade_current);
    TEST_ASSERT_EQUAL(120, c->upgrade_max);
    TEST_ASSERT_EQUAL(1, c->socket_missing_count);
    TEST_ASSERT_EQUAL(2, c->socket_empty_count);
    TEST_ASSERT_EQUAL(4, c->enchant_missing_count);

    /* Verify JSON string fields */
    TEST_ASSERT_NOT_NULL(c->slot_upgrades_json);
    TEST_ASSERT_EQUAL_STRING("[{\"slot\":6}]", c->slot_upgrades_json);
    TEST_ASSERT_EQUAL_STRING("[1]", c->missing_sockets_json);
    TEST_ASSERT_EQUAL_STRING("[6,9]", c->empty_sockets_json);
    TEST_ASSERT_EQUAL_STRING("[5,7,8,11]", c->missing_enchants_json);

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
    RUN_TEST(test_character_copy_new_fields);
    RUN_TEST(test_character_validate_valid);
    RUN_TEST(test_character_validate_missing_name);
    RUN_TEST(test_character_validate_item_level_range);
    RUN_TEST(test_character_validate_delves_range);
    RUN_TEST(test_character_reset_weekly);
    RUN_TEST(test_character_to_json);
    RUN_TEST(test_character_from_json);
    RUN_TEST(test_character_to_json_new_fields);
    RUN_TEST(test_character_from_json_new_fields);
    RUN_TEST(test_character_set_fields);
}
