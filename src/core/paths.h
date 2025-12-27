/*
 * WoW Stat Tracker - Path Utilities
 * BSD 3-Clause License
 */

#ifndef WST_PATHS_H
#define WST_PATHS_H

#include "types.h"

/*
 * Get the platform-specific config directory for the application.
 * Creates the directory if it doesn't exist.
 *
 * Returns:
 *   macOS:   ~/Library/Application Support/wowstat
 *   Windows: %APPDATA%/wowstat
 *   Linux:   ~/.config/wowstat (or $XDG_CONFIG_HOME/wowstat)
 *
 * Caller must free the returned string.
 */
char* paths_get_config_dir(void);

/*
 * Get the path to the character data file.
 * Caller must free the returned string.
 */
char* paths_get_data_file(void);

/*
 * Get the path to the config file.
 * Caller must free the returned string.
 */
char* paths_get_config_file(void);

/*
 * Get the path to the notifications file.
 * Caller must free the returned string.
 */
char* paths_get_notifications_file(void);

/*
 * Get the path to the lock file.
 * Caller must free the returned string.
 */
char* paths_get_lock_file(void);

/*
 * Ensure a directory exists, creating it if necessary.
 * Returns WST_OK on success, WST_ERR_IO on failure.
 */
WstResult paths_ensure_dir(const char* path);

/*
 * Get the user's home directory.
 * Caller must free the returned string.
 */
char* paths_get_home(void);

/*
 * Check if a path is a directory.
 */
bool paths_is_dir(const char* path);

/*
 * Check if a file exists.
 */
bool paths_file_exists(const char* path);

#endif /* WST_PATHS_H */
