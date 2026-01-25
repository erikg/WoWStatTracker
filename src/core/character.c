/*
 * WoW Stat Tracker - Character Implementation
 * BSD 3-Clause License
 */

#include "character.h"
#include "util.h"
#include <stdlib.h>
#include <string.h>
#include <stdio.h>

/* Buffer size for validation error messages */
#define ERR_BUF_SIZE 64

Character* character_new(void) {
    Character* c = wst_calloc(1, sizeof(Character));
    if (!c) return NULL;

    /* Initialize string fields to empty strings */
    c->realm = wst_strdup("");
    c->name = wst_strdup("");
    c->guild = wst_strdup("");
    c->notes = wst_strdup("");
    c->week_id = NULL;  /* Only set when imported from addon */

    /* Per-slot JSON strings - NULL until imported from addon */
    c->slot_upgrades_json = NULL;
    c->missing_sockets_json = NULL;
    c->empty_sockets_json = NULL;
    c->missing_enchants_json = NULL;

    if (!c->realm || !c->name || !c->guild || !c->notes) {
        character_free(c);
        return NULL;
    }

    return c;
}

Character* character_create(const char* realm, const char* name) {
    Character* c = character_new();
    if (!c) return NULL;

    if (character_set_realm(c, realm) != WST_OK ||
        character_set_name(c, name) != WST_OK) {
        character_free(c);
        return NULL;
    }

    return c;
}

void character_free(Character* c) {
    if (!c) return;

    free(c->realm);
    free(c->name);
    free(c->guild);
    free(c->notes);
    free(c->week_id);
    free(c->slot_upgrades_json);
    free(c->missing_sockets_json);
    free(c->empty_sockets_json);
    free(c->missing_enchants_json);
    free(c);
}

Character* character_copy(const Character* src) {
    if (!src) return NULL;

    Character* c = wst_calloc(1, sizeof(Character));
    if (!c) return NULL;

    c->realm = wst_strdup(src->realm ? src->realm : "");
    c->name = wst_strdup(src->name ? src->name : "");
    c->guild = wst_strdup(src->guild ? src->guild : "");
    c->notes = wst_strdup(src->notes ? src->notes : "");

    if (!c->realm || !c->name || !c->guild || !c->notes) {
        character_free(c);
        return NULL;
    }

    c->item_level = src->item_level;
    c->heroic_items = src->heroic_items;
    c->champion_items = src->champion_items;
    c->veteran_items = src->veteran_items;
    c->adventure_items = src->adventure_items;
    c->old_items = src->old_items;
    c->vault_visited = src->vault_visited;
    c->delves = src->delves;
    c->gilded_stash = src->gilded_stash;
    c->gearing_up = src->gearing_up;
    c->quests = src->quests;
    c->timewalk = src->timewalk;

    /* Copy new aggregate fields */
    c->upgrade_current = src->upgrade_current;
    c->upgrade_max = src->upgrade_max;
    c->socket_missing_count = src->socket_missing_count;
    c->socket_empty_count = src->socket_empty_count;
    c->enchant_missing_count = src->enchant_missing_count;

    if (src->week_id) {
        c->week_id = wst_strdup(src->week_id);
        if (!c->week_id) {
            character_free(c);
            return NULL;
        }
    }

    /* Copy per-slot JSON strings */
    if (src->slot_upgrades_json) {
        c->slot_upgrades_json = wst_strdup(src->slot_upgrades_json);
    }
    if (src->missing_sockets_json) {
        c->missing_sockets_json = wst_strdup(src->missing_sockets_json);
    }
    if (src->empty_sockets_json) {
        c->empty_sockets_json = wst_strdup(src->empty_sockets_json);
    }
    if (src->missing_enchants_json) {
        c->missing_enchants_json = wst_strdup(src->missing_enchants_json);
    }

    return c;
}

static void add_error(char*** errors, size_t* count, const char* msg) {
    if (!errors || !count) return;

    size_t new_count = *count + 1;
    char** new_errors = wst_realloc(*errors, new_count * sizeof(char*));
    if (!new_errors) return;

    new_errors[*count] = wst_strdup(msg);
    *errors = new_errors;
    *count = new_count;
}

