/*
 * WoW Stat Tracker - Character Table View Implementation
 * BSD 3-Clause License
 */

#import "CharacterTableView.h"
#import "character.h"
#import "character_store.h"
#import "platform.h"
#import <objc/runtime.h>

/* Column identifiers */
static NSString * const kColRealm = @"realm";
static NSString * const kColName = @"name";
static NSString * const kColGuild = @"guild";
static NSString * const kColItemLevel = @"item_level";
static NSString * const kColHeroicItems = @"heroic_items";
static NSString * const kColChampionItems = @"champion_items";
static NSString * const kColVeteranItems = @"veteran_items";
static NSString * const kColAdventureItems = @"adventure_items";
static NSString * const kColOldItems = @"old_items";
static NSString * const kColVaultVisited = @"vault_visited";
static NSString * const kColDelves = @"delves";
static NSString * const kColGildedStash = @"gilded_stash";
static NSString * const kColGearingUp = @"gearing_up";
static NSString * const kColQuests = @"quests";
static NSString * const kColTimewalk = @"timewalk";
static NSString * const kColNotes = @"notes";

/* Cell colors */
static NSColor *kColorGreen;
static NSColor *kColorYellow;
static NSColor *kColorRed;
static NSColor *kColorDefault;

@interface CharacterTableView ()

@property (nonatomic, assign) CharacterStore *characterStore;

@end

@implementation CharacterTableView

+ (void)initialize {
    if (self == [CharacterTableView class]) {
        kColorGreen = [NSColor colorWithRed:0.56 green:0.93 blue:0.56 alpha:1.0];  /* Light green #90EE90 */
        kColorYellow = [NSColor colorWithRed:1.0 green:1.0 blue:0.88 alpha:1.0];   /* Light yellow #FFFFE0 */
        kColorRed = [NSColor colorWithRed:0.94 green:0.50 blue:0.50 alpha:1.0];    /* Light red #F08080 */
        kColorDefault = [NSColor controlBackgroundColor];
    }
}

- (instancetype)initWithFrame:(NSRect)frameRect {
    self = [super initWithFrame:frameRect];
    if (self) {
        [self setupColumns];
        [self setDataSource:self];
        [self setDelegate:self];
        [self setDoubleAction:@selector(handleDoubleClick:)];
        [self setTarget:self];
        [self setRowHeight:22];
        [self setGridStyleMask:NSTableViewSolidHorizontalGridLineMask];
        [self setUsesAlternatingRowBackgroundColors:YES];
        [self setAllowsColumnReordering:YES];
        [self setAllowsColumnResizing:YES];
        [self setAllowsMultipleSelection:NO];
        [self setAllowsColumnSelection:NO];
    }
    return self;
}

- (void)setupColumns {
    /* Column definitions: identifier, title, width, sortable */
    NSArray *columnDefs = @[
        @[kColRealm, @"Realm", @100, @YES],
        @[kColName, @"Name", @120, @YES],
        @[kColGuild, @"Guild", @100, @YES],
        @[kColItemLevel, @"Item Level", @80, @YES],
        @[kColHeroicItems, @"Heroic", @60, @YES],
        @[kColChampionItems, @"Champion", @70, @YES],
        @[kColVeteranItems, @"Veteran", @65, @YES],
        @[kColAdventureItems, @"Adventure", @75, @YES],
        @[kColOldItems, @"Old", @50, @YES],
        @[kColVaultVisited, @"Vault", @50, @YES],
        @[kColDelves, @"Delves", @55, @YES],
        @[kColGildedStash, @"Gilded", @55, @YES],
        @[kColGearingUp, @"Gearing Up", @80, @YES],
        @[kColQuests, @"Quests", @55, @YES],
        @[kColTimewalk, @"Timewalk", @70, @YES],
        @[kColNotes, @"Notes", @150, @YES],
    ];

    for (NSArray *def in columnDefs) {
        NSString *identifier = def[0];
        NSString *title = def[1];
        CGFloat width = [def[2] floatValue];
        BOOL sortable = [def[3] boolValue];

        NSTableColumn *column = [[NSTableColumn alloc] initWithIdentifier:identifier];
        [[column headerCell] setStringValue:title];
        [column setWidth:width];
        [column setMinWidth:40];
        [column setMaxWidth:400];
        [column setResizingMask:NSTableColumnUserResizingMask];

        if (sortable) {
            NSSortDescriptor *sort = [NSSortDescriptor sortDescriptorWithKey:identifier
                                                                   ascending:YES
                                                                    selector:@selector(compare:)];
            [column setSortDescriptorPrototype:sort];
        }

        [self addTableColumn:column];
    }
}

#pragma mark - Data Management

- (void)reloadWithCharacterStore:(CharacterStore *)store {
    self.characterStore = store;
    [self reloadData];
}

- (void)refreshCellBackgrounds {
    [self reloadData];
}

#pragma mark - NSTableViewDataSource

- (NSInteger)numberOfRowsInTableView:(NSTableView *)tableView {
    if (!self.characterStore) return 0;
    return (NSInteger)character_store_count(self.characterStore);
}

