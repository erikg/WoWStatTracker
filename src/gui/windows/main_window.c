/*
 * WoW Stat Tracker - Windows Main Window Implementation
 * BSD 3-Clause License
 */

#define WIN32_LEAN_AND_MEAN
#define UNICODE
#define _UNICODE

#include <windows.h>
#include <windowsx.h>
#include <commctrl.h>
#include <dwmapi.h>
#include <shlobj.h>
#include <stdio.h>
#include <stdlib.h>

#include "main_window.h"
#include "resource.h"
#include "character.h"
#include "character_store.h"
#include "config.h"
#include "notification.h"
#include "lua_parser.h"
#include "paths.h"
#include "platform.h"
#include "week_id.h"
#include "version.h"

/* Forward declarations for external app state */
extern CharacterStore* GetCharacterStore(void);
extern Config* GetConfig(void);
extern NotificationStore* GetNotificationStore(void);
extern HINSTANCE GetAppInstance(void);

/* Forward declarations for static functions */
static BOOL DoAddonInstall(HWND hWnd);
static BOOL DoAddonUninstall(HWND hWnd);

/* Window class name */
static const wchar_t CLASS_NAME[] = L"WoWStatTrackerMain";

/* Global handles */
static HWND g_hMainWindow = NULL;
static HWND g_hListView = NULL;
static HWND g_hToolbar = NULL;
static HWND g_hStatusBar = NULL;

/* Status message timer */
#define STATUS_TIMEOUT_MS 8000

/* Column definitions */
typedef struct {
    const wchar_t *title;
    int width;
    int format;
} ColumnDef;

static const ColumnDef g_columns[] = {
    { L"Realm",       100, LVCFMT_LEFT },
    { L"Name",        100, LVCFMT_LEFT },
    { L"Guild",        80, LVCFMT_LEFT },
    { L"iLvl",         50, LVCFMT_RIGHT },
    { L"Heroic",       50, LVCFMT_RIGHT },
    { L"Champion",     60, LVCFMT_RIGHT },
    { L"Veteran",      55, LVCFMT_RIGHT },
    { L"Adventure",    65, LVCFMT_RIGHT },
    { L"Old",          40, LVCFMT_RIGHT },
    { L"Vault",        45, LVCFMT_CENTER },
    { L"Delves",       50, LVCFMT_RIGHT },
    { L"Gilded",       50, LVCFMT_RIGHT },
    { L"Gearing",      55, LVCFMT_CENTER },
    { L"Quests",       50, LVCFMT_CENTER },
    { L"Timewalk",     60, LVCFMT_RIGHT },
    { L"Notes",       120, LVCFMT_LEFT },
};
static const int g_numColumns = sizeof(g_columns) / sizeof(g_columns[0]);

/* Sorting state */
static int g_sortColumn = 0;
static BOOL g_sortAscending = TRUE;

/* Dark mode state */
static BOOL g_darkMode = FALSE;

/* Dark mode colors */
#define DARK_BG_COLOR       RGB(32, 32, 32)
#define DARK_TEXT_COLOR     RGB(230, 230, 230)
#define DARK_HEADER_BG      RGB(45, 45, 45)

/* Forward declarations */
static LRESULT CALLBACK MainWndProc(HWND hWnd, UINT uMsg, WPARAM wParam, LPARAM lParam);
static BOOL OnCreate(HWND hWnd, LPCREATESTRUCT lpcs);
static void OnSize(HWND hWnd, UINT state, int cx, int cy);
static void OnDestroy(HWND hWnd);
static void OnCommand(HWND hWnd, int id, HWND hWndCtl, UINT codeNotify);
static LRESULT OnNotify(HWND hWnd, int idCtrl, LPNMHDR pnmh);
static void OnTimer(HWND hWnd, UINT id);
static void OnActivate(HWND hWnd, UINT state, HWND hWndActDeact, BOOL fMinimized);
static void CreateListView(HWND hWnd);
static void CreateToolbar(HWND hWnd);
static void CreateStatusBar(HWND hWnd);
static void SetupMenu(HWND hWnd);
static void LoadWindowState(HWND hWnd);
static void SaveWindowState(HWND hWnd);
static void HandleColumnClick(HWND hWnd, int column);
static void SortListView(void);
static int CALLBACK CompareFunc(LPARAM lParam1, LPARAM lParam2, LPARAM lParamSort);
static void HandleListViewCustomDraw(LPNMLVCUSTOMDRAW pcd, LRESULT *pResult);

/* Register window class */
static BOOL RegisterMainWindowClass(HINSTANCE hInstance) {
    HICON hIcon = LoadIconW(hInstance, MAKEINTRESOURCEW(IDI_APPICON));
    if (!hIcon) {
        hIcon = LoadIconW(NULL, IDI_APPLICATION);
    }

    WNDCLASSEXW wc = {
        .cbSize = sizeof(WNDCLASSEXW),
        .style = CS_HREDRAW | CS_VREDRAW,
        .lpfnWndProc = MainWndProc,
        .cbClsExtra = 0,
        .cbWndExtra = 0,
        .hInstance = hInstance,
        .hIcon = hIcon,
        .hCursor = LoadCursorW(NULL, IDC_ARROW),
        .hbrBackground = (HBRUSH)(COLOR_WINDOW + 1),
        .lpszMenuName = MAKEINTRESOURCEW(IDM_MAINMENU),
        .lpszClassName = CLASS_NAME,
        .hIconSm = hIcon,
    };
    return RegisterClassExW(&wc) != 0;
}

/* Create main window */
HWND CreateMainWindow(HINSTANCE hInstance, int nCmdShow) {
    /* Register window class */
    if (!RegisterMainWindowClass(hInstance)) {
        return NULL;
    }

    /* Create window */
    g_hMainWindow = CreateWindowExW(
        0,
        CLASS_NAME,
        L"WoW Stat Tracker",
        WS_OVERLAPPEDWINDOW,
        CW_USEDEFAULT, CW_USEDEFAULT,
        1000, 600,
        NULL,
        NULL,
        hInstance,
        NULL
    );

    if (!g_hMainWindow) {
        return NULL;
    }

    /* Load window state from config */
    LoadWindowState(g_hMainWindow);

    /* Show window */
    ShowWindow(g_hMainWindow, nCmdShow);
    UpdateWindow(g_hMainWindow);

    return g_hMainWindow;
}

