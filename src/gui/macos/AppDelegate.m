/*
 * WoW Stat Tracker - macOS Application Delegate Implementation
 * BSD 3-Clause License
 */

#import "AppDelegate.h"
#import "MainWindowController.h"
#import "platform.h"
#import "character.h"
#import "character_store.h"
#import "config.h"
#import "notification.h"
#import "paths.h"
#import "week_id.h"
#import "lua_parser.h"
#import "util.h"
#import <sys/stat.h>
#import <objc/runtime.h>

/* Notification type constants */
NSString * const WSTNotifyInfo = @"info";
NSString * const WSTNotifySuccess = @"success";
NSString * const WSTNotifyWarning = @"warning";

/* App version - from generated version.h via types.h */
#import "types.h"
static NSString * const kAppVersion = @WST_VERSION;

/* Config keys */
static NSString * const kConfigWowPath = @"wow_path";
static NSString * const kConfigTheme = @"theme";
static NSString * const kConfigToolbarStyle = @"toolbar_style";
static NSString * const kConfigAutoImport = @"auto_import";
static NSString * const kConfigCheckUpdates = @"check_updates";
static NSString * const kConfigLastWeekId = @"last_week_id";
static NSString * const kConfigWindow = @"window";

@interface AppDelegate ()

@property (nonatomic, strong) MainWindowController *mainWindowController;
@property (nonatomic, assign) CharacterStore *characterStore;
@property (nonatomic, assign) Config *config;
@property (nonatomic, assign) NotificationStore *notificationStore;
@property (nonatomic, copy) NSString *configDir;
@property (nonatomic, copy) NSString *lockFile;
@property (nonatomic, assign) BOOL weeklyResetOccurred;
@property (nonatomic, assign) NSTimeInterval lastImportTime;

@end

@implementation AppDelegate

#pragma mark - Application Lifecycle

- (void)applicationDidFinishLaunching:(NSNotification *)notification {
    /* Set up config directory */
    char *configDir = paths_get_config_dir();
    if (!configDir) {
        [self showFatalError:@"Failed to get config directory"];
        [[NSApplication sharedApplication] terminate:nil];
        return;
    }
    self.configDir = [NSString stringWithUTF8String:configDir];
    free(configDir);

    /* Create config directory if needed */
    [[NSFileManager defaultManager] createDirectoryAtPath:self.configDir
                              withIntermediateDirectories:YES
                                               attributes:nil
                                                    error:nil];

    /* Set up lock file path */
    self.lockFile = [self.configDir stringByAppendingPathComponent:@"wowstat.lock"];

    /* Try to acquire single instance lock */
    WstResult lockResult = platform_lock_acquire([self.lockFile UTF8String]);
    if (lockResult != WST_OK) {
        [self showFatalError:@"Another instance is already running!"];
        [[NSApplication sharedApplication] terminate:nil];
        return;
    }

    /* Load character store */
    NSString *dataFile = [self.configDir stringByAppendingPathComponent:@"wowstat_data.json"];
    self.characterStore = character_store_new([dataFile UTF8String]);
    if (!self.characterStore) {
        [self showFatalError:@"Failed to create character store"];
        [[NSApplication sharedApplication] terminate:nil];
        return;
    }
    character_store_load(self.characterStore);

    /* Load config */
    NSString *configFile = [self.configDir stringByAppendingPathComponent:@"wowstat_config.json"];
    self.config = config_new([configFile UTF8String]);
    if (!self.config) {
        [self showFatalError:@"Failed to create config"];
        [[NSApplication sharedApplication] terminate:nil];
        return;
    }
    config_load(self.config);

    /* Load notification store */
    NSString *notifyFile = [self.configDir stringByAppendingPathComponent:@"notifications.json"];
    self.notificationStore = notification_store_new([notifyFile UTF8String]);
    if (self.notificationStore) {
        notification_store_load(self.notificationStore);
    }

    /* Check for weekly reset */
    self.weeklyResetOccurred = [self checkWeeklyReset];

    /* Create main menu */
    [self setupMainMenu];

    /* Create main window */
    self.mainWindowController = [[MainWindowController alloc] initWithDelegate:self];
    [self.mainWindowController showWindow:nil];

    /* Show weekly reset notification if occurred */
    if (self.weeklyResetOccurred) {
        dispatch_async(dispatch_get_main_queue(), ^{
            [self showNotification:@"Weekly data auto-reset for new WoW week." type:WSTNotifyInfo];
        });
    }

    /* Check for updates on startup if enabled */
    if ([self configBool:kConfigCheckUpdates]) {
        dispatch_async(dispatch_get_global_queue(DISPATCH_QUEUE_PRIORITY_LOW, 0), ^{
            [self checkForUpdates:NO];
        });
    }
}