- (id)tableView:(NSTableView *)tableView objectValueForTableColumn:(NSTableColumn *)tableColumn row:(NSInteger)row {
    if (!self.characterStore) return nil;

    const Character *character = character_store_get(self.characterStore, (size_t)row);
    if (!character) return nil;

    NSString *identifier = [tableColumn identifier];

    if ([identifier isEqualToString:kColRealm]) {
        return character->realm ? [NSString stringWithUTF8String:character->realm] : @"";
    } else if ([identifier isEqualToString:kColName]) {
        return character->name ? [NSString stringWithUTF8String:character->name] : @"";
    } else if ([identifier isEqualToString:kColGuild]) {
        return character->guild ? [NSString stringWithUTF8String:character->guild] : @"";
    } else if ([identifier isEqualToString:kColItemLevel]) {
        return [NSString stringWithFormat:@"%.1f", character->item_level];
    } else if ([identifier isEqualToString:kColHeroicItems]) {
        return @(character->heroic_items);
    } else if ([identifier isEqualToString:kColChampionItems]) {
        return @(character->champion_items);
    } else if ([identifier isEqualToString:kColVeteranItems]) {
        return @(character->veteran_items);
    } else if ([identifier isEqualToString:kColAdventureItems]) {
        return @(character->adventure_items);
    } else if ([identifier isEqualToString:kColOldItems]) {
        return @(character->old_items);
    } else if ([identifier isEqualToString:kColVaultVisited]) {
        return @(character->vault_visited);
    } else if ([identifier isEqualToString:kColDelves]) {
        return @(character->delves);
    } else if ([identifier isEqualToString:kColGildedStash]) {
        return @(character->gilded_stash);
    } else if ([identifier isEqualToString:kColGearingUp]) {
        return @(character->gearing_up);
    } else if ([identifier isEqualToString:kColQuests]) {
        return @(character->quests);
    } else if ([identifier isEqualToString:kColTimewalk]) {
        return @(character->timewalk);
    } else if ([identifier isEqualToString:kColNotes]) {
        return character->notes ? [NSString stringWithUTF8String:character->notes] : @"";
    }

    return nil;
}

- (void)tableView:(NSTableView *)tableView setObjectValue:(id)object forTableColumn:(NSTableColumn *)tableColumn row:(NSInteger)row {
    NSString *identifier = [tableColumn identifier];

    if ([identifier isEqualToString:kColNotes]) {
        if ([self.tableDelegate respondsToSelector:@selector(characterTableView:didEditNotes:forRow:)]) {
            [self.tableDelegate characterTableView:self didEditNotes:object forRow:row];
        }
    }
}

- (void)tableView:(NSTableView *)tableView sortDescriptorsDidChange:(NSArray<NSSortDescriptor *> *)oldDescriptors {
    /* Sorting is handled by the table view automatically for simple cases */
    /* For proper sorting, we'd need to sort the character store and reload */
    [self reloadData];
}

#pragma mark - NSTableViewDelegate

- (NSView *)tableView:(NSTableView *)tableView viewForTableColumn:(NSTableColumn *)tableColumn row:(NSInteger)row {
    NSString *identifier = [tableColumn identifier];

    /* Check if this is a checkbox column */
    BOOL isCheckbox = [identifier isEqualToString:kColVaultVisited] ||
                      [identifier isEqualToString:kColGearingUp] ||
                      [identifier isEqualToString:kColQuests];

    if (isCheckbox) {
        NSButton *checkbox = [tableView makeViewWithIdentifier:[identifier stringByAppendingString:@"_check"] owner:self];
        if (!checkbox) {
            checkbox = [[NSButton alloc] initWithFrame:NSZeroRect];
            [checkbox setButtonType:NSButtonTypeSwitch];
            [checkbox setTitle:@""];
            [checkbox setIdentifier:[identifier stringByAppendingString:@"_check"]];
            [checkbox setTarget:self];
            [checkbox setAction:@selector(checkboxClicked:)];
        }

        const Character *character = character_store_get(self.characterStore, (size_t)row);
        if (character) {
            BOOL value = NO;
            if ([identifier isEqualToString:kColVaultVisited]) {
                value = character->vault_visited;
            } else if ([identifier isEqualToString:kColGearingUp]) {
                value = character->gearing_up;
            } else if ([identifier isEqualToString:kColQuests]) {
                value = character->quests;
            }
            [checkbox setState:value ? NSControlStateValueOn : NSControlStateValueOff];
        }

        /* Store row and column info for click handler */
        [checkbox setTag:row];
        objc_setAssociatedObject(checkbox, "columnId", identifier, OBJC_ASSOCIATION_COPY);

        /* Apply background color */
        NSColor *bgColor = [self backgroundColorForColumn:identifier row:row];
        if (bgColor) {
            NSView *container = [[NSView alloc] initWithFrame:NSZeroRect];
            [container setWantsLayer:YES];
            [container.layer setBackgroundColor:[bgColor CGColor]];
            [container addSubview:checkbox];
            checkbox.frame = container.bounds;
            [checkbox setAutoresizingMask:NSViewWidthSizable | NSViewHeightSizable];
            return container;
        }

        return checkbox;
    }

    /* Text field cell */
    NSTextField *textField = [tableView makeViewWithIdentifier:identifier owner:self];
    if (!textField) {
        textField = [[NSTextField alloc] initWithFrame:NSZeroRect];
        [textField setBezeled:NO];
        [textField setDrawsBackground:NO];
        [textField setEditable:[identifier isEqualToString:kColNotes]];
        [textField setSelectable:YES];
        [textField setIdentifier:identifier];
        [textField setLineBreakMode:NSLineBreakByTruncatingTail];

        if ([identifier isEqualToString:kColNotes]) {
            [textField setTarget:self];
            [textField setAction:@selector(notesEdited:)];
        }
    }

    id value = [self tableView:tableView objectValueForTableColumn:tableColumn row:row];
    if ([value isKindOfClass:[NSNumber class]]) {
        [textField setStringValue:[value stringValue]];
    } else {
        [textField setStringValue:value ?: @""];
    }

    /* Store row for notes editing */
    [textField setTag:row];

    /* Apply background color for weekly columns */
    NSColor *bgColor = [self backgroundColorForColumn:identifier row:row];
    if (bgColor) {
        NSView *container = [[NSView alloc] initWithFrame:NSZeroRect];
        [container setWantsLayer:YES];
        [container.layer setBackgroundColor:[bgColor CGColor]];

        textField.frame = container.bounds;
        [textField setAutoresizingMask:NSViewWidthSizable | NSViewHeightSizable];
        [container addSubview:textField];

        /* Use dark text on light backgrounds */
        [textField setTextColor:[NSColor blackColor]];

        return container;
    }

    return textField;
}

