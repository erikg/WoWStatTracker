/*
 * WoW Stat Tracker - Main Window Controller Implementation
 * BSD 3-Clause License
 */

#import "MainWindowController.h"
#import "AppDelegate.h"
#import "CharacterTableView.h"
#import "character.h"
#import "character_store.h"
#import "config.h"
#import "notification.h"
#import "platform.h"
#import "util.h"
#import <objc/runtime.h>

/* Toolbar item identifiers */
static NSString * const kToolbarAddCharacter = @"AddCharacter";
static NSString * const kToolbarImport = @"Import";
static NSString * const kToolbarResetWeekly = @"ResetWeekly";
static NSString * const kToolbarUpdateAddon = @"UpdateAddon";

/* Status bar constants */
static const NSTimeInterval kStatusDismissDelay = 5.0;

@interface MainWindowController () <CharacterTableViewDelegate>

@property (nonatomic, unsafe_unretained) AppDelegate *appDelegate;
@property (nonatomic, strong) CharacterTableView *tableView;
@property (nonatomic, strong) NSScrollView *scrollView;
@property (nonatomic, strong) NSToolbar *toolbar;
@property (nonatomic, strong) NSTextField *statusLabel;
@property (nonatomic, strong) NSButton *historyButton;
@property (nonatomic, strong) NSImageView *statusIcon;
@property (nonatomic, strong) NSView *statusBar;
@property (nonatomic, strong) NSTimer *statusTimer;
@property (nonatomic, strong) NSPanel *manualPanel;

@end

@implementation MainWindowController

#pragma mark - Initialization

- (instancetype)initWithDelegate:(AppDelegate *)delegate {
    /* Create main window */
    NSRect frame = NSMakeRect(0, 0, 1200, 600);
    NSWindowStyleMask style = NSWindowStyleMaskTitled |
                              NSWindowStyleMaskClosable |
                              NSWindowStyleMaskMiniaturizable |
                              NSWindowStyleMaskResizable;

    NSWindow *window = [[NSWindow alloc] initWithContentRect:frame
                                                   styleMask:style
                                                     backing:NSBackingStoreBuffered
                                                       defer:NO];
    [window setTitle:@"WoW Character Stat Tracker"];
    [window setMinSize:NSMakeSize(800, 400)];

    self = [super initWithWindow:window];
    if (self) {
        _appDelegate = delegate;
        [window setDelegate:self];

        [self setupUI];
        [self setupToolbar];
        [self restoreWindowState];
        [self applyTheme];
    }
    return self;
}

#pragma mark - UI Setup

- (void)setupUI {
    NSView *contentView = [[self window] contentView];

    /* Create scroll view for table */
    self.scrollView = [[NSScrollView alloc] initWithFrame:NSZeroRect];
    [self.scrollView setTranslatesAutoresizingMaskIntoConstraints:NO];
    [self.scrollView setHasVerticalScroller:YES];
    [self.scrollView setHasHorizontalScroller:YES];
    [self.scrollView setBorderType:NSBezelBorder];
    [self.scrollView setAutohidesScrollers:YES];
    [contentView addSubview:self.scrollView];

    /* Create table view */
    self.tableView = [[CharacterTableView alloc] initWithFrame:NSZeroRect];
    [self.tableView setTableDelegate:self];
    [self.tableView setCharacterStore:[self.appDelegate getCharacterStore]];
    [self.scrollView setDocumentView:self.tableView];

    /* Create status bar */
    self.statusBar = [[NSView alloc] initWithFrame:NSZeroRect];
    [self.statusBar setTranslatesAutoresizingMaskIntoConstraints:NO];
    [contentView addSubview:self.statusBar];

    /* Status bar contents */
    self.statusIcon = [[NSImageView alloc] initWithFrame:NSZeroRect];
    [self.statusIcon setTranslatesAutoresizingMaskIntoConstraints:NO];
    [self.statusIcon setHidden:YES];
    [self.statusBar addSubview:self.statusIcon];

    self.statusLabel = [[NSTextField alloc] initWithFrame:NSZeroRect];
    [self.statusLabel setTranslatesAutoresizingMaskIntoConstraints:NO];
    [self.statusLabel setBezeled:NO];
    [self.statusLabel setEditable:NO];
    [self.statusLabel setSelectable:NO];
    [self.statusLabel setDrawsBackground:NO];
    [self.statusLabel setStringValue:@""];
    [self.statusBar addSubview:self.statusLabel];

    self.historyButton = [[NSButton alloc] initWithFrame:NSZeroRect];
    [self.historyButton setTranslatesAutoresizingMaskIntoConstraints:NO];
    [self.historyButton setBezelStyle:NSBezelStyleInline];
    [self.historyButton setImage:[NSImage imageNamed:NSImageNameRevealFreestandingTemplate]];
    [self.historyButton setToolTip:@"Notification History"];
    [self.historyButton setTarget:self];
    [self.historyButton setAction:@selector(showNotificationHistory:)];
    [self.statusBar addSubview:self.historyButton];

    /* Layout constraints */
    NSDictionary *views = @{
        @"scroll": self.scrollView,
        @"status": self.statusBar,
        @"icon": self.statusIcon,
        @"label": self.statusLabel,
        @"history": self.historyButton
    };

    /* Scroll view fills most of the window */
    [contentView addConstraints:
     [NSLayoutConstraint constraintsWithVisualFormat:@"H:|-(10)-[scroll]-(10)-|"
                                             options:0
                                             metrics:nil
                                               views:views]];
    [contentView addConstraints:
     [NSLayoutConstraint constraintsWithVisualFormat:@"V:|-(10)-[scroll]-(0)-[status(24)]-(0)-|"
                                             options:0
                                             metrics:nil
                                               views:views]];
    [contentView addConstraints:
     [NSLayoutConstraint constraintsWithVisualFormat:@"H:|-(0)-[status]-(0)-|"
                                             options:0
                                             metrics:nil
                                               views:views]];

    /* Status bar internal layout */
    [self.statusBar addConstraints:
     [NSLayoutConstraint constraintsWithVisualFormat:@"H:|-(8)-[icon(16)]-(4)-[label]-(8)-[history(24)]-(8)-|"
                                             options:NSLayoutFormatAlignAllCenterY
                                             metrics:nil
                                               views:views]];
    [self.statusBar addConstraint:
     [NSLayoutConstraint constraintWithItem:self.statusIcon
                                  attribute:NSLayoutAttributeCenterY
                                  relatedBy:NSLayoutRelationEqual
                                     toItem:self.statusBar
                                  attribute:NSLayoutAttributeCenterY
                                 multiplier:1.0
                                   constant:0]];
    [self.statusBar addConstraint:
     [NSLayoutConstraint constraintWithItem:self.statusIcon
                                  attribute:NSLayoutAttributeHeight
                                  relatedBy:NSLayoutRelationEqual
                                     toItem:nil
                                  attribute:NSLayoutAttributeNotAnAttribute
                                 multiplier:1.0
                                   constant:16]];
}