- (void)applicationWillTerminate:(NSNotification *)notification {
    /* Save any pending changes */
    if (self.characterStore) {
        character_store_save(self.characterStore);
    }
    if (self.config) {
        config_save(self.config);
    }
    if (self.notificationStore) {
        notification_store_save(self.notificationStore);
    }

    /* Release lock */
    platform_lock_release([self.lockFile UTF8String]);

    /* Clean up */
    if (self.characterStore) {
        character_store_free(self.characterStore);
        self.characterStore = NULL;
    }
    if (self.config) {
        config_free(self.config);
        self.config = NULL;
    }
    if (self.notificationStore) {
        notification_store_free(self.notificationStore);
        self.notificationStore = NULL;
    }
}

- (BOOL)applicationShouldTerminateAfterLastWindowClosed:(NSApplication *)sender {
    return YES;
}

- (void)applicationDidBecomeActive:(NSNotification *)notification {
    /* Auto-import when window gains focus */
    if (![self configBool:kConfigAutoImport]) {
        return;
    }

    /* Debounce: don't import if we imported within the last 5 seconds */
    NSTimeInterval now = [[NSDate date] timeIntervalSince1970];
    if (now - self.lastImportTime < 5.0) {
        return;
    }

    self.lastImportTime = now;
    [self importFromAddon:YES];
}

#pragma mark - Menu Setup

