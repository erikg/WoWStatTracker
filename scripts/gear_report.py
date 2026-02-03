#!/usr/bin/env python3
"""
WoW Stat Tracker - Hero Gear & Vault Report Generator

Reads character data from WoW addon SavedVariables and generates a report
showing hero gear progress and vault rewards.
"""

import argparse
import json
import os
import re
import sys
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Any

# Config and data paths - platform specific
if sys.platform == "win32":
    CONFIG_DIR = Path(os.environ.get("APPDATA", Path.home())) / "wowstat"
else:
    CONFIG_DIR = Path.home() / "Library" / "Application Support" / "wowstat"
CONFIG_FILE = CONFIG_DIR / "wowstat_config.json"

# Vault thresholds (activities needed for each slot)
VAULT_THRESHOLDS = [1, 4, 8]

# Item level reference
ILVL_REFERENCE = {
    "T8+": 710,  # T8-T11 all give same ilvl
    "T2": 678,   # TW/Heroic equivalent
    "T1": 671,
}

# Slot ID to name mapping
SLOT_NAMES = {
    1: "Head",
    2: "Neck",
    3: "Shoulder",
    5: "Chest",
    6: "Waist",
    7: "Legs",
    8: "Feet",
    9: "Wrist",
    10: "Hands",
    11: "Ring1",
    12: "Ring2",
    13: "Trinket1",
    14: "Trinket2",
    15: "Back",
    16: "MainHand",
    17: "OffHand",
}

# Slots that can receive Technomancer's Gift (3 slots only)
SOCKETABLE_SLOTS = {1, 6, 9}

# WoW weekly reset: Tuesday 15:00 UTC
RESET_WEEKDAY = 1  # Monday=0, Tuesday=1 in Python's weekday()
RESET_HOUR = 15


def get_current_week_id() -> str:
    """Calculate the current week_id (YYYYMMDD of the last Tuesday reset)."""
    now = datetime.now(timezone.utc)

    # Calculate days since last Tuesday
    # Python weekday(): Monday=0, Tuesday=1, ...
    days_since_tuesday = (now.weekday() - RESET_WEEKDAY) % 7

    # If it's Tuesday but before reset time, count as previous week
    if now.weekday() == RESET_WEEKDAY and now.hour < RESET_HOUR:
        days_since_tuesday = 7

    # Calculate the last reset timestamp
    last_reset = now - timedelta(days=days_since_tuesday)
    last_reset = last_reset.replace(hour=RESET_HOUR, minute=0, second=0, microsecond=0)

    return last_reset.strftime("%Y%m%d")


