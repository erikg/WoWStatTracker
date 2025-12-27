/*
 * WoW Stat Tracker - Lua SavedVariables Parser
 * BSD 3-Clause License
 */

#ifndef WST_LUA_PARSER_H
#define WST_LUA_PARSER_H

#include "types.h"
#include "character.h"

/*
 * Parsed addon data result.
 */
typedef struct {
    Character** characters;     /* Array of character pointers */
    size_t count;               /* Number of characters */
    char* addon_version;        /* Addon version from metadata (may be NULL) */
} LuaParseResult;

/*
 * Parse WoW Stat Tracker addon SavedVariables file.
 *
 * The file is expected to contain:
 *   WoWStatTrackerDB = { characters = {...}, metadata = {...} }
 *
 * Returns a LuaParseResult struct. On failure, result.characters is NULL.
 */
LuaParseResult lua_parser_parse_addon_file(const char* file_path);

/*
 * Free a LuaParseResult and all its contents.
 */
void lua_parser_free_result(LuaParseResult* result);

/*
 * Parse a Lua table string directly.
 * The content should be the value part (without "WoWStatTrackerDB = ").
 */
LuaParseResult lua_parser_parse_content(const char* content);

#endif /* WST_LUA_PARSER_H */