- (void)setupToolbar {
    self.toolbar = [[NSToolbar alloc] initWithIdentifier:@"MainToolbar"];
    [self.toolbar setDelegate:self];
    [self.toolbar setDisplayMode:NSToolbarDisplayModeIconAndLabel];
    [self.toolbar setAllowsUserCustomization:NO];
    [[self window] setToolbar:self.toolbar];
}

#pragma mark - NSToolbarDelegate

- (NSArray<NSToolbarItemIdentifier> *)toolbarDefaultItemIdentifiers:(NSToolbar *)toolbar {
    return @[
        kToolbarAddCharacter,
        kToolbarImport,
        kToolbarResetWeekly,
        kToolbarUpdateAddon,
        NSToolbarFlexibleSpaceItemIdentifier
    ];
}

- (NSArray<NSToolbarItemIdentifier> *)toolbarAllowedItemIdentifiers:(NSToolbar *)toolbar {
    return [self toolbarDefaultItemIdentifiers:toolbar];
}

- (NSToolbarItem *)toolbar:(NSToolbar *)toolbar
     itemForItemIdentifier:(NSToolbarItemIdentifier)itemIdentifier
 willBeInsertedIntoToolbar:(BOOL)flag {

    NSToolbarItem *item = [[NSToolbarItem alloc] initWithItemIdentifier:itemIdentifier];

    if ([itemIdentifier isEqualToString:kToolbarAddCharacter]) {
        [item setLabel:@"Add Character"];
        [item setImage:[NSImage imageNamed:NSImageNameAddTemplate]];
        [item setToolTip:@"Add a new character"];
        [item setTarget:self];
        [item setAction:@selector(addCharacterClicked:)];
    } else if ([itemIdentifier isEqualToString:kToolbarImport]) {
        [item setLabel:@"Import"];
        [item setImage:[NSImage imageNamed:NSImageNameRefreshTemplate]];
        [item setToolTip:@"Import data from WoW addon"];
        [item setTarget:self.appDelegate];
        [item setAction:@selector(importFromAddonAction:)];
    } else if ([itemIdentifier isEqualToString:kToolbarResetWeekly]) {
        [item setLabel:@"Reset Weekly"];
        [item setImage:[NSImage imageNamed:NSImageNameRefreshFreestandingTemplate]];
        [item setToolTip:@"Reset all weekly activity data"];
        [item setTarget:self.appDelegate];
        [item setAction:@selector(resetWeeklyData:)];
    } else if ([itemIdentifier isEqualToString:kToolbarUpdateAddon]) {
        [item setLabel:@"Update Addon"];
        [item setImage:[NSImage imageNamed:NSImageNameNetwork]];
        [item setToolTip:@"Install/update addon in WoW"];
        [item setTarget:self.appDelegate];
        [item setAction:@selector(installAddon:)];
    }

    return item;
}

#pragma mark - Window Delegate