/* Main window procedure */
static LRESULT CALLBACK MainWndProc(HWND hWnd, UINT uMsg, WPARAM wParam, LPARAM lParam) {
    switch (uMsg) {
        HANDLE_MSG(hWnd, WM_CREATE, OnCreate);
        HANDLE_MSG(hWnd, WM_SIZE, OnSize);
        HANDLE_MSG(hWnd, WM_DESTROY, OnDestroy);
        HANDLE_MSG(hWnd, WM_COMMAND, OnCommand);
        HANDLE_MSG(hWnd, WM_TIMER, OnTimer);
        HANDLE_MSG(hWnd, WM_ACTIVATE, OnActivate);

        case WM_NOTIFY: {
            LPNMHDR pnmh = (LPNMHDR)lParam;
            return OnNotify(hWnd, (int)wParam, pnmh);
        }

        case WM_GETMINMAXINFO: {
            LPMINMAXINFO mmi = (LPMINMAXINFO)lParam;
            mmi->ptMinTrackSize.x = 800;
            mmi->ptMinTrackSize.y = 400;
            return 0;
        }

        default:
            return DefWindowProcW(hWnd, uMsg, wParam, lParam);
    }
}

/* WM_CREATE handler */
static BOOL OnCreate(HWND hWnd, LPCREATESTRUCT lpcs) {
    (void)lpcs;

    /* Create child controls */
    CreateToolbar(hWnd);
    CreateListView(hWnd);
    CreateStatusBar(hWnd);

    /* Setup menu */
    SetupMenu(hWnd);

    /* Apply theme */
    g_darkMode = ShouldUseDarkMode();
    ApplyTheme(hWnd, g_darkMode);

    /* Load characters */
    RefreshCharacterList();

    return TRUE;
}

/* WM_SIZE handler */
static void OnSize(HWND hWnd, UINT state, int cx, int cy) {
    (void)hWnd;
    (void)state;

    if (!g_hListView || !g_hToolbar || !g_hStatusBar) return;

    /* Resize toolbar */
    SendMessageW(g_hToolbar, TB_AUTOSIZE, 0, 0);

    /* Get toolbar height */
    RECT rcToolbar;
    GetWindowRect(g_hToolbar, &rcToolbar);
    int toolbarHeight = rcToolbar.bottom - rcToolbar.top;

    /* Resize status bar */
    SendMessageW(g_hStatusBar, WM_SIZE, 0, 0);

    /* Get status bar height */
    RECT rcStatus;
    GetWindowRect(g_hStatusBar, &rcStatus);
    int statusHeight = rcStatus.bottom - rcStatus.top;

    /* Resize ListView to fill remaining space */
    int listHeight = cy - toolbarHeight - statusHeight;
    if (listHeight < 0) listHeight = 0;

    SetWindowPos(g_hListView, NULL, 0, toolbarHeight, cx, listHeight,
                 SWP_NOZORDER);
}

/* WM_DESTROY handler */
static void OnDestroy(HWND hWnd) {
    SaveWindowState(hWnd);
    PostQuitMessage(0);
}

/* WM_COMMAND handler */
static void OnCommand(HWND hWnd, int id, HWND hWndCtl, UINT codeNotify) {
    (void)hWndCtl;
    (void)codeNotify;

    switch (id) {
        /* File menu */
        case IDM_FILE_PROPERTIES:
            ShowPreferencesDialog(hWnd);
            break;

        case IDM_FILE_EXIT:
            DestroyWindow(hWnd);
            break;

        /* Character menu */
        case IDM_CHAR_ADD:
        case IDT_ADD:
            ShowCharacterDialog(hWnd, -1);
            break;

        case IDM_CHAR_RESET_WEEKLY:
        case IDT_RESET: {
            int result = MessageBoxW(hWnd,
                L"Reset all weekly progress data for all characters?\n\n"
                L"This will clear:\n"
                L"- Vault visited status\n"
                L"- Delves count\n"
                L"- Gilded stash count\n"
                L"- Gearing Up quest\n"
                L"- World Quests\n"
                L"- Timewalking progress",
                L"Reset Weekly Data",
                MB_YESNO | MB_ICONQUESTION);

            if (result == IDYES) {
                CharacterStore *store = GetCharacterStore();
                if (store) {
                    character_store_reset_weekly_all(store);
                    character_store_save(store);
                    RefreshCharacterList();
                    ShowStatusMessage(L"Weekly data reset for all characters.", WST_NOTIFY_SUCCESS);
                }
            }
            break;
        }

        /* Addon menu */
        case IDM_ADDON_IMPORT:
        case IDT_IMPORT:
            DoAddonImport(hWnd);
            break;

        case IDM_ADDON_SET_PATH: {
            BROWSEINFOW bi = {
                .hwndOwner = hWnd,
                .lpszTitle = L"Select World of Warcraft Installation Folder",
                .ulFlags = BIF_RETURNONLYFSDIRS | BIF_NEWDIALOGSTYLE,
            };
            LPITEMIDLIST pidl = SHBrowseForFolderW(&bi);
            if (pidl) {
                wchar_t path[MAX_PATH];
                if (SHGetPathFromIDListW(pidl, path)) {
                    char pathUtf8[MAX_PATH * 3];
                    WideCharToMultiByte(CP_UTF8, 0, path, -1, pathUtf8, sizeof(pathUtf8), NULL, NULL);

                    Config *cfg = GetConfig();
                    if (cfg) {
                        config_set_string(cfg, "wow_path", pathUtf8);
                        config_save(cfg);
                        ShowStatusMessage(L"WoW path updated.", WST_NOTIFY_SUCCESS);
                    }
                }
                CoTaskMemFree(pidl);
            }
            break;
        }

        case IDM_ADDON_INSTALL:
            DoAddonInstall(hWnd);
            break;

        case IDM_ADDON_UNINSTALL:
            DoAddonUninstall(hWnd);
            break;

        /* View menu - Theme */
        case IDM_VIEW_THEME_AUTO:
        case IDM_VIEW_THEME_LIGHT:
        case IDM_VIEW_THEME_DARK: {
            Config *cfg = GetConfig();
            if (cfg) {
                const char *theme = "auto";
                if (id == IDM_VIEW_THEME_LIGHT) theme = "light";
                else if (id == IDM_VIEW_THEME_DARK) theme = "dark";

                config_set_string(cfg, "theme", theme);
                config_save(cfg);

                /* Update theme */
                g_darkMode = ShouldUseDarkMode();
                ApplyTheme(hWnd, g_darkMode);
                SetupMenu(hWnd);
            }
            break;
        }

        case IDM_VIEW_NOTIFICATIONS:
            ShowNotificationsDialog(hWnd);
            break;

        /* Help menu */
        case IDM_HELP_MANUAL:
            ShowManualDialog(hWnd);
            break;

        case IDM_HELP_UPDATE:
            CheckForUpdates(hWnd, TRUE);
            break;

        case IDM_HELP_ABOUT:
            ShowAboutDialog(hWnd);
            break;
    }
}

