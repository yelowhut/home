-- Smoke test for the SurveyZoneList changes.
-- Run with the stub API loaded first.

local ADDON = ADDON_DIR

local failures = 0
local checks = 0

local function check(label, got, want)
    checks = checks + 1
    if got ~= want then
        failures = failures + 1
        print(string.format("FAIL  %-52s got %s want %s", label, tostring(got), tostring(want)))
    else
        print(string.format("ok    %-52s %s", label, tostring(got)))
    end
end

local function loadFile(name)
    local path = ADDON .. "/" .. name
    local fn, err = loadfile(path)
    if fn == nil then
        error("cannot load " .. path .. " : " .. tostring(err))
    end
    fn()
end

-- ------------------------------------------------------------- fake items
-- LibTreasure knows these three. The alchemist one deliberately points at the
-- Ebonheart city map, like the real library data does.
LINK_INFO[57737] = {name = "Blacksmith Survey: Stonefalls", isSurvey = true}
LINK_INFO[57746] = {name = "Alchemist Survey: Stonefalls", isSurvey = true}
LINK_INFO[57740] = {name = "Clothier Survey: Stonefalls", isSurvey = true}
LINK_INFO[43655] = {name = "Stonefalls Treasure Map I", isTreasure = true}

LIB_TREASURE_DATA[57737] = {itemId = 57737, mapId = 7, texture = "stonefalls_survey_blacksmith"}
LIB_TREASURE_DATA[57746] = {itemId = 57746, mapId = 511, texture = "stonefalls_survey_alchemist"}
LIB_TREASURE_DATA[57740] = {itemId = 57740, mapId = 7, texture = "stonefalls_survey_clothier"}
LIB_TREASURE_DATA[43655] = {itemId = 43655, mapId = 7, texture = "treasuremap_stonefalls_001"}

-- LibTreasure does not know these : the name parser has to handle them, and
-- the roman numerals must collapse into a single zone.
LINK_INFO[900001] = {name = "Woodworker Survey: Newland II", isSurvey = true}
LINK_INFO[900002] = {name = "Woodworker Survey: Newland III", isSurvey = true}
LINK_INFO[900003] = {name = "Enchanter Survey: Newland", isSurvey = true}

-- Something that is not a survey at all
LINK_INFO[123456] = {name = "Potato"}

-- ------------------------------------------------------------------ load
loadFile("Initialise.lua")
loadFile("lang\\en.lua")
loadFile("Zone.lua")
loadFile("ChampionPoints.lua")
loadFile("Alerts.lua")
loadFile("Collect.lua")
loadFile("Debug.lua")
loadFile("Events.lua")
loadFile("GUI.lua")
loadFile("GUIItem.lua")
loadFile("Interaction.lua")
loadFile("ItemSort.lua")
loadFile("Recolt.lua")
loadFile("Settings.lua")

-- ------------------------------------------------------------ scenario 1
-- Bag holds Stonefalls surveys from two different LibTreasure maps.
BAGS[BAG_BACKPACK][0] = {itemId = 57737, qty = 3}
BAGS[BAG_BACKPACK][1] = {itemId = 57746, qty = 2}
BAGS[BAG_BACKPACK][2] = {itemId = 43655, qty = 1}
BAGS[BAG_BACKPACK][3] = {itemId = 123456, qty = 5}
BAGS[BAG_BACKPACK][4] = {itemId = 900001, qty = 1}
BAGS[BAG_BACKPACK][5] = {itemId = 900002, qty = 1}
BAGS[BAG_BACKPACK][6] = {itemId = 900003, qty = 4}
-- Bank holds one more Stonefalls survey
BAGS[BAG_BANK][0] = {itemId = 57740, qty = 7}

SurveyZoneList:Initialise()

print("\n=== issue #14 : zone identity ===")

SurveyZoneList.Collect:search()
SurveyZoneList.ItemSort:updateCurrentZone()

local function zoneCount()
    local n = 0
    for _ in pairs(SurveyZoneList.Collect.zoneList) do n = n + 1 end
    return n
end

-- Stonefalls (two maps merged) + Newland (two roman numerals merged) = 2
check("zones found", zoneCount(), 2)

