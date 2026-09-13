SurveyZoneList.GUI = {}

--[[
-- @var table The ui TolLevelWindow
--]]
SurveyZoneList.GUI.ui = nil

--[[
-- @var table The ui backdrop
--]]
SurveyZoneList.GUI.backUI = nil

--[[
-- @var table The first item of the list which display list title
--]]
SurveyZoneList.GUI.title = nil

--[[
-- @var table The second item of the list which display info about the current survey
--]]
SurveyZoneList.GUI.currentNode = nil

--[[
-- @var table Label which display the number of node has been looted on the spot
--]]
SurveyZoneList.GUI.nodeCounter = nil

--[[
-- @var tabke Label which display info about the current spot
--]]
SurveyZoneList.GUI.spotInfo = nil

--[[
-- @var table The row warning about the Plentiful Harvest champion star (issue #13)
--]]
SurveyZoneList.GUI.championWarning = nil

--[[
-- @var table The label inside the champion warning row
--]]
SurveyZoneList.GUI.championWarningLabel = nil

--[[
-- @var bool Whether the champion warning row is currently displayed
--]]
SurveyZoneList.GUI.championWarningShown = false

--[[
-- @var table The fragment used to link the ui to a scene
--]]
SurveyZoneList.GUI.fragment = nil

--[[
-- @var table A list of all GUIItems created. We cannot remove an ui item from
-- memory, so we keep it all created items here to reuse it when the list is refreshed.
--]]
SurveyZoneList.GUI.itemList = {}

--[[
-- @var table All saved variables dedicated to the gui.
--]]
SurveyZoneList.GUI.savedVars = nil

--[[
-- @const table The counter of a zone each placeholder of the display format
-- reads. Placeholder 1 is the zone name, it has no counter.
--]]
SurveyZoneList.GUI.FORMAT_COUNTERS = {
    [2]  = {itemType = "survey",   source = "bag"},
    [3]  = {itemType = "survey",   source = "bag"},
    [4]  = {itemType = "treasure", source = "bag"},
    [5]  = {itemType = "survey",   source = "bank"},
    [6]  = {itemType = "survey",   source = "bank"},
    [7]  = {itemType = "treasure", source = "bank"},
    [8]  = {itemType = "survey",   source = "all"},
    [9]  = {itemType = "survey",   source = "all"},
    [10] = {itemType = "treasure", source = "all"},
}

--[[
-- @var table The counter list derived from the current format, cached.
--]]
SurveyZoneList.GUI.formatCounters = nil

--[[
-- @var string The format formatCounters was derived from.
--]]
SurveyZoneList.GUI.formatCountersFor = nil

--[[
-- Initialise the GUI
--]]
function SurveyZoneList.GUI:init()
    self.savedVars = SurveyZoneList.savedVariables.gui

    self:initSavedVarsValues()
    self:build()
    self:defineFragment()
end

--[[
-- Initialise with a default value all saved variables dedicated to the gui
--]]
function SurveyZoneList.GUI:initSavedVarsValues()
    if self.savedVars.position == nil then
        self.savedVars.position = {}
    end
    if self.savedVars.position.top == nil then
        self.savedVars.position.top = 0
    end
    if self.savedVars.position.left == nil then
        self.savedVars.position.left = 0
    end

    if self.savedVars.hidden == nil then
        self.savedVars.hidden = false
    end

    if self.savedVars.locked == nil then
        self.savedVars.locked = false
    end

    if self.savedVars.displayWithWMap == nil then
        self.savedVars.displayWithWMap = false
    end

    if self.savedVars.displayItemText == nil then
        self.savedVars.displayItemText = "<<1>> : <<2>> - <<3>> / <<4>>"
    end

    if self.savedVars.displaySurvey == nil then
        self.savedVars.displaySurvey = true
    end

    if self.savedVars.displayTreasure == nil then
        self.savedVars.displayTreasure = true
    end

    if self.savedVars.displayCraft == nil then
        self.savedVars.displayCraft = true
    end

    if self.savedVars.textWidth == nil then
        self.savedVars.textWidth = 300
    end
end

--[[
-- The full width of the window, text area plus craft breakdown.
--
-- @return integer
--]]
function SurveyZoneList.GUI:totalWidth()
    local width = self.savedVars.textWidth

    if self.savedVars.displayCraft == true then
        width = width + SurveyZoneList.GUIItem:craftStripWidth()
    end

    return width
end

--[[
-- How many fixed rows sit above the zone list.
--
-- Title and current node are always there. The champion warning only takes a
-- row while it is displayed.
--
-- @return integer
--]]
function SurveyZoneList.GUI:headerRowCount()
    if self.championWarningShown == true then
        return 3
    end

    return 2
end

--[[
-- Build the GUI
--]]
function SurveyZoneList.GUI:build()
    local WindowManager = GetWindowManager()
    local rowHeight     = SurveyZoneList.GUIItem.ROW_HEIGHT

    self.ui = WindowManager:CreateTopLevelWindow("SurveyZoneListUI")
    self.ui:SetClampedToScreen(true)
    self.ui:ClearAnchors()
    self.ui:SetHidden(self.savedVars.hidden)
    self.ui:SetDimensions(self:totalWidth(), rowHeight)
    self.ui:SetHandler("OnMoveStop", function(...) SurveyZoneList.Events.onGuiMoveStop() end)
    self:restorePosition()
    self:defineLocked(self.savedVars.locked)

    self.backUI = WindowManager:CreateControl("SurveyZoneListUIBack", self.ui, CT_BACKDROP)
    self.backUI:SetAnchor(TOPLEFT, self.ui, TOPLEFT, 0, 0)
    self.backUI:SetDimensions(self.ui:GetWidth(), self.ui:GetHeight())
    self.backUI:SetHidden(self.savedVars.hidden)
    self.backUI:SetCenterColor(0, 0, 0, .25)
    self.backUI:SetEdgeColor(0, 0, 0, .25)
    self.backUI:SetEdgeTexture(nil, 1, 1, 0, 0)

    self.title = WindowManager:CreateControl("SurveyZoneListUITitle", self.ui, CT_BACKDROP)
    self.title:SetAnchor(TOPLEFT, self.ui, TOPLEFT, 0, 0)
    self.title:SetDimensions(self.ui:GetWidth(), rowHeight)
    self.title:SetHidden(self.savedVars.hidden)
    self.title:SetCenterColor(0, 0, 0, .25)
    self.title:SetEdgeColor(0, 0, 0, .25)
    self.title:SetEdgeTexture(nil, 1, 1, 0, 0)

    local titleLabel = WindowManager:CreateControl("titleLabel", self.title, CT_LABEL)
    titleLabel:SetAnchor(TOPLEFT, self.title, TOPLEFT, 5, 3)
    titleLabel:SetText(GetString(SI_SURVEYZONELIST_LIST_TITLE))
    titleLabel:SetFont("ZoFontGame")

    self.currentNode = WindowManager:CreateControl("SurveyZoneListUICurrentNode", self.ui, CT_BACKDROP)
    self.currentNode:SetAnchor(TOPLEFT, self.ui, TOPLEFT, 0, rowHeight)
    self.currentNode:SetDimensions(self.ui:GetWidth(), rowHeight)
    self.currentNode:SetHidden(self.savedVars.hidden)
    self.currentNode:SetCenterColor(0, 0, 0, .25)
    self.currentNode:SetEdgeColor(0, 0, 0, .25)
    self.currentNode:SetEdgeTexture(nil, 1, 1, 0, 0)

    local nodeIcon = WindowManager:CreateControl("SurveyZoneListUICurrentNodeIcon", self.currentNode, CT_TEXTURE)
    nodeIcon:SetDimensions(25, 25)
    nodeIcon:SetAnchor(TOPLEFT, self.currentNode, TOPLEFT, 5, 3)
    nodeIcon:SetTexture("/esoui/art/icons/poi/poi_crafting_complete.dds")

    self.nodeCounter = WindowManager:CreateControl("SurveyZoneListUICurrentNodeCounterLabel", self.currentNode, CT_LABEL)
    self.nodeCounter:SetAnchor(TOPLEFT, nodeIcon, TOPLEFT, 30, 3)
    self.nodeCounter:SetText("0/6")
    self.nodeCounter:SetFont("ZoFontGame")

    local spotIcon = WindowManager:CreateControl("SurveyZoneListUICurrentSpotIcon", self.currentNode, CT_TEXTURE)
    spotIcon:SetDimensions(30, 30)
    spotIcon:SetAnchor(TOPLEFT, self.currentNode, TOPLEFT, 110, 3)
    spotIcon:SetTexture("/esoui/art/treeicons/achievements_indexicon_summary_down.dds")

    self.spotInfo = WindowManager:CreateControl("SurveyZoneListUICurrentNodeSpotInfo", self.currentNode, CT_LABEL)
    self.spotInfo:SetAnchor(TOPLEFT, nodeIcon, TOPLEFT, 140, 3)
    self.spotInfo:SetText("No info")
    self.spotInfo:SetFont("ZoFontGame")

    self:buildChampionWarning()
end

--[[
-- Build the row warning that Plentiful Harvest is not slotted (issue #13)
--]]
function SurveyZoneList.GUI:buildChampionWarning()
    local WindowManager = GetWindowManager()
    local rowHeight     = SurveyZoneList.GUIItem.ROW_HEIGHT

    self.championWarning = WindowManager:CreateControl("SurveyZoneListUIChampionWarning", self.ui, CT_BACKDROP)
    self.championWarning:SetAnchor(TOPLEFT, self.ui, TOPLEFT, 0, rowHeight * 2)
    self.championWarning:SetDimensions(self.ui:GetWidth(), rowHeight)
    self.championWarning:SetHidden(true)
    self.championWarning:SetCenterColor(0, 0, 0, .25)
    self.championWarning:SetEdgeColor(0, 0, 0, .25)
    self.championWarning:SetEdgeTexture(nil, 1, 1, 0, 0)

    local warningIcon = WindowManager:CreateControl("SurveyZoneListUIChampionWarningIcon", self.championWarning, CT_TEXTURE)
    warningIcon:SetDimensions(25, 25)
    warningIcon:SetAnchor(TOPLEFT, self.championWarning, TOPLEFT, 5, 3)
    warningIcon:SetTexture("/esoui/art/miscellaneous/new_icon.dds")

    self.championWarningLabel = WindowManager:CreateControl("SurveyZoneListUIChampionWarningLabel", self.championWarning, CT_LABEL)
    self.championWarningLabel:SetAnchor(TOPLEFT, self.championWarning, TOPLEFT, 35, 6)
    self.championWarningLabel:SetFont("ZoFontGameSmall")
    self.championWarningLabel:SetMaxLineCount(1)
    self.championWarningLabel:SetColor(1, 0.7, 0.2, 1)
    self.championWarningLabel:SetText(GetString(SI_SURVEYZONELIST_CP_WARNING))
end

--[[
-- Refresh the champion warning visibility (issue #13)
--]]
function SurveyZoneList.GUI:updateChampionWarning()
    if self.championWarning == nil then
        return
    end

    local shouldWarn = SurveyZoneList.ChampionPoints:shouldWarn()

    if shouldWarn == self.championWarningShown then
        return
    end

    self.championWarningShown = shouldWarn
    self.championWarning:SetHidden(not shouldWarn or self.savedVars.hidden)

    -- The rows below have to move up or down by one row height.
    self:refreshAll()
end

--[[
-- Apply the current width to every control of the window
--]]
function SurveyZoneList.GUI:applyWidth()
    local width = self:totalWidth()

    self.ui:SetDimensions(width, self.ui:GetHeight())
    self.backUI:SetDimensions(width, self.ui:GetHeight())
    self.title:SetDimensions(width, SurveyZoneList.GUIItem.ROW_HEIGHT)
    self.currentNode:SetDimensions(width, SurveyZoneList.GUIItem.ROW_HEIGHT)
    self.championWarning:SetDimensions(width, SurveyZoneList.GUIItem.ROW_HEIGHT)
end

--[[
-- Restore the GUI's position from saved variables
--]]
function SurveyZoneList.GUI:restorePosition()
    self.ui:ClearAnchors()

    local left = self.savedVars.position.left
    local top  = self.savedVars.position.top

    self.ui:SetAnchor(TOPLEFT, GuiRoot, TOPLEFT, left, top)
end

--[[
-- Return info about if the GUI position is locked or not
--
-- @return bool
--]]
function SurveyZoneList.GUI:isLocked()
    return self.savedVars.locked
end

--[[
-- Define if the GUI is locked or not.
--
-- @param bool value
--]]
function SurveyZoneList.GUI:defineLocked(value)
    self.savedVars.locked = value

    self.ui:SetMouseEnabled(not value)
    self.ui:SetMovable(not value)
end

--[[
-- Return info about if the GUI should be displayed when the world map is open or not
--
-- @return bool
--]]
function SurveyZoneList.GUI:isDisplayWithWMap()
    return self.savedVars.displayWithWMap
end

--[[
-- Define if the GUI should be displayed when the world map is open or not
--
-- @param bool value
--]]
function SurveyZoneList.GUI:defineDisplayWithWMap(value)
    self.savedVars.displayWithWMap = value

    if value == true then
        SCENE_MANAGER:GetScene("worldMap"):AddFragment(self.fragment)
    else
        SCENE_MANAGER:GetScene("worldMap"):RemoveFragment(self.fragment)
    end
end

--[[
-- Return the text format used for each item
--
-- @return string
--]]
function SurveyZoneList.GUI:obtainDisplayItemText()
    return self.savedVars.displayItemText
end

--[[
-- Define a new text format for items
--
-- @param string value
--]]
function SurveyZoneList.GUI:defineDisplayItemText(value)
    self.savedVars.displayItemText = value
    self:refreshAll()
end

--[[
-- Return info about if the zone is displayed when it only holds surveys
--
-- @return bool
--]]
function SurveyZoneList.GUI:isDisplaySurvey()
    return self.savedVars.displaySurvey
end

--[[
-- Define if the zone is displayed when it only holds surveys
--
-- @param bool value
--]]
function SurveyZoneList.GUI:defineDisplaySurvey(value)
    self.savedVars.displaySurvey = value
    self:refreshAll()
end

--[[
-- Return info about if the zone is displayed when it only holds treasure maps
--
-- @return bool
--]]
function SurveyZoneList.GUI:isDisplayTreasure()
    return self.savedVars.displayTreasure
end

--[[
-- Define if the zone is displayed when it only holds treasure maps
--
-- @param bool value
--]]
function SurveyZoneList.GUI:defineDisplayTreasure(value)
    self.savedVars.displayTreasure = value
    self:refreshAll()
end

--[[
-- Return info about if the craft breakdown is displayed (issue #10)
--
-- @return bool
--]]
function SurveyZoneList.GUI:isDisplayCraft()
    return self.savedVars.displayCraft
end

--[[
-- Define if the craft breakdown is displayed (issue #10)
--
-- @param bool value
--]]
function SurveyZoneList.GUI:defineDisplayCraft(value)
    self.savedVars.displayCraft = value
    self:applyWidth()
    self:refreshAll()
end

--[[
-- Return the width reserved for the zone text
--
-- @return integer
--]]
function SurveyZoneList.GUI:obtainTextWidth()
    return self.savedVars.textWidth
end

--[[
-- Define the width reserved for the zone text
--
-- @param integer value
--]]
function SurveyZoneList.GUI:defineTextWidth(value)
    self.savedVars.textWidth = value
    self:applyWidth()
    self:refreshAll()
end

--[[
-- Save the GUI's position to savedVariables
--]]
function SurveyZoneList.GUI:savePosition()
    self.savedVars.position.left = self.ui:GetLeft()
    self.savedVars.position.top  = self.ui:GetTop()
end

--[[
-- Define GUI as a fragment linked to scenes.
-- With that, the GUI is hidden when we open a menu (like inventory or map)
--]]
function SurveyZoneList.GUI:defineFragment()
    self.fragment = ZO_SimpleSceneFragment:New(self.ui)

    SCENE_MANAGER:GetScene("hud"):AddFragment(self.fragment)
    SCENE_MANAGER:GetScene("hudui"):AddFragment(self.fragment)
end

--[[
-- Show or hide the GUI
-- If the GUI is currently hidden, it will be shown.
-- If the GUI is currently shown, it will be hidden.
--]]
function SurveyZoneList.GUI:toggle()
    self.savedVars.hidden = not self.savedVars.hidden
    self.ui:SetHidden(self.savedVars.hidden)
    self.backUI:SetHidden(self.savedVars.hidden)
    self.title:SetHidden(self.savedVars.hidden)
    self.currentNode:SetHidden(self.savedVars.hidden)
    self.championWarning:SetHidden(self.savedVars.hidden or not self.championWarningShown)

    if self.savedVars.hidden == true then
        self:hideAllItems()
    else
        self:showAllItems()
    end
end

--[[
-- Build the text of a zone row from the user defined format.
--
-- The substitution is done here instead of with zo_strformat because the
-- format holds up to ten placeholders, and because zo_strformat applies
-- grammatical rules we do not want on plain numbers.
--
-- @param table zoneInfo A value of SurveyZoneList.Collect.orderedList
--
-- @return string
--]]
function SurveyZoneList.GUI:formatZoneText(zoneInfo)
    local function ucfirst(str)
        return (str:gsub("^%l", string.upper))
    end

    local displayName = zoneInfo.displayName
    if displayName == nil or displayName == "" then
        displayName = ucfirst(zoneInfo.name)
    end

    local token = {
        [1]  = displayName,
        [2]  = zoneInfo.survey.bag.nbUnique,
        [3]  = zoneInfo.survey.bag.nbTotal,
        [4]  = zoneInfo.treasure.bag.nbUnique,
        [5]  = zoneInfo.survey.bank.nbUnique,
        [6]  = zoneInfo.survey.bank.nbTotal,
        [7]  = zoneInfo.treasure.bank.nbUnique,
        [8]  = zoneInfo.survey.all.nbUnique,
        [9]  = zoneInfo.survey.all.nbTotal,
        [10] = zoneInfo.treasure.all.nbUnique,
    }

    local text = self:obtainDisplayItemText():gsub("<<(%d+)>>", function(idx)
        local value = token[tonumber(idx)]

        if value == nil then
            return nil
        end

        return tostring(value)
    end)

    return text
end

--[[
-- The counters the current display format reads.
--
-- Derived from the format string and cached until that string changes.
--
-- @return table A list of {itemType, source}
--]]
function SurveyZoneList.GUI:obtainFormatCounters()
    local format = self:obtainDisplayItemText()

    if self.formatCounters ~= nil and self.formatCountersFor == format then
        return self.formatCounters
    end

    local counterList = {}
    local alreadySeen = {}

    for idx in format:gmatch("<<(%d+)>>") do
        local counter = SurveyZoneList.GUI.FORMAT_COUNTERS[tonumber(idx)]

        if counter ~= nil and alreadySeen[idx] == nil then
            alreadySeen[idx] = true
            table.insert(counterList, counter)
        end
    end

    -- A format holding no counter at all, the zone name alone for example,
    -- says nothing about where the maps are. Fall back on everything known.
    if #counterList == 0 then
        counterList = {
            {itemType = "survey",   source = "all"},
            {itemType = "treasure", source = "all"},
        }
    end

    self.formatCounters    = counterList
    self.formatCountersFor = format

    return counterList
end

--[[
-- Whether a zone should appear in the list.
--
-- A zone earns a row only when the row has something to say about it, so the
-- filter reads the very counters the format prints. With the default format,
-- which only reads the backpack, a zone whose maps all sit in the bank would
-- render as "Zone : 0 - 0 / 0" and is left out instead. Adding a bank or a
-- combined placeholder to the format brings that zone back.
--
-- @param table zoneInfo
--
-- @return bool
--]]
function SurveyZoneList.GUI:isZoneDisplayed(zoneInfo)
    for _, counter in ipairs(self:obtainFormatCounters()) do
        local typeDisplayed = self.savedVars.displaySurvey

        if counter.itemType == "treasure" then
            typeDisplayed = self.savedVars.displayTreasure
        end

        if typeDisplayed == true and zoneInfo[counter.itemType][counter.source].nbTotal > 0 then
            return true
        end
    end

    return false
end

--[[
-- Refresh all items displayed
--]]
function SurveyZoneList.GUI:refreshAll()
    self:resetAllItems()

    local idx = 1

    SurveyZoneList.ItemSort:exec()

    for _, zoneInfo in ipairs(SurveyZoneList.Collect.orderedList) do
        if self:isZoneDisplayed(zoneInfo) == true then
            if self.itemList[idx] == nil then
                self.itemList[idx] = SurveyZoneList.GUIItem:new()
            end

            local guiItem = self.itemList[idx]
            guiItem.used     = true
            guiItem.zoneName = zoneInfo.name
            guiItem.zoneInfo = zoneInfo
            guiItem:definePosition(idx)
            guiItem:updateText()
            guiItem:display(self.savedVars.hidden)

            idx = idx + 1
        end
    end

    local rowCount = (idx - 1) + self:headerRowCount()

    self.ui:SetDimensions(self:totalWidth(), rowCount * SurveyZoneList.GUIItem.ROW_HEIGHT)
    self.backUI:SetDimensions(self.ui:GetWidth(), self.ui:GetHeight())
end

--[[
-- Reset each item values an hide it
--]]
function SurveyZoneList.GUI:resetAllItems()
    for _, guiItem in pairs(self.itemList) do
        if guiItem ~= nil then
            guiItem.used     = false
            guiItem.zoneName = nil
            guiItem.zoneInfo = nil
            guiItem:hide()
        end
    end
end

--[[
-- Hide all items
--]]
function SurveyZoneList.GUI:hideAllItems()
    for _, guiItem in pairs(self.itemList) do
        if guiItem ~= nil then
            if guiItem.used == true then
                guiItem:hide()
            end
        end
    end
end

--[[
-- Show all used items
--]]
function SurveyZoneList.GUI:showAllItems()
    for _, guiItem in pairs(self.itemList) do
        if guiItem ~= nil then
            if guiItem.used == true then
                guiItem:show()
            end
        end
    end
end

--[[
-- Update the node counter value displayed
--]]
function SurveyZoneList.GUI:updateCounter()
    self.nodeCounter:SetText(
        zo_strformat(
            "<<1>> / <<2>>",
            SurveyZoneList.Recolt.counter,
            SurveyZoneList.Recolt.maxNode
        )
    )
end

--[[
-- Update the spot info displayed
--]]
function SurveyZoneList.GUI:updateSpotInfo()
    local str = GetString(SI_SURVEYZONELIST_GUI_REMAINING)

    if SurveyZoneList.Alerts.zoneQuantity == 0 then
        str = GetString(SI_SURVEYZONELIST_GUI_GO_NEXT_ZONE)
    elseif SurveyZoneList.Alerts.spotQuantity == 0 then
        str = GetString(SI_SURVEYZONELIST_GUI_GO_NEXT_SPOT)
    end

    self.spotInfo:SetText(zo_strformat(str, SurveyZoneList.Alerts.spotQuantity))
end
