/*
 * WoW Stat Tracker - Lua SavedVariables Parser Implementation
 * BSD 3-Clause License
 */

#include "lua_parser.h"
#include "util.h"
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#include "lua.h"
#include "lauxlib.h"
#include "lualib.h"

#define INITIAL_CAPACITY 32

/* Forward declarations */
static bool get_lua_string(lua_State* L, const char* key, char** out);
static bool get_lua_number(lua_State* L, const char* key, double* out);
static bool get_lua_bool(lua_State* L, const char* key, bool* out);
static Character* parse_character(lua_State* L, const char* char_key);

/*
 * Read entire file into a string.
 */
static char* read_file(const char* path) {
    FILE* f = fopen(path, "r");
    if (!f) return NULL;

    fseek(f, 0, SEEK_END);
    long size = ftell(f);
    fseek(f, 0, SEEK_SET);

    if (size <= 0) {
        fclose(f);
        return wst_strdup("");
    }

    char* content = malloc((size_t)size + 1);
    if (!content) {
        fclose(f);
        return NULL;
    }

    size_t read = fread(content, 1, (size_t)size, f);
    fclose(f);
    content[read] = '\0';

    return content;
}

/*
 * Strip leading whitespace and the "WoWStatTrackerDB = " prefix if present.
 */
static const char* strip_prefix(const char* content) {
    /* Skip leading whitespace (including BOM, \r\n, etc.) */
    while (*content && (*content == ' ' || *content == '\t' ||
                        *content == '\r' || *content == '\n' ||
                        (unsigned char)*content == 0xEF ||  /* UTF-8 BOM */
                        (unsigned char)*content == 0xBB ||
                        (unsigned char)*content == 0xBF)) {
        content++;
    }

    const char* prefix = "WoWStatTrackerDB = ";
    size_t prefix_len = strlen(prefix);

    if (strncmp(content, prefix, prefix_len) == 0) {
        return content + prefix_len;
    }
    return content;
}

LuaParseResult lua_parser_parse_addon_file(const char* file_path) {
    LuaParseResult result = {0};

    char* content = read_file(file_path);
    if (!content) {
        return result;
    }

    result = lua_parser_parse_content(content);
    free(content);
    return result;
}

LuaParseResult lua_parser_parse_content(const char* content) {
    LuaParseResult result = {0};

    if (!content) return result;

    /* Create Lua state */
    lua_State* L = luaL_newstate();
    if (!L) return result;

    luaL_openlibs(L);

    /* Build a Lua script that evaluates the table */
    const char* table_content = strip_prefix(content);

    /* Create script: "return <table_content>" */
    size_t script_len = strlen("return ") + strlen(table_content) + 1;
    char* script = malloc(script_len);
    if (!script) {
        lua_close(L);
        return result;
    }
    snprintf(script, script_len, "return %s", table_content);

    /* Execute the script */
    if (luaL_dostring(L, script) != 0) {
        /* Parse error */
        free(script);
        lua_close(L);
        return result;
    }
    free(script);

    /* The result should be a table on the stack */
    if (!lua_istable(L, -1)) {
        lua_close(L);
        return result;
    }

    /* Extract addon version from metadata */
    lua_getfield(L, -1, "metadata");
    if (lua_istable(L, -1)) {
        get_lua_string(L, "version", &result.addon_version);
    }
    lua_pop(L, 1);  /* pop metadata */

    /* Get characters table */
    lua_getfield(L, -1, "characters");
    if (!lua_istable(L, -1)) {
        lua_close(L);
        return result;
    }

    /* Allocate character array */
    result.characters = wst_calloc(INITIAL_CAPACITY, sizeof(Character*));
    size_t capacity = INITIAL_CAPACITY;

    /* Iterate over characters table */
    lua_pushnil(L);  /* first key */
    while (lua_next(L, -2) != 0) {
        /* key is at -2, value is at -1 */
        if (lua_isstring(L, -2) && lua_istable(L, -1)) {
            const char* char_key = lua_tostring(L, -2);

            /* Parse this character */
            Character* c = parse_character(L, char_key);
            if (c) {
                /* Add to result */
                if (result.count >= capacity) {
                    capacity *= 2;
                    Character** new_arr = wst_realloc(result.characters,
                                                       capacity * sizeof(Character*));
                    if (!new_arr) {
                        character_free(c);
                    } else {
                        result.characters = new_arr;
                        result.characters[result.count++] = c;
                    }
                } else {
                    result.characters[result.count++] = c;
                }
            }
        }
        lua_pop(L, 1);  /* pop value, keep key for next iteration */
    }

    lua_close(L);
    return result;
}

void lua_parser_free_result(LuaParseResult* result) {
    if (!result) return;

    if (result->characters) {
        for (size_t i = 0; i < result->count; i++) {
            character_free(result->characters[i]);
        }
        free(result->characters);
        result->characters = NULL;
    }

    free(result->addon_version);
    result->addon_version = NULL;
    result->count = 0;
}

