/*
 * WoW Stat Tracker - Notification Implementation
 * BSD 3-Clause License
 */

#include "notification.h"
#include "util.h"
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <time.h>

#ifdef _WIN32
#include <windows.h>
#else
#include <sys/time.h>
#endif

#define INITIAL_CAPACITY 64

/* Generate a simple UUID (not cryptographically secure, but sufficient) */
static char* generate_uuid(void) {
    char* uuid = malloc(37);
    if (!uuid) return NULL;

    unsigned int seed;
#ifdef _WIN32
    seed = (unsigned int)GetTickCount() ^ (unsigned int)time(NULL);
#else
    struct timeval tv;
    gettimeofday(&tv, NULL);
    seed = (unsigned int)(tv.tv_sec ^ tv.tv_usec);
#endif

    srand(seed);
    snprintf(uuid, 37,
             "%08x-%04x-%04x-%04x-%012llx",
             (unsigned int)rand(),
             (unsigned int)(rand() & 0xFFFF),
             (unsigned int)((rand() & 0x0FFF) | 0x4000),
             (unsigned int)((rand() & 0x3FFF) | 0x8000),
             (unsigned long long)rand() * rand());

    return uuid;
}

/* Generate ISO timestamp */
static char* generate_timestamp(void) {
    time_t now = time(NULL);
    struct tm* tm_info = localtime(&now);

    char* ts = malloc(32);
    if (!ts) return NULL;

    strftime(ts, 32, "%Y-%m-%dT%H:%M:%S", tm_info);
    return ts;
}

Notification* notification_create(const char* message, WstNotifyType type) {
    Notification* n = wst_calloc(1, sizeof(Notification));
    if (!n) return NULL;

    n->id = generate_uuid();
    n->message = wst_strdup(message ? message : "");
    n->type = type;
    n->timestamp = generate_timestamp();

    if (!n->id || !n->message || !n->timestamp) {
        notification_free(n);
        return NULL;
    }

    return n;
}

void notification_free(Notification* n) {
    if (!n) return;

    free(n->id);
    free(n->message);
    free(n->timestamp);
    free(n);
}

char* notification_format_timestamp(const Notification* n) {
    if (!n || !n->timestamp) return NULL;

    /* Parse ISO timestamp */
    int year, month, day, hour, minute, second;
    int parsed = sscanf(n->timestamp, "%d-%d-%dT%d:%d:%d",
                        &year, &month, &day, &hour, &minute, &second);
    if (parsed < 5) {
        return wst_strdup(n->timestamp);
    }

    static const char* months[] = {
        "Jan", "Feb", "Mar", "Apr", "May", "Jun",
        "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"
    };

    const char* month_name = (month >= 1 && month <= 12) ?
                              months[month - 1] : "???";

    /* Format as "Dec 24, 4:30 PM" */
    char buf[32];
    int hour12 = hour % 12;
    if (hour12 == 0) hour12 = 12;
    const char* ampm = (hour < 12) ? "AM" : "PM";

    snprintf(buf, sizeof(buf), "%s %d, %d:%02d %s",
             month_name, day, hour12, minute, ampm);

    return wst_strdup(buf);
}

const char* notify_type_to_string(WstNotifyType type) {
    switch (type) {
        case WST_NOTIFY_INFO:    return "info";
        case WST_NOTIFY_SUCCESS: return "success";
        case WST_NOTIFY_WARNING: return "warning";
        default:                 return "info";
    }
}

WstNotifyType notify_type_from_string(const char* str) {
    if (!str) return WST_NOTIFY_INFO;

    if (wst_strcasecmp(str, "success") == 0) return WST_NOTIFY_SUCCESS;
    if (wst_strcasecmp(str, "warning") == 0) return WST_NOTIFY_WARNING;
    return WST_NOTIFY_INFO;
}

cJSON* notification_to_json(const Notification* n) {
    if (!n) return NULL;

    cJSON* json = cJSON_CreateObject();
    if (!json) return NULL;

    cJSON_AddStringToObject(json, "id", n->id ? n->id : "");
    cJSON_AddStringToObject(json, "message", n->message ? n->message : "");
    cJSON_AddStringToObject(json, "notification_type", notify_type_to_string(n->type));
    cJSON_AddStringToObject(json, "timestamp", n->timestamp ? n->timestamp : "");

    return json;
}

Notification* notification_from_json(const cJSON* json) {
    if (!json || !cJSON_IsObject(json)) return NULL;

    Notification* n = wst_calloc(1, sizeof(Notification));
    if (!n) return NULL;

    const cJSON* id = cJSON_GetObjectItemCaseSensitive(json, "id");
    const cJSON* msg = cJSON_GetObjectItemCaseSensitive(json, "message");
    const cJSON* type = cJSON_GetObjectItemCaseSensitive(json, "notification_type");
    const cJSON* ts = cJSON_GetObjectItemCaseSensitive(json, "timestamp");

    n->id = wst_strdup(cJSON_IsString(id) ? id->valuestring : "");
    n->message = wst_strdup(cJSON_IsString(msg) ? msg->valuestring : "");
    n->type = notify_type_from_string(
        cJSON_IsString(type) ? type->valuestring : "info");
    n->timestamp = wst_strdup(cJSON_IsString(ts) ? ts->valuestring : "");

    if (!n->id || !n->message || !n->timestamp) {
        notification_free(n);
        return NULL;
    }

    return n;
}

