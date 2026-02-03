-- WoW Stat Tracker - Data Collection
-- Collects character statistics and progress data

local addonName, WoWStatTracker = ...

-- ============================================
-- DEBUG LOGGING (stored in SavedVariables)
-- ============================================

-- Maximum log entries to keep
local MAX_LOG_ENTRIES = 500

-- Add a debug log entry (stored in SavedVariables for external viewing)
function WoWStatTracker:LogDebug(message)
    if not WoWStatTrackerDB then return end

    -- Initialize log if needed
    if not WoWStatTrackerDB.debugLog then
        WoWStatTrackerDB.debugLog = {}
    end

    -- Add timestamped entry
    local entry = {
        time = time(),
        timeStr = date("%Y-%m-%d %H:%M:%S"),
        char = UnitName("player") or "Unknown",
        msg = message,
    }
    table.insert(WoWStatTrackerDB.debugLog, entry)

    -- Trim old entries if too many
    while #WoWStatTrackerDB.debugLog > MAX_LOG_ENTRIES do
        table.remove(WoWStatTrackerDB.debugLog, 1)
    end
end

-- Enhanced Debug function that also logs to SavedVariables
local originalDebug = WoWStatTracker.Debug
function WoWStatTracker:Debug(message)
    -- Always log to SavedVariables
    self:LogDebug(message)

    -- Also print to chat if debug mode is enabled
    if WoWStatTrackerDB and WoWStatTrackerDB.settings and WoWStatTrackerDB.settings.debugMode then
        self:Print("|cff888888[Debug]|r " .. message)
    end
end

-- Clear debug log
function WoWStatTracker:ClearDebugLog()
    if WoWStatTrackerDB then
        WoWStatTrackerDB.debugLog = {}
        self:Print("Debug log cleared")
    end
end

-- Update character data
function WoWStatTracker:UpdateCharacterData()
    if not WoWStatTrackerDB then
        return
    end
    
    local charKey = self:GetCharacterKey()
    local charData = self:CollectCharacterData()
    
    if not charData then
        self:Debug("Failed to collect character data")
        return
    end
    
    -- Initialize character entry if it doesn't exist
    if not WoWStatTrackerDB.characters[charKey] then
        WoWStatTrackerDB.characters[charKey] = {}
    end
    
    -- Update character data
    local existingData = WoWStatTrackerDB.characters[charKey]
    for key, value in pairs(charData) do
        existingData[key] = value
    end
    
    -- Update metadata
    existingData.lastUpdate = time()
    WoWStatTrackerDB.metadata.lastExport = time()
    WoWStatTrackerDB.metadata.totalUpdates = (WoWStatTrackerDB.metadata.totalUpdates or 0) + 1
    
    self:Debug("Updated data for " .. charKey)
    
    -- Schedule next update if auto-update is enabled
    if WoWStatTrackerDB.settings.autoUpdate then
        local interval = WoWStatTrackerDB.settings.updateInterval or 300
        C_Timer.After(interval, function()
            self:UpdateCharacterData()
        end)
    end
end