- (void)windowWillClose:(NSNotification *)notification {
    [self saveWindowState];
}

- (void)windowDidResize:(NSNotification *)notification {
    [self scheduleWindowStateSave];
}

- (void)windowDidMove:(NSNotification *)notification {
    [self scheduleWindowStateSave];
}

#pragma mark - Window State Persistence

- (void)restoreWindowState {
    Config *config = [self.appDelegate getConfig];
    if (!config) return;

    const char *windowJson = config_get_string(config, "window", NULL);
    if (!windowJson || strlen(windowJson) == 0) {
        [[self window] center];
        return;
    }

    /* Parse window state from JSON */
    NSData *data = [[NSString stringWithUTF8String:windowJson] dataUsingEncoding:NSUTF8StringEncoding];
    NSDictionary *state = [NSJSONSerialization JSONObjectWithData:data options:0 error:nil];
    if (!state) {
        [[self window] center];
        return;
    }

    CGFloat width = [state[@"width"] doubleValue] ?: 1200;
    CGFloat height = [state[@"height"] doubleValue] ?: 600;
    CGFloat x = [state[@"x"] doubleValue];
    CGFloat y = [state[@"y"] doubleValue];
    BOOL maximized = [state[@"maximized"] boolValue];

    /* Clamp to reasonable values */
    width = MAX(800, MIN(3840, width));
    height = MAX(400, MIN(2160, height));

    NSRect frame = NSMakeRect(x, y, width, height);
    [[self window] setFrame:frame display:YES];

    if (maximized) {
        [[self window] zoom:nil];
    }
}

- (void)saveWindowState {
    Config *config = [self.appDelegate getConfig];
    if (!config) return;

    NSRect frame = [[self window] frame];
    BOOL isZoomed = [[self window] isZoomed];

    NSDictionary *state = @{
        @"width": @(frame.size.width),
        @"height": @(frame.size.height),
        @"x": @(frame.origin.x),
        @"y": @(frame.origin.y),
        @"maximized": @(isZoomed)
    };

    NSData *data = [NSJSONSerialization dataWithJSONObject:state options:0 error:nil];
    NSString *json = [[NSString alloc] initWithData:data encoding:NSUTF8StringEncoding];
    config_set_string(config, "window", [json UTF8String]);
    config_save(config);
}

- (void)scheduleWindowStateSave {
    /* Debounce window state saves */
    [NSObject cancelPreviousPerformRequestsWithTarget:self
                                             selector:@selector(saveWindowState)
                                               object:nil];
    [self performSelector:@selector(saveWindowState)
               withObject:nil
               afterDelay:0.5];
}

#pragma mark - Table Management

- (void)reloadTableData {
    CharacterStore *store = [self.appDelegate getCharacterStore];
    if (!store) return;

    [self.tableView reloadWithCharacterStore:store];
}

#pragma mark - CharacterTableViewDelegate

- (void)characterTableView:(CharacterTableView *)tableView didDoubleClickRow:(NSInteger)row {
    [self showEditCharacterSheetForIndex:row];
}

- (void)characterTableView:(CharacterTableView *)tableView didToggleColumn:(NSInteger)column row:(NSInteger)row newValue:(BOOL)value {
    CharacterStore *store = [self.appDelegate getCharacterStore];
    if (!store) return;

    Character *character = character_store_get(store, (size_t)row);
    if (!character) return;

    /* Update the appropriate field */
    switch (column) {
        case 9: /* vault_visited */
            character->vault_visited = value;
            break;
        case 12: /* gearing_up */
            character->gearing_up = value;
            break;
        case 13: /* quests */
            character->quests = value;
            break;
        default:
            return;
    }

    character_store_save(store);
    [self reloadTableData];
}

- (void)characterTableView:(CharacterTableView *)tableView didEditNotes:(NSString *)notes forRow:(NSInteger)row {
    CharacterStore *store = [self.appDelegate getCharacterStore];
    if (!store) return;

    Character *character = character_store_get(store, (size_t)row);
    if (!character) return;

    character_set_notes(character, [notes UTF8String]);
    character_store_save(store);
}

#pragma mark - Sheets and Dialogs

- (void)addCharacterClicked:(id)sender {
    [self showAddCharacterSheet];
}

- (void)showAddCharacterSheet {
    [self showCharacterSheetForIndex:-1];
}

- (void)showEditCharacterSheetForIndex:(NSInteger)index {
    [self showCharacterSheetForIndex:index];
}

