/*
 * WoW Stat Tracker - Windows Platform Implementation
 * BSD 3-Clause License
 */

#ifdef _WIN32

#define WIN32_LEAN_AND_MEAN
#include <windows.h>
#include <winhttp.h>
#include <shellapi.h>
#include <shlobj.h>
#include "../platform.h"
#include "../../core/util.h"
#include <stdio.h>

#pragma comment(lib, "winhttp.lib")
#pragma comment(lib, "shell32.lib")

/* Handle for the lock file */
static HANDLE g_lock_handle = INVALID_HANDLE_VALUE;

bool platform_is_dark_theme(void) {
    HKEY hKey;
    DWORD value = 1;  /* Default to light theme (AppsUseLightTheme = 1) */
    DWORD size = sizeof(DWORD);

    /* Check registry for dark mode setting */
    if (RegOpenKeyExW(
            HKEY_CURRENT_USER,
            L"Software\\Microsoft\\Windows\\CurrentVersion\\Themes\\Personalize",
            0,
            KEY_READ,
            &hKey) == ERROR_SUCCESS) {

        RegQueryValueExW(hKey, L"AppsUseLightTheme", NULL, NULL,
                         (LPBYTE)&value, &size);
        RegCloseKey(hKey);
    }

    /* AppsUseLightTheme = 0 means dark mode */
    return value == 0;
}

char* platform_http_get(const char* url) {
    if (!url) return NULL;

    char* result = NULL;
    HINTERNET hSession = NULL;
    HINTERNET hConnect = NULL;
    HINTERNET hRequest = NULL;

    /* Parse URL */
    wchar_t wUrl[2048];
    MultiByteToWideChar(CP_UTF8, 0, url, -1, wUrl, 2048);

    URL_COMPONENTSW urlComp = {0};
    urlComp.dwStructSize = sizeof(urlComp);

    wchar_t hostName[256] = {0};
    wchar_t urlPath[1024] = {0};

    urlComp.lpszHostName = hostName;
    urlComp.dwHostNameLength = 256;
    urlComp.lpszUrlPath = urlPath;
    urlComp.dwUrlPathLength = 1024;

    if (!WinHttpCrackUrl(wUrl, 0, 0, &urlComp)) {
        return NULL;
    }

    /* Open session */
    hSession = WinHttpOpen(
        L"WoWStatTracker/1.0",
        WINHTTP_ACCESS_TYPE_DEFAULT_PROXY,
        WINHTTP_NO_PROXY_NAME,
        WINHTTP_NO_PROXY_BYPASS,
        0);

    if (!hSession) goto cleanup;

    /* Set timeouts */
    DWORD timeout = 10000;  /* 10 seconds */
    WinHttpSetTimeouts(hSession, timeout, timeout, timeout, timeout);

    /* Connect */
    hConnect = WinHttpConnect(
        hSession,
        hostName,
        urlComp.nPort,
        0);

    if (!hConnect) goto cleanup;

    /* Create request */
    DWORD flags = (urlComp.nScheme == INTERNET_SCHEME_HTTPS) ?
                   WINHTTP_FLAG_SECURE : 0;

    hRequest = WinHttpOpenRequest(
        hConnect,
        L"GET",
        urlPath,
        NULL,
        WINHTTP_NO_REFERER,
        WINHTTP_DEFAULT_ACCEPT_TYPES,
        flags);

    if (!hRequest) goto cleanup;

    /* Send request */
    if (!WinHttpSendRequest(hRequest, WINHTTP_NO_ADDITIONAL_HEADERS, 0,
                            WINHTTP_NO_REQUEST_DATA, 0, 0, 0)) {
        goto cleanup;
    }

    /* Receive response */
    if (!WinHttpReceiveResponse(hRequest, NULL)) {
        goto cleanup;
    }

    /* Check status code */
    DWORD statusCode = 0;
    DWORD statusSize = sizeof(statusCode);
    WinHttpQueryHeaders(hRequest,
                        WINHTTP_QUERY_STATUS_CODE | WINHTTP_QUERY_FLAG_NUMBER,
                        WINHTTP_HEADER_NAME_BY_INDEX,
                        &statusCode, &statusSize, WINHTTP_NO_HEADER_INDEX);

    if (statusCode < 200 || statusCode >= 300) {
        goto cleanup;
    }

    /* Read response body */
    size_t totalSize = 0;
    size_t bufferCapacity = 4096;
    char* buffer = malloc(bufferCapacity);
    if (!buffer) goto cleanup;

    DWORD bytesAvailable;
    while (WinHttpQueryDataAvailable(hRequest, &bytesAvailable) && bytesAvailable > 0) {
        /* Grow buffer if needed */
        if (totalSize + bytesAvailable + 1 > bufferCapacity) {
            bufferCapacity = (totalSize + bytesAvailable + 1) * 2;
            char* newBuffer = realloc(buffer, bufferCapacity);
            if (!newBuffer) {
                free(buffer);
                goto cleanup;
            }
            buffer = newBuffer;
        }

        DWORD bytesRead;
        if (!WinHttpReadData(hRequest, buffer + totalSize, bytesAvailable, &bytesRead)) {
            free(buffer);
            goto cleanup;
        }
        totalSize += bytesRead;
    }

    buffer[totalSize] = '\0';
    result = buffer;

cleanup:
    if (hRequest) WinHttpCloseHandle(hRequest);
    if (hConnect) WinHttpCloseHandle(hConnect);
    if (hSession) WinHttpCloseHandle(hSession);

    return result;
}

