-- WoW Stat Tracker - Event Handling
-- Handles game events to trigger data updates

local addonName, WoWStatTracker = ...

-- Set up event handling
function WoWStatTracker:SetupEvents()
    if self.eventFrame then
        return -- Already set up
    end
    
    self.eventFrame = CreateFrame("Frame")
    
    -- Register events we care about
    local events = {
        "PLAYER_EQUIPMENT_CHANGED",  -- Gear changes
        "PLAYER_LEVEL_UP",           -- Level changes
        "GUILD_ROSTER_UPDATE",       -- Guild changes
        "QUEST_TURNED_IN",           -- Quest completion
        "QUEST_ACCEPTED",            -- Quest accepted
        "ACHIEVEMENT_EARNED",        -- Achievement progress
        "ENCOUNTER_END",             -- Dungeon/raid completion
        "CHALLENGE_MODE_COMPLETED",  -- Mythic+ completion
        "SCENARIO_COMPLETED",        -- Scenario/delve completion
        "LFG_COMPLETION_REWARD",     -- Dungeon finder completion (heroic, TW)
        "PLAYER_ENTERING_WORLD",     -- Zone changes, login
        "ZONE_CHANGED_NEW_AREA",     -- Zone changes
    }
    
    for _, event in ipairs(events) do
        self.eventFrame:RegisterEvent(event)
    end
    
    -- Set up event handler
    self.eventFrame:SetScript("OnEvent", function(frame, event, ...)
        self:HandleEvent(event, ...)
    end)
    
    self:Debug("Event handling initialized")
end

-- Handle game events
function WoWStatTracker:HandleEvent(event, ...)
    if not WoWStatTrackerDB or not WoWStatTrackerDB.settings.autoUpdate then
        return
    end
    
    local shouldUpdate = false
    local delay = 1 -- Default delay before update
    
    if event == "PLAYER_EQUIPMENT_CHANGED" then
        -- Gear changed, update item level and quality counts
        shouldUpdate = true
        delay = 2 -- Wait a bit for item info to stabilize
        self:Debug("Equipment changed")
        
    elseif event == "PLAYER_LEVEL_UP" then
        -- Level up, immediate update
        shouldUpdate = true
        delay = 1
        self:Debug("Player leveled up")
        
    elseif event == "GUILD_ROSTER_UPDATE" then
        -- Guild info might have changed
        shouldUpdate = true
        delay = 3
        self:Debug("Guild roster updated")
        
    elseif event == "QUEST_TURNED_IN" then
        local questID = ...
        if questID and self:IsWeeklyQuest(questID) then
            shouldUpdate = true
            delay = 1
            self:Debug("Weekly quest completed: " .. questID)
        end
        
    elseif event == "ACHIEVEMENT_EARNED" then
        local achievementID = ...
        if achievementID and self:IsRelevantAchievement(achievementID) then
            shouldUpdate = true
            delay = 2
            self:Debug("Relevant achievement earned: " .. achievementID)
        end
        
    elseif event == "ENCOUNTER_END" then
        local encounterID, encounterName, difficultyID, groupSize, success = ...
        if success then
            shouldUpdate = true
            delay = 5 -- Wait for loot and achievements to process
            self:Debug("Encounter completed: " .. (encounterName or "Unknown"))
        end
        
    elseif event == "CHALLENGE_MODE_COMPLETED" then
        -- Mythic+ completed
        self:OnMythicPlusCompleted()
        shouldUpdate = true
        delay = 3

    elseif event == "SCENARIO_COMPLETED" then
        -- Scenario completed - check if it was a delve
        self:OnScenarioCompleted()
        shouldUpdate = true
        delay = 3

    elseif event == "LFG_COMPLETION_REWARD" then
        -- Dungeon finder completion (Heroic, Timewalking, etc.)
        self:OnDungeonCompleted("lfg")
        shouldUpdate = true
        delay = 3

    elseif event == "QUEST_ACCEPTED" then
        local questId = ...
        self:OnQuestAccepted(questId)

    elseif event == "PLAYER_ENTERING_WORLD" then
        local isLogin, isReload = ...
        if isLogin then
            -- Full login, schedule update
            shouldUpdate = true
            delay = 10 -- Wait for everything to load
            self:Debug("Player entered world (login)")
        end
        
    elseif event == "ZONE_CHANGED_NEW_AREA" then
        -- Zone change, might have completed activities
        shouldUpdate = true
        delay = 5
        self:Debug("Zone changed")
    end
    
    -- Schedule update if needed
    if shouldUpdate then
        -- Cancel any existing timer
        if self.updateTimer then
            self.updateTimer:Cancel()
        end
        
        -- Schedule new update
        self.updateTimer = C_Timer.NewTimer(delay, function()
            self:UpdateCharacterData()
        end)
    end
