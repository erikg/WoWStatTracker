/*
 * WoW Stat Tracker - Windows Dialogs
 * BSD 3-Clause License
 */

#define WIN32_LEAN_AND_MEAN
#define UNICODE
#define _UNICODE

#include <windows.h>
#include <windowsx.h>
#include <commctrl.h>
#include <shlobj.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#include "main_window.h"
#include "resource.h"
#include "character.h"
#include "character_store.h"
#include "config.h"
#include "notification.h"
#include "platform.h"
#include "version.h"

/* Forward declarations for external app state */
extern CharacterStore* GetCharacterStore(void);
extern Config* GetConfig(void);
extern NotificationStore* GetNotificationStore(void);
extern HINSTANCE GetAppInstance(void);

/* Character dialog state */
static int g_editCharIndex = -1;

/* Dialog procedures */
static INT_PTR CALLBACK CharacterDlgProc(HWND hDlg, UINT uMsg, WPARAM wParam, LPARAM lParam);
static INT_PTR CALLBACK PreferencesDlgProc(HWND hDlg, UINT uMsg, WPARAM wParam, LPARAM lParam);
static INT_PTR CALLBACK ManualDlgProc(HWND hDlg, UINT uMsg, WPARAM wParam, LPARAM lParam);

/* Helper to get text from edit control as UTF-8 */
static char* GetEditTextUtf8(HWND hDlg, int ctrlId) {
    HWND hEdit = GetDlgItem(hDlg, ctrlId);
    int len = GetWindowTextLengthW(hEdit);
    if (len == 0) return NULL;

    wchar_t *wbuf = malloc((len + 1) * sizeof(wchar_t));
    if (!wbuf) return NULL;

    GetWindowTextW(hEdit, wbuf, len + 1);

    int utf8Len = WideCharToMultiByte(CP_UTF8, 0, wbuf, -1, NULL, 0, NULL, NULL);
    char *utf8 = malloc(utf8Len);
    if (utf8) {
        WideCharToMultiByte(CP_UTF8, 0, wbuf, -1, utf8, utf8Len, NULL, NULL);
    }

    free(wbuf);
    return utf8;
}

/* Helper to set edit control text from UTF-8 */
static void SetEditTextUtf8(HWND hDlg, int ctrlId, const char *text) {
    if (!text || text[0] == '\0') {
        SetDlgItemTextW(hDlg, ctrlId, L"");
        return;
    }

    int wlen = MultiByteToWideChar(CP_UTF8, 0, text, -1, NULL, 0);
    wchar_t *wbuf = malloc(wlen * sizeof(wchar_t));
    if (wbuf) {
        MultiByteToWideChar(CP_UTF8, 0, text, -1, wbuf, wlen);
        SetDlgItemTextW(hDlg, ctrlId, wbuf);
        free(wbuf);
    }
}

/* Show character dialog for add/edit */
void ShowCharacterDialog(HWND hWnd, int characterIndex) {
    g_editCharIndex = characterIndex;
    DialogBoxW(GetAppInstance(), MAKEINTRESOURCEW(IDD_CHARACTER), hWnd, CharacterDlgProc);
}

