--[[
-- Champion point check (issue #13).
--
-- Plentiful Harvest gives a chance to gather extra resources, so running a
-- survey without it slotted wastes the survey. This module tells the GUI
-- whether the star is both bought and slotted.
--]]
SurveyZoneList.ChampionPoints = {}

--[[
-- @const integer The ability id behind the Plentiful Harvest champion star.
-- An ability id is language independent, unlike the star name.
--]]
SurveyZoneList.ChampionPoints.PLENTIFUL_HARVEST_ABILITY_ID = 142220

--[[
-- @var table All saved variables dedicated to the champion point check.
--]]
SurveyZoneList.ChampionPoints.savedVars = nil

--[[
-- @var integer|nil The resolved champion skill id
--]]
SurveyZoneList.ChampionPoints.skillId = nil

--[[
-- @var bool Whether we already tried to resolve the skill id
--]]
SurveyZoneList.ChampionPoints.skillIdResolved = false

--[[
-- Initialise the champion point check
--]]
function SurveyZoneList.ChampionPoints:init()
    self.savedVars = SurveyZoneList.savedVariables.championPoints

    self:initSavedVarsValues()
end

--[[
-- Initialise with a default value all saved variables dedicated to this module
--]]
function SurveyZoneList.ChampionPoints:initSavedVarsValues()
    if self.savedVars.warnPlentifulHarvest == nil then
        self.savedVars.warnPlentifulHarvest = false
    end
end

--[[
-- Get the value of warnPlentifulHarvest
--
-- @return bool
--]]
function SurveyZoneList.ChampionPoints:getWarnPlentifulHarvest()
    return self.savedVars.warnPlentifulHarvest
end

--[[
-- Set the value of warnPlentifulHarvest
--
-- @param bool value
--]]
function SurveyZoneList.ChampionPoints:setWarnPlentifulHarvest(value)
    self.savedVars.warnPlentifulHarvest = value
    SurveyZoneList.GUI:updateChampionWarning()
end

--[[
-- Find the champion skill id of Plentiful Harvest.
--
-- The ability id is checked first because it does not depend on the client
-- language. The star name is only used as a fallback, in case a future patch
-- changes the ability behind the star.
--
-- @return integer|nil
--]]
function SurveyZoneList.ChampionPoints:findSkillId()
    if self.skillIdResolved == true then
        return self.skillId
    end

    self.skillIdResolved = true

    if type(GetNumChampionDisciplines) ~= "function" then
        return nil
    end

    local wantedName = SurveyZoneList.lang.championPlentifulHarvest
    local nameMatch  = nil

    for disciplineIndex = 1, GetNumChampionDisciplines() do
        for skillIndex = 1, GetNumChampionDisciplineSkills(disciplineIndex) do
            local skillId = GetChampionSkillId(disciplineIndex, skillIndex)

            if GetChampionAbilityId(skillId) == self.PLENTIFUL_HARVEST_ABILITY_ID then
                self.skillId = skillId
                return skillId
            end

            if nameMatch == nil and wantedName ~= nil then
                local skillName = zo_strformat("<<1>>", GetChampionSkillName(skillId))

                if skillName ~= nil and skillName:lower() == wantedName:lower() then
                    nameMatch = skillId
                end
            end
        end
    end

    self.skillId = nameMatch

    return self.skillId
end

--[[
-- Check whether a champion skill is slotted on the champion bar.
--
-- @param integer skillId
--
-- @return bool
--]]
function SurveyZoneList.ChampionPoints:isSkillSlotted(skillId)
    local startSlotIndex = 1
    local endSlotIndex   = 12

    if type(GetAssignableChampionBarStartAndEndSlots) == "function" then
        startSlotIndex, endSlotIndex = GetAssignableChampionBarStartAndEndSlots()
    end

    for actionSlotIndex = startSlotIndex, endSlotIndex do
        if GetSlotType(actionSlotIndex, HOTBAR_CATEGORY_CHAMPION) == ACTION_TYPE_CHAMPION_SKILL
            and GetSlotBoundId(actionSlotIndex, HOTBAR_CATEGORY_CHAMPION) == skillId
        then
            return true
        end
    end

    return false
end

--[[
-- Whether Plentiful Harvest is bought and slotted.
--
-- When the star cannot be found at all we answer true, so an unexpected game
-- change makes the warning disappear instead of showing it for ever.
--
-- @return bool
--]]
function SurveyZoneList.ChampionPoints:isPlentifulHarvestActive()
    local skillId = self:findSkillId()

    if skillId == nil then
        return true
    end

    if GetNumPointsSpentOnChampionSkill(skillId) <= 0 then
        return false
    end

    if type(CanChampionSkillTypeBeSlotted) == "function"
        and CanChampionSkillTypeBeSlotted(GetChampionSkillType(skillId)) == false
    then
        -- A passive star, buying it is enough.
        return true
    end

    return self:isSkillSlotted(skillId)
end

--[[
-- Whether the GUI should currently display the warning.
--
-- @return bool
--]]
function SurveyZoneList.ChampionPoints:shouldWarn()
    if self.savedVars.warnPlentifulHarvest ~= true then
        return false
    end

    return self:isPlentifulHarvestActive() == false
end