- (void)showCharacterSheetForIndex:(NSInteger)index {
    CharacterStore *store = [self.appDelegate getCharacterStore];
    if (!store) return;

    const Character *existing = (index >= 0) ? character_store_get(store, (size_t)index) : NULL;

    /* Create sheet window */
    NSRect frame = NSMakeRect(0, 0, 400, 520);
    NSWindow *sheet = [[NSWindow alloc] initWithContentRect:frame
                                                  styleMask:NSWindowStyleMaskTitled
                                                    backing:NSBackingStoreBuffered
                                                      defer:NO];
    [sheet setTitle:(index >= 0) ? @"Edit Character" : @"Add Character"];

    NSView *content = [sheet contentView];

    /* Create form fields */
    NSArray *fieldNames = @[
        @"Realm:", @"Name:", @"Guild:", @"Item Level:",
        @"Heroic Items:", @"Champion Items:", @"Veteran Items:",
        @"Adventure Items:", @"Old Items:", @"Vault Visited:",
        @"Delves (0-8):", @"Gilded Stash (0-3):", @"Gearing Up:",
        @"World Quests:", @"Timewalk (0-5):", @"Notes:"
    ];

    NSMutableArray *controls = [NSMutableArray array];
    CGFloat y = frame.size.height - 40;

    for (NSUInteger i = 0; i < fieldNames.count; i++) {
        NSString *fieldName = fieldNames[i];

        /* Label */
        NSTextField *label = [[NSTextField alloc] initWithFrame:NSMakeRect(20, y, 120, 22)];
        [label setStringValue:fieldName];
        [label setBezeled:NO];
        [label setEditable:NO];
        [label setSelectable:NO];
        [label setDrawsBackground:NO];
        [label setAlignment:NSTextAlignmentRight];
        [content addSubview:label];

        /* Control */
        NSControl *control;
        NSInteger fieldIndex = (NSInteger)i;

        if (fieldIndex == 9 || fieldIndex == 12 || fieldIndex == 13) {
            /* Boolean checkbox */
            NSButton *checkbox = [[NSButton alloc] initWithFrame:NSMakeRect(150, y, 200, 22)];
            [checkbox setButtonType:NSButtonTypeSwitch];
            [checkbox setTitle:@""];
            control = checkbox;
        } else if (fieldIndex >= 3 && fieldIndex != 15) {
            /* Numeric field */
            NSTextField *field = [[NSTextField alloc] initWithFrame:NSMakeRect(150, y, 100, 22)];
            control = field;
        } else {
            /* Text field */
            NSTextField *field = [[NSTextField alloc] initWithFrame:NSMakeRect(150, y, 200, 22)];
            control = field;
        }

        [content addSubview:control];
        [controls addObject:control];

        y -= 28;
    }

    /* Populate fields if editing */
    if (existing) {
        [(NSTextField *)controls[0] setStringValue:existing->realm ? [NSString stringWithUTF8String:existing->realm] : @""];
        [(NSTextField *)controls[1] setStringValue:existing->name ? [NSString stringWithUTF8String:existing->name] : @""];
        [(NSTextField *)controls[2] setStringValue:existing->guild ? [NSString stringWithUTF8String:existing->guild] : @""];
        [(NSTextField *)controls[3] setDoubleValue:existing->item_level];
        [(NSTextField *)controls[4] setIntegerValue:existing->heroic_items];
        [(NSTextField *)controls[5] setIntegerValue:existing->champion_items];
        [(NSTextField *)controls[6] setIntegerValue:existing->veteran_items];
        [(NSTextField *)controls[7] setIntegerValue:existing->adventure_items];
        [(NSTextField *)controls[8] setIntegerValue:existing->old_items];
        [(NSButton *)controls[9] setState:existing->vault_visited ? NSControlStateValueOn : NSControlStateValueOff];
        [(NSTextField *)controls[10] setIntegerValue:existing->delves];
        [(NSTextField *)controls[11] setIntegerValue:existing->gilded_stash];
        [(NSButton *)controls[12] setState:existing->gearing_up ? NSControlStateValueOn : NSControlStateValueOff];
        [(NSButton *)controls[13] setState:existing->quests ? NSControlStateValueOn : NSControlStateValueOff];
        [(NSTextField *)controls[14] setIntegerValue:existing->timewalk];
        [(NSTextField *)controls[15] setStringValue:existing->notes ? [NSString stringWithUTF8String:existing->notes] : @""];
    }

    /* Buttons */
    NSButton *cancelButton = [[NSButton alloc] initWithFrame:NSMakeRect(200, 10, 80, 30)];
    [cancelButton setTitle:@"Cancel"];
    [cancelButton setBezelStyle:NSBezelStyleRounded];
    [cancelButton setKeyEquivalent:@"\e"];
    [content addSubview:cancelButton];

    NSButton *saveButton = [[NSButton alloc] initWithFrame:NSMakeRect(290, 10, 80, 30)];
    [saveButton setTitle:@"Save"];
    [saveButton setBezelStyle:NSBezelStyleRounded];
    [saveButton setKeyEquivalent:@"\r"];
    [content addSubview:saveButton];

    NSButton *deleteButton = nil;
    if (index >= 0) {
        deleteButton = [[NSButton alloc] initWithFrame:NSMakeRect(20, 10, 80, 30)];
        [deleteButton setTitle:@"Delete"];
        [deleteButton setBezelStyle:NSBezelStyleRounded];
        [content addSubview:deleteButton];
    }

    /* Show as sheet */
    [[self window] beginSheet:sheet completionHandler:^(NSModalResponse returnCode) {
        if (returnCode == NSModalResponseOK) {
            /* Create character */
            Character *newChar = character_new();
            if (!newChar) return;

            character_set_realm(newChar, [[(NSTextField *)controls[0] stringValue] UTF8String]);
            character_set_name(newChar, [[(NSTextField *)controls[1] stringValue] UTF8String]);
            character_set_guild(newChar, [[(NSTextField *)controls[2] stringValue] UTF8String]);
            newChar->item_level = [(NSTextField *)controls[3] doubleValue];
            newChar->heroic_items = (int)[(NSTextField *)controls[4] integerValue];
            newChar->champion_items = (int)[(NSTextField *)controls[5] integerValue];
            newChar->veteran_items = (int)[(NSTextField *)controls[6] integerValue];
            newChar->adventure_items = (int)[(NSTextField *)controls[7] integerValue];
            newChar->old_items = (int)[(NSTextField *)controls[8] integerValue];
            newChar->vault_visited = [(NSButton *)controls[9] state] == NSControlStateValueOn;
            newChar->delves = (int)[(NSTextField *)controls[10] integerValue];
            newChar->gilded_stash = (int)[(NSTextField *)controls[11] integerValue];
            newChar->gearing_up = [(NSButton *)controls[12] state] == NSControlStateValueOn;
            newChar->quests = [(NSButton *)controls[13] state] == NSControlStateValueOn;
            newChar->timewalk = (int)[(NSTextField *)controls[14] integerValue];
            character_set_notes(newChar, [[(NSTextField *)controls[15] stringValue] UTF8String]);

            /* Validate */
            char **errors = NULL;
            size_t errorCount = 0;
            WstResult result = character_validate(newChar, &errors, &errorCount);

            if (result != WST_OK && errorCount > 0) {
                NSMutableString *errorMsg = [NSMutableString string];
                for (size_t i = 0; i < errorCount; i++) {
                    [errorMsg appendFormat:@"%s\n", errors[i]];
                }
                character_free_errors(errors, errorCount);
                character_free(newChar);

                NSAlert *alert = [[NSAlert alloc] init];
                [alert setMessageText:@"Validation Error"];
                [alert setInformativeText:errorMsg];
                [alert addButtonWithTitle:@"OK"];
                [alert runModal];
                return;
            }

            if (index >= 0) {
                character_store_update(store, (size_t)index, newChar);
            } else {
                character_store_add(store, newChar);
            }

            character_store_save(store);
            [self reloadTableData];

        } else if (returnCode == NSModalResponseAbort) {
            /* Delete character */
            if (index >= 0) {
                character_store_delete(store, (size_t)index);
                character_store_save(store);
                [self reloadTableData];
            }
        }
    }];

    /* Button actions */
    [cancelButton setTarget:self];
    [cancelButton setAction:@selector(cancelSheet:)];
    [saveButton setTarget:self];
    [saveButton setAction:@selector(saveSheet:)];
    if (deleteButton) {
        [deleteButton setTarget:self];
        [deleteButton setAction:@selector(deleteFromSheet:)];
    }

    /* Store sheet reference */
    objc_setAssociatedObject(cancelButton, "sheet", sheet, OBJC_ASSOCIATION_RETAIN);
    objc_setAssociatedObject(saveButton, "sheet", sheet, OBJC_ASSOCIATION_RETAIN);
    if (deleteButton) {
        objc_setAssociatedObject(deleteButton, "sheet", sheet, OBJC_ASSOCIATION_RETAIN);
    }
}