/* --- Notification Store Implementation --- */

NotificationStore* notification_store_new(const char* file_path) {
    NotificationStore* store = wst_calloc(1, sizeof(NotificationStore));
    if (!store) return NULL;

    store->file_path = wst_strdup(file_path);
    if (!store->file_path) {
        free(store);
        return NULL;
    }

    store->notifications = wst_calloc(INITIAL_CAPACITY, sizeof(Notification*));
    if (!store->notifications) {
        free(store->file_path);
        free(store);
        return NULL;
    }

    store->count = 0;
    store->capacity = INITIAL_CAPACITY;

    return store;
}

void notification_store_free(NotificationStore* store) {
    if (!store) return;

    for (size_t i = 0; i < store->count; i++) {
        notification_free(store->notifications[i]);
    }
    free(store->notifications);
    free(store->file_path);
    free(store);
}

WstResult notification_store_load(NotificationStore* store) {
    if (!store || !store->file_path) return WST_ERR_NULL_ARG;

    FILE* f = fopen(store->file_path, "r");
    if (!f) {
        return WST_OK;  /* File doesn't exist, start empty */
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

    if (!json || !cJSON_IsArray(json)) {
        cJSON_Delete(json);
        return WST_ERR_PARSE;
    }

    /* Clear existing */
    for (size_t i = 0; i < store->count; i++) {
        notification_free(store->notifications[i]);
        store->notifications[i] = NULL;
    }
    store->count = 0;

    /* Load from array */
    cJSON* item;
    cJSON_ArrayForEach(item, json) {
        Notification* n = notification_from_json(item);
        if (n) {
            notification_store_add(store, n);
        }
    }

    cJSON_Delete(json);
    return WST_OK;
}

WstResult notification_store_save(const NotificationStore* store) {
    if (!store || !store->file_path) return WST_ERR_NULL_ARG;

    cJSON* array = cJSON_CreateArray();
    if (!array) return WST_ERR_ALLOC;

    for (size_t i = 0; i < store->count; i++) {
        cJSON* item = notification_to_json(store->notifications[i]);
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

    if (rename(temp_path, store->file_path) != 0) {
        remove(temp_path);
        free(temp_path);
        return WST_ERR_IO;
    }

    free(temp_path);
    return WST_OK;
}

static WstResult ensure_capacity(NotificationStore* store) {
    if (store->count < store->capacity) return WST_OK;

    size_t new_capacity = store->capacity * 2;
    Notification** new_arr = wst_realloc(store->notifications,
                                          new_capacity * sizeof(Notification*));
    if (!new_arr) return WST_ERR_ALLOC;

    store->notifications = new_arr;
    store->capacity = new_capacity;
    return WST_OK;
}

WstResult notification_store_add(NotificationStore* store, Notification* n) {
    if (!store || !n) return WST_ERR_NULL_ARG;

    WstResult result = ensure_capacity(store);
    if (result != WST_OK) return result;

    /* Insert at beginning (most recent first) */
    memmove(&store->notifications[1], &store->notifications[0],
            store->count * sizeof(Notification*));
    store->notifications[0] = n;
    store->count++;

    /* Trim if over limit */
    while (store->count > WST_MAX_NOTIFICATION_HISTORY) {
        store->count--;
        notification_free(store->notifications[store->count]);
        store->notifications[store->count] = NULL;
    }

    return WST_OK;
}

bool notification_store_remove(NotificationStore* store, const char* id) {
    if (!store || !id) return false;

    for (size_t i = 0; i < store->count; i++) {
        if (store->notifications[i] &&
            store->notifications[i]->id &&
            strcmp(store->notifications[i]->id, id) == 0) {

            notification_free(store->notifications[i]);

            /* Shift remaining down */
            for (size_t j = i; j < store->count - 1; j++) {
                store->notifications[j] = store->notifications[j + 1];
            }
            store->count--;
            store->notifications[store->count] = NULL;
            return true;
        }
    }
    return false;
}

void notification_store_clear_all(NotificationStore* store) {
    if (!store) return;

    for (size_t i = 0; i < store->count; i++) {
        notification_free(store->notifications[i]);
        store->notifications[i] = NULL;
    }
    store->count = 0;
}

Notification* notification_store_get(const NotificationStore* store, size_t index) {
    if (!store || index >= store->count) return NULL;
    return store->notifications[index];
}

size_t notification_store_count(const NotificationStore* store) {
    return store ? store->count : 0;
}