/* Character dialog procedure */
static INT_PTR CALLBACK CharacterDlgProc(HWND hDlg, UINT uMsg, WPARAM wParam, LPARAM lParam) {
    (void)lParam;

    switch (uMsg) {
        case WM_INITDIALOG: {
            /* Set dialog title */
            SetWindowTextW(hDlg, g_editCharIndex >= 0 ? L"Edit Character" : L"Add Character");

            /* Hide delete button for new characters */
            if (g_editCharIndex < 0) {
                ShowWindow(GetDlgItem(hDlg, IDC_CHAR_DELETE), SW_HIDE);
            }

            /* Populate fields if editing */
            if (g_editCharIndex >= 0) {
                CharacterStore *store = GetCharacterStore();
                if (store) {
                    Character *ch = character_store_get(store, g_editCharIndex);
                    if (ch) {
                        SetEditTextUtf8(hDlg, IDC_CHAR_REALM, ch->realm);
                        SetEditTextUtf8(hDlg, IDC_CHAR_NAME, ch->name);
                        SetEditTextUtf8(hDlg, IDC_CHAR_GUILD, ch->guild);

                        wchar_t buf[32];
                        swprintf(buf, 32, L"%.1f", ch->item_level);
                        SetDlgItemTextW(hDlg, IDC_CHAR_ITEMLEVEL, buf);

                        SetDlgItemInt(hDlg, IDC_CHAR_HEROIC, ch->heroic_items, FALSE);
                        SetDlgItemInt(hDlg, IDC_CHAR_CHAMPION, ch->champion_items, FALSE);
                        SetDlgItemInt(hDlg, IDC_CHAR_VETERAN, ch->veteran_items, FALSE);
                        SetDlgItemInt(hDlg, IDC_CHAR_ADVENTURE, ch->adventure_items, FALSE);
                        SetDlgItemInt(hDlg, IDC_CHAR_OLD, ch->old_items, FALSE);

                        CheckDlgButton(hDlg, IDC_CHAR_VAULT, ch->vault_visited ? BST_CHECKED : BST_UNCHECKED);

                        SetDlgItemInt(hDlg, IDC_CHAR_DELVES, ch->delves, FALSE);
                        SetDlgItemInt(hDlg, IDC_CHAR_GILDED, ch->gilded_stash, FALSE);

                        CheckDlgButton(hDlg, IDC_CHAR_GEARINGUP, ch->gearing_up ? BST_CHECKED : BST_UNCHECKED);
                        CheckDlgButton(hDlg, IDC_CHAR_QUESTS, ch->quests ? BST_CHECKED : BST_UNCHECKED);

                        SetDlgItemInt(hDlg, IDC_CHAR_TIMEWALK, ch->timewalk, FALSE);
                        SetEditTextUtf8(hDlg, IDC_CHAR_NOTES, ch->notes);
                    }
                }
            }

            /* Center dialog */
            RECT rcOwner, rcDlg;
            HWND hOwner = GetParent(hDlg);
            GetWindowRect(hOwner, &rcOwner);
            GetWindowRect(hDlg, &rcDlg);
            int x = rcOwner.left + (rcOwner.right - rcOwner.left - (rcDlg.right - rcDlg.left)) / 2;
            int y = rcOwner.top + (rcOwner.bottom - rcOwner.top - (rcDlg.bottom - rcDlg.top)) / 2;
            SetWindowPos(hDlg, NULL, x, y, 0, 0, SWP_NOSIZE | SWP_NOZORDER);

            return TRUE;
        }

        case WM_COMMAND:
            switch (LOWORD(wParam)) {
                case IDOK: {
                    /* Validate required fields */
                    char *realm = GetEditTextUtf8(hDlg, IDC_CHAR_REALM);
                    char *name = GetEditTextUtf8(hDlg, IDC_CHAR_NAME);

                    if (!realm || realm[0] == '\0') {
                        MessageBoxW(hDlg, L"Realm is required.", L"Validation Error", MB_OK | MB_ICONWARNING);
                        free(realm);
                        free(name);
                        SetFocus(GetDlgItem(hDlg, IDC_CHAR_REALM));
                        return TRUE;
                    }

                    if (!name || name[0] == '\0') {
                        MessageBoxW(hDlg, L"Name is required.", L"Validation Error", MB_OK | MB_ICONWARNING);
                        free(realm);
                        free(name);
                        SetFocus(GetDlgItem(hDlg, IDC_CHAR_NAME));
                        return TRUE;
                    }

                    CharacterStore *store = GetCharacterStore();
                    Character *ch = NULL;
                    BOOL isNew = FALSE;

                    if (g_editCharIndex >= 0) {
                        ch = character_store_get(store, g_editCharIndex);
                    } else {
                        ch = character_new();
                        isNew = TRUE;
                    }

                    if (!ch) {
                        free(realm);
                        free(name);
                        EndDialog(hDlg, IDCANCEL);
                        return TRUE;
                    }

                    /* Update character fields */
                    character_set_realm(ch, realm);
                    character_set_name(ch, name);

                    char *guild = GetEditTextUtf8(hDlg, IDC_CHAR_GUILD);
                    character_set_guild(ch, guild);
                    free(guild);

                    /* Get item level */
                    wchar_t ilvlBuf[32];
                    GetDlgItemTextW(hDlg, IDC_CHAR_ITEMLEVEL, ilvlBuf, 32);
                    ch->item_level = _wtof(ilvlBuf);

                    ch->heroic_items = GetDlgItemInt(hDlg, IDC_CHAR_HEROIC, NULL, FALSE);
                    ch->champion_items = GetDlgItemInt(hDlg, IDC_CHAR_CHAMPION, NULL, FALSE);
                    ch->veteran_items = GetDlgItemInt(hDlg, IDC_CHAR_VETERAN, NULL, FALSE);
                    ch->adventure_items = GetDlgItemInt(hDlg, IDC_CHAR_ADVENTURE, NULL, FALSE);
                    ch->old_items = GetDlgItemInt(hDlg, IDC_CHAR_OLD, NULL, FALSE);

                    ch->vault_visited = IsDlgButtonChecked(hDlg, IDC_CHAR_VAULT) == BST_CHECKED;

                    ch->delves = GetDlgItemInt(hDlg, IDC_CHAR_DELVES, NULL, FALSE);
                    if (ch->delves > 8) ch->delves = 8;

                    ch->gilded_stash = GetDlgItemInt(hDlg, IDC_CHAR_GILDED, NULL, FALSE);
                    if (ch->gilded_stash > 3) ch->gilded_stash = 3;

                    ch->gearing_up = IsDlgButtonChecked(hDlg, IDC_CHAR_GEARINGUP) == BST_CHECKED;
                    ch->quests = IsDlgButtonChecked(hDlg, IDC_CHAR_QUESTS) == BST_CHECKED;

                    ch->timewalk = GetDlgItemInt(hDlg, IDC_CHAR_TIMEWALK, NULL, FALSE);
                    if (ch->timewalk > 5) ch->timewalk = 5;

                    char *notes = GetEditTextUtf8(hDlg, IDC_CHAR_NOTES);
                    character_set_notes(ch, notes);
                    free(notes);

                    free(realm);
                    free(name);

                    if (isNew) {
                        character_store_add(store, ch);
                    }

                    character_store_save(store);
                    RefreshCharacterList();

                    EndDialog(hDlg, IDOK);
                    return TRUE;
                }

                case IDCANCEL:
                    EndDialog(hDlg, IDCANCEL);
                    return TRUE;

                case IDC_CHAR_DELETE: {
                    int result = MessageBoxW(hDlg,
                        L"Are you sure you want to delete this character?",
                        L"Delete Character",
                        MB_YESNO | MB_ICONQUESTION);

                    if (result == IDYES && g_editCharIndex >= 0) {
                        CharacterStore *store = GetCharacterStore();
                        if (store) {
                            character_store_delete(store, (size_t)g_editCharIndex);
                            character_store_save(store);
                            RefreshCharacterList();
                        }
                        EndDialog(hDlg, IDOK);
                    }
                    return TRUE;
                }
            }
            break;
    }

    return FALSE;
}