class LuaParser:
    """Simple recursive descent parser for Lua tables."""

    def __init__(self, content: str):
        self.content = content
        self.pos = 0
        self.length = len(content)

    def parse(self) -> Any:
        """Parse the Lua content and return a Python object."""
        self.skip_whitespace_and_comments()
        # Skip variable assignment
        if self.match_pattern(r'\w+\s*=\s*'):
            pass
        return self.parse_value()

    def skip_whitespace_and_comments(self):
        """Skip whitespace and Lua comments."""
        while self.pos < self.length:
            # Skip whitespace
            if self.content[self.pos].isspace():
                self.pos += 1
            # Skip single-line comments
            elif self.content[self.pos:self.pos+2] == '--':
                while self.pos < self.length and self.content[self.pos] != '\n':
                    self.pos += 1
            else:
                break

    def match_pattern(self, pattern: str) -> str | None:
        """Match a regex pattern at current position."""
        self.skip_whitespace_and_comments()
        match = re.match(pattern, self.content[self.pos:])
        if match:
            result = match.group(0)
            self.pos += len(result)
            return result
        return None

    def peek(self) -> str:
        """Peek at current character."""
        self.skip_whitespace_and_comments()
        if self.pos < self.length:
            return self.content[self.pos]
        return ''

    def consume(self, char: str) -> bool:
        """Consume expected character."""
        self.skip_whitespace_and_comments()
        if self.pos < self.length and self.content[self.pos] == char:
            self.pos += 1
            return True
        return False

    def parse_value(self) -> Any:
        """Parse any Lua value."""
        self.skip_whitespace_and_comments()

        if self.peek() == '{':
            return self.parse_table()
        elif self.peek() == '"':
            return self.parse_string('"')
        elif self.peek() == "'":
            return self.parse_string("'")
        elif self.match_pattern(r'true'):
            return True
        elif self.match_pattern(r'false'):
            return False
        elif self.match_pattern(r'nil'):
            return None
        else:
            # Try to parse a number
            num_match = self.match_pattern(r'-?\d+\.?\d*(?:[eE][+-]?\d+)?')
            if num_match:
                if '.' in num_match or 'e' in num_match.lower():
                    return float(num_match)
                return int(num_match)
        return None

    def parse_string(self, quote: str) -> str:
        """Parse a quoted string."""
        self.consume(quote)
        result = []
        while self.pos < self.length and self.content[self.pos] != quote:
            if self.content[self.pos] == '\\' and self.pos + 1 < self.length:
                self.pos += 1
                escaped = self.content[self.pos]
                if escaped == 'n':
                    result.append('\n')
                elif escaped == 't':
                    result.append('\t')
                elif escaped == 'r':
                    result.append('\r')
                else:
                    result.append(escaped)
            else:
                result.append(self.content[self.pos])
            self.pos += 1
        self.consume(quote)
        return ''.join(result)

    def parse_table(self) -> dict | list:
        """Parse a Lua table (can be dict or array)."""
        self.consume('{')
        result = {}
        is_array = True
        array_index = 1

        while self.peek() and self.peek() != '}':
            key = None
            value = None

            # Check for explicit key
            if self.peek() == '[':
                self.consume('[')
                if self.peek() == '"' or self.peek() == "'":
                    key = self.parse_string(self.peek())
                else:
                    key = self.parse_value()
                self.consume(']')
                self.match_pattern(r'\s*=\s*')
                value = self.parse_value()
                is_array = False
            elif re.match(r'[a-zA-Z_]\w*\s*=', self.content[self.pos:]):
                key_match = self.match_pattern(r'[a-zA-Z_]\w*')
                key = key_match
                self.match_pattern(r'\s*=\s*')
                value = self.parse_value()
                is_array = False
            else:
                # Array element
                value = self.parse_value()
                key = array_index
                array_index += 1

            if key is not None:
                result[key] = value

            # Skip comma
            self.match_pattern(r'\s*,?\s*')

        self.consume('}')
        return result


def parse_lua_table(content: str) -> dict:
    """Parse a Lua table into a Python dictionary."""
    try:
        parser = LuaParser(content)
        return parser.parse()
    except Exception as e:
        print(f"Error parsing Lua table: {e}", file=sys.stderr)
        return {}


def load_config() -> dict:
    """Load the WoWStatTracker config file."""
    if not CONFIG_FILE.exists():
        print(f"Config file not found: {CONFIG_FILE}", file=sys.stderr)
        sys.exit(1)

    with open(CONFIG_FILE) as f:
        return json.load(f)


def load_app_data() -> list[dict]:
    """Load the app's JSON data file for notes."""
    data_file = CONFIG_DIR / "wowstat_data.json"
    if data_file.exists():
        with open(data_file) as f:
            return json.load(f)
    return []


def find_saved_variables(wow_path: str) -> Path | None:
    """Find the addon SavedVariables file."""
    wow_path = Path(wow_path)

    # Look for retail WTF folder
    wtf_path = wow_path / "_retail_" / "WTF" / "Account"
    if not wtf_path.exists():
        print(f"WTF folder not found: {wtf_path}", file=sys.stderr)
        return None

    # Find account folders (skip SavedVariables at account level)
    for account_dir in wtf_path.iterdir():
        if account_dir.is_dir() and account_dir.name != "SavedVariables":
            sv_file = account_dir / "SavedVariables" / "WoWStatTracker_Addon.lua"
            if sv_file.exists():
                return sv_file

    return None


def load_saved_variables(sv_path: Path) -> dict:
    """Load and parse the SavedVariables file."""
    with open(sv_path) as f:
        content = f.read()

    return parse_lua_table(content)


def count_vault_slots(count: int) -> int:
    """Calculate how many vault slots are unlocked based on activity count."""
    slots = 0
    for threshold in VAULT_THRESHOLDS:
        if count >= threshold:
            slots += 1
    return slots


