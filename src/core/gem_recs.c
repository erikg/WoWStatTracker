/*
 * WoW Stat Tracker - Gem/Enchant Recommendations Loader Implementation
 * BSD 3-Clause License
 */

#include "gem_recs.h"
#include "util.h"
#include <stdio.h>
#include <stdlib.h>

struct GemRecs {
    cJSON* root;
};

/*
 * Read entire file into a NUL-terminated string. Caller frees.
 */
static char* read_file(const char* path) {
    FILE* f = fopen(path, "rb");
    if (!f) return NULL;

    fseek(f, 0, SEEK_END);
    long size = ftell(f);
    fseek(f, 0, SEEK_SET);

    if (size <= 0) {
        fclose(f);
        return NULL;
    }

    char* content = malloc((size_t)size + 1);
    if (!content) {
        fclose(f);
        return NULL;
    }

    size_t nread = fread(content, 1, (size_t)size, f);
    fclose(f);
    content[nread] = '\0';

    return content;
}

GemRecs* gem_recs_load(const char* path) {
    if (!path) return NULL;

    char* content = read_file(path);
    if (!content) return NULL;

    cJSON* root = cJSON_Parse(content);
    free(content);
    if (!root) return NULL;

    GemRecs* recs = wst_calloc(1, sizeof(GemRecs));
    if (!recs) {
        cJSON_Delete(root);
        return NULL;
    }
    recs->root = root;
    return recs;
}

const cJSON* gem_recs_lookup(const GemRecs* recs,
                             const char* wow_class, const char* spec) {
    if (!recs || !recs->root || !wow_class || !spec) return NULL;
    if (wst_str_empty(wow_class) || wst_str_empty(spec)) return NULL;

    const cJSON* classes =
        cJSON_GetObjectItemCaseSensitive(recs->root, "classes");
    if (!cJSON_IsObject(classes)) return NULL;

    const cJSON* cls = cJSON_GetObjectItemCaseSensitive(classes, wow_class);
    if (!cJSON_IsObject(cls)) return NULL;

    const cJSON* spec_node = cJSON_GetObjectItemCaseSensitive(cls, spec);
    if (!cJSON_IsObject(spec_node)) return NULL;

    return spec_node;
}

void gem_recs_free(GemRecs* recs) {
    if (!recs) return;
    cJSON_Delete(recs->root);
    free(recs);
}