/* Show preferences dialog */
void ShowPreferencesDialog(HWND hWnd) {
    DialogBoxW(GetAppInstance(), MAKEINTRESOURCEW(IDD_PREFERENCES), hWnd, PreferencesDlgProc);
}

/* Preferences dialog procedure */
static INT_PTR CALLBACK PreferencesDlgProc(HWND hDlg, UINT uMsg, WPARAM wParam, LPARAM lParam) {
    (void)lParam;

    switch (uMsg) {
        case WM_INITDIALOG: {
            Config *cfg = GetConfig();
            if (cfg) {
                /* WoW path */
                const char *wowPath = config_get_string(cfg, "wow_path", "");
                SetEditTextUtf8(hDlg, IDC_PREF_WOWPATH, wowPath);

                /* Theme dropdown */
                HWND hTheme = GetDlgItem(hDlg, IDC_PREF_THEME);
                ComboBox_AddString(hTheme, L"Auto (System)");
                ComboBox_AddString(hTheme, L"Light");
                ComboBox_AddString(hTheme, L"Dark");

                const char *theme = config_get_string(cfg, "theme", "auto");
                int sel = 0;
                if (strcmp(theme, "light") == 0) sel = 1;
                else if (strcmp(theme, "dark") == 0) sel = 2;
                ComboBox_SetCurSel(hTheme, sel);

                /* Checkboxes */
                CheckDlgButton(hDlg, IDC_PREF_AUTOIMPORT,
                    config_get_bool(cfg, "auto_import", FALSE) ? BST_CHECKED : BST_UNCHECKED);
                CheckDlgButton(hDlg, IDC_PREF_CHECKUPDATES,
                    config_get_bool(cfg, "check_updates", TRUE) ? BST_CHECKED : BST_UNCHECKED);
            }

            /* Center dialog */
            RECT rcOwner, rcDlg;
            HWND hOwner = GetParent(hDlg);
            GetWindowRect(hOwner, &rcOwner);
            GetWindowRect(hDlg, &rcDlg);
            int x = rcOwner.left + (rcOwner.right - rcOwner.left - (rcDlg.right - rcDlg.left)) / 2;
            int y = rcOwner.top + (rcOwner.bottom - rcOwner.top - (rcDlg.bottom - rcDlg.top)) / 2;
            SetWindowPos(hDlg, NULL, x, y, 0, 0, SWP_NOSIZE | SWP_NOZORDER);

            return TRUE;
        }

        case WM_COMMAND:
            switch (LOWORD(wParam)) {
                case IDC_PREF_BROWSE: {
                    BROWSEINFOW bi = {
                        .hwndOwner = hDlg,
                        .lpszTitle = L"Select World of Warcraft Installation Folder",
                        .ulFlags = BIF_RETURNONLYFSDIRS | BIF_NEWDIALOGSTYLE,
                    };
                    LPITEMIDLIST pidl = SHBrowseForFolderW(&bi);
                    if (pidl) {
                        wchar_t path[MAX_PATH];
                        if (SHGetPathFromIDListW(pidl, path)) {
                            SetDlgItemTextW(hDlg, IDC_PREF_WOWPATH, path);
                        }
                        CoTaskMemFree(pidl);
                    }
                    return TRUE;
                }

                case IDOK: {
                    Config *cfg = GetConfig();
                    if (cfg) {
                        /* Save WoW path */
                        char *wowPath = GetEditTextUtf8(hDlg, IDC_PREF_WOWPATH);
                        config_set_string(cfg, "wow_path", wowPath ? wowPath : "");
                        free(wowPath);

                        /* Save theme */
                        HWND hTheme = GetDlgItem(hDlg, IDC_PREF_THEME);
                        int sel = ComboBox_GetCurSel(hTheme);
                        const char *theme = "auto";
                        if (sel == 1) theme = "light";
                        else if (sel == 2) theme = "dark";
                        config_set_string(cfg, "theme", theme);

                        /* Save checkboxes */
                        config_set_bool(cfg, "auto_import",
                            IsDlgButtonChecked(hDlg, IDC_PREF_AUTOIMPORT) == BST_CHECKED);
                        config_set_bool(cfg, "check_updates",
                            IsDlgButtonChecked(hDlg, IDC_PREF_CHECKUPDATES) == BST_CHECKED);

                        config_save(cfg);

                        /* Apply theme */
                        HWND hMain = GetMainWindowHandle();
                        if (hMain) {
                            BOOL dark = ShouldUseDarkMode();
                            ApplyTheme(hMain, dark);
                        }
                    }

                    EndDialog(hDlg, IDOK);
                    return TRUE;
                }

                case IDCANCEL:
                    EndDialog(hDlg, IDCANCEL);
                    return TRUE;
            }
            break;
    }

    return FALSE;
}