- (void)setupMainMenu {
    NSMenu *mainMenu = [[NSMenu alloc] init];

    /* Application menu */
    NSMenuItem *appMenuItem = [[NSMenuItem alloc] init];
    NSMenu *appMenu = [[NSMenu alloc] init];
    [appMenuItem setSubmenu:appMenu];
    [mainMenu addItem:appMenuItem];

    [appMenu addItemWithTitle:@"About WoW Stat Tracker"
                       action:@selector(showAbout:)
                keyEquivalent:@""];
    [appMenu addItem:[NSMenuItem separatorItem]];
    [appMenu addItemWithTitle:@"Preferences..."
                       action:@selector(showPreferences:)
                keyEquivalent:@","];
    [appMenu addItem:[NSMenuItem separatorItem]];
    [appMenu addItemWithTitle:@"Quit WoW Stat Tracker"
                       action:@selector(terminate:)
                keyEquivalent:@"q"];

    /* File menu */
    NSMenuItem *fileMenuItem = [[NSMenuItem alloc] init];
    NSMenu *fileMenu = [[NSMenu alloc] initWithTitle:@"File"];
    [fileMenuItem setSubmenu:fileMenu];
    [mainMenu addItem:fileMenuItem];

    /* Characters menu */
    NSMenuItem *charsMenuItem = [[NSMenuItem alloc] init];
    NSMenu *charsMenu = [[NSMenu alloc] initWithTitle:@"Characters"];
    [charsMenuItem setSubmenu:charsMenu];
    [mainMenu addItem:charsMenuItem];

    [charsMenu addItemWithTitle:@"Add Character..."
                         action:@selector(addCharacter:)
                  keyEquivalent:@"n"];
    [charsMenu addItem:[NSMenuItem separatorItem]];
    [charsMenu addItemWithTitle:@"Reset Weekly Data"
                         action:@selector(resetWeeklyData:)
                  keyEquivalent:@""];

    /* Addon menu */
    NSMenuItem *addonMenuItem = [[NSMenuItem alloc] init];
    NSMenu *addonMenu = [[NSMenu alloc] initWithTitle:@"Addon"];
    [addonMenuItem setSubmenu:addonMenu];
    [mainMenu addItem:addonMenuItem];

    [addonMenu addItemWithTitle:@"Import from Addon"
                         action:@selector(importFromAddonAction:)
                  keyEquivalent:@"i"];
    [addonMenu addItem:[NSMenuItem separatorItem]];
    [addonMenu addItemWithTitle:@"Set WoW Location..."
                         action:@selector(setWowLocation:)
                  keyEquivalent:@""];
    [addonMenu addItemWithTitle:@"Install Addon"
                         action:@selector(installAddon:)
                  keyEquivalent:@""];
    [addonMenu addItemWithTitle:@"Uninstall Addon"
                         action:@selector(uninstallAddon:)
                  keyEquivalent:@""];

    /* View menu */
    NSMenuItem *viewMenuItem = [[NSMenuItem alloc] init];
    NSMenu *viewMenu = [[NSMenu alloc] initWithTitle:@"View"];
    [viewMenuItem setSubmenu:viewMenu];
    [mainMenu addItem:viewMenuItem];

    /* Theme submenu */
    NSMenuItem *themeMenuItem = [[NSMenuItem alloc] initWithTitle:@"Theme"
                                                           action:nil
                                                    keyEquivalent:@""];
    NSMenu *themeSubmenu = [[NSMenu alloc] initWithTitle:@"Theme"];
    [themeMenuItem setSubmenu:themeSubmenu];
    [viewMenu addItem:themeMenuItem];

    NSMenuItem *autoTheme = [[NSMenuItem alloc] initWithTitle:@"Auto (System)"
                                                       action:@selector(setThemeAuto:)
                                                keyEquivalent:@""];
    [themeSubmenu addItem:autoTheme];

    NSMenuItem *lightTheme = [[NSMenuItem alloc] initWithTitle:@"Light"
                                                        action:@selector(setThemeLight:)
                                                 keyEquivalent:@""];
    [themeSubmenu addItem:lightTheme];

    NSMenuItem *darkTheme = [[NSMenuItem alloc] initWithTitle:@"Dark"
                                                       action:@selector(setThemeDark:)
                                                keyEquivalent:@""];
    [themeSubmenu addItem:darkTheme];

    /* Help menu */
    NSMenuItem *helpMenuItem = [[NSMenuItem alloc] init];
    NSMenu *helpMenu = [[NSMenu alloc] initWithTitle:@"Help"];
    [helpMenuItem setSubmenu:helpMenu];
    [mainMenu addItem:helpMenuItem];

    [helpMenu addItemWithTitle:@"User Manual"
                        action:@selector(showManual:)
                 keyEquivalent:@""];
    [helpMenu addItemWithTitle:@"Check for Updates..."
                        action:@selector(checkForUpdatesAction:)
                 keyEquivalent:@""];

    [[NSApplication sharedApplication] setMainMenu:mainMenu];
}

#pragma mark - Menu Actions

- (void)showAbout:(id)sender {
    NSAlert *alert = [[NSAlert alloc] init];
    [alert setMessageText:@"WoW Stat Tracker"];
    [alert setInformativeText:[NSString stringWithFormat:
        @"Version %@\n\n"
        @"Track World of Warcraft character statistics and weekly progress.\n\n"
        @"BSD 3-Clause License",
        kAppVersion]];
    [alert addButtonWithTitle:@"OK"];
    [alert runModal];
}

- (void)showPreferences:(id)sender {
    [self.mainWindowController showPreferencesSheet];
}

- (void)addCharacter:(id)sender {
    [self.mainWindowController showAddCharacterSheet];
}

