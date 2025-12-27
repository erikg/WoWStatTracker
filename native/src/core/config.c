/*
 * WoW Stat Tracker - Configuration Implementation
 * BSD 3-Clause License
 */

#include "config.h"
#include "util.h"
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

Config* config_new(const char* file_path) {
    Config* cfg = wst_calloc(1, sizeof(Config));
    if (!cfg) return NULL;

    cfg->file_path = wst_strdup(file_path);
    if (!cfg->file_path) {
        free(cfg);
        return NULL;
    }

    cfg->data = cJSON_CreateObject();
    if (!cfg->data) {
        free(cfg->file_path);
        free(cfg);
        return NULL;
    }

    return cfg;
}

void config_free(Config* cfg) {
    if (!cfg) return;

    cJSON_Delete(cfg->data);
    free(cfg->file_path);
    free(cfg);
}

WstResult config_load(Config* cfg) {
    if (!cfg || !cfg->file_path) return WST_ERR_NULL_ARG;

    FILE* f = fopen(cfg->file_path, "r");
    if (!f) {
        /* File doesn't exist - use empty config */
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

    cJSON* json = cJSON_Parse(content);
    free(content);

    if (!json) {
        return WST_ERR_PARSE;
    }

    if (!cJSON_IsObject(json)) {
        cJSON_Delete(json);
        return WST_ERR_PARSE;
    }

    /* Replace existing data */
    cJSON_Delete(cfg->data);
    cfg->data = json;

    return WST_OK;
}

WstResult config_save(const Config* cfg) {
    if (!cfg || !cfg->file_path || !cfg->data) return WST_ERR_NULL_ARG;

    char* json_str = cJSON_Print(cfg->data);
    if (!json_str) return WST_ERR_ALLOC;

    /* Write to temp file first */
    size_t path_len = strlen(cfg->file_path);
    char* temp_path = malloc(path_len + 5);
    if (!temp_path) {
        cJSON_free(json_str);
        return WST_ERR_ALLOC;
    }
    snprintf(temp_path, path_len + 5, "%s.tmp", cfg->file_path);

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
    if (rename(temp_path, cfg->file_path) != 0) {
        remove(temp_path);
        free(temp_path);
        return WST_ERR_IO;
    }

    free(temp_path);
    return WST_OK;
}

const char* config_get_string(const Config* cfg, const char* key,
                               const char* default_val) {
    if (!cfg || !cfg->data || !key) return default_val;

    const cJSON* item = cJSON_GetObjectItemCaseSensitive(cfg->data, key);
    if (cJSON_IsString(item) && item->valuestring) {
        return item->valuestring;
    }
    return default_val;
}

int config_get_int(const Config* cfg, const char* key, int default_val) {
    if (!cfg || !cfg->data || !key) return default_val;

    const cJSON* item = cJSON_GetObjectItemCaseSensitive(cfg->data, key);
    if (cJSON_IsNumber(item)) {
        return item->valueint;
    }
    return default_val;
}

double config_get_double(const Config* cfg, const char* key, double default_val) {
    if (!cfg || !cfg->data || !key) return default_val;

    const cJSON* item = cJSON_GetObjectItemCaseSensitive(cfg->data, key);
    if (cJSON_IsNumber(item)) {
        return item->valuedouble;
    }
    return default_val;
}

bool config_get_bool(const Config* cfg, const char* key, bool default_val) {
    if (!cfg || !cfg->data || !key) return default_val;

    const cJSON* item = cJSON_GetObjectItemCaseSensitive(cfg->data, key);
    if (cJSON_IsBool(item)) {
        return cJSON_IsTrue(item);
    }
    return default_val;
}

WstResult config_set_string(Config* cfg, const char* key, const char* value) {
    if (!cfg || !cfg->data || !key) return WST_ERR_NULL_ARG;

    /* Remove existing item if present */
    cJSON_DeleteItemFromObjectCaseSensitive(cfg->data, key);

    cJSON* item = cJSON_CreateString(value ? value : "");
    if (!item) return WST_ERR_ALLOC;

    cJSON_AddItemToObject(cfg->data, key, item);
    return WST_OK;
}

WstResult config_set_int(Config* cfg, const char* key, int value) {
    if (!cfg || !cfg->data || !key) return WST_ERR_NULL_ARG;

    cJSON_DeleteItemFromObjectCaseSensitive(cfg->data, key);

    cJSON* item = cJSON_CreateNumber((double)value);
    if (!item) return WST_ERR_ALLOC;

    cJSON_AddItemToObject(cfg->data, key, item);
    return WST_OK;
}

WstResult config_set_double(Config* cfg, const char* key, double value) {
    if (!cfg || !cfg->data || !key) return WST_ERR_NULL_ARG;

    cJSON_DeleteItemFromObjectCaseSensitive(cfg->data, key);

    cJSON* item = cJSON_CreateNumber(value);
    if (!item) return WST_ERR_ALLOC;

    cJSON_AddItemToObject(cfg->data, key, item);
    return WST_OK;
}

WstResult config_set_bool(Config* cfg, const char* key, bool value) {
    if (!cfg || !cfg->data || !key) return WST_ERR_NULL_ARG;

    cJSON_DeleteItemFromObjectCaseSensitive(cfg->data, key);

    cJSON* item = cJSON_CreateBool(value);
    if (!item) return WST_ERR_ALLOC;

    cJSON_AddItemToObject(cfg->data, key, item);
    return WST_OK;
}

cJSON* config_get_object(Config* cfg, const char* key) {
    if (!cfg || !cfg->data || !key) return NULL;

    cJSON* item = cJSON_GetObjectItemCaseSensitive(cfg->data, key);
    if (cJSON_IsObject(item)) {
        return item;
    }
    return NULL;
}

WstResult config_set_object(Config* cfg, const char* key, cJSON* obj) {
    if (!cfg || !cfg->data || !key || !obj) return WST_ERR_NULL_ARG;

    cJSON_DeleteItemFromObjectCaseSensitive(cfg->data, key);
    cJSON_AddItemToObject(cfg->data, key, obj);
    return WST_OK;
}

bool config_has_key(const Config* cfg, const char* key) {
    if (!cfg || !cfg->data || !key) return false;
    return cJSON_HasObjectItem(cfg->data, key);
}

void config_delete_key(Config* cfg, const char* key) {
    if (!cfg || !cfg->data || !key) return;
    cJSON_DeleteItemFromObjectCaseSensitive(cfg->data, key);
}