/* Handle header custom draw for dark mode */
static LRESULT HandleHeaderCustomDraw(LPNMCUSTOMDRAW pcd) {
    switch (pcd->dwDrawStage) {
        case CDDS_PREPAINT:
            return CDRF_NOTIFYITEMDRAW;

        case CDDS_ITEMPREPAINT:
            if (g_darkMode) {
                /* Set dark mode colors for header */
                SetTextColor(pcd->hdc, DARK_TEXT_COLOR);
                SetBkColor(pcd->hdc, DARK_HEADER_BG);
                return CDRF_NEWFONT;
            }
            return CDRF_DODEFAULT;

        default:
            return CDRF_DODEFAULT;
    }
}

/* WM_NOTIFY handler */
static LRESULT OnNotify(HWND hWnd, int idCtrl, LPNMHDR pnmh) {
    (void)idCtrl;
    (void)hWnd;

    /* Check if notification is from the ListView header */
    HWND hHeader = g_hListView ? ListView_GetHeader(g_hListView) : NULL;
    if (hHeader && pnmh->hwndFrom == hHeader && pnmh->code == NM_CUSTOMDRAW) {
        return HandleHeaderCustomDraw((LPNMCUSTOMDRAW)pnmh);
    }

    if (pnmh->hwndFrom == g_hListView) {
        switch (pnmh->code) {
            case NM_DBLCLK: {
                /* Edit character on double-click */
                LPNMITEMACTIVATE pnmia = (LPNMITEMACTIVATE)pnmh;
                if (pnmia->iItem >= 0) {
                    /* Get the actual character index from lParam (may differ after sorting) */
                    LVITEMW lvi = { .mask = LVIF_PARAM, .iItem = pnmia->iItem };
                    ListView_GetItem(g_hListView, &lvi);
                    ShowCharacterDialog(hWnd, (int)lvi.lParam);
                }
                break;
            }

            case LVN_COLUMNCLICK: {
                LPNMLISTVIEW pnmlv = (LPNMLISTVIEW)pnmh;
                HandleColumnClick(hWnd, pnmlv->iSubItem);
                break;
            }

            case NM_CUSTOMDRAW: {
                LPNMLVCUSTOMDRAW pcd = (LPNMLVCUSTOMDRAW)pnmh;
                LRESULT result = CDRF_DODEFAULT;
                HandleListViewCustomDraw(pcd, &result);
                return result;
            }
        }
    }

    return 0;
}

/* WM_TIMER handler */
static void OnTimer(HWND hWnd, UINT id) {
    if (id == IDT_STATUS_DISMISS) {
        ClearStatusMessage();
        KillTimer(hWnd, IDT_STATUS_DISMISS);
    }
}

/* WM_ACTIVATE handler */
static void OnActivate(HWND hWnd, UINT state, HWND hWndActDeact, BOOL fMinimized) {
    (void)hWndActDeact;
    (void)fMinimized;

    if (state != WA_INACTIVE) {
        /* Window activated - check for auto-import */
        Config *cfg = GetConfig();
        if (cfg && config_get_bool(cfg, "auto_import", FALSE)) {
            DoAddonImport(hWnd);
        }
    }
}

/* Create ListView control */
static void CreateListView(HWND hWnd) {
    g_hListView = CreateWindowExW(
        WS_EX_CLIENTEDGE,
        WC_LISTVIEWW,
        L"",
        WS_CHILD | WS_VISIBLE | WS_CLIPSIBLINGS |
        LVS_REPORT | LVS_SHOWSELALWAYS | LVS_SINGLESEL,
        0, 0, 0, 0,
        hWnd,
        (HMENU)IDC_LISTVIEW,
        GetAppInstance(),
        NULL
    );

    /* Set extended styles */
    ListView_SetExtendedListViewStyle(g_hListView,
        LVS_EX_FULLROWSELECT | LVS_EX_GRIDLINES | LVS_EX_DOUBLEBUFFER);

    /* Add columns */
    for (int i = 0; i < g_numColumns; i++) {
        LVCOLUMNW lvc = {
            .mask = LVCF_FMT | LVCF_WIDTH | LVCF_TEXT | LVCF_SUBITEM,
            .fmt = g_columns[i].format,
            .cx = g_columns[i].width,
            .pszText = (LPWSTR)g_columns[i].title,
            .iSubItem = i,
        };
        ListView_InsertColumn(g_hListView, i, &lvc);
    }
}

/* Create toolbar */
static void CreateToolbar(HWND hWnd) {
    g_hToolbar = CreateWindowExW(
        0,
        TOOLBARCLASSNAMEW,
        NULL,
        WS_CHILD | WS_VISIBLE | TBSTYLE_FLAT | TBSTYLE_TOOLTIPS | CCS_TOP,
        0, 0, 0, 0,
        hWnd,
        (HMENU)IDT_TOOLBAR,
        GetAppInstance(),
        NULL
    );

    /* Set button size */
    SendMessageW(g_hToolbar, TB_BUTTONSTRUCTSIZE, sizeof(TBBUTTON), 0);

    /* Add buttons */
    TBBUTTON buttons[] = {
        { I_IMAGENONE, IDT_ADD,    TBSTATE_ENABLED, BTNS_BUTTON, {0}, 0, (INT_PTR)L"Add" },
        { I_IMAGENONE, IDT_IMPORT, TBSTATE_ENABLED, BTNS_BUTTON, {0}, 0, (INT_PTR)L"Import" },
        { I_IMAGENONE, IDT_RESET,  TBSTATE_ENABLED, BTNS_BUTTON, {0}, 0, (INT_PTR)L"Reset Weekly" },
    };

    SendMessageW(g_hToolbar, TB_ADDBUTTONS, _countof(buttons), (LPARAM)buttons);
    SendMessageW(g_hToolbar, TB_AUTOSIZE, 0, 0);
}

