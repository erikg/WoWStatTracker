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

/* Forward declarations for external app state */
extern CharacterStore* GetCharacterStore(void);
extern Config* GetConfig(void);
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
                            character_store_remove(store, g_editCharIndex);
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
            /* Set manual text */
            HWND hEdit = GetDlgItem(hDlg, IDC_CHAR_NOTES);
            int wlen = MultiByteToWideChar(CP_UTF8, 0, g_manualText, -1, NULL, 0);
            wchar_t *wtext = malloc(wlen * sizeof(wchar_t));
            if (wtext) {
                MultiByteToWideChar(CP_UTF8, 0, g_manualText, -1, wtext, wlen);
                SetWindowTextW(hEdit, wtext);
                free(wtext);
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