- (void)resetWeeklyData:(id)sender {
    NSAlert *alert = [[NSAlert alloc] init];
    [alert setMessageText:@"Reset Weekly Data?"];
    [alert setInformativeText:@"This will clear weekly progress for all characters."];
    [alert addButtonWithTitle:@"Reset"];
    [alert addButtonWithTitle:@"Cancel"];
    [[alert buttons][0] setKeyEquivalent:@""];
    [[alert buttons][1] setKeyEquivalent:@"\r"];

    if ([alert runModal] == NSAlertFirstButtonReturn) {
        character_store_reset_weekly_all(self.characterStore);
        character_store_save(self.characterStore);
        [self refreshTable];
        [self showNotification:@"Weekly data reset." type:WSTNotifySuccess];
    }
}

- (void)importFromAddonAction:(id)sender {
    [self importFromAddon:NO];
}

- (void)setWowLocation:(id)sender {
    NSOpenPanel *panel = [NSOpenPanel openPanel];
    [panel setCanChooseFiles:NO];
    [panel setCanChooseDirectories:YES];
    [panel setAllowsMultipleSelection:NO];
    [panel setTitle:@"Select World of Warcraft Folder"];
    [panel setMessage:@"Choose the folder containing '_retail_'"];

    NSString *currentPath = [self configString:kConfigWowPath];
    if (currentPath.length > 0) {
        [panel setDirectoryURL:[NSURL fileURLWithPath:currentPath]];
    }

    if ([panel runModal] == NSModalResponseOK) {
        NSString *path = [[panel URL] path];
        NSString *retailPath = [path stringByAppendingPathComponent:@"_retail_"];

        if ([[NSFileManager defaultManager] fileExistsAtPath:retailPath]) {
            [self setConfigString:kConfigWowPath value:path];
            config_save(self.config);
            [self showNotification:[NSString stringWithFormat:@"WoW path set to: %@", path]
                              type:WSTNotifySuccess];
        } else {
            NSAlert *alert = [[NSAlert alloc] init];
            [alert setMessageText:@"Invalid Selection"];
            [alert setInformativeText:@"The selected folder must contain a '_retail_' directory."];
            [alert addButtonWithTitle:@"OK"];
            [alert runModal];
        }
    }
}

- (void)installAddon:(id)sender {
    NSString *wowPath = [self getWowPath];
    if (!wowPath) return;

    NSString *addonsPath = [[wowPath stringByAppendingPathComponent:@"_retail_"]
                            stringByAppendingPathComponent:@"Interface/AddOns"];

    /* Create AddOns folder if needed */
    [[NSFileManager defaultManager] createDirectoryAtPath:addonsPath
                              withIntermediateDirectories:YES
                                               attributes:nil
                                                    error:nil];

    /* Find addon source */
    NSString *addonSource = [self findAddonSource];
    if (!addonSource) {
        NSAlert *alert = [[NSAlert alloc] init];
        [alert setMessageText:@"Addon Not Found"];
        [alert setInformativeText:@"Could not find the WoWStatTracker addon to install."];
        [alert addButtonWithTitle:@"OK"];
        [alert runModal];
        return;
    }

    /* Copy addon */
    NSString *destPath = [addonsPath stringByAppendingPathComponent:@"WoWStatTracker_Addon"];
    NSError *error = nil;

    /* Remove existing if present */
    [[NSFileManager defaultManager] removeItemAtPath:destPath error:nil];

    if ([[NSFileManager defaultManager] copyItemAtPath:addonSource toPath:destPath error:&error]) {
        [self showNotification:@"Addon installed. Restart WoW to load." type:WSTNotifySuccess];
    } else {
        NSAlert *alert = [[NSAlert alloc] init];
        [alert setMessageText:@"Installation Failed"];
        [alert setInformativeText:[error localizedDescription]];
        [alert addButtonWithTitle:@"OK"];
        [alert runModal];
    }
}

