/*
 * WoW Stat Tracker - Main Window Controller
 * BSD 3-Clause License
 */

#import <Cocoa/Cocoa.h>

@class AppDelegate;

@interface MainWindowController : NSWindowController <NSWindowDelegate, NSToolbarDelegate>

- (instancetype)initWithDelegate:(AppDelegate *)delegate;

/* Table management */
- (void)reloadTableData;

/* Sheets and dialogs */
- (void)showAddCharacterSheet;
- (void)showEditCharacterSheetForIndex:(NSInteger)index;
- (void)showPreferencesSheet;
- (void)showManualWindow:(NSString *)content;

/* Status bar */
- (void)showStatusMessage:(NSString *)message type:(NSString *)type;
- (void)updateNotificationBadge;

/* Theme */
- (void)applyTheme;

@end