/* Create status bar */
static void CreateStatusBar(HWND hWnd) {
    g_hStatusBar = CreateWindowExW(
        0,
        STATUSCLASSNAMEW,
        NULL,
        WS_CHILD | WS_VISIBLE | SBARS_SIZEGRIP,
        0, 0, 0, 0,
        hWnd,
        (HMENU)IDC_STATUSBAR,
        GetAppInstance(),
        NULL
    );

    /* Set parts */
    int parts[] = { -1 };
    SendMessageW(g_hStatusBar, SB_SETPARTS, 1, (LPARAM)parts);
}

/* Setup menu checkmarks based on current settings */
static void SetupMenu(HWND hWnd) {
    HMENU hMenu = GetMenu(hWnd);
    if (!hMenu) return;

    Config *cfg = GetConfig();
    if (!cfg) return;

    const char *theme = config_get_string(cfg, "theme", "auto");

    HMENU hViewMenu = GetSubMenu(hMenu, 3); /* View menu */
    if (hViewMenu) {
        HMENU hThemeMenu = GetSubMenu(hViewMenu, 0);
        if (hThemeMenu) {
            CheckMenuRadioItem(hThemeMenu, IDM_VIEW_THEME_AUTO, IDM_VIEW_THEME_DARK,
                strcmp(theme, "light") == 0 ? IDM_VIEW_THEME_LIGHT :
                strcmp(theme, "dark") == 0 ? IDM_VIEW_THEME_DARK :
                IDM_VIEW_THEME_AUTO,
                MF_BYCOMMAND);
        }
    }
}

/* Load window position/size from config */
static void LoadWindowState(HWND hWnd) {
    Config *cfg = GetConfig();
    if (!cfg) return;

    int x = config_get_int(cfg, "window_x", CW_USEDEFAULT);
    int y = config_get_int(cfg, "window_y", CW_USEDEFAULT);
    int w = config_get_int(cfg, "window_width", 1000);
    int h = config_get_int(cfg, "window_height", 600);
    BOOL maximized = config_get_bool(cfg, "window_maximized", FALSE);

    /* Validate position is on screen */
    RECT workArea;
    SystemParametersInfoW(SPI_GETWORKAREA, 0, &workArea, 0);

    if (x != CW_USEDEFAULT && y != CW_USEDEFAULT) {
        if (x < workArea.left || x > workArea.right - 100) x = CW_USEDEFAULT;
        if (y < workArea.top || y > workArea.bottom - 100) y = CW_USEDEFAULT;
    }

    if (x != CW_USEDEFAULT && y != CW_USEDEFAULT) {
        SetWindowPos(hWnd, NULL, x, y, w, h, SWP_NOZORDER);
    } else {
        SetWindowPos(hWnd, NULL, 0, 0, w, h, SWP_NOMOVE | SWP_NOZORDER);
    }

    if (maximized) {
        ShowWindow(hWnd, SW_MAXIMIZE);
    }

    /* Load sort state */
    g_sortColumn = config_get_int(cfg, "sort_column", 0);
    g_sortAscending = config_get_bool(cfg, "sort_ascending", TRUE);
}

/* Save window position/size to config */
static void SaveWindowState(HWND hWnd) {
    Config *cfg = GetConfig();
    if (!cfg) return;

    WINDOWPLACEMENT wp = { .length = sizeof(WINDOWPLACEMENT) };
    GetWindowPlacement(hWnd, &wp);

    BOOL maximized = (wp.showCmd == SW_MAXIMIZE);
    config_set_bool(cfg, "window_maximized", maximized);

    if (!maximized) {
        RECT rc = wp.rcNormalPosition;
        config_set_int(cfg, "window_x", rc.left);
        config_set_int(cfg, "window_y", rc.top);
        config_set_int(cfg, "window_width", rc.right - rc.left);
        config_set_int(cfg, "window_height", rc.bottom - rc.top);
    }

    config_set_int(cfg, "sort_column", g_sortColumn);
    config_set_bool(cfg, "sort_ascending", g_sortAscending);

    config_save(cfg);
}

/* Handle column header click for sorting */
static void HandleColumnClick(HWND hWnd, int column) {
    (void)hWnd;

    /* Toggle direction if same column, otherwise ascending */
    if (column == g_sortColumn) {
        g_sortAscending = !g_sortAscending;
    } else {
        g_sortColumn = column;
        g_sortAscending = TRUE;
    }

    SortListView();
}

/* Sort ListView by current column */
static void SortListView(void) {
    ListView_SortItemsEx(g_hListView, CompareFunc, g_sortColumn);
}

/* Comparison function for ListView sorting */
static int CALLBACK CompareFunc(LPARAM lParam1, LPARAM lParam2, LPARAM lParamSort) {
    (void)lParamSort;

    CharacterStore *store = GetCharacterStore();
    if (!store) return 0;

    /* ListView_SortItemsEx passes ListView item indices, not lParam values */
    /* We need to get the lParam (character index) from each item */
    LVITEMW lvi1 = { .mask = LVIF_PARAM, .iItem = (int)lParam1 };
    LVITEMW lvi2 = { .mask = LVIF_PARAM, .iItem = (int)lParam2 };

    ListView_GetItem(g_hListView, &lvi1);
    ListView_GetItem(g_hListView, &lvi2);

    Character *c1 = character_store_get(store, (int)lvi1.lParam);
    Character *c2 = character_store_get(store, (int)lvi2.lParam);

    if (!c1 || !c2) return 0;

    int result = 0;

    switch (g_sortColumn) {
        case 0: result = strcmp(c1->realm ? c1->realm : "", c2->realm ? c2->realm : ""); break;
        case 1: result = strcmp(c1->name ? c1->name : "", c2->name ? c2->name : ""); break;
        case 2: result = strcmp(c1->guild ? c1->guild : "", c2->guild ? c2->guild : ""); break;
        case 3: result = (c1->item_level > c2->item_level) - (c1->item_level < c2->item_level); break;
        case 4: result = c1->heroic_items - c2->heroic_items; break;
        case 5: result = c1->champion_items - c2->champion_items; break;
        case 6: result = c1->veteran_items - c2->veteran_items; break;
        case 7: result = c1->adventure_items - c2->adventure_items; break;
        case 8: result = c1->old_items - c2->old_items; break;
        case 9: result = c1->vault_visited - c2->vault_visited; break;
        case 10: result = c1->delves - c2->delves; break;
        case 11: result = c1->gilded_stash - c2->gilded_stash; break;
        case 12: result = c1->gearing_up - c2->gearing_up; break;
        case 13: result = c1->quests - c2->quests; break;
        case 14: result = c1->timewalk - c2->timewalk; break;
        case 15: result = strcmp(c1->notes ? c1->notes : "", c2->notes ? c2->notes : ""); break;
        default: break;
    }

    return g_sortAscending ? result : -result;
}

