SurveyZoneList = {}

SurveyZoneList.lang = {}

SurveyZoneList.name           = "Survey Zone List"
SurveyZoneList.dirName        = "SurveyZoneList"
SurveyZoneList.savedVariables = nil
SurveyZoneList.ready          = false
SurveyZoneList.LAM            = LibAddonMenu2

--[[
-- Module initialiser
-- Intiialise savedVariables, GUI and sort system
--]]
function SurveyZoneList:Initialise()
    SurveyZoneList.savedVariables = ZO_SavedVars:NewAccountWide("SurveyZoneListSavedVariables", 1, nil, {})

    local sectionList = {"gui", "sort", "alerts", "interaction", "bank", "championPoints", "zone"}

    for _, section in ipairs(sectionList) do
        if SurveyZoneList.savedVariables[section] == nil then
            SurveyZoneList.savedVariables[section] = {}
        end
    end

    if SurveyZoneList.savedVariables.bank.readBank == nil then
        SurveyZoneList.savedVariables.bank.readBank = false
    end

    if SurveyZoneList.savedVariables.zone.useLibTreasure == nil then
        SurveyZoneList.savedVariables.zone.useLibTreasure = true
    end

    SurveyZoneList.Zone:init()
    SurveyZoneList.ChampionPoints:init()
    SurveyZoneList.Alerts:init()
    SurveyZoneList.Interaction:init()
    SurveyZoneList.Settings:init()
    SurveyZoneList.GUI:init()
    SurveyZoneList.ItemSort:init()
    SurveyZoneList.ready = true
end