- (void)cancelSheet:(NSButton *)sender {
    NSWindow *sheet = objc_getAssociatedObject(sender, "sheet");
    [[self window] endSheet:sheet returnCode:NSModalResponseCancel];
}

- (void)saveSheet:(NSButton *)sender {
    NSWindow *sheet = objc_getAssociatedObject(sender, "sheet");
    [[self window] endSheet:sheet returnCode:NSModalResponseOK];
}

- (void)deleteFromSheet:(NSButton *)sender {
    NSAlert *confirm = [[NSAlert alloc] init];
    [confirm setMessageText:@"Delete Character?"];
    [confirm setInformativeText:@"This action cannot be undone."];
    [confirm addButtonWithTitle:@"Delete"];
    [confirm addButtonWithTitle:@"Cancel"];

    if ([confirm runModal] == NSAlertFirstButtonReturn) {
        NSWindow *sheet = objc_getAssociatedObject(sender, "sheet");
        [[self window] endSheet:sheet returnCode:NSModalResponseAbort];
    }
}

- (void)showPreferencesSheet {
    Config *config = [self.appDelegate getConfig];
    if (!config) return;

    /* Create preferences window */
    NSRect frame = NSMakeRect(0, 0, 450, 300);
    NSWindow *sheet = [[NSWindow alloc] initWithContentRect:frame
                                                  styleMask:NSWindowStyleMaskTitled
                                                    backing:NSBackingStoreBuffered
                                                      defer:NO];
    [sheet setTitle:@"Preferences"];

    NSView *content = [sheet contentView];
    CGFloat y = frame.size.height - 50;

    /* WoW Path */
    NSTextField *pathLabel = [[NSTextField alloc] initWithFrame:NSMakeRect(20, y, 100, 22)];
    [pathLabel setStringValue:@"WoW Path:"];
    [pathLabel setBezeled:NO];
    [pathLabel setEditable:NO];
    [pathLabel setSelectable:NO];
    [pathLabel setDrawsBackground:NO];
    [content addSubview:pathLabel];

    NSTextField *pathField = [[NSTextField alloc] initWithFrame:NSMakeRect(130, y, 220, 22)];
    const char *pathStr = config_get_string(config, "wow_path", NULL);
    [pathField setStringValue:pathStr ? [NSString stringWithUTF8String:pathStr] : @""];
    [content addSubview:pathField];

    NSButton *browseButton = [[NSButton alloc] initWithFrame:NSMakeRect(360, y, 70, 22)];
    [browseButton setTitle:@"Browse"];
    [browseButton setBezelStyle:NSBezelStyleRounded];
    [content addSubview:browseButton];

    y -= 40;

    /* Theme */
    NSTextField *themeLabel = [[NSTextField alloc] initWithFrame:NSMakeRect(20, y, 100, 22)];
    [themeLabel setStringValue:@"Theme:"];
    [themeLabel setBezeled:NO];
    [themeLabel setEditable:NO];
    [themeLabel setSelectable:NO];
    [themeLabel setDrawsBackground:NO];
    [content addSubview:themeLabel];

    NSPopUpButton *themePopup = [[NSPopUpButton alloc] initWithFrame:NSMakeRect(130, y, 200, 26) pullsDown:NO];
    [themePopup addItemWithTitle:@"Auto (System)"];
    [themePopup addItemWithTitle:@"Light"];
    [themePopup addItemWithTitle:@"Dark"];

    const char *themeStr = config_get_string(config, "theme", NULL);
    if (themeStr) {
        if (strcmp(themeStr, "light") == 0) {
            [themePopup selectItemAtIndex:1];
        } else if (strcmp(themeStr, "dark") == 0) {
            [themePopup selectItemAtIndex:2];
        }
    }
    [content addSubview:themePopup];

    y -= 40;

    /* Auto-import */
    NSButton *autoImportCheck = [[NSButton alloc] initWithFrame:NSMakeRect(130, y, 250, 22)];
    [autoImportCheck setButtonType:NSButtonTypeSwitch];
    [autoImportCheck setTitle:@"Auto-import when window is focused"];
    [autoImportCheck setState:config_get_bool(config, "auto_import", false) ? NSControlStateValueOn : NSControlStateValueOff];
    [content addSubview:autoImportCheck];

    y -= 30;

    /* Check updates */
    NSButton *checkUpdatesCheck = [[NSButton alloc] initWithFrame:NSMakeRect(130, y, 250, 22)];
    [checkUpdatesCheck setButtonType:NSButtonTypeSwitch];
    [checkUpdatesCheck setTitle:@"Check for updates on startup"];
    [checkUpdatesCheck setState:config_get_bool(config, "check_updates", false) ? NSControlStateValueOn : NSControlStateValueOff];
    [content addSubview:checkUpdatesCheck];

    /* Buttons */
    NSButton *cancelButton = [[NSButton alloc] initWithFrame:NSMakeRect(270, 10, 80, 30)];
    [cancelButton setTitle:@"Cancel"];
    [cancelButton setBezelStyle:NSBezelStyleRounded];
    [cancelButton setKeyEquivalent:@"\e"];
    [content addSubview:cancelButton];

    NSButton *okButton = [[NSButton alloc] initWithFrame:NSMakeRect(360, 10, 70, 30)];
    [okButton setTitle:@"OK"];
    [okButton setBezelStyle:NSBezelStyleRounded];
    [okButton setKeyEquivalent:@"\r"];
    [content addSubview:okButton];

    /* Store references for handler */
    NSDictionary *ctrls = @{
        @"pathField": pathField,
        @"themePopup": themePopup,
        @"autoImport": autoImportCheck,
        @"checkUpdates": checkUpdatesCheck
    };
    objc_setAssociatedObject(sheet, "controls", ctrls, OBJC_ASSOCIATION_RETAIN);

    /* Show as sheet */
    [[self window] beginSheet:sheet completionHandler:^(NSModalResponse returnCode) {
        if (returnCode == NSModalResponseOK) {
            NSDictionary *controls = objc_getAssociatedObject(sheet, "controls");

            /* Save settings */
            NSString *path = [(NSTextField *)controls[@"pathField"] stringValue];
            config_set_string(config, "wow_path", [path UTF8String]);

            NSInteger themeIndex = [(NSPopUpButton *)controls[@"themePopup"] indexOfSelectedItem];
            NSString *theme = (themeIndex == 1) ? @"light" : (themeIndex == 2) ? @"dark" : @"auto";
            config_set_string(config, "theme", [theme UTF8String]);

            BOOL autoImport = [(NSButton *)controls[@"autoImport"] state] == NSControlStateValueOn;
            config_set_bool(config, "auto_import", autoImport);

            BOOL checkUpdates = [(NSButton *)controls[@"checkUpdates"] state] == NSControlStateValueOn;
            config_set_bool(config, "check_updates", checkUpdates);

            config_save(config);
            [self applyTheme];
        }
    }];

    /* Button actions */
    [cancelButton setTarget:self];
    [cancelButton setAction:@selector(cancelSheet:)];
    [okButton setTarget:self];
    [okButton setAction:@selector(saveSheet:)];

    objc_setAssociatedObject(cancelButton, "sheet", sheet, OBJC_ASSOCIATION_RETAIN);
    objc_setAssociatedObject(okButton, "sheet", sheet, OBJC_ASSOCIATION_RETAIN);
}