def get_tier_from_level(level: int) -> str:
    """Convert a dungeon/delve level to tier notation."""
    if level >= 8:
        return "T8+"
    elif level >= 2 or level == 0:  # level 0 = timewalking
        return "T2"
    else:
        return "T1"


def get_ilvl_from_tier(tier: str) -> int:
    """Get item level from tier notation."""
    if "T8" in tier:
        return ILVL_REFERENCE["T8+"]
    elif tier == "T1":
        return ILVL_REFERENCE["T1"]
    else:
        return ILVL_REFERENCE["T2"]


def analyze_enchant_info(char_data: dict) -> dict:
    """Analyze enchantment information."""
    result = {
        "missing_enchants": [],  # Slot names missing enchants
        "missing_count": 0,      # Number of enchantable slots without enchants
        "enchant_count": 0,      # Number of enchanted slots
        "enchantable_count": 0,  # Total enchantable slots equipped
    }

    enchant_info = char_data.get("enchant_info", {})
    if not isinstance(enchant_info, dict):
        return result

    # Get missing enchants from addon data
    missing_slots = enchant_info.get("missing_enchants", [])
    if isinstance(missing_slots, dict):
        missing_slots = list(missing_slots.values())
    elif not isinstance(missing_slots, list):
        missing_slots = []

    # Convert slot IDs to names
    for slot_id in missing_slots:
        slot_id = int(slot_id) if isinstance(slot_id, (int, float, str)) else 0
        if slot_id in SLOT_NAMES:
            result["missing_enchants"].append(SLOT_NAMES[slot_id])

    result["enchant_count"] = enchant_info.get("enchant_count", 0)
    result["enchantable_count"] = enchant_info.get("enchantable_count", 0)
    result["missing_count"] = result["enchantable_count"] - result["enchant_count"]

    if result["missing_count"] == 0 and result["missing_enchants"]:
        result["missing_count"] = len(result["missing_enchants"])

    return result


def analyze_socket_info(char_data: dict) -> dict:
    """Analyze socket information for Technomancer's Gift tracking."""
    result = {
        "missing_sockets": [],  # Slot names missing sockets (need Technomancer's Gift)
        "missing_count": 0,     # Number of socketable slots without sockets
        "socketed_count": 0,    # Number of socketable slots with sockets
        "total_socketable": 0,  # Total socketable slots equipped
        "empty_sockets": [],    # Slot names with sockets but no gems
        "empty_count": 0,       # Number of sockets without gems
    }

    socket_info = char_data.get("socket_info", {})
    if not isinstance(socket_info, dict):
        return result

    # Get missing sockets from addon data (socketable slots without sockets)
    missing_slots = socket_info.get("missing_sockets", [])
    if isinstance(missing_slots, dict):
        # Convert dict to list of values
        missing_slots = list(missing_slots.values())
    elif isinstance(missing_slots, list):
        pass
    else:
        missing_slots = []

    # Convert slot IDs to names
    for slot_id in missing_slots:
        slot_id = int(slot_id) if isinstance(slot_id, (int, float, str)) else 0
        if slot_id in SLOT_NAMES:
            result["missing_sockets"].append(SLOT_NAMES[slot_id])

    result["missing_count"] = socket_info.get("socketable_count", 0) - socket_info.get("socketed_count", 0)
    result["socketed_count"] = socket_info.get("socketed_count", 0)
    result["total_socketable"] = socket_info.get("socketable_count", 0)

    # If we have missing_sockets list but no counts, use the list length
    if result["missing_count"] == 0 and result["missing_sockets"]:
        result["missing_count"] = len(result["missing_sockets"])

    # Get empty sockets (have socket but no gem)
    empty_slots = socket_info.get("empty_sockets", [])
    if isinstance(empty_slots, dict):
        empty_slots = list(empty_slots.values())
    elif not isinstance(empty_slots, list):
        empty_slots = []

    for slot_id in empty_slots:
        slot_id = int(slot_id) if isinstance(slot_id, (int, float, str)) else 0
        if slot_id in SLOT_NAMES:
            result["empty_sockets"].append(SLOT_NAMES[slot_id])

    result["empty_count"] = socket_info.get("empty_count", 0)
    if result["empty_count"] == 0 and result["empty_sockets"]:
        result["empty_count"] = len(result["empty_sockets"])

    return result


