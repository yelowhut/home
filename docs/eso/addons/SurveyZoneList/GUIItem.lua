SurveyZoneList.GUIItem = {}
SurveyZoneList.GUIItem.__index = SurveyZoneList.GUIItem

-- @var static integer uiIdx The current uiItem index which represents
-- the number of item already created
SurveyZoneList.GUIItem.uiIdx = 0

-- @const integer Width of one craft column in the breakdown (issue #10)
SurveyZoneList.GUIItem.CRAFT_CELL_WIDTH = 34

-- @const integer Height of one row
SurveyZoneList.GUIItem.ROW_HEIGHT = 30

--[[
-- Total width taken by the craft breakdown.
--
-- @return integer
--]]
function SurveyZoneList.GUIItem:craftStripWidth()
    return #SurveyZoneList.Zone.CRAFT_TYPES * SurveyZoneList.GUIItem.CRAFT_CELL_WIDTH
end

--[[
-- Instanciate a new GUIItem "object"
--
-- @return GUIItem
--]]
function SurveyZoneList.GUIItem:new()
    local guiItem = {
        ui        = nil, -- (table) The item's ui BACKDROP
        uiLabel   = nil, -- (table) The item's ui label
        craftCell = {}, -- (table) One entry per craft type, each with an icon and a label
        parentUI  = SurveyZoneList.GUI.ui, -- (table) The TopLevelWindow in GUI table
        used      = false, -- (bool) If the current item is used or not (cannot be destroyed)
        zoneName  = nil, -- (string) The zone name to display
        zoneInfo  = nil -- (table) Info about the zone, value in SurveyZoneList.Collect.orderedList
    }

    setmetatable(guiItem, self)
    self.uiIdx = self.uiIdx + 1

    guiItem:initUI()
    return guiItem
end

--[[
-- Create ui elements used by the item
--]]
function SurveyZoneList.GUIItem:initUI()
    local WindowManager = GetWindowManager()
    local uiName        = "SurveyZoneListUIItem"..self.uiIdx
    local uiLabelName   = uiName.."_Label"

    self.ui = WindowManager:CreateControl(uiName, self.parentUI, CT_BACKDROP)
    self.ui:SetDimensions(self.parentUI:GetWidth(), SurveyZoneList.GUIItem.ROW_HEIGHT)
    self.ui:SetCenterColor(0, 0, 0, .25)
    self.ui:SetEdgeColor(0, 0, 0, .25)
    self.ui:SetEdgeTexture(nil, 1, 1, 0, 0)

    self.uiLabel = WindowManager:CreateControl(uiLabelName, self.ui, CT_LABEL)
    self.uiLabel:SetAnchor(TOPLEFT, self.ui, TOPLEFT, 5, 3)
    self.uiLabel:SetFont("ZoFontGame")
    self.uiLabel:SetMaxLineCount(1)

    self:initCraftCells(uiName)
end

--[[
-- Create the craft breakdown cells (issue #10).
--
-- Cells are anchored on the right edge of the row, so they stay in place when
-- the user changes the window width.
--
-- @param string uiName The base name of the item's controls
--]]
function SurveyZoneList.GUIItem:initCraftCells(uiName)
    local WindowManager = GetWindowManager()
    local craftTypes    = SurveyZoneList.Zone.CRAFT_TYPES
    local cellWidth     = SurveyZoneList.GUIItem.CRAFT_CELL_WIDTH

    for craftIdx, craftType in ipairs(craftTypes) do
        local offsetFromRight = (#craftTypes - craftIdx) * cellWidth
        local cellName        = uiName.."_Craft_"..craftType

        local cell = WindowManager:CreateControl(cellName, self.ui, CT_CONTROL)
        cell:SetDimensions(cellWidth, SurveyZoneList.GUIItem.ROW_HEIGHT)
        cell:SetAnchor(TOPRIGHT, self.ui, TOPRIGHT, -(offsetFromRight + 5), 0)

        local icon = WindowManager:CreateControl(cellName.."_Icon", cell, CT_TEXTURE)
        icon:SetDimensions(18, 18)
        icon:SetAnchor(TOPLEFT, cell, TOPLEFT, 0, 6)
        icon:SetTexture(SurveyZoneList.Zone.CRAFT_ICONS[craftType])

        local label = WindowManager:CreateControl(cellName.."_Label", cell, CT_LABEL)
        label:SetAnchor(TOPLEFT, cell, TOPLEFT, 20, 6)
        label:SetFont("ZoFontGameSmall")
        label:SetMaxLineCount(1)

        self.craftCell[craftType] = {
            ui    = cell,
            icon  = icon,
            label = label,
        }
    end
end

--[[
-- To display or not the gui
--
-- @param bool isHidden To hide (if true) the item's ui or not (if false)
--]]
function SurveyZoneList.GUIItem:display(isHidden)
    if isHidden == true then
        self:hide()
    else
        self:show()
    end
end

--[[
-- To hide the item's ui
--]]
function SurveyZoneList.GUIItem:hide()
    self.ui:SetHidden(true)
end

--[[
-- To show the item's ui
--]]
function SurveyZoneList.GUIItem:show()
    self.ui:SetHidden(false)
end

--[[
-- Define the item's ui position from the index
--
-- @param integer index The index (position in the list) defined for the item
--]]
function SurveyZoneList.GUIItem:definePosition(index)
    local top = (index - 1 + SurveyZoneList.GUI:headerRowCount()) * SurveyZoneList.GUIItem.ROW_HEIGHT

    self.ui:ClearAnchors()
    self.ui:SetAnchor(TOPLEFT, self.parentUI, TOPLEFT, 0, top)
    self.ui:SetDimensions(self.parentUI:GetWidth(), SurveyZoneList.GUIItem.ROW_HEIGHT)
end

--[[
-- Update the text to display
--]]
function SurveyZoneList.GUIItem:updateText()
    self.uiLabel:SetText(SurveyZoneList.GUI:formatZoneText(self.zoneInfo))
    self:updateCraftCells()
end

--[[
-- Update the craft breakdown of the row (issue #10)
--]]
function SurveyZoneList.GUIItem:updateCraftCells()
    local displayCraft = SurveyZoneList.GUI:isDisplayCraft()
    local stripWidth   = 0

    if displayCraft == true then
        stripWidth = SurveyZoneList.GUIItem:craftStripWidth()
    end

    -- Keep the zone text from running under the craft columns.
    self.uiLabel:SetDimensions(
        math.max(self.ui:GetWidth() - stripWidth - 10, 10),
        SurveyZoneList.GUIItem.ROW_HEIGHT - 6
    )

    for _, craftType in ipairs(SurveyZoneList.Zone.CRAFT_TYPES) do
        local cell = self.craftCell[craftType]

        if cell ~= nil then
            if displayCraft == false or self.zoneInfo == nil then
                cell.ui:SetHidden(true)
            else
                local quantity = 0

                if self.zoneInfo.craft[craftType] ~= nil then
                    quantity = self.zoneInfo.craft[craftType].all
                end

                cell.ui:SetHidden(false)
                cell.label:SetText(tostring(quantity))

                -- A zone with none of that craft stays readable but quiet.
                if quantity > 0 then
                    cell.icon:SetAlpha(1)
                    cell.label:SetAlpha(1)
                else
                    cell.icon:SetAlpha(0.25)
                    cell.label:SetAlpha(0.25)
                end
            end
        end
    end
end