- (void)uninstallAddon:(id)sender {
    NSString *wowPath = [self getWowPath];
    if (!wowPath) return;

    NSString *addonPath = [[[wowPath stringByAppendingPathComponent:@"_retail_"]
                            stringByAppendingPathComponent:@"Interface/AddOns"]
                           stringByAppendingPathComponent:@"WoWStatTracker_Addon"];

    if (![[NSFileManager defaultManager] fileExistsAtPath:addonPath]) {
        NSAlert *alert = [[NSAlert alloc] init];
        [alert setMessageText:@"Addon Not Installed"];
        [alert setInformativeText:@"The WoWStatTracker addon is not currently installed."];
        [alert addButtonWithTitle:@"OK"];
        [alert runModal];
        return;
    }

    NSAlert *confirm = [[NSAlert alloc] init];
    [confirm setMessageText:@"Uninstall WoWStatTracker Addon?"];
    [confirm setInformativeText:@"This will remove the addon from WoW.\nYour saved character data will not be affected."];
    [confirm addButtonWithTitle:@"Uninstall"];
    [confirm addButtonWithTitle:@"Cancel"];

    if ([confirm runModal] == NSAlertFirstButtonReturn) {
        NSError *error = nil;
        if ([[NSFileManager defaultManager] removeItemAtPath:addonPath error:&error]) {
            [self showNotification:@"Addon uninstalled." type:WSTNotifySuccess];
        } else {
            NSAlert *alert = [[NSAlert alloc] init];
            [alert setMessageText:@"Uninstall Failed"];
            [alert setInformativeText:[error localizedDescription]];
            [alert addButtonWithTitle:@"OK"];
            [alert runModal];
        }
    }
}

- (void)setThemeAuto:(id)sender {
    [self setConfigString:kConfigTheme value:@"auto"];
    config_save(self.config);
    [self.mainWindowController applyTheme];
}

- (void)setThemeLight:(id)sender {
    [self setConfigString:kConfigTheme value:@"light"];
    config_save(self.config);
    [self.mainWindowController applyTheme];
}

- (void)setThemeDark:(id)sender {
    [self setConfigString:kConfigTheme value:@"dark"];
    config_save(self.config);
    [self.mainWindowController applyTheme];
}

- (void)showManual:(id)sender {
    /* Find manual file */
    NSString *manualPath = [[NSBundle mainBundle] pathForResource:@"MANUAL" ofType:@"txt"];
    if (!manualPath) {
        /* Development fallback */
        manualPath = [[[NSBundle mainBundle] bundlePath]
                      stringByAppendingPathComponent:@"../../../MANUAL.txt"];
    }

    if ([[NSFileManager defaultManager] fileExistsAtPath:manualPath]) {
        NSError *error = nil;
        NSString *content = [NSString stringWithContentsOfFile:manualPath
                                                      encoding:NSUTF8StringEncoding
                                                         error:&error];
        if (content) {
            [self.mainWindowController showManualWindow:content];
        } else {
            NSAlert *alert = [[NSAlert alloc] init];
            [alert setMessageText:@"Error"];
            [alert setInformativeText:@"Could not read manual file."];
            [alert addButtonWithTitle:@"OK"];
            [alert runModal];
        }
    } else {
        NSAlert *alert = [[NSAlert alloc] init];
        [alert setMessageText:@"Error"];
        [alert setInformativeText:@"Manual file not found."];
        [alert addButtonWithTitle:@"OK"];
        [alert runModal];
    }
}

- (void)checkForUpdatesAction:(id)sender {
    [self checkForUpdates:YES];
}

#pragma mark - Import Logic