WstResult character_validate(const Character* c, char*** errors, size_t* error_count) {
    if (!c) return WST_ERR_NULL_ARG;

    WstResult result = WST_OK;

    if (wst_str_empty(c->name)) {
        add_error(errors, error_count, "Character name is required");
        result = WST_ERR_VALIDATION;
    }

    if (wst_str_empty(c->realm)) {
        add_error(errors, error_count, "Realm is required");
        result = WST_ERR_VALIDATION;
    }

    if (c->item_level < 0.0 || c->item_level > WST_MAX_ITEM_LEVEL) {
        char buf[ERR_BUF_SIZE];
        snprintf(buf, sizeof(buf), "Item level must be between 0 and %.0f",
                 WST_MAX_ITEM_LEVEL);
        add_error(errors, error_count, buf);
        result = WST_ERR_VALIDATION;
    }

    /* Check item counts */
    const struct { const char* name; int value; } items[] = {
        {"heroic_items", c->heroic_items},
        {"champion_items", c->champion_items},
        {"veteran_items", c->veteran_items},
        {"adventure_items", c->adventure_items},
        {"old_items", c->old_items},
    };

    for (size_t i = 0; i < sizeof(items) / sizeof(items[0]); i++) {
        if (items[i].value < 0 || items[i].value > WST_MAX_ITEMS_PER_CAT) {
            char buf[ERR_BUF_SIZE];
            snprintf(buf, sizeof(buf), "%s must be between 0 and %d",
                     items[i].name, WST_MAX_ITEMS_PER_CAT);
            add_error(errors, error_count, buf);
            result = WST_ERR_VALIDATION;
        }
    }

    if (c->delves < 0 || c->delves > WST_MAX_DELVES) {
        char buf[ERR_BUF_SIZE];
        snprintf(buf, sizeof(buf), "Delves must be between 0 and %d", WST_MAX_DELVES);
        add_error(errors, error_count, buf);
        result = WST_ERR_VALIDATION;
    }

    if (c->gilded_stash < 0 || c->gilded_stash > WST_MAX_GILDED_STASH) {
        char buf[ERR_BUF_SIZE];
        snprintf(buf, sizeof(buf), "Gilded stash must be between 0 and %d",
                 WST_MAX_GILDED_STASH);
        add_error(errors, error_count, buf);
        result = WST_ERR_VALIDATION;
    }

    if (c->timewalk < 0 || c->timewalk > WST_MAX_TIMEWALK) {
        char buf[ERR_BUF_SIZE];
        snprintf(buf, sizeof(buf), "Timewalk must be between 0 and %d", WST_MAX_TIMEWALK);
        add_error(errors, error_count, buf);
        result = WST_ERR_VALIDATION;
    }

    return result;
}

void character_free_errors(char** errors, size_t count) {
    if (!errors) return;
    for (size_t i = 0; i < count; i++) {
        free(errors[i]);
    }
    free(errors);
}

void character_reset_weekly(Character* c) {
    if (!c) return;

    c->vault_visited = false;
    c->delves = 0;
    c->gilded_stash = 0;
    c->gearing_up = false;
    c->quests = false;
    c->timewalk = 0;
}

cJSON* character_to_json(const Character* c) {
    if (!c) return NULL;

    cJSON* json = cJSON_CreateObject();
    if (!json) return NULL;

    cJSON_AddStringToObject(json, "realm", c->realm ? c->realm : "");
    cJSON_AddStringToObject(json, "name", c->name ? c->name : "");
    cJSON_AddStringToObject(json, "guild", c->guild ? c->guild : "");
    cJSON_AddNumberToObject(json, "item_level", c->item_level);
    cJSON_AddNumberToObject(json, "heroic_items", c->heroic_items);
    cJSON_AddNumberToObject(json, "champion_items", c->champion_items);
    cJSON_AddNumberToObject(json, "veteran_items", c->veteran_items);
    cJSON_AddNumberToObject(json, "adventure_items", c->adventure_items);
    cJSON_AddNumberToObject(json, "old_items", c->old_items);
    cJSON_AddBoolToObject(json, "vault_visited", c->vault_visited);
    cJSON_AddNumberToObject(json, "delves", c->delves);
    cJSON_AddNumberToObject(json, "gilded_stash", c->gilded_stash);
    cJSON_AddBoolToObject(json, "gearing_up", c->gearing_up);
    cJSON_AddBoolToObject(json, "quests", c->quests);
    cJSON_AddNumberToObject(json, "timewalk", c->timewalk);
    cJSON_AddStringToObject(json, "notes", c->notes ? c->notes : "");

    /* New aggregate fields */
    cJSON_AddNumberToObject(json, "upgrade_current", c->upgrade_current);
    cJSON_AddNumberToObject(json, "upgrade_max", c->upgrade_max);
    cJSON_AddNumberToObject(json, "socket_missing_count", c->socket_missing_count);
    cJSON_AddNumberToObject(json, "socket_empty_count", c->socket_empty_count);
    cJSON_AddNumberToObject(json, "enchant_missing_count", c->enchant_missing_count);

    /* Per-slot JSON strings (stored as-is) */
    if (c->slot_upgrades_json) {
        cJSON_AddStringToObject(json, "slot_upgrades_json", c->slot_upgrades_json);
    }
    if (c->missing_sockets_json) {
        cJSON_AddStringToObject(json, "missing_sockets_json", c->missing_sockets_json);
    }
    if (c->empty_sockets_json) {
        cJSON_AddStringToObject(json, "empty_sockets_json", c->empty_sockets_json);
    }
    if (c->missing_enchants_json) {
        cJSON_AddStringToObject(json, "missing_enchants_json", c->missing_enchants_json);
    }

    return json;
}