/* User manual content */
static const char *g_manualText =
"WoW Stat Tracker - User Manual\n"
"==============================\n\n"
"OVERVIEW\n"
"--------\n"
"WoW Stat Tracker helps you track weekly progress and gear statistics\n"
"for all your World of Warcraft characters in one place.\n\n"
"GETTING STARTED\n"
"---------------\n"
"1. Install the in-game addon:\n"
"   - Use Addon > Install Addon to copy the addon to your WoW folder\n"
"   - Restart WoW or type /reload in-game\n\n"
"2. Set your WoW installation path:\n"
"   - Go to File > Properties\n"
"   - Browse to your WoW installation folder\n\n"
"3. Export data from the game:\n"
"   - Log into each character you want to track\n"
"   - Type /wst update in the chat\n"
"   - Type /reload to save the data\n\n"
"4. Import into the tracker:\n"
"   - Click Addon > Import from Addon (Ctrl+I)\n\n"
"WEEKLY TRACKING\n"
"---------------\n"
"The following progress resets weekly (Tuesday 15:00 UTC):\n"
"- Vault visited status\n"
"- Delves completed (0-8)\n"
"- Gilded stash opened (0-3)\n"
"- Gearing Up quest\n"
"- World Quests\n"
"- Timewalking dungeons (0-5)\n\n"
"The app automatically resets these when a new week begins.\n\n"
"CELL COLORS\n"
"-----------\n"
"- Green: Complete/optimal progress\n"
"- Yellow: Partial progress\n"
"- Red/Default: Not started or needs attention\n\n"
"KEYBOARD SHORTCUTS\n"
"------------------\n"
"Ctrl+N - Add new character\n"
"Ctrl+I - Import from addon\n"
"Double-click - Edit character\n"
"Delete - Delete selected character (in edit dialog)\n";

/* Show manual dialog */
void ShowManualDialog(HWND hWnd) {
    DialogBoxW(GetAppInstance(), MAKEINTRESOURCEW(IDD_MANUAL), hWnd, ManualDlgProc);
}