/* Handle custom draw for cell coloring */
static void HandleListViewCustomDraw(LPNMLVCUSTOMDRAW pcd, LRESULT *pResult) {
    switch (pcd->nmcd.dwDrawStage) {
        case CDDS_PREPAINT:
            *pResult = CDRF_NOTIFYITEMDRAW;
            return;

        case CDDS_ITEMPREPAINT:
            *pResult = CDRF_NOTIFYSUBITEMDRAW;
            return;

        case CDDS_SUBITEM | CDDS_ITEMPREPAINT: {
            int viewIndex = (int)pcd->nmcd.dwItemSpec;
            int subItem = pcd->iSubItem;

            CharacterStore *store = GetCharacterStore();
            if (!store) {
                *pResult = CDRF_DODEFAULT;
                break;
            }

            /* Get the character index from lParam (may differ from view index after sorting) */
            LVITEMW lvi = { .mask = LVIF_PARAM, .iItem = viewIndex };
            ListView_GetItem(g_hListView, &lvi);
            int charIndex = (int)lvi.lParam;

            Character *ch = character_store_get(store, charIndex);
            if (!ch) {
                *pResult = CDRF_DODEFAULT;
                break;
            }

            /* Default colors based on theme */
            if (g_darkMode) {
                pcd->clrText = DARK_TEXT_COLOR;
                pcd->clrTextBk = DARK_BG_COLOR;
            } else {
                pcd->clrText = GetSysColor(COLOR_WINDOWTEXT);
                pcd->clrTextBk = GetSysColor(COLOR_WINDOW);
            }

            /* Status color definitions - darker versions for dark mode */
            COLORREF green, yellow, red;
            if (g_darkMode) {
                green = RGB(50, 120, 50);     /* Dark green */
                yellow = RGB(120, 110, 40);   /* Dark yellow/olive */
                red = RGB(120, 50, 50);       /* Dark red */
            } else {
                green = RGB(144, 238, 144);   /* Light green */
                yellow = RGB(255, 255, 200);  /* Light yellow */
                red = RGB(255, 200, 200);     /* Light red */
            }

            /* For colored cells, use dark text in light mode, light text in dark mode */
            COLORREF coloredText = g_darkMode ? DARK_TEXT_COLOR : RGB(0, 0, 0);

            switch (subItem) {
                case 9: /* Vault */
                    if (ch->vault_visited) {
                        pcd->clrTextBk = green;
                        pcd->clrText = coloredText;
                    } else {
                        /* Check if weeklies are incomplete */
                        BOOL weekliesIncomplete = (ch->delves < 4 || ch->gilded_stash < 3 ||
                                                   !ch->gearing_up || ch->timewalk < 5);
                        if (weekliesIncomplete) {
                            pcd->clrTextBk = yellow;
                            pcd->clrText = coloredText;
                        } else {
                            pcd->clrTextBk = red;
                            pcd->clrText = coloredText;
                        }
                    }
                    break;

                case 10: /* Delves */
                    if (ch->delves >= 4) {
                        pcd->clrTextBk = green;
                        pcd->clrText = coloredText;
                    } else if (ch->delves >= 1) {
                        pcd->clrTextBk = yellow;
                        pcd->clrText = coloredText;
                    }
                    break;

                case 11: /* Gilded */
                    if (ch->gilded_stash >= 3) {
                        pcd->clrTextBk = green;
                        pcd->clrText = coloredText;
                    } else if (ch->gilded_stash >= 1) {
                        pcd->clrTextBk = yellow;
                        pcd->clrText = coloredText;
                    }
                    break;

                case 12: /* Gearing Up */
                    if (ch->gearing_up) {
                        pcd->clrTextBk = green;
                        pcd->clrText = coloredText;
                    } else {
                        pcd->clrTextBk = yellow;
                        pcd->clrText = coloredText;
                    }
                    break;

                case 14: /* Timewalk */
                    if (ch->timewalk >= 5) {
                        pcd->clrTextBk = green;
                        pcd->clrText = coloredText;
                    } else if (ch->timewalk >= 1) {
                        pcd->clrTextBk = yellow;
                        pcd->clrText = coloredText;
                    }
                    break;
            }

            *pResult = CDRF_NEWFONT;
            break;
        }

        default:
            *pResult = CDRF_DODEFAULT;
            break;
    }
}

