/*
 * WoW Stat Tracker - macOS Application Delegate
 * BSD 3-Clause License
 */

#import <Cocoa/Cocoa.h>

@class MainWindowController;

/* Forward declarations for C types */
typedef struct CharacterStore CharacterStore;
typedef struct Config Config;
typedef struct NotificationStore NotificationStore;

@interface AppDelegate : NSObject <NSApplicationDelegate>

@property (nonatomic, strong, readonly) MainWindowController *mainWindowController;

- (void)showNotification:(NSString *)message type:(NSString *)type;
- (void)refreshTable;

/* Data accessors */
- (CharacterStore *)getCharacterStore;
- (Config *)getConfig;
- (NotificationStore *)getNotificationStore;

@end

/* Notification type constants */
extern NSString * const WSTNotifyInfo;
extern NSString * const WSTNotifySuccess;
extern NSString * const WSTNotifyWarning;