/* Manual dialog procedure */
static INT_PTR CALLBACK ManualDlgProc(HWND hDlg, UINT uMsg, WPARAM wParam, LPARAM lParam) {
    (void)lParam;

    switch (uMsg) {
        case WM_INITDIALOG: {
            /* Convert \n to \r\n for Windows edit control */
            HWND hEdit = GetDlgItem(hDlg, IDC_CHAR_NOTES);
            size_t srcLen = strlen(g_manualText);
            size_t newlines = 0;
            for (size_t i = 0; i < srcLen; i++) {
                if (g_manualText[i] == '\n') newlines++;
            }

            char *converted = malloc(srcLen + newlines + 1);
            if (converted) {
                size_t j = 0;
                for (size_t i = 0; i < srcLen; i++) {
                    if (g_manualText[i] == '\n') {
                        converted[j++] = '\r';
                    }
                    converted[j++] = g_manualText[i];
                }
                converted[j] = '\0';

                int wlen = MultiByteToWideChar(CP_UTF8, 0, converted, -1, NULL, 0);
                wchar_t *wtext = malloc(wlen * sizeof(wchar_t));
                if (wtext) {
                    MultiByteToWideChar(CP_UTF8, 0, converted, -1, wtext, wlen);
                    SetWindowTextW(hEdit, wtext);
                    free(wtext);
                }
                free(converted);
            }

            /* Deselect text and scroll to top */
            SendMessage(hEdit, EM_SETSEL, 0, 0);
            SendMessage(hEdit, EM_SCROLLCARET, 0, 0);

            /* Center dialog */
            RECT rcOwner, rcDlg;
            HWND hOwner = GetParent(hDlg);
            GetWindowRect(hOwner, &rcOwner);
            GetWindowRect(hDlg, &rcDlg);
            int x = rcOwner.left + (rcOwner.right - rcOwner.left - (rcDlg.right - rcDlg.left)) / 2;
            int y = rcOwner.top + (rcOwner.bottom - rcOwner.top - (rcDlg.bottom - rcDlg.top)) / 2;
            SetWindowPos(hDlg, NULL, x, y, 0, 0, SWP_NOSIZE | SWP_NOZORDER);

            /* Set focus to Close button instead of edit control */
            SetFocus(GetDlgItem(hDlg, IDCANCEL));
            return FALSE;  /* FALSE because we set focus ourselves */
        }

        case WM_COMMAND:
            if (LOWORD(wParam) == IDCANCEL) {
                EndDialog(hDlg, IDCANCEL);
                return TRUE;
            }
            break;

        case WM_SIZE: {
            /* Resize edit control to fit */
            RECT rcClient;
            GetClientRect(hDlg, &rcClient);

            HWND hEdit = GetDlgItem(hDlg, IDC_CHAR_NOTES);
            HWND hClose = GetDlgItem(hDlg, IDCANCEL);

            RECT rcClose;
            GetWindowRect(hClose, &rcClose);
            int closeHeight = rcClose.bottom - rcClose.top;

            SetWindowPos(hEdit, NULL, 5, 5,
                         rcClient.right - 10,
                         rcClient.bottom - closeHeight - 20,
                         SWP_NOZORDER);

            SetWindowPos(hClose, NULL,
                         rcClient.right - 60,
                         rcClient.bottom - closeHeight - 5,
                         0, 0,
                         SWP_NOSIZE | SWP_NOZORDER);
            break;
        }
    }

    return FALSE;
}

/* Helper to parse version from GitHub release tag (e.g., "v1.2.3" -> major, minor, patch) */
static BOOL ParseVersion(const char *tag, int *major, int *minor, int *patch) {
    if (!tag) return FALSE;

    /* Skip leading 'v' if present */
    if (*tag == 'v' || *tag == 'V') tag++;

    if (sscanf(tag, "%d.%d.%d", major, minor, patch) == 3) {
        return TRUE;
    }
    return FALSE;
}

/* Compare versions: returns 1 if a > b, -1 if a < b, 0 if equal */
static int CompareVersions(int a_major, int a_minor, int a_patch,
                           int b_major, int b_minor, int b_patch) {
    if (a_major != b_major) return (a_major > b_major) ? 1 : -1;
    if (a_minor != b_minor) return (a_minor > b_minor) ? 1 : -1;
    if (a_patch != b_patch) return (a_patch > b_patch) ? 1 : -1;
    return 0;
}

