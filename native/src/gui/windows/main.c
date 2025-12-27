/*
 * WoW Stat Tracker - Windows Application Entry Point
 * BSD 3-Clause License
 */

#define WIN32_LEAN_AND_MEAN
#define UNICODE
#define _UNICODE

#include <windows.h>
#include <commctrl.h>
#include <shlobj.h>
#include <stdio.h>

#include "resource.h"
#include "main_window.h"
#include "character_store.h"
#include "config.h"
#include "notification.h"
#include "paths.h"
#include "platform.h"
#include "week_id.h"
#include "version.h"

/* Application version - from generated version.h */
#define APP_VERSION_W2(x) L ## x
#define APP_VERSION_W(x) APP_VERSION_W2(x)
#define APP_VERSION APP_VERSION_W(WST_VERSION)

/* Global application state */
typedef struct {
    HINSTANCE hInstance;
    HWND hMainWindow;
    CharacterStore *characterStore;
    Config *config;
    NotificationStore *notificationStore;
    wchar_t configDir[MAX_PATH];
    wchar_t lockFile[MAX_PATH];
    BOOL weeklyResetOccurred;
} AppState;

static AppState g_app = {0};

/* Forward declarations */
static BOOL InitializeApplication(HINSTANCE hInstance);
static void ShutdownApplication(void);
static BOOL AcquireSingleInstanceLock(void);
static BOOL CheckWeeklyReset(void);

/* Get application state */
AppState* GetAppState(void) {
    return &g_app;
}

CharacterStore* GetCharacterStore(void) {
    return g_app.characterStore;
}

Config* GetConfig(void) {
    return g_app.config;
}

NotificationStore* GetNotificationStore(void) {
    return g_app.notificationStore;
}

HINSTANCE GetAppInstance(void) {
    return g_app.hInstance;
}

/* Main entry point */
int WINAPI wWinMain(HINSTANCE hInstance, HINSTANCE hPrevInstance,
                    LPWSTR lpCmdLine, int nCmdShow) {
    (void)hPrevInstance;
    (void)lpCmdLine;

    /* Initialize common controls */
    INITCOMMONCONTROLSEX icex = {
        .dwSize = sizeof(INITCOMMONCONTROLSEX),
        .dwICC = ICC_LISTVIEW_CLASSES | ICC_BAR_CLASSES | ICC_STANDARD_CLASSES
    };
    InitCommonControlsEx(&icex);

    /* Initialize COM for shell operations */
    CoInitializeEx(NULL, COINIT_APARTMENTTHREADED);

    /* Initialize application */
    if (!InitializeApplication(hInstance)) {
        MessageBoxW(NULL, L"Failed to initialize application.",
                    L"Error", MB_OK | MB_ICONERROR);
        return 1;
    }

    /* Create and show main window */
    g_app.hMainWindow = CreateMainWindow(hInstance, nCmdShow);
    if (!g_app.hMainWindow) {
        MessageBoxW(NULL, L"Failed to create main window.",
                    L"Error", MB_OK | MB_ICONERROR);
        ShutdownApplication();
        return 1;
    }

    /* Show weekly reset notification if occurred */
    if (g_app.weeklyResetOccurred) {
        ShowStatusMessage(L"Weekly data auto-reset for new WoW week.", WST_NOTIFY_INFO);
    }

    /* Message loop */
    MSG msg;
    while (GetMessageW(&msg, NULL, 0, 0)) {
        if (!IsDialogMessageW(g_app.hMainWindow, &msg)) {
            TranslateMessage(&msg);
            DispatchMessageW(&msg);
        }
    }

    /* Cleanup */
    ShutdownApplication();
    CoUninitialize();

    return (int)msg.wParam;
}

