/*
 * WoW Stat Tracker - Character Store Implementation
 * BSD 3-Clause License
 */

#include "character_store.h"
#include "util.h"
#include "cJSON.h"
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#ifdef _WIN32
#include <windows.h>
#endif

#define INITIAL_CAPACITY 16

CharacterStore* character_store_new(const char* file_path) {
    CharacterStore* store = wst_calloc(1, sizeof(CharacterStore));
    if (!store) return NULL;

    store->file_path = wst_strdup(file_path);
    if (!store->file_path) {
        free(store);
        return NULL;
    }

    store->characters = wst_calloc(INITIAL_CAPACITY, sizeof(Character*));
    if (!store->characters) {
        free(store->file_path);
        free(store);
        return NULL;
    }

    store->count = 0;
    store->capacity = INITIAL_CAPACITY;

    return store;
}

void character_store_free(CharacterStore* store) {
    if (!store) return;

    for (size_t i = 0; i < store->count; i++) {
        character_free(store->characters[i]);
    }
    free(store->characters);
    free(store->file_path);
    free(store);
}

WstResult character_store_load(CharacterStore* store) {
    if (!store || !store->file_path) return WST_ERR_NULL_ARG;

    /* Read file into string */
    FILE* f = fopen(store->file_path, "r");
    if (!f) {
        /* File doesn't exist - start with empty store */
        return WST_OK;
    }

    fseek(f, 0, SEEK_END);
    long size = ftell(f);
    fseek(f, 0, SEEK_SET);

    if (size <= 0) {
        fclose(f);
        return WST_OK;
    }

    char* content = malloc((size_t)size + 1);
    if (!content) {
        fclose(f);
        return WST_ERR_ALLOC;
    }

    size_t read = fread(content, 1, (size_t)size, f);
    fclose(f);
    content[read] = '\0';

    /* Parse JSON */
    cJSON* json = cJSON_Parse(content);
    free(content);

    if (!json) {
        return WST_ERR_PARSE;
    }

    if (!cJSON_IsArray(json)) {
        cJSON_Delete(json);
        return WST_ERR_PARSE;
    }

    /* Clear existing characters */
    for (size_t i = 0; i < store->count; i++) {
        character_free(store->characters[i]);
        store->characters[i] = NULL;
    }
    store->count = 0;

    /* Load characters from array */
    cJSON* item;
    cJSON_ArrayForEach(item, json) {
        Character* c = character_from_json(item);
        if (c) {
            WstResult result = character_store_add(store, c);
            if (result != WST_OK) {
                character_free(c);
            }
        }
    }

    cJSON_Delete(json);
    return WST_OK;
}

