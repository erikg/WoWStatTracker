/*
 * WoW Stat Tracker - macOS Platform Implementation
 * BSD 3-Clause License
 */

#import <Foundation/Foundation.h>
#import <AppKit/AppKit.h>
#include "../platform.h"
#include "../../core/util.h"
#include <fcntl.h>
#include <unistd.h>
#include <sys/stat.h>

/* File descriptor for the lock file */
static int g_lock_fd = -1;

bool platform_is_dark_theme(void) {
    @autoreleasepool {
        /* Check the effective appearance */
        if (@available(macOS 10.14, *)) {
            NSAppearance *appearance = nil;

            /* Use the app's effective appearance if available */
            if (NSApp) {
                appearance = [NSApp effectiveAppearance];
            }

            /* Fallback: check user defaults directly */
            if (!appearance) {
                NSString *style = [[NSUserDefaults standardUserDefaults]
                                   stringForKey:@"AppleInterfaceStyle"];
                return [style isEqualToString:@"Dark"];
            }

            NSAppearanceName bestMatch = [appearance
                bestMatchFromAppearancesWithNames:@[
                    NSAppearanceNameAqua,
                    NSAppearanceNameDarkAqua
                ]];
            return [bestMatch isEqualToString:NSAppearanceNameDarkAqua];
        }

        /* Fallback for older macOS: check AppleInterfaceStyle in user defaults */
        NSString *style = [[NSUserDefaults standardUserDefaults]
                           stringForKey:@"AppleInterfaceStyle"];
        return [style isEqualToString:@"Dark"];
    }
}

char* platform_http_get(const char* url) {
    if (!url) return NULL;

    @autoreleasepool {
        NSURL *nsUrl = [NSURL URLWithString:[NSString stringWithUTF8String:url]];
        if (!nsUrl) return NULL;

        /* Create a synchronous request with timeout */
        NSMutableURLRequest *request = [NSMutableURLRequest requestWithURL:nsUrl];
        [request setHTTPMethod:@"GET"];
        [request setTimeoutInterval:10.0];
        [request setValue:@"WoWStatTracker/1.0" forHTTPHeaderField:@"User-Agent"];

        /* Perform synchronous request */
        __block NSData *responseData = nil;
        __block NSError *error = nil;
        __block NSInteger statusCode = 0;

        dispatch_semaphore_t semaphore = dispatch_semaphore_create(0);

        NSURLSessionDataTask *task = [[NSURLSession sharedSession]
            dataTaskWithRequest:request
            completionHandler:^(NSData *data, NSURLResponse *response, NSError *err) {
                responseData = data;
                error = err;
                if ([response isKindOfClass:[NSHTTPURLResponse class]]) {
                    statusCode = [(NSHTTPURLResponse *)response statusCode];
                }
                dispatch_semaphore_signal(semaphore);
            }];

        [task resume];

        /* Wait for completion with timeout */
        dispatch_time_t timeout = dispatch_time(DISPATCH_TIME_NOW, 15 * NSEC_PER_SEC);
        if (dispatch_semaphore_wait(semaphore, timeout) != 0) {
            [task cancel];
            return NULL;
        }

        if (error || statusCode < 200 || statusCode >= 300 || !responseData) {
            return NULL;
        }

        /* Convert to C string */
        NSString *responseString = [[NSString alloc] initWithData:responseData
                                                         encoding:NSUTF8StringEncoding];
        if (!responseString) return NULL;

        return wst_strdup([responseString UTF8String]);
    }
}

WstResult platform_write_atomic(const char* path, const char* data, size_t len) {
    if (!path || !data) return WST_ERR_NULL_ARG;

    /* Create temp file path */
    size_t path_len = strlen(path);
    char* temp_path = malloc(path_len + 8);
    if (!temp_path) return WST_ERR_ALLOC;
    snprintf(temp_path, path_len + 8, "%s.XXXXXX", path);

    /* Create temp file */
    int fd = mkstemp(temp_path);
    if (fd < 0) {
        free(temp_path);
        return WST_ERR_IO;
    }

    /* Write data */
    ssize_t written = write(fd, data, len);
    if (written < 0 || (size_t)written != len) {
        close(fd);
        unlink(temp_path);
        free(temp_path);
        return WST_ERR_IO;
    }

    /* Sync to disk */
    if (fsync(fd) != 0) {
        close(fd);
        unlink(temp_path);
        free(temp_path);
        return WST_ERR_IO;
    }

    close(fd);

    /* Atomic rename */
    if (rename(temp_path, path) != 0) {
        unlink(temp_path);
        free(temp_path);
        return WST_ERR_IO;
    }

    free(temp_path);
    return WST_OK;
}

WstResult platform_lock_acquire(const char* lock_file) {
    if (!lock_file) return WST_ERR_NULL_ARG;

    /* Already locked? */
    if (g_lock_fd >= 0) return WST_OK;

    /* Open or create lock file */
    g_lock_fd = open(lock_file, O_RDWR | O_CREAT, 0644);
    if (g_lock_fd < 0) {
        return WST_ERR_IO;
    }

    /* Try to acquire exclusive lock (non-blocking) */
    struct flock fl = {
        .l_type = F_WRLCK,
        .l_whence = SEEK_SET,
        .l_start = 0,
        .l_len = 0,  /* Lock entire file */
    };

    if (fcntl(g_lock_fd, F_SETLK, &fl) < 0) {
        close(g_lock_fd);
        g_lock_fd = -1;
        return WST_ERR_LOCK_FAILED;
    }

    /* Write PID to lock file */
    char pid_str[32];
    snprintf(pid_str, sizeof(pid_str), "%d\n", getpid());
    ftruncate(g_lock_fd, 0);
    lseek(g_lock_fd, 0, SEEK_SET);
    write(g_lock_fd, pid_str, strlen(pid_str));

    return WST_OK;
}

void platform_lock_release(const char* lock_file) {
    if (g_lock_fd < 0) return;

    /* Release lock */
    struct flock fl = {
        .l_type = F_UNLCK,
        .l_whence = SEEK_SET,
        .l_start = 0,
        .l_len = 0,
    };
    fcntl(g_lock_fd, F_SETLK, &fl);

    close(g_lock_fd);
    g_lock_fd = -1;

    /* Remove lock file */
    if (lock_file) {
        unlink(lock_file);
    }
}

void platform_open_url(const char* url) {
    if (!url) return;

    @autoreleasepool {
        NSURL *nsUrl = [NSURL URLWithString:[NSString stringWithUTF8String:url]];
        if (nsUrl) {
            [[NSWorkspace sharedWorkspace] openURL:nsUrl];
        }
    }
}