/* Refresh character list from store */
void RefreshCharacterList(void) {
    if (!g_hListView) return;

    CharacterStore *store = GetCharacterStore();
    if (!store) return;

    /* Clear existing items */
    ListView_DeleteAllItems(g_hListView);

    /* Add characters */
    int count = (int)character_store_count(store);
    for (int i = 0; i < count; i++) {
        Character *ch = character_store_get(store, i);
        if (!ch) continue;

        /* Convert strings to wide */
        wchar_t realm[256], name[256], guild[256], notes[512];
        MultiByteToWideChar(CP_UTF8, 0, ch->realm ? ch->realm : "", -1, realm, 256);
        MultiByteToWideChar(CP_UTF8, 0, ch->name ? ch->name : "", -1, name, 256);
        MultiByteToWideChar(CP_UTF8, 0, ch->guild ? ch->guild : "", -1, guild, 256);
        MultiByteToWideChar(CP_UTF8, 0, ch->notes ? ch->notes : "", -1, notes, 512);

        /* Insert item */
        LVITEMW lvi = {
            .mask = LVIF_TEXT | LVIF_PARAM,
            .iItem = i,
            .iSubItem = 0,
            .pszText = realm,
            .lParam = i,
        };
        int idx = ListView_InsertItem(g_hListView, &lvi);

        /* Set subitems */
        ListView_SetItemText(g_hListView, idx, 1, name);
        ListView_SetItemText(g_hListView, idx, 2, guild);

        wchar_t buf[64];

        swprintf(buf, 64, L"%.1f", ch->item_level);
        ListView_SetItemText(g_hListView, idx, 3, buf);

        swprintf(buf, 64, L"%d", ch->heroic_items);
        ListView_SetItemText(g_hListView, idx, 4, buf);

        swprintf(buf, 64, L"%d", ch->champion_items);
        ListView_SetItemText(g_hListView, idx, 5, buf);

        swprintf(buf, 64, L"%d", ch->veteran_items);
        ListView_SetItemText(g_hListView, idx, 6, buf);

        swprintf(buf, 64, L"%d", ch->adventure_items);
        ListView_SetItemText(g_hListView, idx, 7, buf);

        swprintf(buf, 64, L"%d", ch->old_items);
        ListView_SetItemText(g_hListView, idx, 8, buf);

        ListView_SetItemText(g_hListView, idx, 9, ch->vault_visited ? L"Yes" : L"No");

        swprintf(buf, 64, L"%d", ch->delves);
        ListView_SetItemText(g_hListView, idx, 10, buf);

        swprintf(buf, 64, L"%d", ch->gilded_stash);
        ListView_SetItemText(g_hListView, idx, 11, buf);

        ListView_SetItemText(g_hListView, idx, 12, ch->gearing_up ? L"Yes" : L"No");

        ListView_SetItemText(g_hListView, idx, 13, ch->quests ? L"Yes" : L"No");

        swprintf(buf, 64, L"%d", ch->timewalk);
        ListView_SetItemText(g_hListView, idx, 14, buf);

        ListView_SetItemText(g_hListView, idx, 15, notes);
    }

    /* Apply current sort order */
    SortListView();
}

/* Show status message */
void ShowStatusMessage(const wchar_t *message, WstNotifyType type) {
    if (!g_hStatusBar) return;

    (void)type; /* TODO: Use icon based on type */

    SendMessageW(g_hStatusBar, SB_SETTEXTW, 0, (LPARAM)message);

    /* Set auto-dismiss timer */
    KillTimer(g_hMainWindow, IDT_STATUS_DISMISS);
    SetTimer(g_hMainWindow, IDT_STATUS_DISMISS, STATUS_TIMEOUT_MS, NULL);

    /* Store notification */
    NotificationStore *ns = GetNotificationStore();
    if (ns) {
        char msgUtf8[1024];
        WideCharToMultiByte(CP_UTF8, 0, message, -1, msgUtf8, sizeof(msgUtf8), NULL, NULL);

        Notification *n = notification_create(msgUtf8, type);
        if (n) {
            notification_store_add(ns, n);
            notification_store_save(ns);
        }
    }
}

/* Clear status message */
void ClearStatusMessage(void) {
    if (!g_hStatusBar) return;
    SendMessageW(g_hStatusBar, SB_SETTEXTW, 0, (LPARAM)L"");
}

/* Get the directory containing the executable */
static BOOL GetExeDirectory(wchar_t *buffer, size_t bufferLen) {
    if (!GetModuleFileNameW(NULL, buffer, (DWORD)bufferLen)) {
        return FALSE;
    }
    /* Remove the filename, keeping just the directory */
    wchar_t *lastSlash = wcsrchr(buffer, L'\\');
    if (lastSlash) {
        *lastSlash = L'\0';
    }
    return TRUE;
}

/* Recursively delete a directory and all its contents */
static BOOL DeleteDirectoryRecursive(const wchar_t *path) {
    wchar_t searchPath[MAX_PATH];
    swprintf(searchPath, MAX_PATH, L"%s\\*", path);

    WIN32_FIND_DATAW fd;
    HANDLE hFind = FindFirstFileW(searchPath, &fd);
    if (hFind == INVALID_HANDLE_VALUE) {
        return FALSE;
    }

    do {
        if (wcscmp(fd.cFileName, L".") == 0 || wcscmp(fd.cFileName, L"..") == 0) {
            continue;
        }

        wchar_t fullPath[MAX_PATH];
        swprintf(fullPath, MAX_PATH, L"%s\\%s", path, fd.cFileName);

        if (fd.dwFileAttributes & FILE_ATTRIBUTE_DIRECTORY) {
            /* Recursively delete subdirectory */
            if (!DeleteDirectoryRecursive(fullPath)) {
                FindClose(hFind);
                return FALSE;
            }
        } else {
            /* Delete file */
            if (!DeleteFileW(fullPath)) {
                FindClose(hFind);
                return FALSE;
            }
        }
    } while (FindNextFileW(hFind, &fd));

    FindClose(hFind);

    /* Remove the now-empty directory */
    return RemoveDirectoryW(path);
}

/* Recursively copy a directory and all its contents */
static BOOL CopyDirectoryRecursive(const wchar_t *srcPath, const wchar_t *destPath) {
    /* Create destination directory */
    if (!CreateDirectoryW(destPath, NULL)) {
        DWORD err = GetLastError();
        if (err != ERROR_ALREADY_EXISTS) {
            return FALSE;
        }
    }

    wchar_t searchPath[MAX_PATH];
    swprintf(searchPath, MAX_PATH, L"%s\\*", srcPath);

    WIN32_FIND_DATAW fd;
    HANDLE hFind = FindFirstFileW(searchPath, &fd);
    if (hFind == INVALID_HANDLE_VALUE) {
        return FALSE;
    }

    BOOL success = TRUE;
    do {
        if (wcscmp(fd.cFileName, L".") == 0 || wcscmp(fd.cFileName, L"..") == 0) {
            continue;
        }

        wchar_t srcFullPath[MAX_PATH];
        wchar_t destFullPath[MAX_PATH];
        swprintf(srcFullPath, MAX_PATH, L"%s\\%s", srcPath, fd.cFileName);
        swprintf(destFullPath, MAX_PATH, L"%s\\%s", destPath, fd.cFileName);

        if (fd.dwFileAttributes & FILE_ATTRIBUTE_DIRECTORY) {
            /* Recursively copy subdirectory */
            if (!CopyDirectoryRecursive(srcFullPath, destFullPath)) {
                success = FALSE;
                break;
            }
        } else {
            /* Copy file */
            if (!CopyFileW(srcFullPath, destFullPath, FALSE)) {
                success = FALSE;
                break;
            }
        }
    } while (FindNextFileW(hFind, &fd));

    FindClose(hFind);
    return success;
}

