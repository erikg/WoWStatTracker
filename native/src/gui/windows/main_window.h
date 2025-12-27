/*
 * WoW Stat Tracker - Windows Main Window
 * BSD 3-Clause License
 */

#ifndef WST_MAIN_WINDOW_H
#define WST_MAIN_WINDOW_H

#include <windows.h>
#include "notification.h"

/* Create and show main window */
HWND CreateMainWindow(HINSTANCE hInstance, int nCmdShow);

/* Refresh character list from store */
void RefreshCharacterList(void);

/* Show status message with auto-dismiss */
void ShowStatusMessage(const wchar_t *message, WstNotifyType type);

/* Clear status message */
void ClearStatusMessage(void);

/* Get main window handle */
HWND GetMainWindowHandle(void);

/* Get ListView handle */
HWND GetListViewHandle(void);

/* Import from addon */
void DoAddonImport(HWND hWnd);

/* Show character dialog for add/edit */
void ShowCharacterDialog(HWND hWnd, int characterIndex);

/* Show preferences dialog */
void ShowPreferencesDialog(HWND hWnd);

/* Show manual dialog */
void ShowManualDialog(HWND hWnd);

/* Apply theme to window */
void ApplyTheme(HWND hWnd, BOOL dark);

/* Check if dark mode should be used */
BOOL ShouldUseDarkMode(void);

#endif /* WST_MAIN_WINDOW_H */
