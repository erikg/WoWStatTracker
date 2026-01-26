# WoWStatTracker 1.3.0 Release Notes

**Release Date:** January 10, 2026

## Overview

Version 1.3.0 adds Technomancer's Gift socket tracking, a gear report script, and several addon improvements.

## New Features

### Technomancer's Gift Socket Tracking
- Addon detects items missing Technomancer's Gift sockets (Head, Waist, Wrist)
- Uses GetItemGem API for reliable socket detection
- Reports socketable vs socketed counts per character

### Gear Report Script
- New `scripts/gear_report.py` generates a markdown report from SavedVariables
- Shows hero gear upgrade progress (X/Y levels, upgrades remaining)
- Vault rewards by tier with item levels (T8+ at 710, T2 at 678, T1 at 671)
- Status indicators: done, needs work, no vault rewards
- Empty socket and missing enchantment tracking

## Addon Changes

- Updated interface version for WoW patch 12.0.0
- Added BfA timewalking quest ID for A Scarred Path Through Time
- Fixed `/wst update` not clearing chat box by deferring to next frame

## Bug Fixes

- Fixed vault slot counting when SavedVariables has incomplete tier data
- Fixed socket tracking to properly detect Technomancer's Gift
- Fixed gear report script weekly reset detection after Tuesday

## Download

- **macOS**: WoWStatTracker-1.3.0-macOS.dmg
- **Windows**: WoWStatTracker-1.3.0-Setup.exe
