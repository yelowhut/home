SurveyZoneList.ItemSort = {}

-- @var table All saved variables dedicated to the sort system.
SurveyZoneList.ItemSort.savedVars = nil

-- @var string The current zone name, lowercased
SurveyZoneList.ItemSort.currentZoneName = ""

-- @var integer|nil The current zone id, as an overland zone
SurveyZoneList.ItemSort.currentZoneId = nil

-- @const ORDER_TYPE_SURVEY_NB_UNIQUE The value for an order by number of unique survey point
SurveyZoneList.ItemSort.ORDER_TYPE_SURVEY_NB_UNIQUE = "surveyNbUnique"

-- @const ORDER_TYPE_SURVEY_NB_TOTAL The value for an order by the total number of survey in a zone
SurveyZoneList.ItemSort.ORDER_TYPE_SURVEY_NB_TOTAL = "surveyNbTotal"

-- @const ORDER_TYPE_TREASURE_NB_UNIQUE The value for an order by number of treasure map
SurveyZoneList.ItemSort.ORDER_TYPE_TREASURE_NB_UNIQUE = "treasureNbUnique"

-- @const ORDER_TYPE_ZONE_NAME The value for an order by zone name
SurveyZoneList.ItemSort.ORDER_TYPE_ZONE_NAME = "zoneName"

--[[
-- Initialise data used by the sort system
--]]
function SurveyZoneList.ItemSort:init()
    self.savedVars = SurveyZoneList.savedVariables.sort

    self:initSavedVarsValues()
end

--[[
-- Initialise with a default value all saved variables dedicated to the sort system
--]]
function SurveyZoneList.ItemSort:initSavedVarsValues()
    if self.savedVars.order == nil then
        self.savedVars.order = {
            self.ORDER_TYPE_SURVEY_NB_UNIQUE,
            self.ORDER_TYPE_SURVEY_NB_TOTAL,
            self.ORDER_TYPE_TREASURE_NB_UNIQUE,
            self.ORDER_TYPE_ZONE_NAME,
        }
    end

    -- An older version stored a nil in the middle of the order list, which
    -- silently truncated it. Rebuild anything that is not a full list.
    for pos = 1, 4 do
        if self.savedVars.order[pos] == nil then
            self.savedVars.order[pos] = self.ORDER_TYPE_ZONE_NAME
        end
    end

    if self.savedVars.keepCurrentZoneFirst == nil then
        self.savedVars.keepCurrentZoneFirst = true
    end
end

--[[
-- Obtain the current order to use
--
-- @return table
--]]
function SurveyZoneList.ItemSort:obtainOrder()
    return self.savedVars.order
end

--[[
-- Define a new order to use
--
-- @param integer pos The order priority index (1 to 4)
-- @param string value The order type to use
--]]
function SurveyZoneList.ItemSort:defineOrder(pos, value)
    self.savedVars.order[pos] = value
    SurveyZoneList.GUI:refreshAll()
end

--[[
-- Obtain info about if the current zone must always be the first item or not
--
-- @return bool
--]]
function SurveyZoneList.ItemSort:isKeepCurrentZoneFirst()
    return self.savedVars.keepCurrentZoneFirst
end

--[[
-- Define if the current zone must always be the first item or not
--
-- @param bool value
--]]
function SurveyZoneList.ItemSort:defineKeepCurrentZoneFirst(value)
    self.savedVars.keepCurrentZoneFirst = value
    SurveyZoneList.GUI:refreshAll()
end

--[[
-- Update the current zone name and id
--]]
function SurveyZoneList.ItemSort:updateCurrentZone()
    self.currentZoneId   = SurveyZoneList.Zone:currentZoneId()
    self.currentZoneName = ""

    if self.currentZoneId ~= nil then
        self.currentZoneName = SurveyZoneList.Zone:zoneIdToName(self.currentZoneId) or ""
    end

    if self.currentZoneName == "" then
        local fallbackName = GetZoneNameByIndex(GetCurrentMapZoneIndex())

        if fallbackName ~= nil then
            -- The current zone name is not escaped by espaceLuaStr because
            -- it's the string in which we search a zone name, it's not used
            -- as a pattern.
            self.currentZoneName = zo_strformat("<<1>>", fallbackName):lower()
        end
    end
