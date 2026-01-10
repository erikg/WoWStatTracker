-- WoW Stat Tracker Addon
-- Core functionality and initialization

-- Create addon namespace
local addonName, WoWStatTracker = ...

-- Initialize addon object
WoWStatTracker = WoWStatTracker or {}
WoWStatTracker.version = "1.3.0"
WoWStatTracker.lastUpdate = 0

-- Default database structure
local defaultDB = {
    characters = {},
    settings = {
        autoUpdate = true,
        debugMode = false,
        exportOnLogout = true,
        updateInterval = 300, -- 5 minutes
    },
    metadata = {
        version = "1.3.0",
        lastExport = 0,
        totalUpdates = 0,
    }
}

-- Initialize the addon
function WoWStatTracker:Initialize()
    -- Initialize saved variables
    if not WoWStatTrackerDB then
        WoWStatTrackerDB = defaultDB
        self:Debug("Initialized new database")
    else
        -- Merge with defaults for new fields
        self:MergeDefaults(WoWStatTrackerDB, defaultDB)
        self:Debug("Loaded existing database with " .. #(WoWStatTrackerDB.characters or {}) .. " characters")
    end

    -- Always update metadata version to current addon version
    WoWStatTrackerDB.metadata.version = self.version
    
    -- Set up event handling
    self:SetupEvents()
    
    -- Initial data collection
    self:ScheduleUpdate(5) -- Update after 5 seconds
    
    self:Print("WoW Stat Tracker addon loaded successfully!")
end

-- Merge default values for missing keys
function WoWStatTracker:MergeDefaults(target, defaults)
    for key, value in pairs(defaults) do
        if target[key] == nil then
            target[key] = value
        elseif type(value) == "table" and type(target[key]) == "table" then
            self:MergeDefaults(target[key], value)
        end
    end
end

-- Schedule an update after a delay
function WoWStatTracker:ScheduleUpdate(delay)
    C_Timer.After(delay or 1, function()
        self:UpdateCharacterData()
    end)
end

-- Print message to chat
function WoWStatTracker:Print(msg)
    print("|cff00ff00[WoW Stat Tracker]|r " .. msg)
end

-- Debug message
function WoWStatTracker:Debug(msg)
    if WoWStatTrackerDB and WoWStatTrackerDB.settings.debugMode then
        print("|cff888888[WST Debug]|r " .. msg)
    end
end

-- Get current character key
function WoWStatTracker:GetCharacterKey()
    local name = UnitName("player")
    local realm = GetRealmName()
    return name .. "-" .. realm
end

-- Event frame
local eventFrame = CreateFrame("Frame")
eventFrame:RegisterEvent("ADDON_LOADED")
eventFrame:RegisterEvent("PLAYER_LOGIN")
eventFrame:RegisterEvent("PLAYER_LOGOUT")

eventFrame:SetScript("OnEvent", function(self, event, ...)
    if event == "ADDON_LOADED" then
        local loadedAddon = ...
        if loadedAddon == addonName then
            WoWStatTracker:Initialize()
        end
    elseif event == "PLAYER_LOGIN" then
        -- Player fully logged in, safe to collect data
        WoWStatTracker:ScheduleUpdate(10)
    elseif event == "PLAYER_LOGOUT" then
        -- Don't update on logout - game APIs may not work correctly during logout
        -- and could overwrite good data with incorrect values.
        -- Data should already be up-to-date from regular updates and /wst update.
        WoWStatTracker:Debug("Logout - skipping update (APIs unreliable during logout)")
    end
end)