static const char* get_json_string(const cJSON* json, const char* key,
                                    const char* default_val) {
    const cJSON* item = cJSON_GetObjectItemCaseSensitive(json, key);
    if (cJSON_IsString(item) && item->valuestring) {
        return item->valuestring;
    }
    return default_val;
}

static double get_json_number(const cJSON* json, const char* key,
                               double default_val) {
    const cJSON* item = cJSON_GetObjectItemCaseSensitive(json, key);
    if (cJSON_IsNumber(item)) {
        return item->valuedouble;
    }
    return default_val;
}

static bool get_json_bool(const cJSON* json, const char* key, bool default_val) {
    const cJSON* item = cJSON_GetObjectItemCaseSensitive(json, key);
    if (cJSON_IsBool(item)) {
        return cJSON_IsTrue(item);
    }
    return default_val;
}

Character* character_from_json(const cJSON* json) {
    if (!json || !cJSON_IsObject(json)) return NULL;

    Character* c = character_new();
    if (!c) return NULL;

    if (character_set_realm(c, get_json_string(json, "realm", "")) != WST_OK ||
        character_set_name(c, get_json_string(json, "name", "")) != WST_OK ||
        character_set_guild(c, get_json_string(json, "guild", "")) != WST_OK ||
        character_set_notes(c, get_json_string(json, "notes", "")) != WST_OK) {
        character_free(c);
        return NULL;
    }

    c->item_level = get_json_number(json, "item_level", 0.0);
    c->heroic_items = (int)get_json_number(json, "heroic_items", 0);
    c->champion_items = (int)get_json_number(json, "champion_items", 0);
    c->veteran_items = (int)get_json_number(json, "veteran_items", 0);
    c->adventure_items = (int)get_json_number(json, "adventure_items", 0);
    c->old_items = (int)get_json_number(json, "old_items", 0);
    c->vault_visited = get_json_bool(json, "vault_visited", false);
    c->delves = (int)get_json_number(json, "delves", 0);
    c->gilded_stash = (int)get_json_number(json, "gilded_stash", 0);
    c->gearing_up = get_json_bool(json, "gearing_up", false);
    c->quests = get_json_bool(json, "quests", false);
    c->timewalk = (int)get_json_number(json, "timewalk", 0);

    /* New aggregate fields */
    c->upgrade_current = (int)get_json_number(json, "upgrade_current", 0);
    c->upgrade_max = (int)get_json_number(json, "upgrade_max", 0);
    c->socket_missing_count = (int)get_json_number(json, "socket_missing_count", 0);
    c->socket_empty_count = (int)get_json_number(json, "socket_empty_count", 0);
    c->enchant_missing_count = (int)get_json_number(json, "enchant_missing_count", 0);

    /* Per-slot JSON strings */
    const char* slot_upgrades = get_json_string(json, "slot_upgrades_json", NULL);
    if (slot_upgrades) {
        c->slot_upgrades_json = wst_strdup(slot_upgrades);
    }
    const char* missing_sockets = get_json_string(json, "missing_sockets_json", NULL);
    if (missing_sockets) {
        c->missing_sockets_json = wst_strdup(missing_sockets);
    }
    const char* empty_sockets = get_json_string(json, "empty_sockets_json", NULL);
    if (empty_sockets) {
        c->empty_sockets_json = wst_strdup(empty_sockets);
    }
    const char* missing_enchants = get_json_string(json, "missing_enchants_json", NULL);
    if (missing_enchants) {
        c->missing_enchants_json = wst_strdup(missing_enchants);
    }

    return c;
}

static WstResult set_string_field(char** field, const char* value) {
    char* new_val = wst_strdup(value ? value : "");
    if (!new_val) return WST_ERR_ALLOC;

    free(*field);
    *field = new_val;
    return WST_OK;
}

WstResult character_set_realm(Character* c, const char* value) {
    if (!c) return WST_ERR_NULL_ARG;
    return set_string_field(&c->realm, value);
}

WstResult character_set_name(Character* c, const char* value) {
    if (!c) return WST_ERR_NULL_ARG;
    return set_string_field(&c->name, value);
}

WstResult character_set_guild(Character* c, const char* value) {
    if (!c) return WST_ERR_NULL_ARG;
    return set_string_field(&c->guild, value);
}

WstResult character_set_notes(Character* c, const char* value) {
    if (!c) return WST_ERR_NULL_ARG;
    return set_string_field(&c->notes, value);
}

WstResult character_set_week_id(Character* c, const char* value) {
    if (!c) return WST_ERR_NULL_ARG;
    free(c->week_id);
    if (value) {
        c->week_id = wst_strdup(value);
        return c->week_id ? WST_OK : WST_ERR_ALLOC;
    }
    c->week_id = NULL;
    return WST_OK;
}
