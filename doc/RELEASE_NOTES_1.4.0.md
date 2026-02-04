# WoWStatTracker 1.4.0 Release Notes

**Release Date:** February 4, 2026

## Overview

Version 1.4.0 adds a visual status column, detailed gear tooltips, and improved vault tracking to help you quickly see which characters are done for the week.

## Highlights

- **Status Column**: New ✅/⚠️/❌ column shows at-a-glance weekly completion status
- **Gear Tooltips**: Hover over rows to see per-slot upgrade, socket, and enchant details
- **T8+ Vault Tracking**: Accurately tracks high-tier (ilvl 694+) vault rewards
- **Dungeon Vault Support**: Now tracks both delve and dungeon vault progress

## New Features

### Status Column
- ✅ Done: All Hero 8/8 gear with sockets gemmed, OR 3+ vault slots (with T8+ rewards if non-hero gear)
- ⚠️ In Progress: Has vault rewards but not yet done
- ❌ No Rewards: No vault activities completed
- Characters with Champion/Veteran items at max level are not marked as done

### Per-Slot Tooltips
- Shows which slots need upgrades (e.g., "Head - Hero 5/8")
- Separates "Needs Hero Track" for Champion/Veteran 8/8 items (e.g., "Waist - Champion 8/8 (replace with Hero)")
- Lists slots that can accept Technomancer's Gift sockets
- Shows empty gem sockets and missing enchants

### Vault Tracking Improvements
- Tracks both World (delves) and Dungeons vault rows
- Counts T8+ rewards (tier/level 8+) for accurate done status
- Characters with non-hero gear need 3+ T8+ rewards to show done

### Socket and Enchant Tracking
- Tracks Technomancer's Gift socketable slots (Head, Waist, Wrist)
- Detects empty sockets missing gems
- Identifies slots missing enchants

## Addon Changes

- Updated interface version for WoW patch 12.0.0
- Added Shadowlands timewalking quest ID (A Shadowed Path Through Time - 92649)
- Added BfA timewalking quest ID (A Scarred Path Through Time)
- Improved timewalking detection: now detects TW availability when quest is accepted (not just when progress > 0)
- Fixed socket detection using GetItemGem API
- Improved vault tier/level data collection
- Addon now reports non-hero items at max level for hero track guidance

## Bug Fixes

- Fixed vault slot counting when SavedVariables has incomplete tier data
- Fixed socket tracking to properly detect Technomancer's Gift
- Fixed maxed characters (full upgrades + sockets) not showing as done
- Fixed characters with Champion/Veteran 8/8 items incorrectly shown as fully upgraded
- Fixed gear report config path and weekly reset detection

## Technical Improvements

- 121 unit tests (up from 112)
- Added tests for T8+ vault tier parsing
- Improved Lua parser for nested vault data structures

## Download

- **macOS**: WoWStatTracker-1.4.0-macOS.dmg
- **Windows (installer)**: WoWStatTracker-1.4.0-windows-x64-setup.exe
- **Windows (standalone)**: WoWStatTracker-1.4.0-windows-x64.zip - no installation required