end

--[[
-- Whether a zone is the one the player currently stands in.
--
-- Zones resolved through LibTreasure are compared by id, which is exact. Zones
-- resolved by parsing the item name keep the historical name matching.
--
-- @param table zoneInfo
--
-- @return bool
--]]
function SurveyZoneList.ItemSort:isCurrentZone(zoneInfo)
    if zoneInfo.zoneId ~= nil and self.currentZoneId ~= nil then
        return zoneInfo.zoneId == self.currentZoneId
    end

    if self.currentZoneName == "" or zoneInfo.nameEscaped == "" then
        return false
    end

    return string.find(self.currentZoneName, zoneInfo.nameEscaped) ~= nil
end

--[[
-- Escape string to use it in pattern
-- Find at https://stackoverflow.com/a/6707799
--
-- @param String str The string to escape
--
-- @return String
--]]
function SurveyZoneList.ItemSort:espaceLuaStr(str)
    local matches = {
        ["^"] = "%^";
        ["$"] = "%$";
        ["("] = "%(";
        [")"] = "%)";
        ["%"] = "%%";
        ["."] = "%.";
        ["["] = "%[";
        ["]"] = "%]";
        ["*"] = "%*";
        ["+"] = "%+";
        ["-"] = "%-";
        ["?"] = "%?";
    }

    return (str:gsub(".", matches))
end

--[[
-- Execute the table's sort on SurveyZoneList.Collect.orderedList
--]]
function SurveyZoneList.ItemSort:exec()
    table.sort(SurveyZoneList.Collect.orderedList, self.sortZoneList)
end

--[[
-- Obtain the value of a zone for an order type.
--
-- @param table zoneInfo
-- @param string orderType
--
-- @return number|string
--]]
function SurveyZoneList.ItemSort.orderValue(zoneInfo, orderType)
    if orderType == SurveyZoneList.ItemSort.ORDER_TYPE_SURVEY_NB_UNIQUE then
        return zoneInfo.survey.all.nbUnique
    elseif orderType == SurveyZoneList.ItemSort.ORDER_TYPE_SURVEY_NB_TOTAL then
        return zoneInfo.survey.all.nbTotal
    elseif orderType == SurveyZoneList.ItemSort.ORDER_TYPE_TREASURE_NB_UNIQUE then
        return zoneInfo.treasure.all.nbUnique
    end

    return zoneInfo.name
end

--[[
-- Callback function used by table.sort.
-- It's called each time an item in the sorted table is compared to another.
--
-- @param table left The left item to compare
-- @param table right The right item to compare
--
-- @return bool true if left item as the priority on right item, else return false
--]]
function SurveyZoneList.ItemSort.sortZoneList(left, right)
    local itemSort = SurveyZoneList.ItemSort

    -- Current zone always first item
    if itemSort:isKeepCurrentZoneFirst() == true then
        local leftIsCurrent  = itemSort:isCurrentZone(left)
        local rightIsCurrent = itemSort:isCurrentZone(right)

        if leftIsCurrent ~= rightIsCurrent then
            return leftIsCurrent
        end
    end

    for pos = 1, #itemSort.savedVars.order do
        local orderType  = itemSort.savedVars.order[pos]
        local leftValue  = itemSort.orderValue(left, orderType)
        local rightValue = itemSort.orderValue(right, orderType)

        if leftValue ~= rightValue then
            if orderType == itemSort.ORDER_TYPE_ZONE_NAME then
                return leftValue < rightValue
            end

            return leftValue > rightValue
        end
    end

    -- Two zones can never share a name, so this is a stable last resort.
    return left.key < right.key
end