end

-- Check if a quest is a weekly quest we care about
function WoWStatTracker:IsWeeklyQuest(questID)
    -- List of weekly quest IDs that we want to track
    -- These would need to be updated based on current content
    local weeklyQuests = {
        -- Example weekly quest IDs - these would need to be updated
        -- for current expansion content
        70866, -- Example: Weekly dungeon quest
        72068, -- Example: Weekly world quest
        -- Add more weekly quest IDs as needed
    }
    
    for _, id in ipairs(weeklyQuests) do
        if id == questID then
            return true
        end
    end
    
    return false
end

-- Check if an achievement is relevant to our tracking
function WoWStatTracker:IsRelevantAchievement(achievementID)
    -- List of achievements that indicate progress we care about
    local relevantAchievements = {
        -- Example achievement IDs - these would need to be updated
        -- for current expansion content
        -- Delve achievements, weekly boss kills, etc.
        16649, -- Example: Delve achievement
        -- Add more relevant achievement IDs as needed
    }
    
    for _, id in ipairs(relevantAchievements) do
        if id == achievementID then
            return true
        end
    end
    
    return false
end

-- Track delve completion
function WoWStatTracker:OnScenarioCompleted()
    -- Check if we're in a delve
    local _, instanceType = GetInstanceInfo()
    local scenarioInfo = C_ScenarioInfo and C_ScenarioInfo.GetScenarioInfo()

    if not scenarioInfo then
        self:Debug("No scenario info available")
        return
    end

    -- Delves are scenario instances - check if this looks like a delve
    -- Delves have tiers 1-11 and are in the "Delves" category
    local delveTier = self:GetCurrentDelveTier()

    if delveTier and delveTier > 0 then
        self:RecordDelveCompletion(delveTier)
    else
        self:Debug("Scenario completed but not a delve (tier=" .. tostring(delveTier) .. ")")
    end
end

-- Get current delve tier (if in a delve)
function WoWStatTracker:GetCurrentDelveTier()
    -- Try to get the delve tier from the scenario step info or keystone level
    -- In TWW, delves use C_DelvesUI for tier information
    if C_DelvesUI and C_DelvesUI.GetCurrentDelvesSeasonNumber then
        -- We're in delve content, try to get the tier
        -- The tier might be available from the active keystone or scenario info
    end

    -- Alternative: Check active keystone for tier
    if C_ChallengeMode and C_ChallengeMode.GetActiveKeystoneInfo then
        local level = C_ChallengeMode.GetActiveKeystoneInfo()
        if level and level > 0 then
            return level
        end
    end

    -- Try to get from scenario step info
    local scenarioInfo = C_ScenarioInfo and C_ScenarioInfo.GetScenarioInfo()
    if scenarioInfo then
        self:Debug("Scenario: " .. (scenarioInfo.name or "Unknown"))
        -- Delve tier might be encoded in the scenario name or other fields
        -- Look for "Tier X" or "Level X" in the name
        if scenarioInfo.name then
            local tier = scenarioInfo.name:match("Tier%s*(%d+)")
                      or scenarioInfo.name:match("Level%s*(%d+)")
            if tier then
                return tonumber(tier)
            end
        end
    end

    -- Check if we have a bountiful delve active (tier 11)
    -- This is a fallback - ideally we'd have a direct API

    return nil
end

-- Record a delve completion
function WoWStatTracker:RecordDelveCompletion(tier)
    local charKey = self:GetCharacterKey()

    -- Initialize delve tracking if needed
    if not WoWStatTrackerDB.delves then
        WoWStatTrackerDB.delves = {}
    end
    if not WoWStatTrackerDB.delves[charKey] then
        WoWStatTrackerDB.delves[charKey] = {}
    end
    if not WoWStatTrackerDB.delves[charKey].completions then
        WoWStatTrackerDB.delves[charKey].completions = {}
    end

    -- Get current week identifier (resets Tuesday)
    local weekId = self:GetCurrentWeekId()

    -- Initialize this week if needed
    if not WoWStatTrackerDB.delves[charKey].completions[weekId] then
        WoWStatTrackerDB.delves[charKey].completions[weekId] = {}
    end

    -- Record the completion with timestamp
    table.insert(WoWStatTrackerDB.delves[charKey].completions[weekId], {
        tier = tier,
        timestamp = time(),
    })

    self:Debug("Recorded delve completion: Tier " .. tier)
    self:Print("Delve Tier " .. tier .. " completed!")