WstResult platform_write_atomic(const char* path, const char* data, size_t len) {
    if (!path || !data) return WST_ERR_NULL_ARG;

    /* Create temp file path */
    size_t path_len = strlen(path);
    char* temp_path = malloc(path_len + 8);
    if (!temp_path) return WST_ERR_ALLOC;
    snprintf(temp_path, path_len + 8, "%s.tmp", path);

    /* Convert to wide string */
    wchar_t wTempPath[MAX_PATH];
    wchar_t wPath[MAX_PATH];
    MultiByteToWideChar(CP_UTF8, 0, temp_path, -1, wTempPath, MAX_PATH);
    MultiByteToWideChar(CP_UTF8, 0, path, -1, wPath, MAX_PATH);

    /* Write to temp file */
    HANDLE hFile = CreateFileW(
        wTempPath,
        GENERIC_WRITE,
        0,
        NULL,
        CREATE_ALWAYS,
        FILE_ATTRIBUTE_NORMAL,
        NULL);

    if (hFile == INVALID_HANDLE_VALUE) {
        free(temp_path);
        return WST_ERR_IO;
    }

    DWORD written;
    BOOL success = WriteFile(hFile, data, (DWORD)len, &written, NULL);

    /* Flush to disk */
    FlushFileBuffers(hFile);
    CloseHandle(hFile);

    if (!success || written != len) {
        DeleteFileW(wTempPath);
        free(temp_path);
        return WST_ERR_IO;
    }

    /* Atomic rename (MoveFileEx with REPLACE_EXISTING) */
    if (!MoveFileExW(wTempPath, wPath, MOVEFILE_REPLACE_EXISTING)) {
        DeleteFileW(wTempPath);
        free(temp_path);
        return WST_ERR_IO;
    }

    free(temp_path);
    return WST_OK;
}

WstResult platform_lock_acquire(const char* lock_file) {
    if (!lock_file) return WST_ERR_NULL_ARG;

    /* Already locked? */
    if (g_lock_handle != INVALID_HANDLE_VALUE) return WST_OK;

    /* Convert to wide string */
    wchar_t wPath[MAX_PATH];
    MultiByteToWideChar(CP_UTF8, 0, lock_file, -1, wPath, MAX_PATH);

    /* Create/open lock file with exclusive access */
    g_lock_handle = CreateFileW(
        wPath,
        GENERIC_READ | GENERIC_WRITE,
        0,  /* No sharing - exclusive access */
        NULL,
        CREATE_ALWAYS,
        FILE_ATTRIBUTE_NORMAL,
        NULL);

    if (g_lock_handle == INVALID_HANDLE_VALUE) {
        DWORD error = GetLastError();
        if (error == ERROR_SHARING_VIOLATION) {
            return WST_ERR_LOCK_FAILED;
        }
        return WST_ERR_IO;
    }

    /* Also lock the file explicitly */
    OVERLAPPED overlapped = {0};
    if (!LockFileEx(g_lock_handle, LOCKFILE_EXCLUSIVE_LOCK | LOCKFILE_FAIL_IMMEDIATELY,
                    0, MAXDWORD, MAXDWORD, &overlapped)) {
        CloseHandle(g_lock_handle);
        g_lock_handle = INVALID_HANDLE_VALUE;
        return WST_ERR_LOCK_FAILED;
    }

    /* Write PID to lock file */
    char pid_str[32];
    int pid_len = snprintf(pid_str, sizeof(pid_str), "%lu\n", GetCurrentProcessId());
    DWORD written;
    WriteFile(g_lock_handle, pid_str, pid_len, &written, NULL);
    FlushFileBuffers(g_lock_handle);

    return WST_OK;
}

void platform_lock_release(const char* lock_file) {
    if (g_lock_handle == INVALID_HANDLE_VALUE) return;

    /* Unlock and close */
    OVERLAPPED overlapped = {0};
    UnlockFileEx(g_lock_handle, 0, MAXDWORD, MAXDWORD, &overlapped);
    CloseHandle(g_lock_handle);
    g_lock_handle = INVALID_HANDLE_VALUE;

    /* Delete lock file */
    if (lock_file) {
        wchar_t wPath[MAX_PATH];
        MultiByteToWideChar(CP_UTF8, 0, lock_file, -1, wPath, MAX_PATH);
        DeleteFileW(wPath);
    }
}

void platform_open_url(const char* url) {
    if (!url) return;

    wchar_t wUrl[2048];
    MultiByteToWideChar(CP_UTF8, 0, url, -1, wUrl, 2048);

    ShellExecuteW(NULL, L"open", wUrl, NULL, NULL, SW_SHOWNORMAL);
}

#endif /* _WIN32 */
