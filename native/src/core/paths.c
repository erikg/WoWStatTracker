/*
 * WoW Stat Tracker - Path Utilities Implementation
 * BSD 3-Clause License
 */

#include "paths.h"
#include "util.h"
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/stat.h>

#ifdef _WIN32
#include <windows.h>
#include <shlobj.h>
#else
#include <unistd.h>
#include <pwd.h>
#endif

char* paths_get_home(void) {
#ifdef _WIN32
    char* home = getenv("USERPROFILE");
    if (home) return wst_strdup(home);

    char* drive = getenv("HOMEDRIVE");
    char* path = getenv("HOMEPATH");
    if (drive && path) {
        return wst_path_join(drive, path);
    }
    return NULL;
#else
    char* home = getenv("HOME");
    if (home) return wst_strdup(home);

    struct passwd* pw = getpwuid(getuid());
    if (pw && pw->pw_dir) {
        return wst_strdup(pw->pw_dir);
    }
    return NULL;
#endif
}

char* paths_get_config_dir(void) {
    char* result = NULL;

#ifdef _WIN32
    char* appdata = getenv("APPDATA");
    if (appdata) {
        result = wst_path_join(appdata, WST_APP_NAME);
    } else {
        char* home = paths_get_home();
        if (home) {
            char* appdata_path = wst_path_join(home, "AppData\\Roaming");
            free(home);
            if (appdata_path) {
                result = wst_path_join(appdata_path, WST_APP_NAME);
                free(appdata_path);
            }
        }
    }
#elif defined(__APPLE__)
    char* home = paths_get_home();
    if (home) {
        char* lib = wst_path_join(home, "Library/Application Support");
        free(home);
        if (lib) {
            result = wst_path_join(lib, WST_APP_NAME);
            free(lib);
        }
    }
#else
    /* Linux/Unix: use XDG_CONFIG_HOME or ~/.config */
    char* xdg = getenv("XDG_CONFIG_HOME");
    if (xdg && xdg[0] != '\0') {
        result = wst_path_join(xdg, WST_APP_NAME);
    } else {
        char* home = paths_get_home();
        if (home) {
            char* cfg = wst_path_join(home, ".config");
            free(home);
            if (cfg) {
                result = wst_path_join(cfg, WST_APP_NAME);
                free(cfg);
            }
        }
    }
#endif

    /* Create the directory if it doesn't exist */
    if (result) {
        paths_ensure_dir(result);
    }

    return result;
}

char* paths_get_data_file(void) {
    char* dir = paths_get_config_dir();
    if (!dir) return NULL;

    char* path = wst_path_join(dir, "wowstat_data.json");
    free(dir);
    return path;
}

char* paths_get_config_file(void) {
    char* dir = paths_get_config_dir();
    if (!dir) return NULL;

    char* path = wst_path_join(dir, "wowstat_config.json");
    free(dir);
    return path;
}

char* paths_get_notifications_file(void) {
    char* dir = paths_get_config_dir();
    if (!dir) return NULL;

    char* path = wst_path_join(dir, "notifications.json");
    free(dir);
    return path;
}

char* paths_get_lock_file(void) {
    char* dir = paths_get_config_dir();
    if (!dir) return NULL;

    char* path = wst_path_join(dir, "wowstat.lock");
    free(dir);
    return path;
}

WstResult paths_ensure_dir(const char* path) {
    if (!path) return WST_ERR_NULL_ARG;

    /* Check if already exists */
    if (paths_is_dir(path)) {
        return WST_OK;
    }

#ifdef _WIN32
    /* Try to create the directory, including parents */
    int result = SHCreateDirectoryExA(NULL, path, NULL);
    if (result == ERROR_SUCCESS || result == ERROR_ALREADY_EXISTS) {
        return WST_OK;
    }
    return WST_ERR_IO;
#else
    /* Create with mkdir -p style: create parents if needed */
    char* path_copy = wst_strdup(path);
    if (!path_copy) return WST_ERR_ALLOC;

    char* p = path_copy;
    if (*p == '/') p++;  /* Skip leading slash */

    while (*p) {
        while (*p && *p != '/') p++;
        if (*p == '/') {
            *p = '\0';
            mkdir(path_copy, 0755);
            *p = '/';
            p++;
        }
    }

    int result = mkdir(path_copy, 0755);
    free(path_copy);

    if (result == 0 || paths_is_dir(path)) {
        return WST_OK;
    }
    return WST_ERR_IO;
#endif
}

bool paths_is_dir(const char* path) {
    if (!path) return false;

    struct stat st;
    if (stat(path, &st) != 0) {
        return false;
    }
    return S_ISDIR(st.st_mode);
}

bool paths_file_exists(const char* path) {
    if (!path) return false;

    struct stat st;
    return stat(path, &st) == 0;
}
