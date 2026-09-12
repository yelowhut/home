--[[
-- Zone resolution.
--
-- Turn a survey / treasure map item into a stable zone key.
--
-- The preferred source is LibTreasure, which knows the real map of every
-- survey and treasure map item id. When the library is missing, or does not
-- know the item (a brand new chapter, for example), we fall back to parsing
-- the item name like the addon always did.
--
-- See issue #14 : the name parser creates duplicated zones because survey
-- names are not consistent across zones and languages.
--]]
SurveyZoneList.Zone = {}

--[[
-- @const string Prefix used for a key resolved through LibTreasure
--]]
SurveyZoneList.Zone.KEY_PREFIX_ID = "z:"

--[[
-- @const string Prefix used for a key resolved through the name parser
--]]
SurveyZoneList.Zone.KEY_PREFIX_NAME = "n:"

--[[
-- @const table All craft types a survey can be about.
-- Order matters, it's the display order of the craft breakdown (issue #10).
--]]
SurveyZoneList.Zone.CRAFT_TYPES = {
    "blacksmith",
    "clothier",
    "woodworker",
    "enchanter",
    "alchemist",
    "jewelry",
}

--[[
-- @const table Icon displayed for each craft type.
--]]
SurveyZoneList.Zone.CRAFT_ICONS = {
    blacksmith = "/esoui/art/icons/master_writ_blacksmithing.dds",
    clothier   = "/esoui/art/icons/master_writ_clothier.dds",
    woodworker = "/esoui/art/icons/master_writ_woodworking.dds",
    enchanter  = "/esoui/art/icons/master_writ_enchanting.dds",
    alchemist  = "/esoui/art/icons/master_writ_alchemy.dds",
    jewelry    = "/esoui/art/icons/master_writ_jewelry.dds",
}

--[[
-- @var table Cache of mapId => zoneId, to avoid redoing the parent walk.
--]]
SurveyZoneList.Zone.mapIdCache = {}

--[[
-- @var table Cache of zoneId => display name.
--]]
SurveyZoneList.Zone.zoneNameCache = {}

--[[
-- @var bool Whether LibTreasure is available. Resolved once at init.
--]]
SurveyZoneList.Zone.hasLibTreasure = false

--[[
-- Initialise the zone resolver.
--]]
function SurveyZoneList.Zone:init()
    self.hasLibTreasure = (type(LibTreasure_GetItemIdData) == "function")
    self.mapIdCache     = {}
    self.zoneNameCache  = {}
end

--[[
-- Walk up the zone hierarchy until we reach the overland zone.
--
-- LibTreasure stores one entry per map, including city and delve sub maps,
-- and its item index keeps the *last* map seen for an item id. So the
-- "Alchemist Survey: Stonefalls" item resolves to the Ebonheart city map and
-- not to Stonefalls. Walking up to the root parent puts it back where the
-- player expects to see it.
--
-- @param integer zoneId The zone id to start from
--
-- @return integer The root parent zone id
--]]
function SurveyZoneList.Zone:walkToRootZone(zoneId)
    if type(zoneId) ~= "number" or zoneId <= 0 then
        return zoneId
    end

    -- A bounded loop, never trust the game data to terminate on its own.
    for _ = 1, 10 do
        local parentZoneId = GetParentZoneId(zoneId)

        if type(parentZoneId) ~= "number" or parentZoneId <= 0 or parentZoneId == zoneId then
            break
        end

        zoneId = parentZoneId
    end

    return zoneId
end

--[[
-- Convert a LibTreasure mapId into an overland zone id.
--
-- @param integer mapId
--
-- @return integer|nil
--]]
function SurveyZoneList.Zone:mapIdToZoneId(mapId)
    if type(mapId) ~= "number" or mapId <= 0 then
        return nil
    end

    if self.mapIdCache[mapId] ~= nil then
        -- false is the cached "we tried and it failed" marker
        if self.mapIdCache[mapId] == false then
            return nil
        end

        return self.mapIdCache[mapId]
    end

    local zoneIndex = select(4, GetMapInfoById(mapId))

    if type(zoneIndex) ~= "number" or zoneIndex <= 0 then
        self.mapIdCache[mapId] = false
        return nil
    end

    local zoneId = GetZoneId(zoneIndex)

    if type(zoneId) ~= "number" or zoneId <= 0 then
        self.mapIdCache[mapId] = false
        return nil
    end

    zoneId = self:walkToRootZone(zoneId)
    self.mapIdCache[mapId] = zoneId

    return zoneId
