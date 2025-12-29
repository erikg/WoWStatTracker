/*
 * WoW Stat Tracker - Week ID Implementation
 * BSD 3-Clause License
 */

#include "week_id.h"
#include "util.h"
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <time.h>

/* WoW resets on Tuesday at 15:00 UTC */
#define RESET_WEEKDAY 2     /* Tuesday (0=Sunday in struct tm) */
#define RESET_HOUR    15    /* 15:00 UTC */

/*
 * Calculate the last reset timestamp for a given time.
 * Returns the Unix timestamp of the most recent Tuesday 15:00 UTC.
 */
static time_t calculate_last_reset(time_t now) {
    struct tm* utc = gmtime(&now);
    if (!utc) return now;

    /* Calculate days since last Tuesday */
    /* tm_wday: 0=Sunday, 1=Monday, 2=Tuesday, ... */
    int days_since_tuesday = (utc->tm_wday - RESET_WEEKDAY + 7) % 7;

    /* If it's Tuesday but before reset time, count as previous week */
    if (utc->tm_wday == RESET_WEEKDAY && utc->tm_hour < RESET_HOUR) {
        days_since_tuesday = 7;
    }

    /* Calculate the timestamp for the last reset */
    struct tm reset_tm = *utc;
    reset_tm.tm_mday -= days_since_tuesday;
    reset_tm.tm_hour = RESET_HOUR;
    reset_tm.tm_min = 0;
    reset_tm.tm_sec = 0;

    /* Normalize the struct tm (handles month/day boundaries) */
#ifdef _WIN32
    time_t reset_time = _mkgmtime(&reset_tm);
#else
    time_t reset_time = timegm(&reset_tm);
    if (reset_time == (time_t)-1) {
        /* If timegm isn't available or failed, use mktime and adjust */
        reset_time = mktime(&reset_tm);
        /* Adjust for local timezone offset */
        reset_time += utc->tm_gmtoff;
    }
#endif

    return reset_time;
}

char* week_id_for_timestamp(long long timestamp) {
    time_t t = (time_t)timestamp;
    time_t reset = calculate_last_reset(t);

    struct tm* reset_tm = gmtime(&reset);
    if (!reset_tm) return NULL;

    char* buf = malloc(16);
    if (!buf) return NULL;

    snprintf(buf, 16, "%04d%02d%02d",
             reset_tm->tm_year + 1900,
             reset_tm->tm_mon + 1,
             reset_tm->tm_mday);

    return buf;
}

char* week_id_current(void) {
    return week_id_for_timestamp((long long)time(NULL));
}

bool week_id_equal(const char* id1, const char* id2) {
    if (!id1 || !id2) return false;
    return strcmp(id1, id2) == 0;
}

bool week_id_is_current(const char* week_id) {
    if (!week_id) return false;

    char* current = week_id_current();
    if (!current) return false;

    bool result = week_id_equal(week_id, current);
    free(current);
    return result;
}
