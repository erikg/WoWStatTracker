/*
 * WoW Stat Tracker - Platform Abstraction Layer
 * BSD 3-Clause License
 */

#ifndef WST_PLATFORM_H
#define WST_PLATFORM_H

#include "../core/types.h"

/*
 * Check if the system is using dark theme.
 * Returns true if dark mode is enabled.
 */
bool platform_is_dark_theme(void);

/*
 * Perform an HTTP GET request.
 * Returns the response body (caller must free) or NULL on error.
 */
char* platform_http_get(const char* url);

/*
 * Write data to a file atomically (write to temp, then rename).
 * Returns WST_OK on success, WST_ERR_IO on failure.
 */
WstResult platform_write_atomic(const char* path, const char* data, size_t len);

/*
 * Acquire an exclusive file lock.
 * Returns WST_OK on success, WST_ERR_LOCK_FAILED if already locked.
 */
WstResult platform_lock_acquire(const char* lock_file);

/*
 * Release a file lock.
 */
void platform_lock_release(const char* lock_file);

/*
 * Open a URL in the default browser.
 */
void platform_open_url(const char* url);

#endif /* WST_PLATFORM_H */