def analyze_vault_rewards(char_data: dict) -> dict:
    """Analyze vault rewards for a character."""
    result = {
        "delve_count": 0,
        "dungeon_count": 0,
        "delve_slots": 0,
        "dungeon_slots": 0,
        "total_slots": 0,
        "rewards": [],
        "has_t8_plus": 0,  # Count of rewards at ilvl 694+
    }

    # Delves (World row) - only count slots if we have actual tier data
    # The vault API can report count > 0 even with no delves done
    vault_delves = char_data.get("vault_delves", {})
    if isinstance(vault_delves, dict):
        tiers = vault_delves.get("tiers", {})
        if isinstance(tiers, dict) and tiers:
            # Calculate slots from count (tiers dict may be incomplete)
            result["delve_count"] = vault_delves.get("count", 0)
            result["delve_slots"] = count_vault_slots(result["delve_count"])
            for threshold, tier in tiers.items():
                tier_str = get_tier_from_level(int(tier))
                ilvl = get_ilvl_from_tier(tier_str)
                result["rewards"].append((tier_str, ilvl))
                # Count rewards at ilvl 694+ (T8 threshold)
                if ilvl >= 694:
                    result["has_t8_plus"] += 1
            # Fill in missing reward entries for slots not in tiers dict
            for i in range(result["delve_slots"] - len(tiers)):
                # Assume T2 for missing entries (conservative estimate)
                result["rewards"].append(("T2", ILVL_REFERENCE["T2"]))

    # Dungeons (M+ row) - TW/Heroic can unlock slots even without tier data
    vault_dungeons = char_data.get("vault_dungeons", {})
    if isinstance(vault_dungeons, dict):
        result["dungeon_count"] = vault_dungeons.get("count", 0)
        levels = vault_dungeons.get("levels", {})

        if isinstance(levels, dict) and levels:
            # Calculate slots from count (levels dict may be incomplete)
            result["dungeon_slots"] = count_vault_slots(result["dungeon_count"])
            for threshold, level in levels.items():
                tier_str = get_tier_from_level(int(level))
                ilvl = get_ilvl_from_tier(tier_str)
                result["rewards"].append((tier_str, ilvl))
                # Count rewards at ilvl 694+ (T8 threshold)
                if ilvl >= 694:
                    result["has_t8_plus"] += 1
            # Fill in missing reward entries for slots not in levels dict
            for i in range(result["dungeon_slots"] - len(levels)):
                # Assume T2 for missing entries (TW/Heroic level)
                result["rewards"].append(("T2", ILVL_REFERENCE["T2"]))
        elif result["dungeon_count"] > 0:
            # TW/Heroic dungeons - no level data but count > 0
            # These unlock slots at T2 (678) level
            result["dungeon_slots"] = count_vault_slots(result["dungeon_count"])
            for _ in range(result["dungeon_slots"]):
                result["rewards"].append(("T2", ILVL_REFERENCE["T2"]))

    result["total_slots"] = result["delve_slots"] + result["dungeon_slots"]

    return result


def format_vault_rewards(rewards: list) -> str:
    """Format vault rewards for display."""
    if not rewards:
        return "-"

    # Group by tier
    tier_counts = {}
    for tier, ilvl in rewards:
        key = f"{tier} ({ilvl})"
        tier_counts[key] = tier_counts.get(key, 0) + 1

    # Format as "T8+ (710) x2, T2 (678) x1"
    parts = []
    for key, count in sorted(tier_counts.items(), key=lambda x: -get_ilvl_from_tier(x[0].split()[0])):
        if count > 1:
            parts.append(f"{key} ×{count}")
        else:
            parts.append(key)

    return ", ".join(parts)


def get_timewalk_progress(char_data: dict) -> int:
    """Get timewalking quest progress (0-5)."""
    tw_quest = char_data.get("timewalking_quest", {})
    if isinstance(tw_quest, dict):
        if tw_quest.get("completed"):
            return 5
        return int(tw_quest.get("progress", 0))
    return 0