local stonefalls = SurveyZoneList.Collect.zoneList["z:101"]
check("stonefalls resolved by zone id", stonefalls ~= nil, true)
check("stonefalls name", stonefalls.name, "stonefalls")
check("ebonheart did NOT become its own zone", SurveyZoneList.Collect.zoneList["z:512"], nil)
check("stonefalls survey bag total", stonefalls.survey.bag.nbTotal, 5)
check("stonefalls survey bag unique", stonefalls.survey.bag.nbUnique, 2)
check("stonefalls treasure bag unique", stonefalls.treasure.bag.nbUnique, 1)

local newland = SurveyZoneList.Collect.zoneList["n:newland"]
check("newland resolved by name parser", newland ~= nil, true)
check("newland is not keyed by zone id", newland.zoneId, nil)
check("newland roman numerals merged", newland.survey.bag.nbUnique, 3)
check("newland survey total", newland.survey.bag.nbTotal, 6)

print("\n=== issue #12 : bank ===")

check("bank ignored while the setting is off", stonefalls.survey.bank.nbTotal, 0)

SurveyZoneList.savedVariables.bank.readBank = true
SurveyZoneList.Collect:search()
stonefalls = SurveyZoneList.Collect.zoneList["z:101"]

check("bank survey total", stonefalls.survey.bank.nbTotal, 7)
check("bank survey unique", stonefalls.survey.bank.nbUnique, 1)
check("bag total untouched by the bank", stonefalls.survey.bag.nbTotal, 5)
check("combined unique", stonefalls.survey.all.nbUnique, 3)
check("combined total", stonefalls.survey.all.nbTotal, 12)

print("\n=== issue #10 : craft breakdown ===")

check("blacksmith in bag", stonefalls.craft.blacksmith.all, 3)
check("alchemist in bag", stonefalls.craft.alchemist.all, 2)
check("clothier from bank", stonefalls.craft.clothier.all, 7)
check("woodworker in stonefalls", stonefalls.craft.woodworker.all, 0)
check("newland woodworker via name parser", newland.craft.woodworker.all, 2)
check("newland enchanter via name parser", newland.craft.enchanter.all, 4)

print("\n=== display ===")

SurveyZoneList.GUI:refreshAll()

local firstRow = SurveyZoneList.GUI.itemList[1]
check("first row is the current zone", firstRow.zoneInfo.name, "stonefalls")
check("row text", firstRow.uiLabel:GetText(), "Stonefalls : 2 - 5 / 1")

SurveyZoneList.GUI:defineDisplayItemText("<<1>> bag <<3>> bank <<6>> all <<9>>")
check("row text with bank placeholders",
      SurveyZoneList.GUI.itemList[1].uiLabel:GetText(),
      "Stonefalls bag 5 bank 7 all 12")
SurveyZoneList.GUI:defineDisplayItemText("<<1>> : <<2>> - <<3>> / <<4>>")

check("window width includes the craft strip",
      SurveyZoneList.GUI:totalWidth(),
      300 + 6 * 34)

print("\n=== incremental updates ===")

-- Use one blacksmith survey : 3 -> 2
BAGS[BAG_BACKPACK][0].qty = 2
SurveyZoneList.Events.onMoveItem(0, BAG_BACKPACK, 0, false, 0, INVENTORY_UPDATE_REASON_DEFAULT, 2)
stonefalls = SurveyZoneList.Collect.zoneList["z:101"]
check("after using one survey, bag total", stonefalls.survey.bag.nbTotal, 4)
check("after using one survey, blacksmith", stonefalls.craft.blacksmith.all, 2)
check("alert saw the remaining quantity", SurveyZoneList.Alerts.spotQuantity, 2)

-- Use the last two : slot empties
BAGS[BAG_BACKPACK][0] = nil
SurveyZoneList.Events.onMoveItem(0, BAG_BACKPACK, 0, false, 0, INVENTORY_UPDATE_REASON_DEFAULT, 0)
stonefalls = SurveyZoneList.Collect.zoneList["z:101"]
check("after emptying the slot, bag total", stonefalls.survey.bag.nbTotal, 2)
check("after emptying the slot, blacksmith", stonefalls.craft.blacksmith.all, 0)
check("alert saw zero left", SurveyZoneList.Alerts.spotQuantity, 0)

