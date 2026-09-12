-- Minimal stand-in for the parts of the ESO API the addon touches.
-- Enough to load every file and run the collect / sort / display path.

-- ---------------------------------------------------------------- constants
ITEMTYPE_TROPHY                          = 1
SPECIALIZED_ITEMTYPE_TROPHY_SURVEY_REPORT = 10
SPECIALIZED_ITEMTYPE_TROPHY_TREASURE_MAP  = 11
BAG_BACKPACK                             = 1
BAG_BANK                                 = 2
BAG_SUBSCRIBER_BANK                      = 6
CT_BACKDROP, CT_LABEL, CT_TEXTURE, CT_CONTROL = 1, 2, 3, 4
TOPLEFT, TOPRIGHT                        = 1, 2
HOTBAR_CATEGORY_CHAMPION                 = 3
ACTION_TYPE_CHAMPION_SKILL               = 7
ADDITIONAL_INTERACT_INFO_NONE            = 0
EVENT_ADD_ON_LOADED                      = 1
EVENT_PLAYER_ACTIVATED                   = 2
EVENT_INVENTORY_SINGLE_SLOT_UPDATE       = 3
EVENT_CLIENT_INTERACT_RESULT             = 4
EVENT_LOOT_RECEIVED                      = 5
EVENT_OPEN_BANK                          = 6
EVENT_CLOSE_BANK                         = 7
EVENT_HOTBAR_SLOT_UPDATED                = 8
EVENT_ACTION_SLOTS_ALL_HOTBARS_UPDATED   = 9
REGISTER_FILTER_BAG_ID                   = 1
REGISTER_FILTER_INVENTORY_UPDATE_REASON  = 2
INVENTORY_UPDATE_REASON_DEFAULT          = 0
CSA_CATEGORY_SMALL_TEXT                  = 1
SOUNDS                                   = setmetatable({}, {__index = function() return "snd" end})

-- ------------------------------------------------------------------- world
-- Stonefalls is zone 101. Ebonheart (map 511) is a city inside it, which is
-- exactly the case LibTreasure resolves to the wrong map.
local mapIdToZoneIndex = {[7] = 7, [511] = 511, [58] = 58}
local zoneIndexToZoneId = {[7] = 101, [511] = 512, [58] = 181}
local parentZoneId = {[101] = 101, [512] = 101, [181] = 181}
local zoneIdToName = {[101] = "Stonefalls", [512] = "Ebonheart", [181] = "Deshaan"}

CURRENT_ZONE_ID = 101

function GetMapInfoById(mapId)
    local zoneIndex = mapIdToZoneIndex[mapId]
    if zoneIndex == nil then return nil, nil, nil, nil, nil end
    return "map"..mapId, 1, 1, zoneIndex, ""
end

function GetZoneId(zoneIndex) return zoneIndexToZoneId[zoneIndex] or 0 end
function GetParentZoneId(zoneId) return parentZoneId[zoneId] or 0 end
function GetZoneNameById(zoneId) return zoneIdToName[zoneId] end
function GetZoneIndex(zoneId)
    for idx, id in pairs(zoneIndexToZoneId) do
        if id == zoneId then return idx end
    end
    return 0
end
function GetZoneNameByIndex(zoneIndex) return zoneIdToName[GetZoneId(zoneIndex)] end
function GetCurrentMapZoneIndex() return 7 end
function GetUnitWorldPosition(unit) return CURRENT_ZONE_ID, 0, 0, 0 end

-- -------------------------------------------------------------------- bags
-- BAGS[bagId][slotIdx] = {itemId, name, isSurvey, qty}
BAGS = {[BAG_BACKPACK] = {}, [BAG_BANK] = {}, [BAG_SUBSCRIBER_BANK] = {}}
BAG_SIZE = 20

function GetBagSize(bagId) return BAG_SIZE end

local function slotItem(bagId, slotIdx)
    local bag = BAGS[bagId]
    if bag == nil then return nil end
    return bag[slotIdx]
end

function GetItemLink(bagId, slotIdx)
    local item = slotItem(bagId, slotIdx)
    if item == nil then return "" end
    return "|H1:item:"..item.itemId..":x|h|h"
end

function GetSlotStackSize(bagId, slotIdx)
    local item = slotItem(bagId, slotIdx)
    if item == nil then return 0 end
    return item.qty
end

LINK_INFO = {} -- itemId => {name, isSurvey}

function GetItemLinkItemId(itemLink)
    return tonumber(itemLink:match("item:(%d+)"))
end

function GetItemLinkItemType(itemLink)
    local itemId = GetItemLinkItemId(itemLink)
    local info = LINK_INFO[itemId]
    if info == nil then return 99, 99 end
    if info.isSurvey then
        return ITEMTYPE_TROPHY, SPECIALIZED_ITEMTYPE_TROPHY_SURVEY_REPORT
    end
    if info.isTreasure then
        return ITEMTYPE_TROPHY, SPECIALIZED_ITEMTYPE_TROPHY_TREASURE_MAP
    end
    return 99, 99