/* Check for updates from GitHub releases */
void CheckForUpdates(HWND hWnd, BOOL showIfCurrent) {
    ShowStatusMessage(L"Checking for updates...", WST_NOTIFY_INFO);

    /* Fetch latest release info from GitHub API */
    const char *url = "https://api.github.com/repos/erikg/WoWStatTracker/releases/latest";
    char *response = platform_http_get(url);

    if (!response) {
        ShowStatusMessage(L"Failed to check for updates. Check your internet connection.", WST_NOTIFY_WARNING);
        return;
    }

    /* Parse the tag_name from JSON response */
    /* Simple parsing - look for "tag_name": "vX.Y.Z" */
    char *tagStart = strstr(response, "\"tag_name\"");
    if (!tagStart) {
        free(response);
        ShowStatusMessage(L"Failed to parse update information.", WST_NOTIFY_WARNING);
        return;
    }

    /* Find the version string */
    tagStart = strchr(tagStart, ':');
    if (!tagStart) {
        free(response);
        ShowStatusMessage(L"Failed to parse update information.", WST_NOTIFY_WARNING);
        return;
    }

    /* Skip to opening quote */
    tagStart = strchr(tagStart, '"');
    if (!tagStart) {
        free(response);
        ShowStatusMessage(L"Failed to parse update information.", WST_NOTIFY_WARNING);
        return;
    }
    tagStart++; /* Skip the quote */

    /* Find closing quote */
    char *tagEnd = strchr(tagStart, '"');
    if (!tagEnd) {
        free(response);
        ShowStatusMessage(L"Failed to parse update information.", WST_NOTIFY_WARNING);
        return;
    }

    /* Extract version tag */
    size_t tagLen = tagEnd - tagStart;
    char *tag = malloc(tagLen + 1);
    if (!tag) {
        free(response);
        return;
    }
    memcpy(tag, tagStart, tagLen);
    tag[tagLen] = '\0';

    /* Parse remote version */
    int remoteMajor, remoteMinor, remotePatch;
    if (!ParseVersion(tag, &remoteMajor, &remoteMinor, &remotePatch)) {
        free(tag);
        free(response);
        ShowStatusMessage(L"Failed to parse version number.", WST_NOTIFY_WARNING);
        return;
    }

    /* Compare with current version */
    int cmp = CompareVersions(remoteMajor, remoteMinor, remotePatch,
                              WST_VERSION_MAJOR, WST_VERSION_MINOR, WST_VERSION_PATCH);

    if (cmp > 0) {
        /* Newer version available */
        wchar_t msg[256];
        swprintf(msg, 256, L"Update available: v%d.%d.%d (current: v%d.%d.%d)",
                 remoteMajor, remoteMinor, remotePatch,
                 WST_VERSION_MAJOR, WST_VERSION_MINOR, WST_VERSION_PATCH);
        ShowStatusMessage(msg, WST_NOTIFY_WARNING);

        /* Ask user if they want to download */
        wchar_t dlgMsg[512];
        swprintf(dlgMsg, 512,
            L"A new version is available!\n\n"
            L"Current version: v%d.%d.%d\n"
            L"Latest version: v%d.%d.%d\n\n"
            L"Would you like to open the download page?",
            WST_VERSION_MAJOR, WST_VERSION_MINOR, WST_VERSION_PATCH,
            remoteMajor, remoteMinor, remotePatch);

        int result = MessageBoxW(hWnd, dlgMsg, L"Update Available",
                                 MB_YESNO | MB_ICONINFORMATION);
        if (result == IDYES) {
            platform_open_url("https://github.com/erikg/WoWStatTracker/releases/latest");
        }
    } else if (showIfCurrent) {
        /* Already up to date - only show if explicitly requested */
        wchar_t msg[128];
        swprintf(msg, 128, L"You're running the latest version (v%d.%d.%d).",
                 WST_VERSION_MAJOR, WST_VERSION_MINOR, WST_VERSION_PATCH);
        ShowStatusMessage(msg, WST_NOTIFY_SUCCESS);
    }

    free(tag);
    free(response);
}

/* Helper to format timestamp for display */
static void FormatTimestamp(const char *iso, wchar_t *out, size_t outLen) {
    /* Parse ISO format: 2024-12-31T14:30:00 */
    int year, month, day, hour, min;
    if (sscanf(iso, "%d-%d-%dT%d:%d", &year, &month, &day, &hour, &min) == 5) {
        const wchar_t *months[] = {
            L"Jan", L"Feb", L"Mar", L"Apr", L"May", L"Jun",
            L"Jul", L"Aug", L"Sep", L"Oct", L"Nov", L"Dec"
        };
        if (month >= 1 && month <= 12) {
            swprintf(out, outLen, L"%s %d, %02d:%02d", months[month-1], day, hour, min);
            return;
        }
    }
    /* Fallback */
    MultiByteToWideChar(CP_UTF8, 0, iso, -1, out, (int)outLen);
}