/* Install the addon to WoW AddOns folder */
static BOOL DoAddonInstall(HWND hWnd) {
    (void)hWnd;

    Config *cfg = GetConfig();
    if (!cfg) {
        ShowStatusMessage(L"Internal error: config not initialized.", WST_NOTIFY_WARNING);
        return FALSE;
    }

    /* Check WoW path is configured */
    const char *wowPath = config_get_string(cfg, "wow_path", NULL);
    if (!wowPath || strlen(wowPath) == 0) {
        ShowStatusMessage(L"WoW path not set. Use Addon → Set WoW Location first.", WST_NOTIFY_WARNING);
        return FALSE;
    }

    /* Get exe directory to find bundled addon */
    wchar_t exeDir[MAX_PATH];
    if (!GetExeDirectory(exeDir, MAX_PATH)) {
        ShowStatusMessage(L"Failed to get application directory.", WST_NOTIFY_WARNING);
        return FALSE;
    }

    /* Build source addon path (next to exe) */
    wchar_t srcAddonPath[MAX_PATH];
    swprintf(srcAddonPath, MAX_PATH, L"%s\\WoWStatTracker_Addon", exeDir);

    /* Check source addon exists */
    DWORD srcAttrs = GetFileAttributesW(srcAddonPath);
    if (srcAttrs == INVALID_FILE_ATTRIBUTES || !(srcAttrs & FILE_ATTRIBUTE_DIRECTORY)) {
        ShowStatusMessage(L"Addon source not found. Package may be incomplete.", WST_NOTIFY_WARNING);
        return FALSE;
    }

    /* Build destination path: wow_path\_retail_\Interface\AddOns */
    wchar_t wowPathW[MAX_PATH];
    MultiByteToWideChar(CP_UTF8, 0, wowPath, -1, wowPathW, MAX_PATH);

    wchar_t interfacePath[MAX_PATH];
    swprintf(interfacePath, MAX_PATH, L"%s\\_retail_\\Interface", wowPathW);

    wchar_t addonsPath[MAX_PATH];
    swprintf(addonsPath, MAX_PATH, L"%s\\AddOns", interfacePath);

    wchar_t destAddonPath[MAX_PATH];
    swprintf(destAddonPath, MAX_PATH, L"%s\\WoWStatTracker_Addon", addonsPath);

    /* Create Interface and AddOns directories if they don't exist */
    CreateDirectoryW(interfacePath, NULL);
    CreateDirectoryW(addonsPath, NULL);

    /* Remove existing addon if present */
    DWORD destAttrs = GetFileAttributesW(destAddonPath);
    if (destAttrs != INVALID_FILE_ATTRIBUTES) {
        if (!DeleteDirectoryRecursive(destAddonPath)) {
            ShowStatusMessage(L"Failed to remove existing addon.", WST_NOTIFY_WARNING);
            return FALSE;
        }
    }

    /* Copy addon */
    if (!CopyDirectoryRecursive(srcAddonPath, destAddonPath)) {
        ShowStatusMessage(L"Failed to copy addon files.", WST_NOTIFY_WARNING);
        return FALSE;
    }

    ShowStatusMessage(L"Addon installed successfully!", WST_NOTIFY_SUCCESS);
    return TRUE;
}

/* Uninstall the addon from WoW AddOns folder */
static BOOL DoAddonUninstall(HWND hWnd) {
    (void)hWnd;

    Config *cfg = GetConfig();
    if (!cfg) {
        ShowStatusMessage(L"Internal error: config not initialized.", WST_NOTIFY_WARNING);
        return FALSE;
    }

    /* Check WoW path is configured */
    const char *wowPath = config_get_string(cfg, "wow_path", NULL);
    if (!wowPath || strlen(wowPath) == 0) {
        ShowStatusMessage(L"WoW path not set. Use Addon → Set WoW Location first.", WST_NOTIFY_WARNING);
        return FALSE;
    }

    /* Build addon path */
    wchar_t wowPathW[MAX_PATH];
    MultiByteToWideChar(CP_UTF8, 0, wowPath, -1, wowPathW, MAX_PATH);

    wchar_t addonPath[MAX_PATH];
    swprintf(addonPath, MAX_PATH, L"%s\\_retail_\\Interface\\AddOns\\WoWStatTracker_Addon", wowPathW);

    /* Check if addon exists */
    DWORD attrs = GetFileAttributesW(addonPath);
    if (attrs == INVALID_FILE_ATTRIBUTES) {
        ShowStatusMessage(L"Addon is not installed.", WST_NOTIFY_INFO);
        return TRUE; /* Not an error */
    }

    /* Confirm uninstallation */
    int result = MessageBoxW(hWnd,
        L"Are you sure you want to uninstall the WoWStatTracker addon?",
        L"Uninstall Addon",
        MB_YESNO | MB_ICONQUESTION);

    if (result != IDYES) {
        return FALSE;
    }

    /* Delete addon directory */
    if (!DeleteDirectoryRecursive(addonPath)) {
        ShowStatusMessage(L"Failed to remove addon files.", WST_NOTIFY_WARNING);
        return FALSE;
    }

    ShowStatusMessage(L"Addon uninstalled successfully.", WST_NOTIFY_SUCCESS);
    return TRUE;
}

/* Get handles */
HWND GetMainWindowHandle(void) { return g_hMainWindow; }
HWND GetListViewHandle(void) { return g_hListView; }