-- Re-reading the same slot event twice must not double count
SurveyZoneList.Events.onMoveItem(0, BAG_BACKPACK, 0, false, 0, INVENTORY_UPDATE_REASON_DEFAULT, 0)
stonefalls = SurveyZoneList.Collect.zoneList["z:101"]
check("repeated event does not drift", stonefalls.survey.bag.nbTotal, 2)

-- A full rescan must agree with the incremental state
SurveyZoneList.Collect:search()
check("rescan agrees on bag total",
      SurveyZoneList.Collect.zoneList["z:101"].survey.bag.nbTotal, 2)
check("rescan agrees on craft",
      SurveyZoneList.Collect.zoneList["z:101"].craft.alchemist.all, 2)

-- Dropping every item of a zone removes the zone
BAGS[BAG_BACKPACK][4] = nil
BAGS[BAG_BACKPACK][5] = nil
BAGS[BAG_BACKPACK][6] = nil
SurveyZoneList.Events.onMoveItem(0, BAG_BACKPACK, 4, false, 0, INVENTORY_UPDATE_REASON_DEFAULT, 0)
SurveyZoneList.Events.onMoveItem(0, BAG_BACKPACK, 5, false, 0, INVENTORY_UPDATE_REASON_DEFAULT, 0)
SurveyZoneList.Events.onMoveItem(0, BAG_BACKPACK, 6, false, 0, INVENTORY_UPDATE_REASON_DEFAULT, 0)
check("emptied zone is dropped", SurveyZoneList.Collect.zoneList["n:newland"], nil)
check("zones left", zoneCount(), 1)

print("\n=== issue #13 : champion points ===")

CHAMPION_SKILLS[1] = {abilityId = 111, name = "Something Else", points = 10}
CHAMPION_SKILLS[2] = {abilityId = 142220, name = "Plentiful Harvest", points = 0}
SurveyZoneList.ChampionPoints.skillIdResolved = false

check("skill resolved by ability id", SurveyZoneList.ChampionPoints:findSkillId(), 2)
check("not bought means not active", SurveyZoneList.ChampionPoints:isPlentifulHarvestActive(), false)

CHAMPION_SKILLS[2].points = 50
check("bought but not slotted", SurveyZoneList.ChampionPoints:isPlentifulHarvestActive(), false)

CHAMPION_SLOTTED[4] = 2
check("bought and slotted", SurveyZoneList.ChampionPoints:isPlentifulHarvestActive(), true)

check("warning off while the setting is off", SurveyZoneList.ChampionPoints:shouldWarn(), false)

SurveyZoneList.savedVariables.championPoints.warnPlentifulHarvest = true
CHAMPION_SLOTTED[4] = nil
check("warning on when unslotted", SurveyZoneList.ChampionPoints:shouldWarn(), true)

SurveyZoneList.GUI:updateChampionWarning()
check("warning row visible", SurveyZoneList.GUI.championWarningShown, true)
check("header rows grew to 3", SurveyZoneList.GUI:headerRowCount(), 3)

CHAMPION_SLOTTED[4] = 2
SurveyZoneList.GUI:updateChampionWarning()
check("warning row hidden again", SurveyZoneList.GUI.championWarningShown, false)
check("header rows back to 2", SurveyZoneList.GUI:headerRowCount(), 2)

print("\n=== LibTreasure missing ===")

USE_LIB_TREASURE = false
SurveyZoneList.Zone.mapIdCache = {}
SurveyZoneList.Collect:search()
local parsed = SurveyZoneList.Collect.zoneList["n:stonefalls"]
check("falls back to the name parser", parsed ~= nil, true)
check("parsed stonefalls survey total", parsed.survey.bag.nbTotal, 2)
USE_LIB_TREASURE = true

print("\n=== debug command ===")
DEBUG_LINES = {}
SurveyZoneList.Collect:search()
SurveyZoneList.Debug:run("zones")
check("debug printed something", #DEBUG_LINES > 0, true)
SurveyZoneList.Debug:run("cp")
SurveyZoneList.Debug:run("zone")

print(string.format("\n%d checks, %d failures", checks, failures))
if failures > 0 then os.exit(1) end