- (void)showManualWindow:(NSString *)content {
    if (!self.manualPanel) {
        self.manualPanel = [[NSPanel alloc] initWithContentRect:NSMakeRect(0, 0, 600, 500)
                                                      styleMask:NSWindowStyleMaskTitled |
                                                                NSWindowStyleMaskClosable |
                                                                NSWindowStyleMaskResizable
                                                        backing:NSBackingStoreBuffered
                                                          defer:NO];
        [self.manualPanel setTitle:@"User Manual"];

        NSScrollView *scrollView = [[NSScrollView alloc] initWithFrame:[[self.manualPanel contentView] bounds]];
        [scrollView setAutoresizingMask:NSViewWidthSizable | NSViewHeightSizable];
        [scrollView setHasVerticalScroller:YES];

        NSTextView *textView = [[NSTextView alloc] initWithFrame:[[scrollView contentView] bounds]];
        [textView setAutoresizingMask:NSViewWidthSizable | NSViewHeightSizable];
        [textView setEditable:NO];
        [textView setFont:[NSFont fontWithName:@"Menlo" size:12]];
        [textView setTextContainerInset:NSMakeSize(10, 10)];

        [scrollView setDocumentView:textView];
        [[self.manualPanel contentView] addSubview:scrollView];

        objc_setAssociatedObject(self.manualPanel, "textView", textView, OBJC_ASSOCIATION_RETAIN);
    }

    NSTextView *textView = objc_getAssociatedObject(self.manualPanel, "textView");
    [textView setString:content];
    [self.manualPanel center];
    [self.manualPanel makeKeyAndOrderFront:nil];
}