/* Helper to populate notifications listbox */
static void PopulateNotificationsList(HWND hList) {
    SendMessage(hList, LB_RESETCONTENT, 0, 0);

    NotificationStore *ns = GetNotificationStore();
    if (!ns) return;

    size_t count = notification_store_count(ns);
    if (count == 0) {
        int idx = (int)SendMessageW(hList, LB_ADDSTRING, 0, (LPARAM)L"No notifications.");
        SendMessage(hList, LB_SETITEMDATA, idx, (LPARAM)-1);  /* -1 = no valid notification */
        return;
    }

    /* Add notifications (newest first) */
    for (size_t i = count; i > 0; i--) {
        Notification *n = notification_store_get(ns, i - 1);
        if (n && n->message) {
            const wchar_t *icon = L"";
            switch (n->type) {
                case WST_NOTIFY_SUCCESS: icon = L"\u2714"; break;  /* checkmark */
                case WST_NOTIFY_WARNING: icon = L"\u26A0"; break;  /* warning */
                case WST_NOTIFY_INFO:
                default: icon = L"\u2139"; break;  /* info */
            }

            /* Format timestamp */
            wchar_t timeStr[32] = L"";
            if (n->timestamp) {
                FormatTimestamp(n->timestamp, timeStr, 32);
            }

            /* Convert message to wide */
            int msgLen = MultiByteToWideChar(CP_UTF8, 0, n->message, -1, NULL, 0);
            wchar_t *msgW = malloc(msgLen * sizeof(wchar_t));
            if (msgW) {
                MultiByteToWideChar(CP_UTF8, 0, n->message, -1, msgW, msgLen);

                /* Format: "[icon] [time] message" */
                size_t lineLen = wcslen(icon) + wcslen(timeStr) + msgLen + 10;
                wchar_t *line = malloc(lineLen * sizeof(wchar_t));
                if (line) {
                    swprintf(line, lineLen, L"%s  %s  %s", icon, timeStr, msgW);
                    int idx = (int)SendMessageW(hList, LB_ADDSTRING, 0, (LPARAM)line);
                    /* Store index into notifications array as item data */
                    SendMessage(hList, LB_SETITEMDATA, idx, (LPARAM)(i - 1));
                    free(line);
                }
                free(msgW);
            }
        }
    }
}

/* Notifications dialog procedure */
static INT_PTR CALLBACK NotificationsDlgProc(HWND hDlg, UINT uMsg, WPARAM wParam, LPARAM lParam) {
    (void)lParam;

    switch (uMsg) {
        case WM_INITDIALOG: {
            /* Populate listbox */
            HWND hList = GetDlgItem(hDlg, IDC_NOTIF_LIST);
            PopulateNotificationsList(hList);

            /* Center dialog */
            RECT rcOwner, rcDlg;
            HWND hOwner = GetParent(hDlg);
            GetWindowRect(hOwner, &rcOwner);
            GetWindowRect(hDlg, &rcDlg);
            int x = rcOwner.left + (rcOwner.right - rcOwner.left - (rcDlg.right - rcDlg.left)) / 2;
            int y = rcOwner.top + (rcOwner.bottom - rcOwner.top - (rcDlg.bottom - rcDlg.top)) / 2;
            SetWindowPos(hDlg, NULL, x, y, 0, 0, SWP_NOSIZE | SWP_NOZORDER);

            return TRUE;
        }

        case WM_COMMAND:
            switch (LOWORD(wParam)) {
                case IDCANCEL:
                    EndDialog(hDlg, IDCANCEL);
                    return TRUE;

                case IDC_NOTIF_DELETE: {
                    HWND hList = GetDlgItem(hDlg, IDC_NOTIF_LIST);
                    int sel = (int)SendMessage(hList, LB_GETCURSEL, 0, 0);
                    if (sel != LB_ERR) {
                        LRESULT data = SendMessage(hList, LB_GETITEMDATA, sel, 0);
                        if (data != LB_ERR && data != -1) {  /* -1 = "No notifications" placeholder */
                            NotificationStore *ns = GetNotificationStore();
                            if (ns) {
                                size_t idx = (size_t)data;
                                Notification *n = notification_store_get(ns, idx);
                                if (n && n->id) {
                                    notification_store_remove(ns, n->id);
                                    notification_store_save(ns);
                                    PopulateNotificationsList(hList);
                                }
                            }
                        }
                    }
                    return TRUE;
                }

                case IDC_NOTIF_CLEAR: {
                    NotificationStore *ns = GetNotificationStore();
                    if (ns) {
                        notification_store_clear_all(ns);
                        notification_store_save(ns);
                        PopulateNotificationsList(GetDlgItem(hDlg, IDC_NOTIF_LIST));
                    }
                    return TRUE;
                }
            }
            break;

        case WM_SIZE: {
            /* Resize listbox to fit */
            RECT rcClient;
            GetClientRect(hDlg, &rcClient);

            HWND hList = GetDlgItem(hDlg, IDC_NOTIF_LIST);
            HWND hDelete = GetDlgItem(hDlg, IDC_NOTIF_DELETE);
            HWND hClear = GetDlgItem(hDlg, IDC_NOTIF_CLEAR);
            HWND hClose = GetDlgItem(hDlg, IDCANCEL);

            RECT rcBtn;
            GetWindowRect(hClose, &rcBtn);
            int btnHeight = rcBtn.bottom - rcBtn.top;
            int btnWidth = rcBtn.right - rcBtn.left;

            SetWindowPos(hList, NULL, 5, 5,
                         rcClient.right - 10,
                         rcClient.bottom - btnHeight - 20,
                         SWP_NOZORDER);

            SetWindowPos(hDelete, NULL,
                         5,
                         rcClient.bottom - btnHeight - 5,
                         0, 0,
                         SWP_NOSIZE | SWP_NOZORDER);

            SetWindowPos(hClear, NULL,
                         5 + btnWidth + 5,
                         rcClient.bottom - btnHeight - 5,
                         0, 0,
                         SWP_NOSIZE | SWP_NOZORDER);

            SetWindowPos(hClose, NULL,
                         rcClient.right - btnWidth - 5,
                         rcClient.bottom - btnHeight - 5,
                         0, 0,
                         SWP_NOSIZE | SWP_NOZORDER);
            break;
        }
    }

    return FALSE;
}

