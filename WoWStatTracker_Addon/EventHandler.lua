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
        "ACHIEVEMENT_EARNED",        -- Achievement progress
        "ENCOUNTER_END",             -- Dungeon/raid completion
        "CHALLENGE_MODE_COMPLETED",   -- Mythic+ completion
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
        shouldUpdate = true
        delay = 3
        self:Debug("Challenge mode completed")
        
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

-- Manual update command
function WoWStatTracker:ForceUpdate()
    self:UpdateCharacterData()
    self:Print("Character data updated manually")
end

-- Slash command handler
SLASH_WOWSTATTRACKER1 = "/wst"
SLASH_WOWSTATTRACKER2 = "/wowstat"

function SlashCmdList.WOWSTATTRACKER(msg, editBox)
    local command = string.lower(msg or "")
    
    if command == "update" then
        WoWStatTracker:ForceUpdate()
    elseif command == "debug" then
        if WoWStatTrackerDB then
            WoWStatTrackerDB.settings.debugMode = not WoWStatTrackerDB.settings.debugMode
            WoWStatTracker:Print("Debug mode " .. (WoWStatTrackerDB.settings.debugMode and "enabled" or "disabled"))
        end
    elseif command == "status" then
        WoWStatTracker:ShowStatus()
    elseif command == "export" then
        WoWStatTracker:ExportData()
    else
        WoWStatTracker:Print("Available commands:")
        print("  /wst update - Force data update")
        print("  /wst debug - Toggle debug mode")
        print("  /wst status - Show addon status")
        print("  /wst export - Export data now")
    end
end