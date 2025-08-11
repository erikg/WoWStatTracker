-- WoW Stat Tracker - UI and Export Functions
-- Provides user interface and data export functionality

local addonName, WoWStatTracker = ...

-- Show addon status
function WoWStatTracker:ShowStatus()
    if not WoWStatTrackerDB then
        self:Print("Database not initialized")
        return
    end
    
    local charCount = 0
    for _ in pairs(WoWStatTrackerDB.characters) do
        charCount = charCount + 1
    end
    
    self:Print("=== WoW Stat Tracker Status ===")
    print("  Version: " .. WoWStatTracker.version)
    print("  Characters tracked: " .. charCount)
    print("  Total updates: " .. (WoWStatTrackerDB.metadata.totalUpdates or 0))
    print("  Auto-update: " .. (WoWStatTrackerDB.settings.autoUpdate and "Enabled" or "Disabled"))
    print("  Debug mode: " .. (WoWStatTrackerDB.settings.debugMode and "Enabled" or "Disabled"))
    
    local lastExport = WoWStatTrackerDB.metadata.lastExport or 0
    if lastExport > 0 then
        print("  Last export: " .. date("%Y-%m-%d %H:%M:%S", lastExport))
    else
        print("  Last export: Never")
    end
end

-- Export data in format compatible with the Python application
function WoWStatTracker:ExportData()
    if not WoWStatTrackerDB then
        self:Print("No data to export")
        return
    end
    
    -- Convert our data format to match the Python application format
    local exportData = {}
    
    for charKey, charData in pairs(WoWStatTrackerDB.characters) do
        local exportChar = {
            name = charData.name or "Unknown",
            realm = charData.realm or "Unknown",
            guild = charData.guild or "",
            item_level = charData.item_level or 0,
            heroic_items = charData.heroic_items or 0,
            champion_items = charData.champion_items or 0,
            adventure_items = charData.adventure_items or 0,
            old_items = charData.old_items or 0,
            vault_visited = charData.vault_visited or false,
            delves = charData.delves or 0,
            gundarz = charData.gundarz or false,
            quests = charData.quests or false,
            timewalk = charData.timewalk or 0,
            
            -- Metadata
            lastUpdate = charData.lastUpdate or 0,
            source = "WoWStatTracker_Addon",
            dataVersion = charData.dataVersion or WoWStatTracker.version,
        }
        
        table.insert(exportData, exportChar)
    end
    
    -- Store formatted data for the Python app to read
    WoWStatTrackerDB.exportData = {
        characters = exportData,
        metadata = {
            exportTime = time(),
            exportVersion = WoWStatTracker.version,
            addonSource = true,
        }
    }
    
    self:Print("Data exported successfully! " .. #exportData .. " characters exported.")
    self:Print("Python application can now import this data using 'Update from WoW Addon'")
end

-- Create a simple minimap button
function WoWStatTracker:CreateMinimapButton()
    if self.minimapButton then
        return -- Already created
    end
    
    local button = CreateFrame("Button", "WoWStatTrackerMinimapButton", Minimap)
    button:SetSize(32, 32)
    button:SetFrameStrata("MEDIUM")
    button:SetFrameLevel(8)
    button:SetHighlightTexture("Interface\\Minimap\\UI-Minimap-ZoomButton-Highlight")
    
    -- Position on minimap
    button:SetPoint("TOPLEFT", Minimap, "TOPLEFT", 0, 0)
    
    -- Create button texture
    local texture = button:CreateTexture(nil, "BACKGROUND")
    texture:SetTexture("Interface\\Icons\\INV_Misc_Note_01")
    texture:SetSize(20, 20)
    texture:SetPoint("CENTER")
    
    -- Tooltip
    button:SetScript("OnEnter", function(self)
        GameTooltip:SetOwner(self, "ANCHOR_LEFT")
        GameTooltip:SetText("WoW Stat Tracker")
        GameTooltip:AddLine("Left-click: Update data", 1, 1, 1)
        GameTooltip:AddLine("Right-click: Show status", 1, 1, 1)
        GameTooltip:Show()
    end)
    
    button:SetScript("OnLeave", function(self)
        GameTooltip:Hide()
    end)
    
    -- Click handlers
    button:SetScript("OnClick", function(self, button)
        if button == "LeftButton" then
            WoWStatTracker:ForceUpdate()
        elseif button == "RightButton" then
            WoWStatTracker:ShowStatus()
        end
    end)
    
    -- Enable mouse clicks
    button:RegisterForClicks("LeftButtonUp", "RightButtonUp")
    
    self.minimapButton = button
    self:Debug("Minimap button created")
end

-- Simple configuration panel
function WoWStatTracker:ShowConfigPanel()
    if self.configFrame then
        if self.configFrame:IsShown() then
            self.configFrame:Hide()
        else
            self.configFrame:Show()
        end
        return
    end
    
    -- Create config frame
    local frame = CreateFrame("Frame", "WoWStatTrackerConfig", UIParent, "BasicFrameTemplateWithInset")
    frame:SetSize(400, 300)
    frame:SetPoint("CENTER")
    frame:SetMovable(true)
    frame:EnableMouse(true)
    frame:RegisterForDrag("LeftButton")
    frame:SetScript("OnDragStart", frame.StartMoving)
    frame:SetScript("OnDragStop", frame.StopMovingOrSizing)
    
    -- Title
    frame.title = frame:CreateFontString(nil, "OVERLAY")
    frame.title:SetFontObject("GameFontHighlight")
    frame.title:SetPoint("LEFT", frame.TitleBg, "LEFT", 5, 0)
    frame.title:SetText("WoW Stat Tracker Configuration")
    
    -- Auto-update checkbox
    local autoUpdateCheck = CreateFrame("CheckButton", nil, frame, "InterfaceOptionsCheckButtonTemplate")
    autoUpdateCheck:SetPoint("TOPLEFT", frame.InsetBg, "TOPLEFT", 10, -10)
    autoUpdateCheck.Text:SetText("Enable automatic updates")
    autoUpdateCheck:SetChecked(WoWStatTrackerDB.settings.autoUpdate)
    autoUpdateCheck:SetScript("OnClick", function(self)
        WoWStatTrackerDB.settings.autoUpdate = self:GetChecked()
        WoWStatTracker:Print("Auto-update " .. (WoWStatTrackerDB.settings.autoUpdate and "enabled" or "disabled"))
    end)
    
    -- Debug mode checkbox
    local debugCheck = CreateFrame("CheckButton", nil, frame, "InterfaceOptionsCheckButtonTemplate")
    debugCheck:SetPoint("TOPLEFT", autoUpdateCheck, "BOTTOMLEFT", 0, -5)
    debugCheck.Text:SetText("Enable debug mode")
    debugCheck:SetChecked(WoWStatTrackerDB.settings.debugMode)
    debugCheck:SetScript("OnClick", function(self)
        WoWStatTrackerDB.settings.debugMode = self:GetChecked()
        WoWStatTracker:Print("Debug mode " .. (WoWStatTrackerDB.settings.debugMode and "enabled" or "disabled"))
    end)
    
    -- Export on logout checkbox
    local logoutCheck = CreateFrame("CheckButton", nil, frame, "InterfaceOptionsCheckButtonTemplate")
    logoutCheck:SetPoint("TOPLEFT", debugCheck, "BOTTOMLEFT", 0, -5)
    logoutCheck.Text:SetText("Export data on logout")
    logoutCheck:SetChecked(WoWStatTrackerDB.settings.exportOnLogout)
    logoutCheck:SetScript("OnClick", function(self)
        WoWStatTrackerDB.settings.exportOnLogout = self:GetChecked()
    end)
    
    -- Manual export button
    local exportButton = CreateFrame("Button", nil, frame, "GameMenuButtonTemplate")
    exportButton:SetPoint("TOPLEFT", logoutCheck, "BOTTOMLEFT", 0, -20)
    exportButton:SetSize(150, 25)
    exportButton:SetText("Export Data Now")
    exportButton:SetScript("OnClick", function()
        WoWStatTracker:ExportData()
    end)
    
    -- Update button
    local updateButton = CreateFrame("Button", nil, frame, "GameMenuButtonTemplate")
    updateButton:SetPoint("LEFT", exportButton, "RIGHT", 10, 0)
    updateButton:SetSize(150, 25)
    updateButton:SetText("Update Data Now")
    updateButton:SetScript("OnClick", function()
        WoWStatTracker:ForceUpdate()
    end)
    
    -- Status display
    local statusText = frame:CreateFontString(nil, "OVERLAY", "GameFontHighlight")
    statusText:SetPoint("TOPLEFT", exportButton, "BOTTOMLEFT", 0, -20)
    statusText:SetPoint("RIGHT", frame.InsetBg, "RIGHT", -10, 0)
    statusText:SetJustifyH("LEFT")
    
    -- Update status text
    local function updateStatus()
        local charCount = 0
        for _ in pairs(WoWStatTrackerDB.characters) do
            charCount = charCount + 1
        end
        
        local status = string.format("Characters tracked: %d\nTotal updates: %d\nLast export: %s", 
            charCount,
            WoWStatTrackerDB.metadata.totalUpdates or 0,
            WoWStatTrackerDB.metadata.lastExport > 0 and date("%Y-%m-%d %H:%M:%S", WoWStatTrackerDB.metadata.lastExport) or "Never"
        )
        statusText:SetText(status)
    end
    
    updateStatus()
    
    -- Close button functionality
    frame:SetScript("OnHide", function()
        -- Save settings when closed
    end)
    
    self.configFrame = frame
    frame:Show()
end

-- Initialize UI components
function WoWStatTracker:InitializeUI()
    -- Create minimap button
    self:CreateMinimapButton()
    
    self:Debug("UI initialized")
end