end

-- Get week identifier (for weekly reset tracking)
function WoWStatTracker:GetCurrentWeekId()
    -- Weekly reset is Tuesday 15:00 UTC (7:00 AM PST)
    -- Calculate a week ID based on this
    local resetDay = 3  -- Tuesday (1=Sunday)
    local resetHour = 15  -- 15:00 UTC

    local now = time()
    local utcDate = date("!*t", now)

    -- Calculate days since last Tuesday
    local daysSinceReset = (utcDate.wday - resetDay) % 7
    if utcDate.wday == resetDay and utcDate.hour < resetHour then
        daysSinceReset = 7
    end

    -- Get timestamp of last reset
    local lastReset = now - (daysSinceReset * 86400)
    -- Normalize to midnight
    local resetDate = date("!*t", lastReset)
    resetDate.hour = resetHour
    resetDate.min = 0
    resetDate.sec = 0

    return date("!%Y%m%d", time(resetDate))
end

-- Get delve completions for current week
function WoWStatTracker:GetWeeklyDelveCompletions()
    local charKey = self:GetCharacterKey()
    local weekId = self:GetCurrentWeekId()

    if not WoWStatTrackerDB.delves
       or not WoWStatTrackerDB.delves[charKey]
       or not WoWStatTrackerDB.delves[charKey].completions
       or not WoWStatTrackerDB.delves[charKey].completions[weekId] then
        return {}
    end

    return WoWStatTrackerDB.delves[charKey].completions[weekId]
end

-- Count delves at or above a certain tier this week
function WoWStatTracker:CountDelvesAtTier(minTier)
    local completions = self:GetWeeklyDelveCompletions()
    local count = 0

    for _, completion in ipairs(completions) do
        if completion.tier >= minTier then
            count = count + 1
        end
    end

    return count
end

-- ============================================
-- DUNGEON TRACKING
-- ============================================

-- Dungeon types
local DUNGEON_TYPE = {
    MYTHIC_PLUS = "mythic_plus",
    HEROIC = "heroic",
    TIMEWALKING = "timewalking",
    NORMAL = "normal",
    MYTHIC_ZERO = "mythic",
}

-- Track M+ completion
function WoWStatTracker:OnMythicPlusCompleted()
    local level, _, _, _ = C_ChallengeMode.GetCompletionInfo()
    local mapID = C_ChallengeMode.GetActiveChallengeMapID()
    local dungeonName = mapID and C_ChallengeMode.GetMapUIInfo(mapID) or "Unknown"

    self:RecordDungeonCompletion(DUNGEON_TYPE.MYTHIC_PLUS, level or 0, dungeonName)
end

-- Track LFG dungeon completion (Heroic, Timewalking, Normal)
function WoWStatTracker:OnDungeonCompleted(source)
    local _, instanceType, difficultyID, difficultyName = GetInstanceInfo()

    -- Determine dungeon type from difficulty
    local dungeonType = DUNGEON_TYPE.NORMAL
    local level = 0

    -- Difficulty IDs:
    -- 1 = Normal, 2 = Heroic, 23 = Mythic, 24 = Timewalking
    -- 8 = Mythic+ (but we handle that separately)
    if difficultyID == 2 then
        dungeonType = DUNGEON_TYPE.HEROIC
        level = 0
    elseif difficultyID == 24 then
        dungeonType = DUNGEON_TYPE.TIMEWALKING
        level = 0
    elseif difficultyID == 23 then
        dungeonType = DUNGEON_TYPE.MYTHIC_ZERO
        level = 0
    end

    local dungeonName = GetInstanceInfo() or "Unknown"

    self:RecordDungeonCompletion(dungeonType, level, dungeonName)
end

-- Record a dungeon completion
function WoWStatTracker:RecordDungeonCompletion(dungeonType, level, dungeonName)
    local charKey = self:GetCharacterKey()
    local weekId = self:GetCurrentWeekId()

    -- Initialize dungeon tracking if needed
    if not WoWStatTrackerDB.dungeons then
        WoWStatTrackerDB.dungeons = {}
    end
    if not WoWStatTrackerDB.dungeons[charKey] then
        WoWStatTrackerDB.dungeons[charKey] = {}
    end
    if not WoWStatTrackerDB.dungeons[charKey][weekId] then
        WoWStatTrackerDB.dungeons[charKey][weekId] = {}
    end

    -- Record the completion
    table.insert(WoWStatTrackerDB.dungeons[charKey][weekId], {
        type = dungeonType,
        level = level,
        name = dungeonName,
        timestamp = time(),
    })

    self:Debug("Recorded dungeon: " .. dungeonType .. " level " .. level .. " (" .. dungeonName .. ")")
    self:Print("Dungeon completed: " .. dungeonName .. " (" .. dungeonType .. ")")