end

--[[
-- Obtain the display name of a zone id.
--
-- @param integer zoneId
--
-- @return string|nil
--]]
function SurveyZoneList.Zone:zoneIdToName(zoneId)
    if type(zoneId) ~= "number" or zoneId <= 0 then
        return nil
    end

    if self.zoneNameCache[zoneId] ~= nil then
        if self.zoneNameCache[zoneId] == false then
            return nil
        end

        return self.zoneNameCache[zoneId]
    end

    local zoneName = nil

    if type(GetZoneNameById) == "function" then
        zoneName = GetZoneNameById(zoneId)
    end

    if (zoneName == nil or zoneName == "") and type(GetZoneIndex) == "function" then
        zoneName = GetZoneNameByIndex(GetZoneIndex(zoneId))
    end

    if zoneName == nil or zoneName == "" then
        self.zoneNameCache[zoneId] = false
        return nil
    end

    zoneName = zo_strformat("<<1>>", zoneName):lower()
    self.zoneNameCache[zoneId] = zoneName

    return zoneName
end

--[[
-- Obtain the zone id the player currently stands in, as an overland zone.
--
-- GetCurrentMapZoneIndex follows the *opened map*, so it lies as soon as the
-- player browses the world map. The player world position does not.
--
-- @return integer|nil
--]]
function SurveyZoneList.Zone:currentZoneId()
    local zoneId = GetUnitWorldPosition("player")

    if type(zoneId) ~= "number" or zoneId <= 0 then
        zoneId = GetZoneId(GetCurrentMapZoneIndex())
    end

    if type(zoneId) ~= "number" or zoneId <= 0 then
        return nil
    end

    return self:walkToRootZone(zoneId)
end

--[[
-- Read the craft type out of a LibTreasure texture name.
--
-- Texture names look like "stonefalls_survey_blacksmith". Jewelry is spelled
-- two different ways in the library data, so it gets normalised here.
--
-- @param string texture
--
-- @return string|nil One of CRAFT_TYPES
--]]
function SurveyZoneList.Zone:craftFromTexture(texture)
    if type(texture) ~= "string" then
        return nil
    end

    local craft = texture:match("_survey_(%a+)$")

    if craft == nil then
        return nil
    end

    if craft == "jewelrycrafting" then
        craft = "jewelry"
    end

    if SurveyZoneList.Zone.CRAFT_ICONS[craft] == nil then
        return nil
    end

    return craft
end

--[[
-- Read the craft type out of a localised item name.
--
-- Used only when LibTreasure does not know the item. Survey names are built
-- as "<craft> Survey: <zone>" in every supported language, so the craft name
-- sits before the colon.
--
-- @param string itemName Already lowercased
--
-- @return string|nil One of CRAFT_TYPES
--]]
function SurveyZoneList.Zone:craftFromName(itemName)
    if type(itemName) ~= "string" then
        return nil
    end

    for craft, patternList in pairs(SurveyZoneList.lang.craftFindName) do
        for _, pattern in ipairs(patternList) do
            if itemName:find(pattern) ~= nil then
                return craft
            end
        end
    end

    return nil
end

--[[
-- Parse a survey / treasure map item name to extract the zone name.
--
-- This is the historical detection, kept as a fallback for items LibTreasure
-- does not know yet.
--
-- @param string itemName Already lowercased
--
-- @return string|nil
--]]
function SurveyZoneList.Zone:parseZoneName(itemName)
    local itemZoneName = nil

    for _, matchStr in ipairs(SurveyZoneList.lang.collectFindName) do
        if itemZoneName == nil then
            itemZoneName = itemName:match(matchStr)
        end
    end

    if itemZoneName == nil then
        return nil
    end

    -- Strip the roman numeral suffix so "Craglorn I" and "Craglorn II" end up
    -- in the same zone.
    if itemZoneName:find("i$") ~= nil or itemZoneName:find("v$") ~= nil or itemZoneName:find("x$") ~= nil then
        local patternList = {
            "^(.*) i+$",  -- "i" or "ii" or "iii" ...
            "^(.*) iv$",  -- only "iv"
            "^(.*) vi*$", -- "v" or "vi" or "vii" ...
            "^(.*) xi*$", -- "x" or "xi" or "xii" ...
        }

        for _, pattern in ipairs(patternList) do
            local matchItemZoneName = itemZoneName:match(pattern)

            if matchItemZoneName ~= nil then
                itemZoneName = matchItemZoneName
                break
            end
        end
    end

    -- Trailing whitespace, including the non breaking space used by the DE and
    -- RU item names, which used to create a duplicated zone entry.
    itemZoneName = itemZoneName:gsub("^%s+", ""):gsub("%s+$", "")

    if itemZoneName == "" then
        return nil
    end

    return itemZoneName