end

function GetItemLinkName(itemLink)
    local info = LINK_INFO[GetItemLinkItemId(itemLink)]
    if info == nil then return "" end
    return info.name
end

function GetItemName(bagId, slotIdx) return GetItemLinkName(GetItemLink(bagId, slotIdx)) end

-- ------------------------------------------------------------ LibTreasure
-- itemId => {itemId, mapId, pinType, x, y, texture}
LIB_TREASURE_DATA = {}
USE_LIB_TREASURE = true

function LibTreasure_GetItemIdData(itemId)
    if not USE_LIB_TREASURE then return nil end
    return LIB_TREASURE_DATA[itemId]
end

-- ------------------------------------------------------------- champion pts
CHAMPION_SKILLS = {} -- skillId => {abilityId, name, points}
CHAMPION_SLOTTED = {}

function GetNumChampionDisciplines() return 1 end
function GetChampionDisciplineId(i) return i end
function GetChampionDisciplineType(i) return 1 end
function GetNumChampionDisciplineSkills(i)
    local n = 0
    for _ in pairs(CHAMPION_SKILLS) do n = n + 1 end
    return n
end
function GetChampionSkillId(disciplineIndex, skillIndex) return skillIndex end
function GetChampionAbilityId(skillId)
    local s = CHAMPION_SKILLS[skillId]
    return s and s.abilityId or 0
end
function GetChampionSkillName(skillId)
    local s = CHAMPION_SKILLS[skillId]
    return s and s.name or ""
end
function GetNumPointsSpentOnChampionSkill(skillId)
    local s = CHAMPION_SKILLS[skillId]
    return s and s.points or 0
end
function GetChampionSkillType(skillId) return 1 end
function CanChampionSkillTypeBeSlotted(skillType) return true end
function GetAssignableChampionBarStartAndEndSlots() return 1, 12 end
function GetSlotType(slotIndex, hotbar)
    if CHAMPION_SLOTTED[slotIndex] then return ACTION_TYPE_CHAMPION_SKILL end
    return 0
end
function GetSlotBoundId(slotIndex, hotbar) return CHAMPION_SLOTTED[slotIndex] or 0 end

-- --------------------------------------------------------------- UI stubs
local function makeControl(name)
    local c = {__name = name, __children = {}, __text = nil, __hidden = false,
               __w = 300, __h = 30}
    function c:SetText(t) self.__text = t end
    function c:GetText() return self.__text end
    function c:SetHidden(v) self.__hidden = v end
    function c:IsHidden() return self.__hidden end
    function c:SetDimensions(w, h) self.__w, self.__h = w, h end
    function c:GetWidth() return self.__w end
    function c:GetHeight() return self.__h end
    function c:GetLeft() return 0 end
    function c:GetTop() return 0 end
    return setmetatable(c, {__index = function() return function() end end})
end

ALL_CONTROLS = {}

local windowManager = {}
function windowManager:CreateTopLevelWindow(name)
    local c = makeControl(name); ALL_CONTROLS[name] = c; return c
end
function windowManager:CreateControl(name, parent, ctype)
    local c = makeControl(name); c.__type = ctype; ALL_CONTROLS[name] = c; return c
end
function GetWindowManager() return windowManager end

SCENE_MANAGER = {GetScene = function() return {AddFragment = function() end,
                                              RemoveFragment = function() end,
                                              RegisterCallback = function() end} end}
ZO_SimpleSceneFragment = {New = function() return {} end}
EVENT_MANAGER = {RegisterForEvent = function() end, AddFilterForEvent = function() end}
RETICLE = {interactContext = makeControl("reticle")}
function ZO_PostHook() end
SLASH_COMMANDS = {}
CENTER_SCREEN_ANNOUNCE = {
    CreateMessageParams = function() return setmetatable({}, {__index = function() return function() end end}) end,
    AddMessageWithParams = function() end,
}
function PlaySound() end
GuiRoot = makeControl("GuiRoot")

LibAddonMenu2 = {RegisterAddonPanel = function() end, RegisterOptionControls = function(_, _, opts)
    LAM_OPTIONS = opts
end}

ZO_SavedVars = {NewAccountWide = function() return {} end}

-- --------------------------------------------------------------- strings
STRINGS = {}
function ZO_CreateStringId(id, value)
    STRINGS[id] = value
    _G[id] = id
end
function GetString(id) return STRINGS[id] or id end

function zo_strformat(fmt, ...)
    local args = {...}
    local out = tostring(fmt):gsub("<<(%d+)>>", function(n)
        local v = args[tonumber(n)]
        if v == nil then return "" end
        return tostring(v)
    end)
    return out
end

function zo_iconTextFormat(_, _, _, text) return text end

DEBUG_LINES = {}
function d(text) table.insert(DEBUG_LINES, tostring(text)) end
