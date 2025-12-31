/*
 * WoW Stat Tracker - Windows Resource Definitions
 * BSD 3-Clause License
 */

#ifndef WST_RESOURCE_H
#define WST_RESOURCE_H

/* Menu IDs */
#define IDM_MAINMENU            100

#define IDM_FILE_PROPERTIES     101
#define IDM_FILE_EXIT           102

#define IDM_CHAR_ADD            110
#define IDM_CHAR_EDIT           111
#define IDM_CHAR_DELETE         112
#define IDM_CHAR_RESET_WEEKLY   113

#define IDM_ADDON_IMPORT        120
#define IDM_ADDON_SET_PATH      121
#define IDM_ADDON_INSTALL       122
#define IDM_ADDON_UNINSTALL     123

#define IDM_VIEW_THEME_AUTO     130
#define IDM_VIEW_THEME_LIGHT    131
#define IDM_VIEW_THEME_DARK     132

#define IDM_HELP_MANUAL         140
#define IDM_HELP_UPDATE         141
#define IDM_HELP_ABOUT          142

/* Toolbar IDs */
#define IDT_TOOLBAR             200
#define IDT_ADD                 201
#define IDT_IMPORT              202
#define IDT_RESET               203
#define IDT_UPDATE_ADDON        204

/* Control IDs */
#define IDC_LISTVIEW            300
#define IDC_STATUSBAR           301

/* Dialog IDs */
#define IDD_CHARACTER           400
#define IDD_PREFERENCES         401
#define IDD_MANUAL              402

/* Character Dialog Controls */
#define IDC_CHAR_REALM          410
#define IDC_CHAR_NAME           411
#define IDC_CHAR_GUILD          412
#define IDC_CHAR_ITEMLEVEL      413
#define IDC_CHAR_HEROIC         414
#define IDC_CHAR_CHAMPION       415
#define IDC_CHAR_VETERAN        416
#define IDC_CHAR_ADVENTURE      417
#define IDC_CHAR_OLD            418
#define IDC_CHAR_VAULT          419
#define IDC_CHAR_DELVES         420
#define IDC_CHAR_GILDED         421
#define IDC_CHAR_GEARINGUP      422
#define IDC_CHAR_QUESTS         423
#define IDC_CHAR_TIMEWALK       424
#define IDC_CHAR_NOTES          425
#define IDC_CHAR_DELETE         426

/* Preferences Dialog Controls */
#define IDC_PREF_WOWPATH        430
#define IDC_PREF_BROWSE         431
#define IDC_PREF_THEME          432
#define IDC_PREF_AUTOIMPORT     433
#define IDC_PREF_CHECKUPDATES   434

/* Timer IDs */
#define IDT_STATUS_DISMISS      500
#define IDT_AUTOIMPORT          501

/* String IDs */
#define IDS_APP_TITLE           1000
#define IDS_APP_CLASS           1001

/* Icon IDs */
#define IDI_APPICON             1

#endif /* WST_RESOURCE_H */