end

-- Get weekly dungeon completions
function WoWStatTracker:GetWeeklyDungeonCompletions()
    local charKey = self:GetCharacterKey()
    local weekId = self:GetCurrentWeekId()

    if not WoWStatTrackerDB.dungeons
       or not WoWStatTrackerDB.dungeons[charKey]
       or not WoWStatTrackerDB.dungeons[charKey][weekId] then
        return {}
    end

    return WoWStatTrackerDB.dungeons[charKey][weekId]
end

-- Count dungeons by type
function WoWStatTracker:CountDungeonsByType(dungeonType)
    local completions = self:GetWeeklyDungeonCompletions()
    local count = 0

    for _, completion in ipairs(completions) do
        if completion.type == dungeonType then
            count = count + 1
        end
    end

    return count
end

-- ============================================
-- TIMEWALKING QUEST TRACKING
-- ============================================

-- Timewalking weekly quest IDs
local TIMEWALKING_QUEST_IDS = {
    72727,  -- A Burning Path Through Time (BC)
    72726,  -- A Frozen Path Through Time (WotLK)
    72810,  -- A Shattered Path Through Time (Cataclysm)
    72725,  -- A Shrouded Path Through Time (MoP)
    72724,  -- A Savage Path Through Time (WoD)
    72719,  -- A Fel Path Through Time (Legion)
    86731,  -- An Original Path Through Time (Classic)
}

-- Track quest acceptance
function WoWStatTracker:OnQuestAccepted(questId)
    for _, twQuestId in ipairs(TIMEWALKING_QUEST_IDS) do
        if questId == twQuestId then
            local charKey = self:GetCharacterKey()
            if not WoWStatTrackerDB.timewalking then
                WoWStatTrackerDB.timewalking = {}
            end
            if not WoWStatTrackerDB.timewalking[charKey] then
                WoWStatTrackerDB.timewalking[charKey] = {}
            end
            WoWStatTrackerDB.timewalking[charKey].questAccepted = questId
            WoWStatTrackerDB.timewalking[charKey].acceptedAt = time()
            self:Debug("Timewalking quest accepted: " .. questId)
            return
        end
    end
end

-- Check timewalking quest status
function WoWStatTracker:GetTimewalkingQuestStatus()
    local result = {
        questId = nil,
        accepted = false,
        completed = false,
        progress = 0,
    }

    for _, questId in ipairs(TIMEWALKING_QUEST_IDS) do
        if C_QuestLog.IsOnQuest(questId) then
            result.questId = questId
            result.accepted = true
            local objectives = C_QuestLog.GetQuestObjectives(questId)
            if objectives and objectives[1] then
                result.progress = objectives[1].numFulfilled or 0
            end
            return result
        end
        if C_QuestLog.IsQuestFlaggedCompleted(questId) then
            result.questId = questId
            result.completed = true
            result.progress = 5
            return result
        end
    end

    return result
end

-- Manual update command
function WoWStatTracker:ForceUpdate()
    self:UpdateCharacterData()
    self:Print("Character data updated manually")
end

-- Slash command handler
SLASH_WOWSTATTRACKER1 = "/wst"
SLASH_WOWSTATTRACKER2 = "/wowstat"

