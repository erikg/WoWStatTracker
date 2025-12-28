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
@property (nonatomic, strong) NSMutableArray<NSNumber *> *sortedIndices;

@end

@implementation CharacterTableView

- (void)dealloc {
    [_sortedIndices release];
    [super dealloc];
}

+ (void)initialize {
    if (self == [CharacterTableView class]) {
        /* MRC: must retain static colors since colorWithRed: returns autoreleased objects */
        kColorGreen = [[NSColor colorWithRed:0.56 green:0.93 blue:0.56 alpha:1.0] retain];  /* Light green #90EE90 */
        kColorYellow = [[NSColor colorWithRed:1.0 green:1.0 blue:0.88 alpha:1.0] retain];   /* Light yellow #FFFFE0 */
        kColorRed = [[NSColor colorWithRed:0.94 green:0.50 blue:0.50 alpha:1.0] retain];    /* Light red #F08080 */
        kColorDefault = [[NSColor controlBackgroundColor] retain];
    }
}

- (instancetype)initWithFrame:(NSRect)frameRect {
    self = [super initWithFrame:frameRect];
    if (self) {
        _sortedIndices = [[NSMutableArray alloc] init];  /* MRC: must alloc/init, not use autoreleased array */
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

        /* Enable autosave for column widths and order */
        [self setAutosaveName:@"CharacterTableColumns"];
        [self setAutosaveTableColumns:YES];
    }
    return self;
}

- (void)setupColumns {
    /* Column definitions: identifier, title, width */
    NSArray *columnDefs = @[
        @[kColRealm, @"Realm", @100],
        @[kColName, @"Name", @120],
        @[kColGuild, @"Guild", @100],
        @[kColItemLevel, @"Item Level", @80],
        @[kColHeroicItems, @"Heroic", @60],
        @[kColChampionItems, @"Champion", @70],
        @[kColVeteranItems, @"Veteran", @65],
        @[kColAdventureItems, @"Adventure", @75],
        @[kColOldItems, @"Old", @50],
        @[kColVaultVisited, @"Vault", @50],
        @[kColDelves, @"Delves", @55],
        @[kColGildedStash, @"Gilded", @55],
        @[kColGearingUp, @"Gearing Up", @80],
        @[kColQuests, @"Quests", @55],
        @[kColTimewalk, @"Timewalk", @70],
        @[kColNotes, @"Notes", @150],
    ];

    for (NSArray *def in columnDefs) {
        NSString *identifier = def[0];
        NSString *title = def[1];
        CGFloat width = [def[2] floatValue];

        NSTableColumn *column = [[NSTableColumn alloc] initWithIdentifier:identifier];
        [[column headerCell] setStringValue:title];
        [column setWidth:width];
        [column setMinWidth:40];
        [column setMaxWidth:400];
        [column setResizingMask:NSTableColumnUserResizingMask];

        /* Enable sorting - all columns are sortable */
        NSSortDescriptor *sort = [NSSortDescriptor sortDescriptorWithKey:identifier
                                                               ascending:YES];
        [column setSortDescriptorPrototype:sort];

        [self addTableColumn:column];
    }
}

#pragma mark - Data Management

- (void)reloadWithCharacterStore:(CharacterStore *)store {
    self.characterStore = store;

    /* Restore saved sort order on first load */
    if ([[self sortDescriptors] count] == 0) {
        NSString *savedKey = [[NSUserDefaults standardUserDefaults] stringForKey:@"CharacterTableSortKey"];
        if (savedKey) {
            BOOL ascending = [[NSUserDefaults standardUserDefaults] boolForKey:@"CharacterTableSortAscending"];
            NSSortDescriptor *sort = [NSSortDescriptor sortDescriptorWithKey:savedKey ascending:ascending];
            [self setSortDescriptors:@[sort]];
        }
    }

    [self rebuildSortedIndices];
    [self reloadData];
}

- (void)rebuildSortedIndices {
    [self.sortedIndices removeAllObjects];

    if (!self.characterStore) return;

    size_t count = character_store_count(self.characterStore);
    for (size_t i = 0; i < count; i++) {
        [self.sortedIndices addObject:@(i)];
    }

    /* Apply current sort descriptors if any */
    if ([[self sortDescriptors] count] > 0) {
        [self applySortDescriptors];
    }
}

