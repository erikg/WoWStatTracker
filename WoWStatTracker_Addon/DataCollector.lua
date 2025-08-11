-- WoW Stat Tracker - Data Collection
-- Collects character statistics and progress data

local addonName, WoWStatTracker = ...

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
    
    local data = {
        -- Basic character info
        name = name,
        realm = realm,
        class = UnitClass("player"),
        level = UnitLevel("player"),
        guild = GetGuildInfo("player") or "",
        
        -- Item level
        item_level = self:GetAverageItemLevel(),
        
        -- Gear counts by quality
        heroic_items = self:CountItemsByQuality(4), -- Epic
        champion_items = self:CountItemsByQuality(3), -- Rare
        veteran_items = self:CountVeteranItems(), -- Items in veteran item level range
        adventure_items = self:CountItemsByQuality(2), -- Uncommon
        old_items = self:CountItemsByQuality(1), -- Common
        
        -- Weekly progress
        vault_visited = self:HasVisitedVault(),
        delves = self:GetDelvesCompleted(),
        gundarz = self:HasKilledGundarz(),
        quests = self:GetWeeklyQuestsCompleted(),
        timewalk = self:GetTimewalkingCompleted(),
        
        -- Timestamps
        lastLogin = time(),
        dataVersion = WoWStatTracker.version,
    }
    
    return data
end

-- Get average item level
function WoWStatTracker:GetAverageItemLevel()
    local totalIlvl = 0
    local itemCount = 0
    
    -- Equipment slots to check
    local slots = {
        1, 2, 3, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17
    }
    
    for _, slotId in ipairs(slots) do
        local itemLink = GetInventoryItemLink("player", slotId)
        if itemLink then
            local itemLevel = GetDetailedItemLevelInfo(itemLink)
            if itemLevel and itemLevel > 0 then
                totalIlvl = totalIlvl + itemLevel
                itemCount = itemCount + 1
            end
        end
    end
    
    return itemCount > 0 and math.floor(totalIlvl / itemCount) or 0
end

-- Count items by quality in equipped gear
function WoWStatTracker:CountItemsByQuality(quality)
    local count = 0
    
    -- Equipment slots
    local slots = {
        1, 2, 3, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17
    }
    
    for _, slotId in ipairs(slots) do
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

-- Count veteran items (items in a specific item level range)
function WoWStatTracker:CountVeteranItems()
    local count = 0
    
    -- Equipment slots
    local slots = {
        1, 2, 3, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17
    }
    
    -- Define veteran item level range (adjust these values based on current content)
    local VETERAN_MIN_ILVL = 580  -- Minimum item level for veteran items
    local VETERAN_MAX_ILVL = 619  -- Maximum item level for veteran items
    
    for _, slotId in ipairs(slots) do
        local itemLink = GetInventoryItemLink("player", slotId)
        if itemLink then
            local itemLevel = GetDetailedItemLevelInfo(itemLink)
            if itemLevel and itemLevel >= VETERAN_MIN_ILVL and itemLevel <= VETERAN_MAX_ILVL then
                count = count + 1
            end
        end
    end
    
    return count
end

-- Check if player has visited the Great Vault this week
function WoWStatTracker:HasVisitedVault()
    -- Try to check if the weekly chest/vault has been opened
    -- This is approximate as there's no direct API
    local hasWeeklyRewards = false
    
    -- Check for weekly quest completion or achievement progress
    -- This is a simplified check - in practice you might track this differently
    if C_WeeklyRewards and C_WeeklyRewards.HasAvailableRewards then
        hasWeeklyRewards = C_WeeklyRewards.HasAvailableRewards()
    end
    
    -- Return true if we detect vault interaction
    return hasWeeklyRewards or false
end

-- Get number of delves completed this week
function WoWStatTracker:GetDelvesCompleted()
    -- This would need to track delve-specific achievements or quest completion
    -- For now, return a placeholder that could be manually updated
    local delves = 0
    
    -- You could track specific delve achievements here
    -- or parse combat log for delve completions
    
    return delves
end

-- Check if Gundarg (or weekly world boss) has been killed
function WoWStatTracker:HasKilledGundarz()
    -- Check for weekly world boss kills
    -- This would typically check specific quest completion or achievements
    local killed = false
    
    -- Example: Check if weekly world boss quest is completed
    -- You'd need to find the specific quest ID for the current week's world boss
    
    return killed
end

-- Get weekly quests completed
function WoWStatTracker:GetWeeklyQuestsCompleted()
    -- Count weekly quests that have been completed
    local completed = 0
    
    -- This could check for specific weekly quest achievements
    -- or track quest completion through events
    
    return completed > 0
end

-- Get timewalking dungeons completed this week
function WoWStatTracker:GetTimewalkingCompleted()
    -- Check for timewalking-specific achievements or quest completion
    local completed = 0
    
    -- You could track timewalking dungeon achievements here
    
    return completed
end