end

--[[
-- Resolve the item held in a bag slot.
--
-- @param integer bagId
-- @param integer slotIdx
--
-- @return table|nil A table with key, zoneId, name, craft and isSurvey, or nil
--                   when the slot does not hold a survey or a treasure map.
--]]
function SurveyZoneList.Zone:resolveSlot(bagId, slotIdx)
    local itemLink = GetItemLink(bagId, slotIdx)

    if itemLink == nil or itemLink == "" then
        return nil
    end

    return self:resolveItemLink(itemLink)
end

--[[
-- Resolve an item link to its zone.
--
-- @param string itemLink
--
-- @return table|nil
--]]
function SurveyZoneList.Zone:resolveItemLink(itemLink)
    if itemLink == nil or itemLink == "" then
        return nil
    end

    local itemType, subType = GetItemLinkItemType(itemLink)

    if itemType ~= ITEMTYPE_TROPHY then
        return nil
    end

    if subType ~= SPECIALIZED_ITEMTYPE_TROPHY_SURVEY_REPORT and subType ~= SPECIALIZED_ITEMTYPE_TROPHY_TREASURE_MAP then
        return nil
    end

    local isSurvey = (subType == SPECIALIZED_ITEMTYPE_TROPHY_SURVEY_REPORT)
    local resolved = nil

    if SurveyZoneList.Zone:isLibTreasureEnabled() then
        resolved = self:resolveWithLibTreasure(itemLink, isSurvey)
    end

    if resolved == nil then
        resolved = self:resolveWithName(itemLink, isSurvey)
    end

    return resolved
end

--[[
-- Whether the LibTreasure resolution is available and enabled by the user.
--
-- @return bool
--]]
function SurveyZoneList.Zone:isLibTreasureEnabled()
    if self.hasLibTreasure == false then
        return false
    end

    return SurveyZoneList.savedVariables.zone.useLibTreasure ~= false
end

--[[
-- Resolve an item through LibTreasure.
--
-- @param string itemLink
-- @param bool isSurvey
--
-- @return table|nil
--]]
function SurveyZoneList.Zone:resolveWithLibTreasure(itemLink, isSurvey)
    local itemId = GetItemLinkItemId(itemLink)

    if type(itemId) ~= "number" or itemId <= 0 then
        return nil
    end

    local itemData = LibTreasure_GetItemIdData(itemId)

    if itemData == nil then
        return nil
    end

    local zoneId = self:mapIdToZoneId(itemData.mapId)

    if zoneId == nil then
        return nil
    end

    local zoneName = self:zoneIdToName(zoneId)

    if zoneName == nil then
        return nil
    end

    local craft = nil
    if isSurvey == true then
        craft = self:craftFromTexture(itemData.texture)
    end

    return {
        key      = self.KEY_PREFIX_ID..zoneId,
        zoneId   = zoneId,
        name     = zoneName,
        craft    = craft,
        isSurvey = isSurvey,
    }
end

--[[
-- Resolve an item by parsing its name.
--
-- @param string itemLink
-- @param bool isSurvey
--
-- @return table|nil
--]]
function SurveyZoneList.Zone:resolveWithName(itemLink, isSurvey)
    local itemName = zo_strformat("<<1>>", GetItemLinkName(itemLink)):lower()

    if itemName == "" then
        return nil
    end

    local zoneName = self:parseZoneName(itemName)

    if zoneName == nil then
        return nil
    end

    local craft = nil
    if isSurvey == true then
        craft = self:craftFromName(itemName)
    end

    return {
        key      = self.KEY_PREFIX_NAME..zoneName,
        zoneId   = nil,
        name     = zoneName,
        craft    = craft,
        isSurvey = isSurvey,
    }
end