/* Import from addon */
void DoAddonImport(HWND hWnd) {
    (void)hWnd;

    Config *cfg = GetConfig();
    CharacterStore *store = GetCharacterStore();

    if (!cfg || !store) {
        ShowStatusMessage(L"Internal error: config or store not initialized.", WST_NOTIFY_WARNING);
        return;
    }

    const char *wowPath = config_get_string(cfg, "wow_path", NULL);
    if (!wowPath || strlen(wowPath) == 0) {
        ShowStatusMessage(L"WoW path not set. Use Addon → Set WoW Location.", WST_NOTIFY_WARNING);
        return;
    }

    /* Build SavedVariables path */
    char svPath[MAX_PATH * 3];
    snprintf(svPath, sizeof(svPath), "%s/_retail_/WTF/Account", wowPath);

    /* Find SavedVariables file - look for WoWStatTracker.lua in any account folder */
    /* For now, just try a pattern */
    char pattern[MAX_PATH * 4];
    snprintf(pattern, sizeof(pattern), "%s/*/SavedVariables/WoWStatTracker.lua", svPath);

    /* Use FindFirstFile to search */
    wchar_t patternW[MAX_PATH * 4];
    MultiByteToWideChar(CP_UTF8, 0, pattern, -1, patternW, MAX_PATH * 4);

    /* We need to do a directory search - simplified version */
    char firstAccountPath[MAX_PATH * 4] = {0};

    /* Try to find the account folder */
    wchar_t accountSearchW[MAX_PATH * 3];
    MultiByteToWideChar(CP_UTF8, 0, svPath, -1, accountSearchW, MAX_PATH * 3);
    wcscat_s(accountSearchW, MAX_PATH * 3, L"\\*");

    WIN32_FIND_DATAW fd;
    HANDLE hFind = FindFirstFileW(accountSearchW, &fd);
    if (hFind != INVALID_HANDLE_VALUE) {
        do {
            if (fd.dwFileAttributes & FILE_ATTRIBUTE_DIRECTORY) {
                if (wcscmp(fd.cFileName, L".") != 0 && wcscmp(fd.cFileName, L"..") != 0) {
                    /* Try this account folder */
                    char accountName[256];
                    WideCharToMultiByte(CP_UTF8, 0, fd.cFileName, -1, accountName, 256, NULL, NULL);
                    snprintf(firstAccountPath, sizeof(firstAccountPath),
                             "%s/%s/SavedVariables/WoWStatTracker.lua", svPath, accountName);

                    /* Check if file exists */
                    DWORD attrs = GetFileAttributesA(firstAccountPath);
                    if (attrs != INVALID_FILE_ATTRIBUTES) {
                        break; /* Found it */
                    }
                    firstAccountPath[0] = 0;
                }
            }
        } while (FindNextFileW(hFind, &fd));
        FindClose(hFind);
    }

    if (firstAccountPath[0] == 0) {
        ShowStatusMessage(L"No addon data found. Install addon and /reload in WoW.", WST_NOTIFY_WARNING);
        return;
    }

    /* Parse the Lua file */
    LuaParseResult parseResult = lua_parser_parse_addon_file(firstAccountPath);
    if (!parseResult.characters || parseResult.count == 0) {
        ShowStatusMessage(L"No character data found in addon file.", WST_NOTIFY_WARNING);
        lua_parser_free_result(&parseResult);
        return;
    }

    /* Import characters */
    int importedCount = 0;
    int updatedCount = 0;

    for (size_t i = 0; i < parseResult.count; i++) {
        Character *addonChar = parseResult.characters[i];

        if (!addonChar || !addonChar->name || !addonChar->realm) {
            continue;
        }

        /* Find or create character */
        int existingIdx = character_store_find(store, addonChar->realm, addonChar->name);

        if (existingIdx >= 0) {
            /* Update existing character */
            Character *existing = character_store_get(store, existingIdx);
            if (existing) {
                /* Update all fields from addon */
                if (addonChar->guild) character_set_guild(existing, addonChar->guild);
                existing->item_level = addonChar->item_level;
                existing->heroic_items = addonChar->heroic_items;
                existing->champion_items = addonChar->champion_items;
                existing->veteran_items = addonChar->veteran_items;
                existing->adventure_items = addonChar->adventure_items;
                existing->old_items = addonChar->old_items;
                existing->vault_visited = addonChar->vault_visited;
                existing->delves = addonChar->delves;
                existing->gilded_stash = addonChar->gilded_stash;
                existing->gearing_up = addonChar->gearing_up;
                existing->quests = addonChar->quests;
                existing->timewalk = addonChar->timewalk;
                updatedCount++;
            }
        } else {
            /* Add new character - make a copy since store takes ownership */
            Character *newChar = character_copy(addonChar);
            if (newChar) {
                character_store_add(store, newChar);
                importedCount++;
            }
        }
    }

    lua_parser_free_result(&parseResult);

    /* Save and refresh */
    character_store_save(store);
    RefreshCharacterList();

    /* Show result */
    wchar_t msg[256];
    swprintf(msg, 256, L"Imported %d new, updated %d characters.", importedCount, updatedCount);
    ShowStatusMessage(msg, WST_NOTIFY_SUCCESS);
}

/* Check if dark mode should be used */
BOOL ShouldUseDarkMode(void) {
    Config *cfg = GetConfig();
    if (!cfg) return FALSE;

    const char *theme = config_get_string(cfg, "theme", "auto");

    if (strcmp(theme, "dark") == 0) return TRUE;
    if (strcmp(theme, "light") == 0) return FALSE;

    /* Auto - check system setting */
    return platform_is_dark_theme();
}

/* Apply theme to window */
void ApplyTheme(HWND hWnd, BOOL dark) {
    g_darkMode = dark;

    /* Use DWM to set dark mode for title bar (Windows 10 1809+) */
    BOOL useDark = dark;
    /* DWMWA_USE_IMMERSIVE_DARK_MODE = 20 */
    DwmSetWindowAttribute(hWnd, 20, &useDark, sizeof(useDark));

    /* Apply to ListView */
    if (g_hListView) {
        if (dark) {
            ListView_SetBkColor(g_hListView, DARK_BG_COLOR);
            ListView_SetTextBkColor(g_hListView, DARK_BG_COLOR);
            ListView_SetTextColor(g_hListView, DARK_TEXT_COLOR);
        } else {
            ListView_SetBkColor(g_hListView, GetSysColor(COLOR_WINDOW));
            ListView_SetTextBkColor(g_hListView, GetSysColor(COLOR_WINDOW));
            ListView_SetTextColor(g_hListView, GetSysColor(COLOR_WINDOWTEXT));
        }

        /* Force header to redraw with new colors (via custom draw) */
        HWND hHeader = ListView_GetHeader(g_hListView);
        if (hHeader) {
            InvalidateRect(hHeader, NULL, TRUE);
        }

        InvalidateRect(g_hListView, NULL, TRUE);
    }

    /* Force redraw */
    RedrawWindow(hWnd, NULL, NULL, RDW_INVALIDATE | RDW_UPDATENOW | RDW_ALLCHILDREN);
}