- (void)applySortDescriptors {
    NSArray<NSSortDescriptor *> *descriptors = [self sortDescriptors];
    if ([descriptors count] == 0 || !self.characterStore) return;

    CharacterStore *store = self.characterStore;

    [self.sortedIndices sortUsingComparator:^NSComparisonResult(NSNumber *a, NSNumber *b) {
        size_t idxA = [a unsignedIntegerValue];
        size_t idxB = [b unsignedIntegerValue];

        const Character *charA = character_store_get(store, idxA);
        const Character *charB = character_store_get(store, idxB);

        if (!charA || !charB) return NSOrderedSame;

        for (NSSortDescriptor *desc in descriptors) {
            NSString *key = [desc key];
            NSComparisonResult result = NSOrderedSame;

            if ([key isEqualToString:kColRealm]) {
                NSString *sA = charA->realm ? [NSString stringWithUTF8String:charA->realm] : @"";
                NSString *sB = charB->realm ? [NSString stringWithUTF8String:charB->realm] : @"";
                result = [sA localizedCaseInsensitiveCompare:sB];
            } else if ([key isEqualToString:kColName]) {
                NSString *sA = charA->name ? [NSString stringWithUTF8String:charA->name] : @"";
                NSString *sB = charB->name ? [NSString stringWithUTF8String:charB->name] : @"";
                result = [sA localizedCaseInsensitiveCompare:sB];
            } else if ([key isEqualToString:kColGuild]) {
                NSString *sA = charA->guild ? [NSString stringWithUTF8String:charA->guild] : @"";
                NSString *sB = charB->guild ? [NSString stringWithUTF8String:charB->guild] : @"";
                result = [sA localizedCaseInsensitiveCompare:sB];
            } else if ([key isEqualToString:kColItemLevel]) {
                if (charA->item_level < charB->item_level) result = NSOrderedAscending;
                else if (charA->item_level > charB->item_level) result = NSOrderedDescending;
            } else if ([key isEqualToString:kColHeroicItems]) {
                if (charA->heroic_items < charB->heroic_items) result = NSOrderedAscending;
                else if (charA->heroic_items > charB->heroic_items) result = NSOrderedDescending;
            } else if ([key isEqualToString:kColChampionItems]) {
                if (charA->champion_items < charB->champion_items) result = NSOrderedAscending;
                else if (charA->champion_items > charB->champion_items) result = NSOrderedDescending;
            } else if ([key isEqualToString:kColVeteranItems]) {
                if (charA->veteran_items < charB->veteran_items) result = NSOrderedAscending;
                else if (charA->veteran_items > charB->veteran_items) result = NSOrderedDescending;
            } else if ([key isEqualToString:kColAdventureItems]) {
                if (charA->adventure_items < charB->adventure_items) result = NSOrderedAscending;
                else if (charA->adventure_items > charB->adventure_items) result = NSOrderedDescending;
            } else if ([key isEqualToString:kColOldItems]) {
                if (charA->old_items < charB->old_items) result = NSOrderedAscending;
                else if (charA->old_items > charB->old_items) result = NSOrderedDescending;
            } else if ([key isEqualToString:kColVaultVisited]) {
                if (charA->vault_visited < charB->vault_visited) result = NSOrderedAscending;
                else if (charA->vault_visited > charB->vault_visited) result = NSOrderedDescending;
            } else if ([key isEqualToString:kColDelves]) {
                if (charA->delves < charB->delves) result = NSOrderedAscending;
                else if (charA->delves > charB->delves) result = NSOrderedDescending;
            } else if ([key isEqualToString:kColGildedStash]) {
                if (charA->gilded_stash < charB->gilded_stash) result = NSOrderedAscending;
                else if (charA->gilded_stash > charB->gilded_stash) result = NSOrderedDescending;
            } else if ([key isEqualToString:kColGearingUp]) {
                if (charA->gearing_up < charB->gearing_up) result = NSOrderedAscending;
                else if (charA->gearing_up > charB->gearing_up) result = NSOrderedDescending;
            } else if ([key isEqualToString:kColQuests]) {
                if (charA->quests < charB->quests) result = NSOrderedAscending;
                else if (charA->quests > charB->quests) result = NSOrderedDescending;
            } else if ([key isEqualToString:kColTimewalk]) {
                if (charA->timewalk < charB->timewalk) result = NSOrderedAscending;
                else if (charA->timewalk > charB->timewalk) result = NSOrderedDescending;
            } else if ([key isEqualToString:kColNotes]) {
                NSString *sA = charA->notes ? [NSString stringWithUTF8String:charA->notes] : @"";
                NSString *sB = charB->notes ? [NSString stringWithUTF8String:charB->notes] : @"";
                result = [sA localizedCaseInsensitiveCompare:sB];
            }

            if (result != NSOrderedSame) {
                return [desc ascending] ? result : -result;
            }
        }

        return NSOrderedSame;
    }];
}