/* Show notifications dialog */
void ShowNotificationsDialog(HWND hWnd) {
    DialogBoxW(GetAppInstance(), MAKEINTRESOURCEW(IDD_NOTIFICATIONS), hWnd, NotificationsDlgProc);
}

/* About dialog procedure */
static INT_PTR CALLBACK AboutDlgProc(HWND hDlg, UINT uMsg, WPARAM wParam, LPARAM lParam) {
    switch (uMsg) {
        case WM_INITDIALOG: {
            /* Set version string */
            wchar_t version[64];
            swprintf(version, 64, L"Version %d.%d.%d",
                     WST_VERSION_MAJOR, WST_VERSION_MINOR, WST_VERSION_PATCH);
            SetDlgItemTextW(hDlg, IDC_ABOUT_VERSION, version);

            /* Center dialog */
            RECT rcOwner, rcDlg;
            HWND hOwner = GetParent(hDlg);
            GetWindowRect(hOwner, &rcOwner);
            GetWindowRect(hDlg, &rcDlg);
            int x = rcOwner.left + (rcOwner.right - rcOwner.left - (rcDlg.right - rcDlg.left)) / 2;
            int y = rcOwner.top + (rcOwner.bottom - rcOwner.top - (rcDlg.bottom - rcDlg.top)) / 2;
            SetWindowPos(hDlg, NULL, x, y, 0, 0, SWP_NOSIZE | SWP_NOZORDER);

            return TRUE;
        }

        case WM_NOTIFY: {
            NMHDR *nmhdr = (NMHDR *)lParam;
            if (nmhdr->code == NM_CLICK || nmhdr->code == NM_RETURN) {
                /* SysLink was clicked */
                PNMLINK pnmLink = (PNMLINK)lParam;
                if (pnmLink->item.szUrl[0] != L'\0') {
                    /* Convert wide URL to UTF-8 */
                    char url[512];
                    WideCharToMultiByte(CP_UTF8, 0, pnmLink->item.szUrl, -1, url, 512, NULL, NULL);
                    platform_open_url(url);
                }
            }
            break;
        }

        case WM_COMMAND:
            if (LOWORD(wParam) == IDOK || LOWORD(wParam) == IDCANCEL) {
                EndDialog(hDlg, LOWORD(wParam));
                return TRUE;
            }
            break;
    }

    return FALSE;
}

/* Show about dialog */
void ShowAboutDialog(HWND hWnd) {
    DialogBoxW(GetAppInstance(), MAKEINTRESOURCEW(IDD_ABOUT), hWnd, AboutDlgProc);
}
