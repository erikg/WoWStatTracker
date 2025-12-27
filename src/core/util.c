/*
 * WoW Stat Tracker - Utility Functions Implementation
 * BSD 3-Clause License
 */

#include "util.h"
#include <ctype.h>
#include <stdlib.h>
#include <string.h>

char* wst_strdup(const char* src) {
    if (!src) return NULL;

    size_t len = strlen(src) + 1;
    char* dup = malloc(len);
    if (dup) {
        memcpy(dup, src, len);
    }
    return dup;
}

char* wst_strndup(const char* src, size_t max_len) {
    if (!src) return NULL;

    size_t len = 0;
    while (len < max_len && src[len] != '\0') {
        len++;
    }

    char* dup = malloc(len + 1);
    if (dup) {
        memcpy(dup, src, len);
        dup[len] = '\0';
    }
    return dup;
}

size_t wst_strlcpy(char* dst, const char* src, size_t dst_size) {
    if (!dst || dst_size == 0) return 0;
    if (!src) {
        dst[0] = '\0';
        return 0;
    }

    size_t src_len = strlen(src);
    size_t copy_len = (src_len < dst_size - 1) ? src_len : dst_size - 1;

    memcpy(dst, src, copy_len);
    dst[copy_len] = '\0';

    return src_len;
}

size_t wst_strlcat(char* dst, const char* src, size_t dst_size) {
    if (!dst || !src) return 0;

    size_t dst_len = strlen(dst);
    if (dst_len >= dst_size) return dst_size + strlen(src);

    size_t src_len = strlen(src);
    size_t space_left = dst_size - dst_len - 1;
    size_t copy_len = (src_len < space_left) ? src_len : space_left;

    memcpy(dst + dst_len, src, copy_len);
    dst[dst_len + copy_len] = '\0';

    return dst_len + src_len;
}

void* wst_calloc(size_t nmemb, size_t size) {
    return calloc(nmemb, size);
}

void* wst_realloc(void* ptr, size_t size) {
    return realloc(ptr, size);
}

void wst_free(void** ptr) {
    if (ptr && *ptr) {
        free(*ptr);
        *ptr = NULL;
    }
}

bool wst_str_empty(const char* s) {
    return s == NULL || s[0] == '\0';
}

int wst_strcmp(const char* a, const char* b) {
    if (a == b) return 0;
    if (!a) return -1;
    if (!b) return 1;
    return strcmp(a, b);
}

int wst_strcasecmp(const char* a, const char* b) {
    if (a == b) return 0;
    if (!a) return -1;
    if (!b) return 1;

    while (*a && *b) {
        int diff = tolower((unsigned char)*a) - tolower((unsigned char)*b);
        if (diff != 0) return diff;
        a++;
        b++;
    }
    return tolower((unsigned char)*a) - tolower((unsigned char)*b);
}

char* wst_strtrim(char* s) {
    if (!s) return NULL;

    /* Trim leading whitespace */
    while (*s && isspace((unsigned char)*s)) {
        s++;
    }

    if (*s == '\0') return s;

    /* Trim trailing whitespace */
    char* end = s + strlen(s) - 1;
    while (end > s && isspace((unsigned char)*end)) {
        *end-- = '\0';
    }

    return s;
}

char* wst_path_join(const char* a, const char* b) {
    if (!a || !b) return NULL;

    size_t a_len = strlen(a);
    size_t b_len = strlen(b);

    /* Check if we need a separator */
    bool need_sep = (a_len > 0 && a[a_len - 1] != '/' && a[a_len - 1] != '\\');

    size_t total = a_len + (need_sep ? 1 : 0) + b_len + 1;
    char* result = malloc(total);
    if (!result) return NULL;

    memcpy(result, a, a_len);
    if (need_sep) {
#ifdef _WIN32
        result[a_len] = '\\';
#else
        result[a_len] = '/';
#endif
        memcpy(result + a_len + 1, b, b_len + 1);
    } else {
        memcpy(result + a_len, b, b_len + 1);
    }

    return result;
}