- (void)refreshCellBackgrounds {
    [self reloadData];
}

/* Get the actual character store index for a display row */
- (size_t)characterIndexForRow:(NSInteger)row {
    if (row < 0 || (NSUInteger)row >= [self.sortedIndices count]) {
        return (size_t)-1;
    }
    return [self.sortedIndices[(NSUInteger)row] unsignedIntegerValue];
}

#pragma mark - NSTableViewDataSource

- (NSInteger)numberOfRowsInTableView:(NSTableView *)tableView {
    return (NSInteger)[self.sortedIndices count];
}

- (id)tableView:(NSTableView *)tableView objectValueForTableColumn:(NSTableColumn *)tableColumn row:(NSInteger)row {
    if (!self.characterStore) return nil;

    size_t charIndex = [self characterIndexForRow:row];
    if (charIndex == (size_t)-1) return nil;

    const Character *character = character_store_get(self.characterStore, charIndex);
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
        size_t charIndex = [self characterIndexForRow:row];
        if (charIndex != (size_t)-1 && [self.tableDelegate respondsToSelector:@selector(characterTableView:didEditNotes:forRow:)]) {
            [self.tableDelegate characterTableView:self didEditNotes:object forRow:(NSInteger)charIndex];
        }
    }
}

- (void)tableView:(NSTableView *)tableView sortDescriptorsDidChange:(NSArray<NSSortDescriptor *> *)oldDescriptors {
    [self applySortDescriptors];
    [self reloadData];

    /* Save sort order to user defaults */
    NSArray<NSSortDescriptor *> *descriptors = [self sortDescriptors];
    if ([descriptors count] > 0) {
        NSSortDescriptor *primary = descriptors[0];
        [[NSUserDefaults standardUserDefaults] setObject:[primary key] forKey:@"CharacterTableSortKey"];
        [[NSUserDefaults standardUserDefaults] setBool:[primary ascending] forKey:@"CharacterTableSortAscending"];
    }
}

#pragma mark - NSTableViewDelegate

- (NSView *)tableView:(NSTableView *)tableView viewForTableColumn:(NSTableColumn *)tableColumn row:(NSInteger)row {
    NSString *identifier = [tableColumn identifier];

    size_t charIndex = [self characterIndexForRow:row];
    if (charIndex == (size_t)-1) return nil;

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

        const Character *character = character_store_get(self.characterStore, charIndex);
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

        /* Store character index and column info for click handler */
        [checkbox setTag:(NSInteger)charIndex];
        objc_setAssociatedObject(checkbox, "columnId", identifier, OBJC_ASSOCIATION_COPY);

        /* Apply background color */
        NSColor *bgColor = [self backgroundColorForColumn:identifier characterIndex:charIndex];
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

    /* Store character index for notes editing */
    [textField setTag:(NSInteger)charIndex];

    /* Apply background color for weekly columns */
    NSColor *bgColor = [self backgroundColorForColumn:identifier characterIndex:charIndex];
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

- (NSColor *)backgroundColorForColumn:(NSString *)identifier characterIndex:(size_t)charIndex {
    if (!self.characterStore) return nil;

    const Character *character = character_store_get(self.characterStore, charIndex);
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
    if (row >= 0) {
        size_t charIndex = [self characterIndexForRow:row];
        if (charIndex != (size_t)-1 && [self.tableDelegate respondsToSelector:@selector(characterTableView:didDoubleClickRow:)]) {
            [self.tableDelegate characterTableView:self didDoubleClickRow:(NSInteger)charIndex];
        }
    }
}

- (void)checkboxClicked:(NSButton *)sender {
    NSInteger charIndex = [sender tag];
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
        [self.tableDelegate characterTableView:self didToggleColumn:column row:charIndex newValue:newValue];
    }
}

- (void)notesEdited:(NSTextField *)sender {
    NSInteger charIndex = [sender tag];
    NSString *notes = [sender stringValue];

    if ([self.tableDelegate respondsToSelector:@selector(characterTableView:didEditNotes:forRow:)]) {
        [self.tableDelegate characterTableView:self didEditNotes:notes forRow:charIndex];
    }
}

@end
