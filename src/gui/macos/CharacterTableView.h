/*
 * WoW Stat Tracker - Character Table View
 * BSD 3-Clause License
 */

#import <Cocoa/Cocoa.h>

@class CharacterTableView;

typedef struct CharacterStore CharacterStore;

@protocol CharacterTableViewDelegate <NSObject>

@optional
- (void)characterTableView:(CharacterTableView *)tableView didDoubleClickRow:(NSInteger)row;
- (void)characterTableView:(CharacterTableView *)tableView didToggleColumn:(NSInteger)column row:(NSInteger)row newValue:(BOOL)value;
- (void)characterTableView:(CharacterTableView *)tableView didEditNotes:(NSString *)notes forRow:(NSInteger)row;

@end

@interface CharacterTableView : NSTableView <NSTableViewDataSource, NSTableViewDelegate>

@property (nonatomic, unsafe_unretained) id<CharacterTableViewDelegate> tableDelegate;

- (void)reloadWithCharacterStore:(CharacterStore *)store;
- (void)refreshCellBackgrounds;

@end