- (void)importFromAddon:(BOOL)silent {
    NSString *addonFile = [self findAddonDataFile];
    if (!addonFile) {
        if (!silent) {
            NSAlert *alert = [[NSAlert alloc] init];
            [alert setMessageText:@"WoW Addon Data Not Found"];
            [alert setInformativeText:
                @"Could not find WoW Stat Tracker addon data.\n\n"
                @"Please ensure:\n"
                @"1. The WoW Stat Tracker addon is installed\n"
                @"2. You have logged in with your characters\n"
                @"3. The addon has exported data (/wst export)"];
            [alert addButtonWithTitle:@"OK"];
            [alert runModal];
        }
        return;
    }

    /* Parse addon data using LuaParseResult */
    LuaParseResult parseResult = lua_parser_parse_addon_file([addonFile UTF8String]);
    if (!parseResult.characters || parseResult.count == 0) {
        if (!silent) {
            NSAlert *alert = [[NSAlert alloc] init];
            [alert setMessageText:@"No Data Found"];
            [alert setInformativeText:@"Could not parse character data from addon file."];
            [alert addButtonWithTitle:@"OK"];
            [alert runModal];
        }
        lua_parser_free_result(&parseResult);
        return;
    }

    /* Check version mismatch */
    if (parseResult.addon_version && strcmp(parseResult.addon_version, [kAppVersion UTF8String]) != 0) {
        if (!silent) {
            [self showVersionMismatchWarning:[NSString stringWithUTF8String:parseResult.addon_version]];
        }
    }

    /* Get current week ID */
    char *currentWeekStr = week_id_current();

    /* Update characters */
    int updated = 0;
    int added = 0;

    for (size_t i = 0; i < parseResult.count; i++) {
        Character *addonChar = parseResult.characters[i];

        if (!addonChar || !addonChar->name || !addonChar->realm) {
            continue;
        }

        /* Find existing character */
        int existingIdx = character_store_find(self.characterStore, addonChar->realm, addonChar->name);

        if (existingIdx >= 0) {
            /* Update existing character */
            Character *existing = character_store_get(self.characterStore, (size_t)existingIdx);
            BOOL changed = [self updateCharacter:existing from:addonChar];
            if (changed) {
                updated++;
            }
        } else {
            /* Add new character - make a copy since store takes ownership */
            Character *newChar = character_copy(addonChar);
            if (newChar) {
                character_store_add(self.characterStore, newChar);
                added++;
            }
        }
    }

    /* Clean up */
    free(currentWeekStr);
    lua_parser_free_result(&parseResult);

    /* Save and refresh */
    if (updated > 0 || added > 0) {
        character_store_save(self.characterStore);
        [self refreshTable];

        if (!silent) {
            NSString *msg;
            if (updated > 0 && added > 0) {
                msg = [NSString stringWithFormat:@"Updated %d, added %d character%@.",
                       updated, added, (updated + added == 1) ? @"" : @"s"];
            } else if (updated > 0) {
                msg = [NSString stringWithFormat:@"Updated %d character%@.",
                       updated, updated == 1 ? @"" : @"s"];
            } else {
                msg = [NSString stringWithFormat:@"Added %d character%@.",
                       added, added == 1 ? @"" : @"s"];
            }
            [self showNotification:msg type:WSTNotifySuccess];
        }
    } else if (!silent) {
        [self showNotification:@"All characters up to date." type:WSTNotifyInfo];
    }
}

