/*
 * WoW Stat Tracker - Character Data Structure
 * BSD 3-Clause License
 */

#ifndef WST_CHARACTER_H
#define WST_CHARACTER_H

#include "types.h"
#include "cJSON.h"

/*
 * Character data structure.
 * All string fields are heap-allocated and owned by the struct.
 */
struct Character {
    char* realm;            /* Required */
    char* name;             /* Required */
    char* guild;
    double item_level;      /* 0-1000 */
    int heroic_items;       /* 0-50 */
    int champion_items;     /* 0-50 */
    int veteran_items;      /* 0-50 */
    int adventure_items;    /* 0-50 */
    int old_items;          /* 0-50 */
    bool vault_visited;
    int delves;             /* 0-8 */
    int gilded_stash;       /* 0-3 */
    bool gearing_up;
    bool quests;
    int timewalk;           /* 0-5 */
    char* notes;
};

/*
 * Create a new character with default values.
 * Returns NULL on allocation failure.
 */
Character* character_new(void);

/*
 * Create a character with specified realm and name.
 * Returns NULL on allocation failure.
 */
Character* character_create(const char* realm, const char* name);

/*
 * Free a character and all its strings.
 */
void character_free(Character* c);

/*
 * Deep copy a character.
 * Returns NULL on allocation failure.
 */
Character* character_copy(const Character* src);

/*
 * Validate character data.
 * Returns WST_OK if valid, WST_ERR_VALIDATION if not.
 * If errors is not NULL, appends error messages (caller must free each string).
 */
WstResult character_validate(const Character* c, char*** errors, size_t* error_count);

/*
 * Free an array of error messages.
 */
void character_free_errors(char** errors, size_t count);

/*
 * Reset weekly tracking fields to defaults.
 */
void character_reset_weekly(Character* c);

/*
 * Convert character to cJSON object.
 * Returns NULL on allocation failure.
 */
cJSON* character_to_json(const Character* c);

/*
 * Create character from cJSON object.
 * Returns NULL on allocation failure or invalid data.
 */
Character* character_from_json(const cJSON* json);

/*
 * Set string field on character (handles freeing old value and duplication).
 * Returns WST_OK or WST_ERR_ALLOC.
 */
WstResult character_set_realm(Character* c, const char* value);
WstResult character_set_name(Character* c, const char* value);
WstResult character_set_guild(Character* c, const char* value);
WstResult character_set_notes(Character* c, const char* value);

#endif /* WST_CHARACTER_H */