function SlashCmdList.WOWSTATTRACKER(msg, editBox)
    local args = {}
    for word in msg:gmatch("%S+") do
        table.insert(args, word:lower())
    end
    local command = args[1] or ""

    if command == "update" then
        WoWStatTracker:ForceUpdate()
    elseif command == "debug" then
        if WoWStatTrackerDB then
            WoWStatTrackerDB.settings.debugMode = not WoWStatTrackerDB.settings.debugMode
            WoWStatTracker:Print("Debug mode " .. (WoWStatTrackerDB.settings.debugMode and "enabled" or "disabled"))
        end
    elseif command == "status" then
        WoWStatTracker:ShowStatus()
    elseif command == "delves" then
        WoWStatTracker:ShowDelveStatus()
    elseif command == "adddelve" then
        -- Manual delve entry: /wst adddelve <tier>
        local tier = tonumber(args[2])
        if tier and tier >= 1 and tier <= 11 then
            WoWStatTracker:RecordDelveCompletion(tier)
        else
            WoWStatTracker:Print("Usage: /wst adddelve <tier> (1-11)")
        end
    elseif command == "cleardelves" then
        -- Clear delve data for current week
        WoWStatTracker:ClearWeeklyDelves()
    elseif command == "export" then
        WoWStatTracker:ExportData()
    elseif command == "gilded" then
        WoWStatTracker:ShowGildedStatus()
    elseif command == "explore" then
        WoWStatTracker:ExploreDelveAPI()
    elseif command == "clearlog" then
        WoWStatTracker:ClearDebugLog()
    elseif command == "log" then
        -- Show recent log entries in chat
        if WoWStatTrackerDB and WoWStatTrackerDB.debugLog then
            local count = #WoWStatTrackerDB.debugLog
            WoWStatTracker:Print("Debug log has " .. count .. " entries")
            -- Show last 10 entries
            local start = math.max(1, count - 9)
            for i = start, count do
                local entry = WoWStatTrackerDB.debugLog[i]
                print("  [" .. entry.timeStr .. "] " .. entry.msg)
            end
            print("  Use 'wst_log.py' to view full log")
        else
            WoWStatTracker:Print("No debug log entries")
        end
    else
        WoWStatTracker:Print("Available commands:")
        print("  /wst update - Force data update")
        print("  /wst debug - Toggle debug mode (chat output)")
        print("  /wst status - Show addon status")
        print("  /wst delves - Show delve progress")
        print("  /wst gilded - Show gilded stash (tier 11 bonus crests)")
        print("  /wst explore - Explore C_DelvesUI API")
        print("  /wst log - Show recent debug log entries")
        print("  /wst clearlog - Clear debug log")
        print("  /wst adddelve <tier> - Manually add a delve completion")
        print("  /wst cleardelves - Clear this week's delve data")
        print("  /wst export - Export data now")
    end
end

-- Clear weekly delve data
function WoWStatTracker:ClearWeeklyDelves()
    local charKey = self:GetCharacterKey()
    local weekId = self:GetCurrentWeekId()

    if WoWStatTrackerDB.delves
       and WoWStatTrackerDB.delves[charKey]
       and WoWStatTrackerDB.delves[charKey].completions then
        WoWStatTrackerDB.delves[charKey].completions[weekId] = {}
        self:Print("Cleared delve data for this week")
    end
end

-- Show delve status
function WoWStatTracker:ShowDelveStatus()
    local delveVault = self:GetDelvesFromVault()
    local dungeonVault = self:GetDungeonsFromVault()
    local delveEvents = self:GetWeeklyDelveCompletions()
    local dungeonEvents = self:GetWeeklyDungeonCompletions()
    local twStatus = self:GetTimewalkingQuestStatus()

    self:Print("Weekly Progress:")

    -- Delves
    print("|cff00ff00Delves:|r " .. delveVault.count .. " (from vault)")
    if delveVault.tiers[1] then print("  Slot 1: Tier " .. delveVault.tiers[1]) end
    if delveVault.tiers[4] then print("  Slot 2: Tier " .. delveVault.tiers[4]) end
    if delveVault.tiers[8] then print("  Slot 3: Tier " .. delveVault.tiers[8]) end

    if #delveEvents > 0 then
        print("  Tracked completions:")
        for i, c in ipairs(delveEvents) do
            print("    " .. i .. ". Tier " .. c.tier .. " (" .. date("%m/%d %H:%M", c.timestamp) .. ")")
        end
    end

    -- Dungeons
    print("|cff00ff00Dungeons:|r " .. dungeonVault.count .. " (from vault)")
    if dungeonVault.levels[1] then print("  Slot 1: Level " .. dungeonVault.levels[1]) end
    if dungeonVault.levels[4] then print("  Slot 2: Level " .. dungeonVault.levels[4]) end
    if dungeonVault.levels[8] then print("  Slot 3: Level " .. dungeonVault.levels[8]) end

    if #dungeonEvents > 0 then
        print("  Tracked completions:")
        for i, c in ipairs(dungeonEvents) do
            local info = c.type
            if c.level and c.level > 0 then info = info .. " +" .. c.level end
            print("    " .. i .. ". " .. (c.name or "?") .. " (" .. info .. ") " .. date("%m/%d %H:%M", c.timestamp))
        end
    end

    -- Timewalking quest
    print("|cff00ff00Timewalking Quest:|r")
    if twStatus.completed then
        print("  Completed (5/5)")
    elseif twStatus.accepted then
        print("  In progress: " .. twStatus.progress .. "/5")
    else
        print("  Not accepted")
    end

    -- Timewalking count from event tracking
    local twCount = self:CountDungeonsByType("timewalking")
    if twCount > 0 then
        print("  Tracked TW dungeons: " .. twCount)
    end
end