/*
 * WoW Stat Tracker - Configuration Storage
 * BSD 3-Clause License
 */

#ifndef WST_CONFIG_H
#define WST_CONFIG_H

#include "types.h"
#include "cJSON.h"

/*
 * Configuration store - key-value settings backed by JSON.
 */
struct Config {
    cJSON* data;
    char* file_path;
};

/*
 * Create a new config store.
 * Returns NULL on allocation failure.
 */
Config* config_new(const char* file_path);

/*
 * Free the config store.
 */
void config_free(Config* cfg);

/*
 * Load configuration from JSON file.
 * Returns WST_OK on success (including if file doesn't exist).
 */
WstResult config_load(Config* cfg);

/*
 * Save configuration to JSON file atomically.
 * Returns WST_OK on success, WST_ERR_IO on error.
 */
WstResult config_save(const Config* cfg);

/*
 * Get a string value. Returns default_val if key doesn't exist.
 * The returned string is owned by config and should not be freed.
 */
const char* config_get_string(const Config* cfg, const char* key,
                               const char* default_val);

/*
 * Get an integer value. Returns default_val if key doesn't exist.
 */
int config_get_int(const Config* cfg, const char* key, int default_val);

/*
 * Get a double value. Returns default_val if key doesn't exist.
 */
double config_get_double(const Config* cfg, const char* key, double default_val);

/*
 * Get a boolean value. Returns default_val if key doesn't exist.
 */
bool config_get_bool(const Config* cfg, const char* key, bool default_val);

/*
 * Set a string value.
 * Returns WST_OK on success, WST_ERR_ALLOC on memory error.
 */
WstResult config_set_string(Config* cfg, const char* key, const char* value);

/*
 * Set an integer value.
 * Returns WST_OK on success.
 */
WstResult config_set_int(Config* cfg, const char* key, int value);

/*
 * Set a double value.
 * Returns WST_OK on success.
 */
WstResult config_set_double(Config* cfg, const char* key, double value);

/*
 * Set a boolean value.
 * Returns WST_OK on success.
 */
WstResult config_set_bool(Config* cfg, const char* key, bool value);

/*
 * Get a nested object. Returns NULL if not found.
 * The returned object is owned by config.
 */
cJSON* config_get_object(Config* cfg, const char* key);

/*
 * Set a nested object (takes ownership of obj).
 * Returns WST_OK on success.
 */
WstResult config_set_object(Config* cfg, const char* key, cJSON* obj);

/*
 * Check if a key exists.
 */
bool config_has_key(const Config* cfg, const char* key);

/*
 * Delete a key.
 */
void config_delete_key(Config* cfg, const char* key);

#endif /* WST_CONFIG_H */
