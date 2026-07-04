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

/* Character-store index of the selected row, or -1 if no selection. */
- (NSInteger)selectedCharacterIndex;

/* Full status/gear detail text (the row tooltip content) for the character at
 * the given store index, or nil. Used by the character details window. */
- (NSString *)detailTextForCharacterAtIndex:(NSInteger)index;

@end