#pragma mark - Status Bar

- (void)showStatusMessage:(NSString *)message type:(NSString *)type {
    /* Cancel any pending dismiss */
    [self.statusTimer invalidate];

    /* Set icon based on type */
    NSImage *icon;
    if ([type isEqualToString:WSTNotifySuccess]) {
        icon = [NSImage imageNamed:NSImageNameStatusAvailable];
    } else if ([type isEqualToString:WSTNotifyWarning]) {
        icon = [NSImage imageNamed:NSImageNameCaution];
    } else {
        icon = [NSImage imageNamed:NSImageNameInfo];
    }
    [self.statusIcon setImage:icon];
    [self.statusIcon setHidden:NO];

    /* Set message */
    [self.statusLabel setStringValue:message];

    /* Schedule auto-dismiss */
    self.statusTimer = [NSTimer scheduledTimerWithTimeInterval:kStatusDismissDelay
                                                        target:self
                                                      selector:@selector(dismissStatus:)
                                                      userInfo:nil
                                                       repeats:NO];
}

- (void)dismissStatus:(NSTimer *)timer {
    [self.statusIcon setHidden:YES];
    [self.statusLabel setStringValue:@""];
}

- (void)showNotificationHistory:(id)sender {
    NotificationStore *store = [self.appDelegate getNotificationStore];
    if (!store) return;

    /* Create popover with notification list */
    NSPopover *popover = [[NSPopover alloc] init];
    [popover setBehavior:NSPopoverBehaviorTransient];

    /* Create content view controller */
    NSViewController *vc = [[NSViewController alloc] init];
    NSView *contentView = [[NSView alloc] initWithFrame:NSMakeRect(0, 0, 350, 300)];

    /* Title */
    NSTextField *title = [[NSTextField alloc] initWithFrame:NSMakeRect(10, 270, 200, 20)];
    [title setStringValue:@"Notifications"];
    [title setBezeled:NO];
    [title setEditable:NO];
    [title setSelectable:NO];
    [title setDrawsBackground:NO];
    [title setFont:[NSFont boldSystemFontOfSize:14]];
    [contentView addSubview:title];

    /* Clear All button */
    NSButton *clearButton = [[NSButton alloc] initWithFrame:NSMakeRect(260, 265, 80, 25)];
    [clearButton setTitle:@"Clear All"];
    [clearButton setBezelStyle:NSBezelStyleRounded];
    [clearButton setTarget:self];
    [clearButton setAction:@selector(clearAllNotifications:)];
    objc_setAssociatedObject(clearButton, "popover", popover, OBJC_ASSOCIATION_RETAIN);
    [contentView addSubview:clearButton];

    /* Scroll view for notifications */
    NSScrollView *scrollView = [[NSScrollView alloc] initWithFrame:NSMakeRect(10, 10, 330, 250)];
    [scrollView setHasVerticalScroller:YES];
    [scrollView setBorderType:NSBezelBorder];

    /* List content */
    NSView *listView = [[NSView alloc] initWithFrame:NSMakeRect(0, 0, 310, 250)];
    CGFloat y = 240;

    size_t count = notification_store_count(store);
    if (count == 0) {
        NSTextField *emptyLabel = [[NSTextField alloc] initWithFrame:NSMakeRect(10, 110, 290, 30)];
        [emptyLabel setStringValue:@"No notifications"];
        [emptyLabel setBezeled:NO];
        [emptyLabel setEditable:NO];
        [emptyLabel setSelectable:NO];
        [emptyLabel setDrawsBackground:NO];
        [emptyLabel setAlignment:NSTextAlignmentCenter];
        [emptyLabel setTextColor:[NSColor secondaryLabelColor]];
        [listView addSubview:emptyLabel];
    } else {
        for (size_t i = 0; i < count; i++) {
            Notification *notif = notification_store_get(store, i);
            if (!notif) continue;

            y -= 50;

            /* Message */
            NSTextField *msgLabel = [[NSTextField alloc] initWithFrame:NSMakeRect(10, y + 20, 280, 20)];
            [msgLabel setStringValue:notif->message ? [NSString stringWithUTF8String:notif->message] : @""];
            [msgLabel setBezeled:NO];
            [msgLabel setEditable:NO];
            [msgLabel setSelectable:NO];
            [msgLabel setDrawsBackground:NO];
            [msgLabel setLineBreakMode:NSLineBreakByTruncatingTail];
            [listView addSubview:msgLabel];

            /* Timestamp */
            NSTextField *timeLabel = [[NSTextField alloc] initWithFrame:NSMakeRect(10, y, 280, 16)];
            char *formatted = notification_format_timestamp(notif);
            [timeLabel setStringValue:formatted ? [NSString stringWithUTF8String:formatted] : @""];
            free(formatted);
            [timeLabel setBezeled:NO];
            [timeLabel setEditable:NO];
            [timeLabel setSelectable:NO];
            [timeLabel setDrawsBackground:NO];
            [timeLabel setFont:[NSFont systemFontOfSize:10]];
            [timeLabel setTextColor:[NSColor secondaryLabelColor]];
            [listView addSubview:timeLabel];
        }

        /* Adjust list view height */
        CGFloat listHeight = MAX(250, count * 50);
        [listView setFrameSize:NSMakeSize(310, listHeight)];
    }

    [scrollView setDocumentView:listView];
    [contentView addSubview:scrollView];

    [vc setView:contentView];
    [popover setContentViewController:vc];
    [popover showRelativeToRect:[self.historyButton bounds]
                         ofView:self.historyButton
                  preferredEdge:NSRectEdgeMaxY];
}