def get_status_emoji(char_data: dict, vault_info: dict, socket_info: dict,
                     tw_available: bool) -> str:
    """Determine status emoji for character."""
    hero_items = char_data.get("heroic_items", 0)
    champ_items = char_data.get("champion_items", 0)
    vet_items = char_data.get("veteran_items", 0)
    adv_items = char_data.get("adventure_items", 0)

    has_non_hero = champ_items > 0 or vet_items > 0 or adv_items > 0
    total_slots = vault_info["total_slots"]
    has_t8_plus = vault_info["has_t8_plus"]
    timewalk = get_timewalk_progress(char_data)

    # Check if fully maxed (all upgrades done + all sockets gemmed)
    upgrade_current = char_data.get("upgrade_current", 0)
    upgrade_max = char_data.get("upgrade_max", 0)
    fully_upgraded = upgrade_max > 0 and upgrade_current == upgrade_max
    all_sockets_gemmed = socket_info["missing_count"] == 0 and socket_info["empty_count"] == 0

    # Fully maxed character on all hero gear = done regardless of vault
    # But still need at least 1 TW if available
    if fully_upgraded and all_sockets_gemmed and not has_non_hero:
        if tw_available and timewalk < 1:
            return "⚠️"
        return "✅"

    # No vault rewards at all = red X
    if total_slots == 0:
        return "❌"

    # If TW is available, everyone needs at least 1 TW completion
    if tw_available and timewalk < 1:
        return "⚠️"

    # Done criteria (vault-based for characters still upgrading)
    if not has_non_hero and total_slots >= 3:
        # All hero gear + 3 vault rewards
        return "✅"
    elif has_non_hero and has_t8_plus >= 3 and total_slots >= 3:
        # Has champ/vet gear: need 3+ T8+ (gilded) + 3 total vault rewards
        # Also need 5/5 timewalking if TW is available (drops random hero gear)
        if tw_available and timewalk < 5:
            return "⚠️"
        return "✅"

    # In between (has some rewards but not done)
    return "⚠️"


def analyze_character(char_data: dict, is_current_week: bool,
                      tw_available: bool) -> dict:
    """Analyze a single character's data.

    Args:
        char_data: Character data from SavedVariables
        is_current_week: Whether the data's week_id matches the current week
        tw_available: Whether timewalking is available this week
    """
    name = char_data.get("name", "Unknown")
    realm = char_data.get("realm", "Unknown")
    char_class = char_data.get("class", "Unknown")
    ilvl = char_data.get("item_level", 0)

    # If data is from a previous week, treat weekly fields as reset
    if not is_current_week:
        # Create a copy with zeroed weekly fields
        char_data = dict(char_data)
        char_data["vault_delves"] = {}
        char_data["vault_dungeons"] = {}
        char_data["delves"] = 0
        char_data["timewalking_done"] = False
        char_data["timewalking_quest"] = {}

    hero_items = char_data.get("heroic_items", 0)
    champ_items = char_data.get("champion_items", 0)
    vet_items = char_data.get("veteran_items", 0)

    upgrade_current = char_data.get("upgrade_current", 0)
    upgrade_max = char_data.get("upgrade_max", 0)
    upgrades_left = upgrade_max - upgrade_current

    vault_info = analyze_vault_rewards(char_data)
    socket_info = analyze_socket_info(char_data)
    enchant_info = analyze_enchant_info(char_data)
    status = get_status_emoji(char_data, vault_info, socket_info, tw_available)

    # Determine missing gear notes
    missing = []
    if champ_items > 0:
        missing.append(f"{champ_items} Champ")
    if vet_items > 0:
        missing.append(f"{vet_items} Vet")

    # Format socket info for display (missing = needs Technomancer's Gift)
    if socket_info["missing_count"] > 0:
        socket_display = f"{socket_info['missing_count']} ({', '.join(socket_info['missing_sockets'])})"
    else:
        socket_display = "-"

    # Format empty socket info (has socket but needs gem)
    if socket_info["empty_count"] > 0:
        empty_display = f"{socket_info['empty_count']} ({', '.join(socket_info['empty_sockets'])})"
    else:
        empty_display = "-"

    # Format enchant info (missing enchantments)
    if enchant_info["missing_count"] > 0:
        enchant_display = f"{enchant_info['missing_count']} ({', '.join(enchant_info['missing_enchants'])})"
    else:
        enchant_display = "-"

    return {
        "name": name,
        "realm": realm,
        "full_name": f"{name}-{realm}",
        "class": char_class,
        "ilvl": ilvl,
        "hero_items": hero_items,
        "champ_items": champ_items,
        "upgrade_current": upgrade_current,
        "upgrade_max": upgrade_max,
        "upgrades_left": upgrades_left,
        "is_complete": upgrades_left == 0 and champ_items == 0 and vet_items == 0,
        "vault_info": vault_info,
        "vault_display": format_vault_rewards(vault_info["rewards"]),
        "socket_info": socket_info,
        "socket_display": socket_display,
        "empty_display": empty_display,
        "enchant_info": enchant_info,
        "enchant_display": enchant_display,
        "status": status,
        "missing": ", ".join(missing) if missing else "-",
        "user_notes": "",  # Will be filled in from app data
    }


