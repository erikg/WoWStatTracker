/*
 * WoW Stat Tracker - Core Types
 * BSD 3-Clause License
 */

#ifndef WST_TYPES_H
#define WST_TYPES_H

#include <stdbool.h>
#include <stddef.h>
#include <stdint.h>

/* Result codes */
typedef enum {
    WST_OK = 0,
    WST_ERR_NULL_ARG,
    WST_ERR_ALLOC,
    WST_ERR_IO,
    WST_ERR_PARSE,
    WST_ERR_VALIDATION,
    WST_ERR_NOT_FOUND,
    WST_ERR_OUT_OF_RANGE,
    WST_ERR_LOCK_FAILED,
} WstResult;

/* Validation limits */
#define WST_MAX_ITEM_LEVEL      1000.0
#define WST_MAX_ITEMS_PER_CAT   50
#define WST_MAX_DELVES          8
#define WST_MAX_GILDED_STASH    3
#define WST_MAX_TIMEWALK        5

/* Theme constants */
typedef enum {
    WST_THEME_AUTO = 0,
    WST_THEME_LIGHT,
    WST_THEME_DARK,
} WstTheme;

/* Application info */
#define WST_APP_NAME        "wowstat"
#define WST_GITHUB_REPO     "erikg/WoWStatTracker"

/* Version is defined in generated version.h */
#include "version.h"

/* Forward declarations */
typedef struct Character Character;
typedef struct CharacterStore CharacterStore;
typedef struct Config Config;
typedef struct Notification Notification;
typedef struct NotificationStore NotificationStore;

#endif /* WST_TYPES_H */