- (void)clearAllNotifications:(NSButton *)sender {
    NotificationStore *store = [self.appDelegate getNotificationStore];
    if (store) {
        notification_store_clear_all(store);
        notification_store_save(store);
    }

    NSPopover *popover = objc_getAssociatedObject(sender, "popover");
    [popover close];

    [self updateNotificationBadge];
}

- (void)updateNotificationBadge {
    NotificationStore *store = [self.appDelegate getNotificationStore];
    if (!store) return;

    size_t count = notification_store_count(store);
    if (count > 0) {
        [self.historyButton setTitle:[NSString stringWithFormat:@"%zu", MIN(count, (size_t)99)]];
    } else {
        [self.historyButton setTitle:@""];
    }
}

#pragma mark - Theme

- (void)applyTheme {
    Config *config = [self.appDelegate getConfig];
    if (!config) return;

    const char *themeStr = config_get_string(config, "theme", NULL);
    BOOL useDark = NO;

    if (!themeStr || strcmp(themeStr, "auto") == 0) {
        useDark = platform_is_dark_theme();
    } else if (strcmp(themeStr, "dark") == 0) {
        useDark = YES;
    }

    if (@available(macOS 10.14, *)) {
        NSAppearance *appearance = useDark ?
            [NSAppearance appearanceNamed:NSAppearanceNameDarkAqua] :
            [NSAppearance appearanceNamed:NSAppearanceNameAqua];
        [[self window] setAppearance:appearance];
    }

    [self.tableView refreshCellBackgrounds];
}

@end