- (NSColor *)backgroundColorForColumn:(NSString *)identifier row:(NSInteger)row {
    if (!self.characterStore) return nil;

    const Character *character = character_store_get(self.characterStore, (size_t)row);
    if (!character) return nil;

    BOOL useDark = platform_is_dark_theme();

    /* Determine completion status for weekly items */
    BOOL delvesDone = character->delves >= 4;
    BOOL allWeekliesDone = character->gearing_up && character->quests && delvesDone;

    if ([identifier isEqualToString:kColVaultVisited]) {
        if (character->vault_visited) {
            return kColorGreen;
        } else if (allWeekliesDone) {
            return kColorRed;  /* Should visit vault */
        } else {
            return useDark ? nil : kColorYellow;
        }
    } else if ([identifier isEqualToString:kColDelves]) {
        if (character->delves >= 4) {
            return kColorGreen;
        } else if (character->delves > 0) {
            return kColorYellow;
        }
    } else if ([identifier isEqualToString:kColGildedStash]) {
        if (character->gilded_stash >= 3) {
            return kColorGreen;
        } else if (character->gilded_stash > 0) {
            return kColorYellow;
        } else {
            return kColorRed;
        }
    } else if ([identifier isEqualToString:kColGearingUp] || [identifier isEqualToString:kColQuests]) {
        BOOL value = [identifier isEqualToString:kColGearingUp] ? character->gearing_up : character->quests;
        if (value) {
            return kColorGreen;
        } else {
            return useDark ? nil : kColorYellow;
        }
    } else if ([identifier isEqualToString:kColTimewalk]) {
        if (character->timewalk >= 5) {
            return kColorGreen;
        } else if (character->timewalk > 0) {
            return kColorYellow;
        }
    }

    return nil;
}

#pragma mark - Actions

- (void)handleDoubleClick:(id)sender {
    NSInteger row = [self clickedRow];
    if (row >= 0 && [self.tableDelegate respondsToSelector:@selector(characterTableView:didDoubleClickRow:)]) {
        [self.tableDelegate characterTableView:self didDoubleClickRow:row];
    }
}

- (void)checkboxClicked:(NSButton *)sender {
    NSInteger row = [sender tag];
    NSString *columnId = objc_getAssociatedObject(sender, "columnId");
    BOOL newValue = [sender state] == NSControlStateValueOn;

    if ([self.tableDelegate respondsToSelector:@selector(characterTableView:didToggleColumn:row:newValue:)]) {
        NSInteger column = 0;
        if ([columnId isEqualToString:kColVaultVisited]) {
            column = 9;
        } else if ([columnId isEqualToString:kColGearingUp]) {
            column = 12;
        } else if ([columnId isEqualToString:kColQuests]) {
            column = 13;
        }
        [self.tableDelegate characterTableView:self didToggleColumn:column row:row newValue:newValue];
    }
}

- (void)notesEdited:(NSTextField *)sender {
    NSInteger row = [sender tag];
    NSString *notes = [sender stringValue];

    if ([self.tableDelegate respondsToSelector:@selector(characterTableView:didEditNotes:forRow:)]) {
        [self.tableDelegate characterTableView:self didEditNotes:notes forRow:row];
    }
}

@end