static BOOL InitializeApplication(HINSTANCE hInstance) {
    g_app.hInstance = hInstance;

    /* Get config directory */
    char *configDir = paths_get_config_dir();
    if (!configDir) {
        return FALSE;
    }

    /* Convert to wide string */
    MultiByteToWideChar(CP_UTF8, 0, configDir, -1, g_app.configDir, MAX_PATH);
    free(configDir);

    /* Create config directory if needed */
    SHCreateDirectoryExW(NULL, g_app.configDir, NULL);

    /* Set up lock file path */
    swprintf(g_app.lockFile, MAX_PATH, L"%s\\wowstat.lock", g_app.configDir);

    /* Acquire single instance lock */
    if (!AcquireSingleInstanceLock()) {
        MessageBoxW(NULL, L"Another instance is already running!",
                    L"WoW Stat Tracker", MB_OK | MB_ICONWARNING);
        return FALSE;
    }

    /* Build file paths */
    wchar_t dataFile[MAX_PATH];
    wchar_t configFile[MAX_PATH];
    wchar_t notifyFile[MAX_PATH];

    swprintf(dataFile, MAX_PATH, L"%s\\wowstat_data.json", g_app.configDir);
    swprintf(configFile, MAX_PATH, L"%s\\wowstat_config.json", g_app.configDir);
    swprintf(notifyFile, MAX_PATH, L"%s\\notifications.json", g_app.configDir);

    /* Convert to UTF-8 for C libraries */
    char dataFileUtf8[MAX_PATH * 3];
    char configFileUtf8[MAX_PATH * 3];
    char notifyFileUtf8[MAX_PATH * 3];

    WideCharToMultiByte(CP_UTF8, 0, dataFile, -1, dataFileUtf8, sizeof(dataFileUtf8), NULL, NULL);
    WideCharToMultiByte(CP_UTF8, 0, configFile, -1, configFileUtf8, sizeof(configFileUtf8), NULL, NULL);
    WideCharToMultiByte(CP_UTF8, 0, notifyFile, -1, notifyFileUtf8, sizeof(notifyFileUtf8), NULL, NULL);

    /* Load character store */
    g_app.characterStore = character_store_new(dataFileUtf8);
    if (!g_app.characterStore) {
        return FALSE;
    }
    character_store_load(g_app.characterStore);

    /* Load config */
    g_app.config = config_new(configFileUtf8);
    if (!g_app.config) {
        return FALSE;
    }
    config_load(g_app.config);

    /* Load notification store */
    g_app.notificationStore = notification_store_new(notifyFileUtf8);
    if (g_app.notificationStore) {
        notification_store_load(g_app.notificationStore);
    }

    /* Check for weekly reset */
    g_app.weeklyResetOccurred = CheckWeeklyReset();

    return TRUE;
}

static void ShutdownApplication(void) {
    /* Save data */
    if (g_app.characterStore) {
        character_store_save(g_app.characterStore);
        character_store_free(g_app.characterStore);
        g_app.characterStore = NULL;
    }

    if (g_app.config) {
        config_save(g_app.config);
        config_free(g_app.config);
        g_app.config = NULL;
    }

    if (g_app.notificationStore) {
        notification_store_save(g_app.notificationStore);
        notification_store_free(g_app.notificationStore);
        g_app.notificationStore = NULL;
    }

    /* Release lock */
    char lockFileUtf8[MAX_PATH * 3];
    WideCharToMultiByte(CP_UTF8, 0, g_app.lockFile, -1, lockFileUtf8, sizeof(lockFileUtf8), NULL, NULL);
    platform_lock_release(lockFileUtf8);
}

static BOOL AcquireSingleInstanceLock(void) {
    char lockFileUtf8[MAX_PATH * 3];
    WideCharToMultiByte(CP_UTF8, 0, g_app.lockFile, -1, lockFileUtf8, sizeof(lockFileUtf8), NULL, NULL);
    return platform_lock_acquire(lockFileUtf8) == WST_OK;
}

static BOOL CheckWeeklyReset(void) {
    char *currentWeekStr = week_id_current();
    if (!currentWeekStr) return FALSE;

    const char *lastWeekStr = config_get_string(g_app.config, "last_week_id", NULL);

    if (!lastWeekStr || strlen(lastWeekStr) == 0) {
        /* First run - just record current week */
        config_set_string(g_app.config, "last_week_id", currentWeekStr);
        config_save(g_app.config);
        free(currentWeekStr);
        return FALSE;
    }

    BOOL resetOccurred = !week_id_equal(currentWeekStr, lastWeekStr);
    if (resetOccurred) {
        /* Week changed - reset weekly data */
        character_store_reset_weekly_all(g_app.characterStore);
        character_store_save(g_app.characterStore);

        config_set_string(g_app.config, "last_week_id", currentWeekStr);
        config_save(g_app.config);
    }

    free(currentWeekStr);
    return resetOccurred;
}