/*
 * Get a string field from the table at the top of the stack.
 * Returns true if field exists and is a string.
 */
static bool get_lua_string(lua_State* L, const char* key, char** out) {
    lua_getfield(L, -1, key);
    bool success = false;
    if (lua_isstring(L, -1)) {
        const char* str = lua_tostring(L, -1);
        *out = wst_strdup(str ? str : "");
        success = (*out != NULL);
    }
    lua_pop(L, 1);
    return success;
}

/*
 * Get a number field from the table at the top of the stack.
 */
static bool get_lua_number(lua_State* L, const char* key, double* out) {
    lua_getfield(L, -1, key);
    bool success = false;
    if (lua_isnumber(L, -1)) {
        *out = lua_tonumber(L, -1);
        success = true;
    }
    lua_pop(L, 1);
    return success;
}

/*
 * Get a boolean field from the table at the top of the stack.
 */
static bool get_lua_bool(lua_State* L, const char* key, bool* out) {
    lua_getfield(L, -1, key);
    bool success = false;
    if (lua_isboolean(L, -1)) {
        *out = lua_toboolean(L, -1);
        success = true;
    }
    lua_pop(L, 1);
    return success;
}

/*
 * Get a nested table's number field.
 */
static bool get_nested_number(lua_State* L, const char* table_key,
                               const char* field_key, double* out) {
    lua_getfield(L, -1, table_key);
    if (!lua_istable(L, -1)) {
        lua_pop(L, 1);
        return false;
    }
    bool success = get_lua_number(L, field_key, out);
    lua_pop(L, 1);
    return success;
}

/*
 * Get a nested table's boolean field.
 */
static bool get_nested_bool(lua_State* L, const char* table_key,
                             const char* field_key, bool* out) {
    lua_getfield(L, -1, table_key);
    if (!lua_istable(L, -1)) {
        lua_pop(L, 1);
        return false;
    }
    bool success = get_lua_bool(L, field_key, out);
    lua_pop(L, 1);
    return success;
}

/*
 * Parse a character from the Lua table at the top of the stack.
 * char_key is the "Name-Realm" key.
 */
static Character* parse_character(lua_State* L, const char* char_key) {
    /* Split "Name-Realm" */
    const char* dash = strrchr(char_key, '-');
    if (!dash) return NULL;

    size_t name_len = (size_t)(dash - char_key);
    char* name = wst_strndup(char_key, name_len);
    char* realm = wst_strdup(dash + 1);

    if (!name || !realm) {
        free(name);
        free(realm);
        return NULL;
    }

    Character* c = character_create(realm, name);
    free(name);
    free(realm);

    if (!c) return NULL;

    /* Extract fields from the table at top of stack */
    char* guild = NULL;
    if (get_lua_string(L, "guild", &guild)) {
        character_set_guild(c, guild);
        free(guild);
    }

    double item_level = 0;
    if (get_lua_number(L, "item_level", &item_level)) {
        c->item_level = item_level;
    }

    double d;
    if (get_lua_number(L, "heroic_items", &d)) c->heroic_items = (int)d;
    if (get_lua_number(L, "champion_items", &d)) c->champion_items = (int)d;
    if (get_lua_number(L, "veteran_items", &d)) c->veteran_items = (int)d;
    if (get_lua_number(L, "adventure_items", &d)) c->adventure_items = (int)d;
    if (get_lua_number(L, "old_items", &d)) c->old_items = (int)d;

    bool b;
    if (get_lua_bool(L, "vault_visited", &b)) c->vault_visited = b;
    if (get_lua_bool(L, "gearing_up", &b)) c->gearing_up = b;
    if (get_lua_bool(L, "quests", &b)) c->quests = b;

    /* Delves: from vault_delves.count */
    if (get_nested_number(L, "vault_delves", "count", &d)) {
        c->delves = (int)d;
        /* Subtract 1 if gearing_up was completed (it counts as a delve) */
        if (c->gearing_up && c->delves > 0) {
            c->delves--;
        }
    }

    /* Gilded stash: from gilded_stash.claimed */
    if (get_nested_number(L, "gilded_stash", "claimed", &d)) {
        c->gilded_stash = (int)d;
    }

    /* Timewalk: check timewalking_quest completion status */
    bool tw_complete = false;
    if (get_nested_bool(L, "timewalking_quest", "completed", &tw_complete)) {
        if (tw_complete) {
            c->timewalk = WST_MAX_TIMEWALK;
        } else {
            double progress = 0;
            if (get_nested_number(L, "timewalking_quest", "progress", &progress)) {
                c->timewalk = (int)progress;
            }
        }
    }

    return c;
}