WstResult character_store_save(const CharacterStore* store) {
    if (!store || !store->file_path) return WST_ERR_NULL_ARG;

    /* Build JSON array */
    cJSON* array = cJSON_CreateArray();
    if (!array) return WST_ERR_ALLOC;

    for (size_t i = 0; i < store->count; i++) {
        cJSON* item = character_to_json(store->characters[i]);
        if (item) {
            cJSON_AddItemToArray(array, item);
        }
    }

    char* json_str = cJSON_Print(array);
    cJSON_Delete(array);

    if (!json_str) return WST_ERR_ALLOC;

    /* Write to temp file first */
    size_t path_len = strlen(store->file_path);
    char* temp_path = malloc(path_len + 5);
    if (!temp_path) {
        cJSON_free(json_str);
        return WST_ERR_ALLOC;
    }
    snprintf(temp_path, path_len + 5, "%s.tmp", store->file_path);

#ifdef _WIN32
    /* Use Windows APIs for proper UTF-8 path handling */
    wchar_t wTempPath[MAX_PATH];
    wchar_t wPath[MAX_PATH];
    MultiByteToWideChar(CP_UTF8, 0, temp_path, -1, wTempPath, MAX_PATH);
    MultiByteToWideChar(CP_UTF8, 0, store->file_path, -1, wPath, MAX_PATH);

    HANDLE hFile = CreateFileW(wTempPath, GENERIC_WRITE, 0, NULL,
                               CREATE_ALWAYS, FILE_ATTRIBUTE_NORMAL, NULL);
    if (hFile == INVALID_HANDLE_VALUE) {
        free(temp_path);
        cJSON_free(json_str);
        return WST_ERR_IO;
    }

    size_t len = strlen(json_str);
    DWORD written;
    BOOL success = WriteFile(hFile, json_str, (DWORD)len, &written, NULL);
    FlushFileBuffers(hFile);
    CloseHandle(hFile);
    cJSON_free(json_str);

    if (!success || written != len) {
        DeleteFileW(wTempPath);
        free(temp_path);
        return WST_ERR_IO;
    }

    /* Atomic rename with replace */
    if (!MoveFileExW(wTempPath, wPath, MOVEFILE_REPLACE_EXISTING)) {
        DeleteFileW(wTempPath);
        free(temp_path);
        return WST_ERR_IO;
    }
#else
    FILE* f = fopen(temp_path, "w");
    if (!f) {
        free(temp_path);
        cJSON_free(json_str);
        return WST_ERR_IO;
    }

    size_t written = fwrite(json_str, 1, strlen(json_str), f);
    fclose(f);
    cJSON_free(json_str);

    if (written == 0) {
        remove(temp_path);
        free(temp_path);
        return WST_ERR_IO;
    }

    /* Atomic rename */
    if (rename(temp_path, store->file_path) != 0) {
        remove(temp_path);
        free(temp_path);
        return WST_ERR_IO;
    }
#endif

    free(temp_path);
    return WST_OK;
}

static WstResult ensure_capacity(CharacterStore* store) {
    if (store->count < store->capacity) return WST_OK;

    size_t new_capacity = store->capacity * 2;
    Character** new_chars = wst_realloc(store->characters,
                                         new_capacity * sizeof(Character*));
    if (!new_chars) return WST_ERR_ALLOC;

    store->characters = new_chars;
    store->capacity = new_capacity;
    return WST_OK;
}

WstResult character_store_add(CharacterStore* store, Character* c) {
    if (!store || !c) return WST_ERR_NULL_ARG;

    WstResult result = ensure_capacity(store);
    if (result != WST_OK) return result;

    store->characters[store->count++] = c;
    return WST_OK;
}

WstResult character_store_update(CharacterStore* store, size_t index, Character* c) {
    if (!store || !c) return WST_ERR_NULL_ARG;
    if (index >= store->count) return WST_ERR_OUT_OF_RANGE;

    character_free(store->characters[index]);
    store->characters[index] = c;
    return WST_OK;
}

WstResult character_store_delete(CharacterStore* store, size_t index) {
    if (!store) return WST_ERR_NULL_ARG;
    if (index >= store->count) return WST_ERR_OUT_OF_RANGE;

    character_free(store->characters[index]);

    /* Shift remaining characters down */
    for (size_t i = index; i < store->count - 1; i++) {
        store->characters[i] = store->characters[i + 1];
    }
    store->count--;
    store->characters[store->count] = NULL;

    return WST_OK;
}

Character* character_store_get(const CharacterStore* store, size_t index) {
    if (!store || index >= store->count) return NULL;
    return store->characters[index];
}

size_t character_store_count(const CharacterStore* store) {
    return store ? store->count : 0;
}

void character_store_reset_weekly_all(CharacterStore* store) {
    if (!store) return;

    for (size_t i = 0; i < store->count; i++) {
        character_reset_weekly(store->characters[i]);
    }
}

int character_store_find(const CharacterStore* store,
                          const char* realm, const char* name) {
    if (!store || !realm || !name) return -1;

    for (size_t i = 0; i < store->count; i++) {
        const Character* c = store->characters[i];
        if (wst_strcmp(c->realm, realm) == 0 &&
            wst_strcmp(c->name, name) == 0) {
            return (int)i;
        }
    }
    return -1;
}
