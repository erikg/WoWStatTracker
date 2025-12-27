/*
 * WoW Stat Tracker - Week ID Calculation
 * BSD 3-Clause License
 *
 * Calculates WoW weekly reset periods based on Tuesday 15:00 UTC.
 */

#ifndef WST_WEEK_ID_H
#define WST_WEEK_ID_H

#include <stdbool.h>

/*
 * Get the current WoW week ID as a string in YYYYMMDD format.
 * The week ID represents the Tuesday reset date for the current week.
 * Caller must free the returned string.
 */
char* week_id_current(void);

/*
 * Get the week ID for a specific Unix timestamp.
 * Caller must free the returned string.
 */
char* week_id_for_timestamp(long long timestamp);

/*
 * Compare two week IDs.
 * Returns true if they represent the same week.
 */
bool week_id_equal(const char* id1, const char* id2);

/*
 * Check if week_id is the current week.
 */
bool week_id_is_current(const char* week_id);

#endif /* WST_WEEK_ID_H */
