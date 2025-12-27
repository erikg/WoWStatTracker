/*
 * WoW Stat Tracker - Utility Functions
 * BSD 3-Clause License
 */

#ifndef WST_UTIL_H
#define WST_UTIL_H

#include "types.h"
#include <stddef.h>

/*
 * Duplicate a string. Returns NULL on allocation failure.
 * If src is NULL, returns NULL.
 */
char* wst_strdup(const char* src);

/*
 * Duplicate a string with maximum length.
 * Returns NULL on allocation failure or if src is NULL.
 */
char* wst_strndup(const char* src, size_t max_len);

/*
 * Safe string copy. Always null-terminates.
 * Returns number of characters copied (excluding null).
 */
size_t wst_strlcpy(char* dst, const char* src, size_t dst_size);

/*
 * Safe string concatenation. Always null-terminates.
 * Returns total length that would have been copied.
 */
size_t wst_strlcat(char* dst, const char* src, size_t dst_size);

/*
 * Allocate and zero memory.
 * Returns NULL on failure.
 */
void* wst_calloc(size_t nmemb, size_t size);

/*
 * Reallocate memory. On failure, original pointer is unchanged.
 * Returns NULL on failure.
 */
void* wst_realloc(void* ptr, size_t size);

/*
 * Free memory and set pointer to NULL.
 */
void wst_free(void** ptr);

/*
 * Check if string is empty or NULL.
 */
bool wst_str_empty(const char* s);

/*
 * Compare strings, NULL-safe (NULL < any string).
 */
int wst_strcmp(const char* a, const char* b);

/*
 * Case-insensitive string compare.
 */
int wst_strcasecmp(const char* a, const char* b);

/*
 * Trim whitespace from both ends of string in-place.
 * Returns pointer to start of trimmed content within original buffer.
 */
char* wst_strtrim(char* s);

/*
 * Join path components. Caller must free result.
 * Returns NULL on allocation failure.
 */
char* wst_path_join(const char* a, const char* b);

#endif /* WST_UTIL_H */