def get_notes_display(c: dict) -> str:
    """Combine missing gear info with user notes."""
    parts = []
    if c["missing"] != "-":
        parts.append(c["missing"])
    if c["user_notes"]:
        parts.append(f"({c['user_notes']})")
    return " ".join(parts) if parts else "-"


def display_width(s: str) -> int:
    """Calculate display width accounting for emoji and wide characters."""
    width = 0
    i = 0
    while i < len(s):
        c = s[i]
        code = ord(c)
        # Check for emoji (common ranges)
        if code >= 0x1F300:  # Emoji and symbols
            width += 2
        elif code >= 0x2600 and code <= 0x27BF:  # Misc symbols
            width += 2
        elif code >= 0x2700 and code <= 0x27BF:  # Dingbats
            width += 2
        # Variation selectors (don't add width)
        elif code == 0xFE0F or code == 0xFE0E:
            pass
        else:
            width += 1
        i += 1
    return width


def pad_to_width(s: str, target_width: int) -> str:
    """Pad string to target display width."""
    current = display_width(s)
    if current < target_width:
        return s + " " * (target_width - current)
    return s


def print_table(headers: list[str], rows: list[list[str]]) -> None:
    """Print an aligned table."""
    if not rows:
        return

    # Calculate column widths based on display width
    widths = [display_width(h) for h in headers]
    for row in rows:
        for i, cell in enumerate(row):
            if i < len(widths):
                widths[i] = max(widths[i], display_width(cell))

    # Print header
    header_line = " | ".join(pad_to_width(h, widths[i]) for i, h in enumerate(headers))
    print(f"| {header_line} |")

    # Print separator
    sep_line = " | ".join("-" * widths[i] for i in range(len(headers)))
    print(f"| {sep_line} |")

    # Print rows
    for row in rows:
        row_line = " | ".join(
            pad_to_width(row[i] if i < len(row) else "", widths[i])
            for i in range(len(headers))
        )
        print(f"| {row_line} |")


