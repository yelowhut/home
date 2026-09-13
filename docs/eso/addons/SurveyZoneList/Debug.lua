--[[
-- Debug helpers, reachable with "/szl <command>".
--
-- These exist because the zone resolution and the champion star lookup both
-- depend on game data that cannot be checked outside the running game.
--]]
SurveyZoneList.Debug = {}

--[[
-- Print a line in the chat window
--
-- @param string text
--]]
function SurveyZoneList.Debug:print(text)
    d("[SZL] "..text)
end

--[[
-- Dispatch a debug command
--
-- @param string args The text typed after the slash command
--]]
function SurveyZoneList.Debug:run(args)
    local command = args:lower():gsub("^%s+", ""):gsub("%s+$", "")

    if command == "zones" then
        self:dumpZones()
    elseif command == "cp" then
        self:dumpChampionPoints()
    elseif command == "zone" then
        self:dumpCurrentZone()
    else
        self:print("commands : zone, zones, cp")
    end
end

--[[
-- Print what the addon thinks the current zone is
--]]
function SurveyZoneList.Debug:dumpCurrentZone()
    local zoneId = SurveyZoneList.Zone:currentZoneId()

    self:print(zo_strformat(
        "current zone id <<1>>, name <<2>>",
        tostring(zoneId),
        tostring(SurveyZoneList.ItemSort.currentZoneName)
    ))

    self:print(zo_strformat(
        "LibTreasure available <<1>>, used <<2>>",
        tostring(SurveyZoneList.Zone.hasLibTreasure),
        tostring(SurveyZoneList.Zone:isLibTreasureEnabled())
    ))
end

--[[
-- Print every zone currently held, with how it was resolved.
--
-- A zone showing "parsed" was not found in LibTreasure. Two lines with the
-- same name mean the duplication of issue #14 is still happening.
--]]
function SurveyZoneList.Debug:dumpZones()
    local count = 0

    for _, zoneInfo in ipairs(SurveyZoneList.Collect.orderedList) do
        count = count + 1

        local origin = "parsed"
        if zoneInfo.zoneId ~= nil then
            origin = "zoneId "..zoneInfo.zoneId
        end

        local craftText = ""
        for _, craftType in ipairs(SurveyZoneList.Zone.CRAFT_TYPES) do
            craftText = craftText..craftType:sub(1, 2)..":"..zoneInfo.craft[craftType].all.." "
        end

        self:print(zo_strformat(
            "<<1>> (<<2>>) survey bag <<3>> bank <<4>>, treasure bag <<5>> bank <<6>> | <<7>>",
            zoneInfo.name,
            origin,
            zoneInfo.survey.bag.nbTotal,
            zoneInfo.survey.bank.nbTotal,
            zoneInfo.treasure.bag.nbTotal,
            zoneInfo.treasure.bank.nbTotal,
            craftText
        ))
    end

    self:print(count.." zone(s)")
end

--[[
-- Print the champion star resolution (issue #13)
--]]
function SurveyZoneList.Debug:dumpChampionPoints()
    local championPoints = SurveyZoneList.ChampionPoints
    local skillId        = championPoints:findSkillId()

    if skillId == nil then
        self:print("Plentiful Harvest champion skill not found")
        return
    end

    self:print(zo_strformat(
        "Plentiful Harvest : skillId <<1>>, name <<2>>, points <<3>>, active <<4>>",
        skillId,
        zo_strformat("<<1>>", GetChampionSkillName(skillId)),
        GetNumPointsSpentOnChampionSkill(skillId),
        tostring(championPoints:isPlentifulHarvestActive())
    ))
end