- (BOOL)updateCharacter:(Character *)existing from:(Character *)addon {
    BOOL changed = NO;

    /* Update non-weekly fields */
    if (addon->guild && (!existing->guild || strcmp(existing->guild, addon->guild) != 0)) {
        character_set_guild(existing, addon->guild);
        changed = YES;
    }
    if (addon->item_level != existing->item_level) {
        existing->item_level = addon->item_level;
        changed = YES;
    }
    if (addon->heroic_items != existing->heroic_items) {
        existing->heroic_items = addon->heroic_items;
        changed = YES;
    }
    if (addon->champion_items != existing->champion_items) {
        existing->champion_items = addon->champion_items;
        changed = YES;
    }
    if (addon->veteran_items != existing->veteran_items) {
        existing->veteran_items = addon->veteran_items;
        changed = YES;
    }
    if (addon->adventure_items != existing->adventure_items) {
        existing->adventure_items = addon->adventure_items;
        changed = YES;
    }
    if (addon->old_items != existing->old_items) {
        existing->old_items = addon->old_items;
        changed = YES;
    }

    /* Update weekly fields */
    if (addon->vault_visited != existing->vault_visited) {
        existing->vault_visited = addon->vault_visited;
        changed = YES;
    }
    if (addon->delves != existing->delves) {
        existing->delves = addon->delves;
        changed = YES;
    }
    if (addon->gilded_stash != existing->gilded_stash) {
        existing->gilded_stash = addon->gilded_stash;
        changed = YES;
    }
    if (addon->gearing_up != existing->gearing_up) {
        existing->gearing_up = addon->gearing_up;
        changed = YES;
    }
    if (addon->quests != existing->quests) {
        existing->quests = addon->quests;
        changed = YES;
    }
    if (addon->timewalk != existing->timewalk) {
        existing->timewalk = addon->timewalk;
        changed = YES;
    }

    return changed;
}

#pragma mark - Helper Methods

- (NSString *)getWowPath {
    NSString *wowPath = [self configString:kConfigWowPath];

    /* Check if already configured and valid */
    if (wowPath.length > 0 && [[NSFileManager defaultManager] fileExistsAtPath:wowPath]) {
        return wowPath;
    }

    /* Try default path */
    NSString *defaultPath = @"/Applications/World of Warcraft";
    NSString *retailPath = [defaultPath stringByAppendingPathComponent:@"_retail_"];
    if ([[NSFileManager defaultManager] fileExistsAtPath:retailPath]) {
        [self setConfigString:kConfigWowPath value:defaultPath];
        config_save(self.config);
        return defaultPath;
    }

    /* Prompt user */
    [self setWowLocation:nil];
    return [self configString:kConfigWowPath];
}

- (NSString *)findAddonDataFile {
    NSString *wowPath = [self getWowPath];
    if (!wowPath) return nil;

    NSString *wtfPath = [[wowPath stringByAppendingPathComponent:@"_retail_"]
                         stringByAppendingPathComponent:@"WTF/Account"];

    NSFileManager *fm = [NSFileManager defaultManager];
    if (![fm fileExistsAtPath:wtfPath]) return nil;

    NSArray *accounts = [fm contentsOfDirectoryAtPath:wtfPath error:nil];
    for (NSString *account in accounts) {
        if ([account hasPrefix:@"."]) continue;

        NSString *addonFile = [[[wtfPath stringByAppendingPathComponent:account]
                                stringByAppendingPathComponent:@"SavedVariables"]
                               stringByAppendingPathComponent:@"WoWStatTracker_Addon.lua"];

        if ([fm fileExistsAtPath:addonFile]) {
            return addonFile;
        }
    }

    return nil;
}

- (NSString *)findAddonSource {
    /* Check bundle Resources */
    NSString *bundlePath = [[NSBundle mainBundle] pathForResource:@"WoWStatTracker_Addon"
                                                           ofType:nil];
    if (bundlePath) return bundlePath;

    /* Development fallback */
    NSString *devPath = [[[NSBundle mainBundle] bundlePath]
                         stringByAppendingPathComponent:@"../../../WoWStatTracker_Addon"];
    if ([[NSFileManager defaultManager] fileExistsAtPath:devPath]) {
        return devPath;
    }

    return nil;
}

- (BOOL)checkWeeklyReset {
    char *currentWeekStr = week_id_current();
    if (!currentWeekStr) return NO;

    const char *lastWeekStr = config_get_string(self.config, [kConfigLastWeekId UTF8String], NULL);

    if (!lastWeekStr || strlen(lastWeekStr) == 0) {
        /* First run - just record current week */
        config_set_string(self.config, [kConfigLastWeekId UTF8String], currentWeekStr);
        config_save(self.config);
        free(currentWeekStr);
        return NO;
    }

    BOOL resetOccurred = !week_id_equal(currentWeekStr, lastWeekStr);
    if (resetOccurred) {
        /* Week changed - reset weekly data */
        character_store_reset_weekly_all(self.characterStore);
        character_store_save(self.characterStore);

        config_set_string(self.config, [kConfigLastWeekId UTF8String], currentWeekStr);
        config_save(self.config);
    }

    free(currentWeekStr);
    return resetOccurred;
}