-- Collect all character data
function WoWStatTracker:CollectCharacterData()
    local name = UnitName("player")
    local realm = GetRealmName()

    if not name or not realm then
        return nil
    end

    -- Get upgrade track counts for all equipped items
    local trackCounts, upgradeProgress, slotUpgrades = self:CountItemsByUpgradeTrack()

    -- Get socket and enchant info
    local socketInfo = self:GetSocketInfo()
    local enchantInfo = self:GetEnchantInfo()

    local data = {
        -- Basic character info
        name = name,
        realm = realm,
        class = UnitClass("player"),
        level = UnitLevel("player"),
        guild = GetGuildInfo("player") or "",

        -- Item level (float for precision)
        item_level = self:GetAverageItemLevel(),

        -- Gear counts by upgrade track (from tooltip parsing)
        heroic_items = trackCounts.hero + trackCounts.myth,  -- Hero and Myth tracks
        champion_items = trackCounts.champion,
        veteran_items = trackCounts.veteran,
        adventure_items = trackCounts.adventurer,
        old_items = trackCounts.no_track,  -- Items without upgrade track

        -- Upgrade progress (e.g., 85/128 means 85 upgrades done out of 128 possible)
        upgrade_current = upgradeProgress.current_total,
        upgrade_max = upgradeProgress.max_total,

        -- Per-slot upgrade details (for tooltip display)
        slot_upgrades = slotUpgrades,

        -- Weekly progress (from Great Vault API - aggregate data)
        vault_visited = self:HasVisitedVault(),
        vault_delves = self:GetDelvesFromVault(),  -- {count, tiers={[1]=tier, [4]=tier, [8]=tier}}
        vault_dungeons = self:GetDungeonsFromVault(),  -- {count, levels={[1]=lvl, [4]=lvl, [8]=lvl}}

        -- Event-tracked completions (individual with timestamps)
        delve_completions = self:GetWeeklyDelveCompletions(),  -- [{tier, timestamp}, ...]
        dungeon_completions = self:GetWeeklyDungeonCompletions(),  -- [{type, level, name, timestamp}, ...]
        timewalking_quest = self:GetTimewalkingQuestStatus(),  -- {questId, accepted, completed, progress}

        -- Other weekly progress
        gearing_up = self:HasCompletedGearingUp(),
        quests = self:GetWeeklyQuestsCompleted(),

        -- Gilded stash (tier 11 bonus crests)
        gilded_stash = self:GetGildedStashStatus(),  -- {available, claimed, total}

        -- Socket info (for Technomancer's Gift tracking)
        socket_info = socketInfo,  -- {slots_with_sockets, missing_sockets, empty_sockets, socketable_count, socketed_count, empty_count}

        -- Enchant info (missing enchantments)
        enchant_info = enchantInfo,  -- {missing_enchants, enchant_count, enchantable_count}

        -- Timestamps and week tracking
        lastLogin = time(),
        dataVersion = WoWStatTracker.version,
        week_id = self:GetCurrentWeekId(),  -- Track which week this data is from
    }

    return data
end

-- Equipment slots to check (excludes shirt slot 4 and tabard slot 19)
local EQUIPMENT_SLOTS = {
    1,  -- Head
    2,  -- Neck
    3,  -- Shoulder
    5,  -- Chest
    6,  -- Waist
    7,  -- Legs
    8,  -- Feet
    9,  -- Wrist
    10, -- Hands
    11, -- Finger 1
    12, -- Finger 2
    13, -- Trinket 1
    14, -- Trinket 2
    15, -- Back
    16, -- Main Hand
    17, -- Off Hand
}

-- Upgrade track constants (from C_ItemUpgrade API)
local UPGRADE_TRACK = {
    ADVENTURER = 1,
    VETERAN = 2,
    CHAMPION = 3,
    HERO = 4,
    MYTH = 5,  -- Mythic track for highest tier
}

-- Slots that can receive Technomancer's Gift (adds a socket)
-- Per Wowhead: Helms, Bracers, Belts only
local SOCKETABLE_SLOTS = {
    [1] = true,   -- Head
    [6] = true,   -- Waist (Belt)
    [9] = true,   -- Wrist (Bracer)
}

-- Slot names for debugging/display
local SLOT_NAMES = {
    [1] = "Head",
    [2] = "Neck",
    [3] = "Shoulder",
    [5] = "Chest",
    [6] = "Waist",
    [7] = "Legs",
    [8] = "Feet",
    [9] = "Wrist",
    [10] = "Hands",
    [11] = "Ring1",
    [12] = "Ring2",
    [13] = "Trinket1",
    [14] = "Trinket2",
    [15] = "Back",
    [16] = "MainHand",
    [17] = "OffHand",
}

-- Check if an item has a socket
-- Returns: { hasSocket = bool, hasGem = bool }
function WoWStatTracker:ItemHasSocket(itemLink)
    local result = { hasSocket = false, hasGem = false }

    if not itemLink then
        return result
    end

    -- Method 1: Check for socketed gem using GetItemGem API
    -- This is the most reliable way to detect filled sockets
    if GetItemGem then
        local gemLink = GetItemGem(itemLink, 1)
        if gemLink and gemLink ~= "" then
            result.hasSocket = true
            result.hasGem = true
            return result
        end
    end

    -- Method 2: Check tooltip for empty sockets
    -- Empty sockets show "Prismatic Socket" or "Empty Socket" in tooltip
    if C_TooltipInfo and C_TooltipInfo.GetHyperlink then
        local tooltipData = C_TooltipInfo.GetHyperlink(itemLink)
        if tooltipData and tooltipData.lines then
            for _, line in ipairs(tooltipData.lines) do
                if line.leftText then
                    if line.leftText:match("Prismatic Socket") or
                       line.leftText:match("Empty Socket") then
                        result.hasSocket = true
                        -- hasGem stays false since GetItemGem check above found nothing
                    end
                end
            end
        end
    end

    return result
end

-- Get socket information for all equipped items
-- Returns: { slots_with_sockets = {slot_ids}, missing_sockets = {slot_ids for socketable slots without sockets},
--            empty_sockets = {slot_ids with sockets but no gems} }
function WoWStatTracker:GetSocketInfo()
    local result = {
        slots_with_sockets = {},     -- List of slot IDs that have sockets
        missing_sockets = {},         -- List of socketable slot IDs missing sockets (need Technomancer's Gift)
        empty_sockets = {},           -- List of slot IDs with sockets but no gems
        socketable_count = 0,         -- Total socketable slots
        socketed_count = 0,           -- Socketable slots that have sockets
        empty_count = 0,              -- Sockets without gems
    }

    -- Wrap in pcall to prevent errors from breaking the update
    local success, err = pcall(function()
        for _, slotId in ipairs(EQUIPMENT_SLOTS) do
            local itemLink = GetInventoryItemLink("player", slotId)
            if itemLink then
                local socketInfo = self:ItemHasSocket(itemLink)

                if socketInfo.hasSocket then
                    table.insert(result.slots_with_sockets, slotId)

                    -- Track sockets without gems
                    if not socketInfo.hasGem then
                        table.insert(result.empty_sockets, slotId)
                        result.empty_count = result.empty_count + 1
                    end
                end

                -- Check if this is a socketable slot (can use Technomancer's Gift)
                if SOCKETABLE_SLOTS[slotId] then
                    result.socketable_count = result.socketable_count + 1
                    if socketInfo.hasSocket then
                        result.socketed_count = result.socketed_count + 1
                    else
                        table.insert(result.missing_sockets, slotId)
                    end
                end
            end
        end
    end)

    if not success then
        self:Debug("GetSocketInfo error: " .. tostring(err))
    end

    return result
end

-- Slots that can be enchanted
-- In TWW: Chest, Back, Wrist, Legs, Feet, Rings, Weapon
local ENCHANTABLE_SLOTS = {
    [5] = true,   -- Chest
    [7] = true,   -- Legs
    [8] = true,   -- Feet
    [9] = true,   -- Wrist
    [11] = true,  -- Ring 1
    [12] = true,  -- Ring 2
    [15] = true,  -- Back
    [16] = true,  -- Main Hand
}

-- Check if an item has an enchantment by scanning its tooltip
-- Returns: true if enchanted, false otherwise
function WoWStatTracker:ItemHasEnchant(itemLink)
    if not itemLink then
        return false
    end

    -- Use C_TooltipInfo to get tooltip data
    if C_TooltipInfo and C_TooltipInfo.GetHyperlink then
        local tooltipData = C_TooltipInfo.GetHyperlink(itemLink)
        if tooltipData and tooltipData.lines then
            for _, line in ipairs(tooltipData.lines) do
                if line.leftText then
                    -- Enchantments show as "Enchanted: <name>" or specific enchant effects
                    -- Also check for common TWW enchant patterns
                    if line.leftText:match("^Enchanted:") or
                       line.leftText:match("Council's") or
                       line.leftText:match("Crystalline") or
                       line.leftText:match("Defender's") or
                       line.leftText:match("Cavalry's") or
                       line.leftText:match("Scout's") or
                       line.leftText:match("Oathsworn's") or
                       line.leftText:match("Stormrider's") or
                       line.leftText:match("Radiant") or
                       line.leftText:match("Cursed") then
                        return true
                    end
                end
            end
        end
    end

    return false
end

-- Get enchantment information for all equipped items
-- Returns: { missing_enchants = {slot_ids}, enchant_count = N, enchantable_count = N }
function WoWStatTracker:GetEnchantInfo()
    local result = {
        missing_enchants = {},    -- List of enchantable slot IDs without enchants
        enchant_count = 0,        -- Number of enchanted slots
        enchantable_count = 0,    -- Total enchantable slots equipped
    }

    -- Wrap in pcall to prevent errors from breaking the update
    local success, err = pcall(function()
        for _, slotId in ipairs(EQUIPMENT_SLOTS) do
            local itemLink = GetInventoryItemLink("player", slotId)
            if itemLink then
                -- Check if this is an enchantable slot
                if ENCHANTABLE_SLOTS[slotId] then
                    result.enchantable_count = result.enchantable_count + 1
                    if self:ItemHasEnchant(itemLink) then
                        result.enchant_count = result.enchant_count + 1
                    else
                        table.insert(result.missing_enchants, slotId)
                    end
                end
            end
        end
    end)

    if not success then
        self:Debug("GetEnchantInfo error: " .. tostring(err))
    end

    return result
end

-- Get average item level (returns float for precision)
function WoWStatTracker:GetAverageItemLevel()
    local totalIlvl = 0
    local itemCount = 0

    for _, slotId in ipairs(EQUIPMENT_SLOTS) do
        local itemLink = GetInventoryItemLink("player", slotId)
        if itemLink then
            local itemLevel = GetDetailedItemLevelInfo(itemLink)
            if itemLevel and itemLevel > 0 then
                totalIlvl = totalIlvl + itemLevel
                itemCount = itemCount + 1
            end
        end
    end

    local result = itemCount > 0 and (totalIlvl / itemCount) or 0

    -- If no items found (e.g., during logout), preserve cached value
    if itemCount == 0 then
        local charKey = self:GetCharacterKey()
        if WoWStatTrackerDB and WoWStatTrackerDB.characters and WoWStatTrackerDB.characters[charKey] then
            local cached = WoWStatTrackerDB.characters[charKey].item_level
            if cached and cached > 0 then
                self:LogDebug("GetAverageItemLevel: 0 items, using cached=" .. string.format("%.1f", cached))
                return cached
            end
        end
    end

    -- Always log item level calculation for debugging
    self:LogDebug("GetAverageItemLevel: " .. itemCount .. " items, total=" .. totalIlvl .. ", avg=" .. string.format("%.1f", result))

    return result
end

-- Track name to ID mapping
local TRACK_NAME_TO_ID = {
    ["Adventurer"] = UPGRADE_TRACK.ADVENTURER,
    ["Explorer"] = UPGRADE_TRACK.ADVENTURER,  -- Alternative name
    ["Veteran"] = UPGRADE_TRACK.VETERAN,
    ["Champion"] = UPGRADE_TRACK.CHAMPION,
    ["Hero"] = UPGRADE_TRACK.HERO,
    ["Myth"] = UPGRADE_TRACK.MYTH,
    ["Mythic"] = UPGRADE_TRACK.MYTH,
}

-- Get upgrade track for an item by scanning tooltip
-- Returns: track number (1=Adventurer, 2=Veteran, 3=Champion, 4=Hero, 5=Myth), or nil, or "special" for artifact/rank items
function WoWStatTracker:GetItemUpgradeTrack(itemLink)
    if not itemLink then
        return nil
    end

    -- Use C_TooltipInfo to get tooltip data without creating a visible tooltip
    if C_TooltipInfo and C_TooltipInfo.GetHyperlink then
        local tooltipData = C_TooltipInfo.GetHyperlink(itemLink)
        if tooltipData and tooltipData.lines then
            local itemName = GetItemInfo(itemLink) or "Unknown"
            local debugMode = WoWStatTrackerDB and WoWStatTrackerDB.settings.debugMode

            -- Debug: show first few tooltip lines
            if debugMode then
                self:Debug("Tooltip for " .. itemName .. ":")
                for i, line in ipairs(tooltipData.lines) do
                    if i <= 8 and line.leftText then
                        self:Debug("  [" .. i .. "] " .. line.leftText)
                    end
                end
            end

            -- Check for special items (Artifact with Rank) - these are not "old", they're special
            local isArtifact = false
            local hasRank = false
            for _, line in ipairs(tooltipData.lines) do
                if line.leftText then
                    if line.leftText == "Artifact" then
                        isArtifact = true
                    end
                    if line.leftText:match("Rank%s*%d") then
                        hasRank = true
                    end
                end
            end
            if isArtifact and hasRank then
                if debugMode then
                    self:Debug("  SPECIAL: Artifact with Rank (e.g., Reshii Wraps)")
                end
                return "special"
            end

            for _, line in ipairs(tooltipData.lines) do
                if line.leftText then
                    -- Match "Upgrade Level: Hero 4/8" format
                    local trackName, current, max = line.leftText:match("Upgrade Level:%s*(%a+)%s+(%d+)/(%d+)")
                    if trackName and TRACK_NAME_TO_ID[trackName] then
                        if debugMode then
                            self:Debug("  FOUND: " .. trackName .. " " .. current .. "/" .. max)
                        end
                        return TRACK_NAME_TO_ID[trackName], tonumber(current), tonumber(max)
                    end
                end
            end
        end
    end

    -- Fallback: try the old C_ItemUpgrade API
    if C_ItemUpgrade and C_ItemUpgrade.GetItemUpgradeItemInfo then
        local upgradeInfo = C_ItemUpgrade.GetItemUpgradeItemInfo(itemLink)
        if upgradeInfo and upgradeInfo.currTrack then
            return upgradeInfo.currTrack
        end
    end

    if WoWStatTrackerDB and WoWStatTrackerDB.settings.debugMode then
        local itemName = GetItemInfo(itemLink) or "Unknown"
        self:Debug("No track found for " .. itemName)
    end

    return nil
end

-- Track ID to name mapping for per-slot data
local TRACK_ID_TO_NAME = {
    [UPGRADE_TRACK.ADVENTURER] = "Adventurer",
    [UPGRADE_TRACK.VETERAN] = "Veteran",
    [UPGRADE_TRACK.CHAMPION] = "Champion",
    [UPGRADE_TRACK.HERO] = "Hero",
    [UPGRADE_TRACK.MYTH] = "Myth",
}

-- Count equipped items by upgrade track
-- Returns: counts table, upgrades table, slot_upgrades table (per-slot details)
function WoWStatTracker:CountItemsByUpgradeTrack()
    local counts = {
        adventurer = 0,
        veteran = 0,
        champion = 0,
        hero = 0,
        myth = 0,
        special = 0,   -- Special items like Reshii Wraps (Artifact with Rank)
        no_track = 0,  -- Items without upgrade track (old gear)
    }
    -- Track total upgrade levels (e.g., 4/8 + 6/8 = 10 current, 16 max)
    local upgrades = {
        current_total = 0,
        max_total = 0,
    }
    -- Per-slot upgrade details for tooltip display
    local slot_upgrades = {}

    local itemsFound = 0
    for _, slotId in ipairs(EQUIPMENT_SLOTS) do
        local itemLink = GetInventoryItemLink("player", slotId)
        if itemLink then
            itemsFound = itemsFound + 1
            local track, current, max = self:GetItemUpgradeTrack(itemLink)
            if track == "special" then
                -- Special items (Artifact with Rank) - don't count as old
                counts.special = counts.special + 1
            elseif track == UPGRADE_TRACK.ADVENTURER then
                counts.adventurer = counts.adventurer + 1
            elseif track == UPGRADE_TRACK.VETERAN then
                counts.veteran = counts.veteran + 1
            elseif track == UPGRADE_TRACK.CHAMPION then
                counts.champion = counts.champion + 1
            elseif track == UPGRADE_TRACK.HERO then
                counts.hero = counts.hero + 1
            elseif track == UPGRADE_TRACK.MYTH then
                counts.myth = counts.myth + 1
            else
                -- Item has no upgrade track (old gear)
                counts.no_track = counts.no_track + 1
            end
            -- Sum up upgrade progress and store per-slot data
            if current and max then
                upgrades.current_total = upgrades.current_total + current
                upgrades.max_total = upgrades.max_total + max

                -- Store per-slot details for items that need attention:
                -- 1. Not fully upgraded on current track (current < max)
                -- 2. Fully upgraded but on a non-hero track (needs hero replacement)
                local trackName = TRACK_ID_TO_NAME[track]
                local needsUpgrade = current < max
                local needsHero = (current >= max) and
                    (track == UPGRADE_TRACK.CHAMPION or
                     track == UPGRADE_TRACK.VETERAN or
                     track == UPGRADE_TRACK.ADVENTURER)
                if trackName and (needsUpgrade or needsHero) then
                    local itemId = GetItemInfoInstant(itemLink)
                    slot_upgrades[slotId] = {
                        slot = slotId,
                        slot_name = SLOT_NAMES[slotId] or "Unknown",
                        track = trackName,
                        current = current,
                        max = max,
                        item_id = itemId or 0,
                    }
                end
            end
        end
    end

    -- If no items found (e.g., during logout), preserve cached values
    if itemsFound == 0 then
        local charKey = self:GetCharacterKey()
        if WoWStatTrackerDB and WoWStatTrackerDB.characters and WoWStatTrackerDB.characters[charKey] then
            local char = WoWStatTrackerDB.characters[charKey]
            counts.hero = char.heroic_items or 0
            counts.champion = char.champion_items or 0
            counts.veteran = char.veteran_items or 0
            counts.adventurer = char.adventure_items or 0
            counts.no_track = char.old_items or 0
            upgrades.current_total = char.upgrade_current or 0
            upgrades.max_total = char.upgrade_max or 0
            slot_upgrades = char.slot_upgrades or {}
            self:LogDebug("CountItemsByUpgradeTrack: 0 items, using cached values")
        end
    end

    return counts, upgrades, slot_upgrades
end

-- Legacy function for backward compatibility - count by item quality
function WoWStatTracker:CountItemsByQuality(quality)
    local count = 0

    for _, slotId in ipairs(EQUIPMENT_SLOTS) do
        local itemLink = GetInventoryItemLink("player", slotId)
        if itemLink then
            local _, _, itemQuality = GetItemInfo(itemLink)
            if itemQuality == quality then
                count = count + 1
            end
        end
    end

    return count
end

-- Check if player has visited/claimed the Great Vault this week
function WoWStatTracker:HasVisitedVault()
    if not C_WeeklyRewards then
        return false
    end

    local debugMode = WoWStatTrackerDB and WoWStatTrackerDB.settings.debugMode

    -- Check if there are rewards available to claim
    local hasAvailable = C_WeeklyRewards.HasAvailableRewards and C_WeeklyRewards.HasAvailableRewards()

    -- Check if we can claim rewards (slightly different API)
    local canClaim = C_WeeklyRewards.CanClaimRewards and C_WeeklyRewards.CanClaimRewards()

    -- Check if any slot has been unlocked (has rewards, even if claimed)
    local hasUnlockedSlot = false
    local hasClaimedSlot = false

    -- Activity types to check: 1=Raid, 2=MythicPlus, 3=World
    local activityTypes = {
        {type = 1, name = "Raid"},
        {type = 2, name = "MythicPlus"},
        {type = 3, name = "World"},
    }

    if C_WeeklyRewards.GetActivities then
        for _, typeInfo in ipairs(activityTypes) do
            local activities = C_WeeklyRewards.GetActivities(typeInfo.type)

            if debugMode then
                self:Debug("--- " .. typeInfo.name .. " (type " .. typeInfo.type .. ") ---")
            end

            if activities then
                for i, activity in ipairs(activities) do
                    if debugMode then
                        self:Debug(typeInfo.name .. " Slot " .. i .. ": prog=" .. tostring(activity.progress) ..
                                   " thresh=" .. tostring(activity.threshold) ..
                                   " lvl=" .. tostring(activity.level) ..
                                   " claimID=" .. tostring(activity.claimID) ..
                                   " claimed=" .. tostring(activity.claimed))
                    end

                    -- Check if this slot is unlocked (progress >= threshold)
                    if activity.progress and activity.threshold and activity.progress >= activity.threshold then
                        hasUnlockedSlot = true
                        if debugMode then
                            self:Debug("  >> UNLOCKED")
                        end
                    end

                    -- Check if reward was claimed for this slot
                    if activity.claimID or activity.claimed then
                        hasClaimedSlot = true
                        if debugMode then
                            self:Debug("  >> CLAIMED")
                        end
                    end
                end
            else
                if debugMode then
                    self:Debug("  (no activities)")
                end
            end
        end
    end

    if debugMode then
        self:Debug("Vault: avail=" .. tostring(hasAvailable) ..
                   " canClaim=" .. tostring(canClaim) ..
                   " unlocked=" .. tostring(hasUnlockedSlot) ..
                   " claimed=" .. tostring(hasClaimedSlot))
    end

    -- Vault visited = claimed a reward OR no rewards available to claim
    -- (either already claimed, or no activities done this week)
    return hasClaimedSlot or not canClaim
end

-- Get delve/world activity information from Great Vault
-- Returns: { count, tiers = {tier_at_1, tier_at_4, tier_at_8} }
function WoWStatTracker:GetDelvesFromVault()
    local result = {
        count = 0,
        tiers = {},  -- tier level at each threshold (1, 4, 8)
    }

    if C_WeeklyRewards and C_WeeklyRewards.GetActivities then
        local activities = C_WeeklyRewards.GetActivities(Enum.WeeklyRewardChestThresholdType.World)
        if activities then
            for _, activity in ipairs(activities) do
                -- progress is the total count of activities
                if activity.progress and activity.progress > result.count then
                    result.count = activity.progress
                end
                -- level is the tier for this threshold slot
                -- threshold is how many needed (1, 4, 8)
                if activity.level and activity.level > 0 then
                    result.tiers[activity.threshold] = activity.level
                end
            end
        end
    end

    if WoWStatTrackerDB and WoWStatTrackerDB.settings.debugMode then
        self:Debug("Vault World Activities: " .. result.count .. " completed")
        for threshold, tier in pairs(result.tiers) do
            self:Debug("  At " .. threshold .. ": Tier " .. tier)
        end
    end

    return result
end

-- Get dungeon (Heroic/Mythic/Timewalking) information from Great Vault
-- Returns: { count, levels = {level_at_1, level_at_4, level_at_8} }
function WoWStatTracker:GetDungeonsFromVault()
    local result = {
        count = 0,
        levels = {},  -- M+ level or dungeon difficulty at each threshold
    }

    if C_WeeklyRewards and C_WeeklyRewards.GetActivities then
        local activities = C_WeeklyRewards.GetActivities(Enum.WeeklyRewardChestThresholdType.MythicPlus)
        if activities then
            for _, activity in ipairs(activities) do
                if activity.progress and activity.progress > result.count then
                    result.count = activity.progress
                end
                if activity.level and activity.level > 0 then
                    result.levels[activity.threshold] = activity.level
                end
            end
        end
    end

    if WoWStatTrackerDB and WoWStatTrackerDB.settings.debugMode then
        self:Debug("Vault Dungeons: " .. result.count .. " completed")
        for threshold, level in pairs(result.levels) do
            self:Debug("  At " .. threshold .. ": Level " .. level)
        end
    end

    return result
end

-- "Gearing Up for Trouble" - Awakening the Machine weekly quest
local GEARING_UP_QUEST_ID = 83333

-- Check if "Gearing Up for Trouble" weekly quest is completed
function WoWStatTracker:HasCompletedGearingUp()
    -- Check if quest is completed this week
    if C_QuestLog.IsQuestFlaggedCompleted(GEARING_UP_QUEST_ID) then
        if WoWStatTrackerDB and WoWStatTrackerDB.settings.debugMode then
            self:Debug("Awakening the Machine weekly completed")
        end
        return true
    end

    -- Check if quest is in progress and get wave count
    if C_QuestLog.IsOnQuest(GEARING_UP_QUEST_ID) then
        local objectives = C_QuestLog.GetQuestObjectives(GEARING_UP_QUEST_ID)
        if objectives and objectives[1] then
            local progress = objectives[1].numFulfilled or 0
            if WoWStatTrackerDB and WoWStatTrackerDB.settings.debugMode then
                self:Debug("Awakening the Machine progress: " .. progress .. "/20 waves")
            end
        end
    end

    return false
end

-- Get weekly quests completed (placeholder for future expansion)
function WoWStatTracker:GetWeeklyQuestsCompleted()
    -- Could track Theater Troupe, Spreading the Light, etc.
    return false
end

-- Timewalking weekly quest IDs (complete 5 dungeons)
-- These are the "A [X] Path Through Time" quests
-- The War Within (11.x) uses 833xx IDs, older expansions used 727xx
-- Shared via WoWStatTracker object so EventHandler.lua can use it too
WoWStatTracker.TIMEWALKING_QUEST_IDS = {
    -- The War Within (current)
    83363,  -- A Burning Path Through Time (BC)
    83365,  -- A Frozen Path Through Time (WotLK)
    83359,  -- A Shattered Path Through Time (Cataclysm)
    83362,  -- A Shrouded Path Through Time (MoP)
    83364,  -- A Savage Path Through Time (WoD)
    83360,  -- A Fel Path Through Time (Legion)
    83274,  -- An Original Path Through Time (Classic)
    88805,  -- A Scarred Path Through Time (BfA)
    92649,  -- A Shadowed Path Through Time (Shadowlands)
    -- Legacy IDs (pre-War Within, kept for compatibility)
    72727,  -- A Burning Path Through Time (BC)
    72726,  -- A Frozen Path Through Time (WotLK)
    72810,  -- A Shattered Path Through Time (Cataclysm)
    72725,  -- A Shrouded Path Through Time (MoP)
    72724,  -- A Savage Path Through Time (WoD)
    72719,  -- A Fel Path Through Time (Legion)
}

-- Get timewalking progress
function WoWStatTracker:GetTimewalkingCompleted()
    local debugMode = WoWStatTrackerDB and WoWStatTrackerDB.settings.debugMode

    for _, questId in ipairs(self.TIMEWALKING_QUEST_IDS) do
        -- Check if quest is in log (active this week)
        if C_QuestLog.IsOnQuest(questId) then
            -- Get objectives to see progress (X/5 dungeons)
            local objectives = C_QuestLog.GetQuestObjectives(questId)
            if objectives and objectives[1] then
                local progress = objectives[1].numFulfilled or 0
                if debugMode then
                    self:Debug("Timewalking quest " .. questId .. " in progress: " .. progress .. "/5")
                end
                return progress
            end
        end
        -- Check if already completed this week
        if C_QuestLog.IsQuestFlaggedCompleted(questId) then
            if debugMode then
                self:Debug("Timewalking quest " .. questId .. " completed this week")
            end
            return 5  -- Completed = 5/5
        end
    end

    -- Try checking via weekly cache/bonus roll currency or other methods
    -- If we can't find it via quests, check if there's TW event active
    if debugMode then
        self:Debug("No timewalking quest found active or completed")
        -- Debug: Check a few quest IDs to see their status
        for _, questId in ipairs({72727, 72726, 72810, 72725, 72724, 72719}) do
            local onQuest = C_QuestLog.IsOnQuest(questId)
            local completed = C_QuestLog.IsQuestFlaggedCompleted(questId)
            if onQuest or completed then
                self:Debug("  Quest " .. questId .. ": onQuest=" .. tostring(onQuest) .. " completed=" .. tostring(completed))
            end
        end
    end

    return 0
end

-- ============================================
-- GILDED STASH TRACKING (Tier 11 Bonus Crests)
-- ============================================

-- Explore C_DelvesUI API to discover available functions
function WoWStatTracker:ExploreDelveAPI()
    self:Print("Exploring C_DelvesUI API...")
    self:Debug("=== ExploreDelveAPI Start ===")

    if not C_DelvesUI then
        print("  C_DelvesUI is not available")
        self:Debug("C_DelvesUI not available")
        return
    end

    self:Debug("C_DelvesUI exists, type=" .. type(C_DelvesUI))

    -- Try known function names directly since pairs() may not work on API tables
    local knownFuncs = {
        "GetCurrentDelvesSeasonNumber",
        "GetDelvesAffixInfo",
        "GetFactionForCompanion",
        "GetGildedStashProgress",
        "GetBountifulProgress",
        "GetWeeklyBountifulProgress",
        "GetBountifulDelveInfo",
        "HasBountifulDelve",
        "GetDelvesSeasonInfo",
        "GetSeasonProgress",
        "GetRuneforgeEffectInfo",
        "GetCurrentCompanionInfo",
        "GetCompanionInfo",
        "IsCompanionSlotUnlocked",
        "GetUnlockedCompanionData",
        "GetDelveLevel",
        "GetCurrentDelveInfo",
        "GetActiveDelveInfo",
    }

    print("|cff00ff00Testing C_DelvesUI functions:|r")
    for _, name in ipairs(knownFuncs) do
        local func = C_DelvesUI[name]
        if func then
            local success, r1, r2, r3 = pcall(func)
            if success then
                local result = tostring(r1)
                if r2 ~= nil then result = result .. ", " .. tostring(r2) end
                if r3 ~= nil then result = result .. ", " .. tostring(r3) end
                print("  " .. name .. " = " .. result)
                self:Debug(name .. " = " .. result)
                if type(r1) == "table" then
                    for k, v in pairs(r1) do
                        self:Debug("  ." .. tostring(k) .. " = " .. tostring(v))
                    end
                end
            else
                self:Debug(name .. " ERROR: " .. tostring(r1))
            end
        else
            self:Debug(name .. " not found")
        end
    end

    -- Check crest currencies
    print("|cff00ff00Checking crest currencies:|r")
    local crestCurrencies = {
        {id = 3008, name = "Gilded Harbinger Crest"},
        {id = 2914, name = "Weathered Crest"},
        {id = 2915, name = "Carved Crest"},
        {id = 2916, name = "Runed Crest"},
    }
    for _, curr in ipairs(crestCurrencies) do
        local info = C_CurrencyInfo.GetCurrencyInfo(curr.id)
        if info then
            local msg = curr.name .. ": " .. tostring(info.quantity) .. "/" .. tostring(info.maxQuantity)
            print("  " .. msg)
            self:Debug(msg)
        end
    end

    -- Log to savedvariables for review
    self:Debug("=== ExploreDelveAPI Complete ===")
end

-- Explore C_DelvesUI for gilded stash - called during update
function WoWStatTracker:LogDelvesAPIInfo()
    self:Debug("--- C_DelvesUI API Check ---")

    if not C_DelvesUI then
        self:Debug("C_DelvesUI not available")
        return
    end

    -- Test known functions
    local tests = {
        {"GetCurrentDelvesSeasonNumber", function() return C_DelvesUI.GetCurrentDelvesSeasonNumber and C_DelvesUI.GetCurrentDelvesSeasonNumber() end},
        {"HasActiveDelve", function() return C_DelvesUI.HasActiveDelve and C_DelvesUI.HasActiveDelve() end},
    }

    for _, test in ipairs(tests) do
        local name, func = test[1], test[2]
        local ok, result = pcall(func)
        if ok then
            self:Debug("  " .. name .. " = " .. tostring(result))
        end
    end

    -- Check currencies that might be gilded stash related
    local currencies = {
        2914, 2915, 2916, 2917, -- Harbinger crests (Weathered/Carved/Runed/Gilded)
        3008,                    -- Valorstones
        -- TWW Season 2+ currencies
        3028, 3029, 3030, 3031, 3032, 3033, 3034, 3035, 3036, 3037, 3038, 3039,
        3040, 3041, 3042, 3043, 3044, 3045, 3046, 3047, 3048, 3049, 3050,
        -- Delve-specific?
        3100, 3101, 3102, 3103, 3104, 3105,
    }

    for _, id in ipairs(currencies) do
        local info = C_CurrencyInfo.GetCurrencyInfo(id)
        if info and info.name and info.name ~= "" and info.quantity > 0 then
            self:Debug("  Currency " .. id .. ": " .. info.name .. " = " .. tostring(info.quantity) .. "/" .. tostring(info.maxQuantity))
        end
    end

    -- Check for gilded stash related quests (weekly bonus crest quests)
    -- Scan a range of quest IDs to find gilded stash trackers
    self:Debug("  Gilded stash quest scan (83690-83720):")
    local gildedCount = 0
    for qid = 83690, 83720 do
        if C_QuestLog.IsQuestFlaggedCompleted(qid) then
            gildedCount = gildedCount + 1
            self:Debug("    Quest " .. qid .. " COMPLETED")
        end
    end
    self:Debug("  Total completed in range: " .. gildedCount)

    -- Scan for active timewalking quest (search wider range)
    self:Debug("  Timewalking quest scan:")
    -- Check active quests for "Path Through Time" in title
    local numQuests = C_QuestLog.GetNumQuestLogEntries()
    for i = 1, numQuests do
        local info = C_QuestLog.GetInfo(i)
        if info and info.title and info.title:find("Path") then
            self:Debug("    ACTIVE: " .. info.questID .. ": " .. info.title)
            local obj = C_QuestLog.GetQuestObjectives(info.questID)
            if obj and obj[1] then
                self:Debug("      Progress: " .. tostring(obj[1].numFulfilled) .. "/" .. tostring(obj[1].numRequired))
            end
        end
    end
    -- Also scan legacy ranges
    for qid = 72710, 72730 do
        if C_QuestLog.IsOnQuest(qid) or C_QuestLog.IsQuestFlaggedCompleted(qid) then
            local title = C_QuestLog.GetTitleForQuestID(qid)
            local onQuest = C_QuestLog.IsOnQuest(qid)
            local completed = C_QuestLog.IsQuestFlaggedCompleted(qid)
            self:Debug("    " .. qid .. ": " .. tostring(title) .. " on=" .. tostring(onQuest) .. " done=" .. tostring(completed))
            if onQuest then
                local obj = C_QuestLog.GetQuestObjectives(qid)
                if obj and obj[1] then
                    self:Debug("      Progress: " .. tostring(obj[1].numFulfilled) .. "/" .. tostring(obj[1].numRequired))
                end
            end
        end
    end
    -- Also scan 83700-83720 and 84700-84720 for TWW era quests
    for qid = 83700, 83720 do
        if C_QuestLog.IsOnQuest(qid) or C_QuestLog.IsQuestFlaggedCompleted(qid) then
            local title = C_QuestLog.GetTitleForQuestID(qid)
            local onQuest = C_QuestLog.IsOnQuest(qid)
            self:Debug("    " .. qid .. ": " .. tostring(title) .. " on=" .. tostring(onQuest))
            if onQuest then
                local obj = C_QuestLog.GetQuestObjectives(qid)
                if obj and obj[1] then
                    self:Debug("      Progress: " .. tostring(obj[1].numFulfilled) .. "/" .. tostring(obj[1].numRequired))
                end
            end
        end
    end
    for qid = 84700, 84720 do
        if C_QuestLog.IsOnQuest(qid) or C_QuestLog.IsQuestFlaggedCompleted(qid) then
            local title = C_QuestLog.GetTitleForQuestID(qid)
            local onQuest = C_QuestLog.IsOnQuest(qid)
            self:Debug("    " .. qid .. ": " .. tostring(title) .. " on=" .. tostring(onQuest))
            if onQuest then
                local obj = C_QuestLog.GetQuestObjectives(qid)
                if obj and obj[1] then
                    self:Debug("      Progress: " .. tostring(obj[1].numFulfilled) .. "/" .. tostring(obj[1].numRequired))
                end
            end
        end
    end

    self:Debug("--- End API Check ---")
end

-- Gilded Stash tracking via UI Widgets (from Plumber addon research)
-- Widget IDs that may contain gilded stash spell info
local GILDED_STASH_WIDGET_IDS = {6659, 6718, 6719, 6720, 6721, 6722, 6723, 6724, 6725, 6726, 6727, 6728, 6729, 6794, 7193}
-- Spell ID for Gilded Stash (spell 1216211)
local GILDED_STASH_SPELL_ID = 1216211

-- Get gilded stash tooltip from UI widgets
local function GetGildedStashTooltip()
    if not C_UIWidgetManager or not C_UIWidgetManager.GetSpellDisplayVisualizationInfo then
        return nil
    end

    for _, widgetID in ipairs(GILDED_STASH_WIDGET_IDS) do
        local info = C_UIWidgetManager.GetSpellDisplayVisualizationInfo(widgetID)
        if info and info.spellInfo then
            if info.spellInfo.spellID == GILDED_STASH_SPELL_ID and info.spellInfo.shownState == 1 then
                return info.spellInfo.tooltip
            end
        end
    end
    return nil
end

-- Get gilded stash status (bonus crests from tier 11 delves)
-- Returns: { available = 3, claimed = 0, total = 3 }
function WoWStatTracker:GetGildedStashStatus()
    local result = {
        available = 0,  -- How many can still be claimed
        claimed = 0,    -- How many have been claimed
        total = 3,      -- Total per week (usually 3)
    }

    local debugMode = WoWStatTrackerDB and WoWStatTrackerDB.settings.debugMode

    -- Log API info during debug mode
    if debugMode then
        self:LogDelvesAPIInfo()
    end

    -- Primary method: UI Widget tracking (same method as Plumber addon)
    -- This uses C_UIWidgetManager.GetSpellDisplayVisualizationInfo to find gilded stash progress
    local tooltip = GetGildedStashTooltip()
    if tooltip then
        -- Extract "X/Y" from tooltip text
        local current, max = string.match(tooltip, "(%d+)/(%d+)")
        if current and max then
            current = tonumber(current)
            max = tonumber(max)
            if max and max > 0 then
                result.claimed = current
                result.total = max
                result.available = max - current
                if debugMode then
                    self:Debug("Gilded Stash (widget): " .. current .. "/" .. max)
                end
                return result
            end
        end
        if debugMode then
            self:Debug("Gilded Stash tooltip found but couldn't parse: " .. tostring(tooltip))
        end
    else
        if debugMode then
            self:Debug("Gilded Stash: Widget not found (may need to be in Khaz Algar)")
        end
    end

    -- Fallback: Try C_DelvesUI API
    if C_DelvesUI then
        if C_DelvesUI.GetGildedStashProgress then
            local claimed, total = C_DelvesUI.GetGildedStashProgress()
            if claimed and total then
                result.claimed = claimed
                result.total = total
                result.available = total - claimed
                if debugMode then
                    self:Debug("Gilded Stash (API): " .. claimed .. "/" .. total)
                end
                return result
            end
        end
    end

    -- Fallback: Preserve last known value from saved data
    -- This handles the case when player is not in Khaz Algar
    local charKey = self:GetCharacterKey()
    if WoWStatTrackerDB and WoWStatTrackerDB.characters and WoWStatTrackerDB.characters[charKey] then
        local savedData = WoWStatTrackerDB.characters[charKey].gilded_stash
        if savedData and savedData.claimed then
            result.claimed = savedData.claimed
            result.total = savedData.total or 3
            result.available = result.total - result.claimed
            if debugMode then
                self:Debug("Gilded Stash (cached): " .. result.claimed .. "/" .. result.total)
            end
            return result
        end
    end

    if debugMode then
        self:Debug("Gilded Stash: Could not determine progress")
    end

    return result
end

-- Show gilded stash status via slash command
function WoWStatTracker:ShowGildedStatus()
    local status = self:GetGildedStashStatus()

    self:Print("Gilded Stash Status:")
    print("  Claimed: " .. status.claimed .. "/" .. status.total)
    if status.claimed >= status.total then
        print("  |cff00ff00All bonus crests claimed this week!|r")
    else
        print("  |cffffff00" .. status.available .. " bonus crests still available|r")
    end
end