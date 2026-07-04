/*
 * WoW Stat Tracker - Gem/Enchant Recommendations Loader
 * BSD 3-Clause License
 *
 * Loads the bundled data/gem_enchant_recs.json recommendation file and
 * provides lookup by class/spec display name (matching the addon's fields).
 */

#ifndef WST_GEM_RECS_H
#define WST_GEM_RECS_H

#include "cJSON.h"

/* Opaque handle owning the parsed recommendation document. */
typedef struct GemRecs GemRecs;

/*
 * Parse the recommendation JSON file at 'path'.
 * Returns an owned handle, or NULL on failure (missing file / parse error).
 */
GemRecs* gem_recs_load(const char* path);

/*
 * Look up the spec node (containing "enchants" and "gems") for a given
 * class/spec display name (e.g. "Priest"/"Holy").
 * Returns a borrowed cJSON pointer owned by the handle, or NULL if the
 * class/spec is not present or any argument is NULL.
 */
const cJSON* gem_recs_lookup(const GemRecs* recs,
                             const char* wow_class, const char* spec);

/*
 * Free a recommendations handle and its parsed document.
 */
void gem_recs_free(GemRecs* recs);

#endif /* WST_GEM_RECS_H */