- (void)checkForUpdates:(BOOL)showNoUpdate {
    /* Placeholder for update checking logic */
    /* Would use platform_http_get to check GitHub releases */
    if (showNoUpdate) {
        dispatch_async(dispatch_get_main_queue(), ^{
            [self showNotification:[NSString stringWithFormat:@"You're running the latest version (v%@).",
                                    kAppVersion]
                              type:WSTNotifySuccess];
        });
    }
}

- (void)showVersionMismatchWarning:(NSString *)addonVersion {
    NSString *msg = [NSString stringWithFormat:@"Version mismatch: addon v%@, GUI v%@",
                     addonVersion, kAppVersion];
    [self showNotification:msg type:WSTNotifyWarning];

    NSAlert *alert = [[NSAlert alloc] init];
    [alert setMessageText:@"Addon Version Mismatch"];
    [alert setInformativeText:[NSString stringWithFormat:
        @"The WoW addon version (v%@) does not match the GUI version (v%@).\n\n"
        @"This may cause data import issues. Please update both components to the same version.\n\n"
        @"You can reinstall the addon from: Addon > Install Addon",
        addonVersion, kAppVersion]];
    [alert addButtonWithTitle:@"OK"];
    [alert runModal];
}

#pragma mark - Config Helpers

- (NSString *)configString:(NSString *)key {
    const char *value = config_get_string(self.config, [key UTF8String], NULL);
    if (value) {
        return [NSString stringWithUTF8String:value];
    }
    return @"";
}

- (void)setConfigString:(NSString *)key value:(NSString *)value {
    config_set_string(self.config, [key UTF8String], [value UTF8String]);
}

- (BOOL)configBool:(NSString *)key {
    return config_get_bool(self.config, [key UTF8String], false);
}

- (void)setConfigBool:(NSString *)key value:(BOOL)value {
    config_set_bool(self.config, [key UTF8String], value);
}

- (int)configInt:(NSString *)key {
    return config_get_int(self.config, [key UTF8String], 0);
}

- (void)setConfigInt:(NSString *)key value:(int)value {
    config_set_int(self.config, [key UTF8String], value);
}

#pragma mark - Public Methods

- (void)showNotification:(NSString *)message type:(NSString *)type {
    /* Add to notification store */
    if (self.notificationStore) {
        WstNotifyType notifyType = WST_NOTIFY_INFO;
        if ([type isEqualToString:WSTNotifySuccess]) {
            notifyType = WST_NOTIFY_SUCCESS;
        } else if ([type isEqualToString:WSTNotifyWarning]) {
            notifyType = WST_NOTIFY_WARNING;
        }

        Notification *notification = notification_create([message UTF8String], notifyType);
        if (notification) {
            notification_store_add(self.notificationStore, notification);
            notification_store_save(self.notificationStore);
        }
    }

    /* Show in status bar */
    [self.mainWindowController showStatusMessage:message type:type];
}

- (void)refreshTable {
    [self.mainWindowController reloadTableData];
}

- (CharacterStore *)getCharacterStore {
    return self.characterStore;
}

- (Config *)getConfig {
    return self.config;
}

- (NotificationStore *)getNotificationStore {
    return self.notificationStore;
}

#pragma mark - Error Handling

- (void)showFatalError:(NSString *)message {
    NSAlert *alert = [[NSAlert alloc] init];
    [alert setMessageText:@"Fatal Error"];
    [alert setInformativeText:message];
    [alert setAlertStyle:NSAlertStyleCritical];
    [alert addButtonWithTitle:@"Quit"];
    [alert runModal];
}

@end