def print_report(characters: list[dict]) -> None:
    """Print the formatted report."""
    # Sort by status, then by upgrades left
    def sort_key(c):
        status_order = {"✅": 0, "⚠️": 1, "❌": 2}
        return (status_order.get(c["status"], 1), c["upgrades_left"], -c["ilvl"])

    characters.sort(key=sort_key)

    # Separate into groups and sort each by ilvl (descending)
    complete = sorted([c for c in characters if c["is_complete"]], key=lambda c: -c["ilvl"])
    almost = sorted([c for c in characters if not c["is_complete"] and c["upgrades_left"] < 10], key=lambda c: -c["ilvl"])
    needs_work = sorted([c for c in characters if not c["is_complete"] and c["upgrades_left"] >= 10], key=lambda c: -c["ilvl"])

    print("## Hero Gear & Vault Report\n")

    # Fully complete (all hero 8/8, no champion/veteran items)
    if complete:
        print(f"### Fully 8/8 Hero ({len(complete)} characters)\n")
        headers = ["Character", "Class", "iLvl", "Vault Rewards", "Sockets", "Needs Gem", "Needs Enchant"]
        rows = [
            [f"{c['status']} {c['name']}-{c['realm']}", c['class'], f"{c['ilvl']:.1f}", c['vault_display'], c['socket_display'], c['empty_display'], c['enchant_display']]
            for c in complete
        ]
        print_table(headers, rows)
        print()

    # Almost done
    if almost:
        print(f"### Almost Done ({len(almost)} characters)\n")
        headers = ["Character", "Class", "iLvl", "Progress", "Left", "Vault Rewards", "Sockets", "Needs Gem", "Needs Enchant", "Notes"]
        rows = [
            [
                f"{c['status']} {c['name']}-{c['realm']}",
                c['class'],
                f"{c['ilvl']:.1f}",
                f"{c['upgrade_current']}/{c['upgrade_max']}",
                str(c['upgrades_left']),
                c['vault_display'],
                c['socket_display'],
                c['empty_display'],
                c['enchant_display'],
                get_notes_display(c)
            ]
            for c in almost
        ]
        print_table(headers, rows)
        print()

    # Needs work
    if needs_work:
        print(f"### More Work Needed ({len(needs_work)} characters)\n")
        headers = ["Character", "Class", "iLvl", "Progress", "Left", "Vault Rewards", "Sockets", "Needs Gem", "Needs Enchant", "Missing"]
        rows = [
            [
                f"{c['status']} {c['name']}-{c['realm']}",
                c['class'],
                f"{c['ilvl']:.1f}",
                f"{c['upgrade_current']}/{c['upgrade_max']}",
                str(c['upgrades_left']),
                c['vault_display'],
                c['socket_display'],
                c['empty_display'],
                c['enchant_display'],
                get_notes_display(c)
            ]
            for c in needs_work
        ]
        print_table(headers, rows)
        print()

    # Summary
    done_count = sum(1 for c in characters if c["status"] == "✅")
    warn_count = sum(1 for c in characters if c["status"] == "⚠️")
    fail_count = sum(1 for c in characters if c["status"] == "❌")
    total_left = sum(c["upgrades_left"] for c in characters)

    print("### Summary\n")
    headers = ["Status", "Count", "Meaning"]
    rows = [
        ["✅", str(done_count), "Done for the week"],
        ["⚠️", str(warn_count), "Need more vault slots or T8+ content"],
        ["❌", str(fail_count), "No vault rewards"],
    ]
    print_table(headers, rows)
    print()
    print(f"- {total_left} upgrade levels remaining across all characters")


def main():
    parser = argparse.ArgumentParser(
        description="Generate hero gear and vault progress report from WoW addon data"
    )
    parser.add_argument(
        "--hide-done",
        action="store_true",
        help="Hide characters that are done for the week (✅ status)"
    )
    args = parser.parse_args()

    # Load config
    config = load_config()
    wow_path = config.get("wow_path")

    if not wow_path:
        print("wow_path not found in config", file=sys.stderr)
        sys.exit(1)

    # Find SavedVariables
    sv_path = find_saved_variables(wow_path)
    if not sv_path:
        print("Could not find WoWStatTracker_Addon.lua", file=sys.stderr)
        sys.exit(1)

    # Load data
    data = load_saved_variables(sv_path)
    if not data:
        print("Failed to load SavedVariables", file=sys.stderr)
        sys.exit(1)

    characters_data = data.get("characters", {})
    if not characters_data:
        print("No character data found", file=sys.stderr)
        sys.exit(1)

    # Load app data for notes
    app_data = load_app_data()
    notes_map = {}
    for char in app_data:
        key = f"{char.get('name', '')}-{char.get('realm', '')}"
        if char.get("notes"):
            notes_map[key] = char["notes"]

    # Get current week_id for comparison
    current_week_id = get_current_week_id()

    # First pass: detect if timewalking is available this week
    # (any character with current week data has TW quest accepted or progress > 0)
    tw_available = False
    for char_key, char_data in characters_data.items():
        if isinstance(char_data, dict):
            char_week_id = char_data.get("week_id", "")
            if char_week_id == current_week_id:
                tw_quest = char_data.get("timewalking_quest", {})
                if isinstance(tw_quest, dict) and (tw_quest.get("accepted") or tw_quest.get("progress", 0) > 0):
                    tw_available = True
                    break

    # Analyze characters
    characters = []
    for char_key, char_data in characters_data.items():
        if isinstance(char_data, dict):
            # Check if this character's data is from the current week
            char_week_id = char_data.get("week_id", "")
            is_current_week = char_week_id == current_week_id
            analysis = analyze_character(char_data, is_current_week, tw_available)
            # Add notes from app data
            if analysis["full_name"] in notes_map:
                analysis["user_notes"] = notes_map[analysis["full_name"]]
            characters.append(analysis)

    # Filter out done characters if requested
    if args.hide_done:
        characters = [c for c in characters if c["status"] != "✅"]

    # Print report
    print_report(characters)


if __name__ == "__main__":
    main()
