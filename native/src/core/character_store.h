/*
 * WoW Stat Tracker - Character Store
 * BSD 3-Clause License
 */

#ifndef WST_CHARACTER_STORE_H
#define WST_CHARACTER_STORE_H

#include "types.h"
#include "character.h"

/*
 * Character store - manages a collection of characters with JSON persistence.
 */
struct CharacterStore {
    Character** characters;
    size_t count;
    size_t capacity;
    char* file_path;
};

/*
 * Create a new character store.
 * Returns NULL on allocation failure.
 */
CharacterStore* character_store_new(const char* file_path);

/*
 * Free the character store and all characters.
 */
void character_store_free(CharacterStore* store);

/*
 * Load characters from JSON file.
 * Returns WST_OK on success, WST_ERR_IO on file error, WST_ERR_PARSE on parse error.
 */
WstResult character_store_load(CharacterStore* store);

/*
 * Save characters to JSON file atomically.
 * Returns WST_OK on success, WST_ERR_IO on error.
 */
WstResult character_store_save(const CharacterStore* store);

/*
 * Add a character to the store (takes ownership).
 * Returns WST_OK on success, WST_ERR_ALLOC on memory error.
 */
WstResult character_store_add(CharacterStore* store, Character* c);

/*
 * Update a character at index.
 * Returns WST_OK on success, WST_ERR_OUT_OF_RANGE if index is invalid.
 */
WstResult character_store_update(CharacterStore* store, size_t index, Character* c);

/*
 * Delete a character at index.
 * Returns WST_OK on success, WST_ERR_OUT_OF_RANGE if index is invalid.
 */
WstResult character_store_delete(CharacterStore* store, size_t index);

/*
 * Get a character at index (does not transfer ownership).
 * Returns NULL if index is out of range.
 */
Character* character_store_get(const CharacterStore* store, size_t index);

/*
 * Get the number of characters.
 */
size_t character_store_count(const CharacterStore* store);

/*
 * Reset weekly data for all characters.
 */
void character_store_reset_weekly_all(CharacterStore* store);

/*
 * Find a character by realm and name.
 * Returns index or -1 if not found.
 */
int character_store_find(const CharacterStore* store,
                          const char* realm, const char* name);

#endif /* WST_CHARACTER_STORE_H */
