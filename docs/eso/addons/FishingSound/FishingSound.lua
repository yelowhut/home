FishingSound = FishingSound or {}
local FS = FishingSound

------------------------------------------------------------
--  VARIABLES: 
------------------------------------------------------------

--[[
List of Good SoundIDs to use for fishing bite: NEEDS TO BE CONSTANT VALUE


ABILITY_SYNERGY_READY
ABILITY_ULTIMATE_READY
ACTIVE_SKILL_MORPG_CHOSEN
ANTIQUITIES_FANFARE_COMPLETED
ARMORY_OPEN
AVA_GATE_OPENED
BATTLEGROUND_CAPTURE_AREA_CAPTURED_OTHER_TEAM
BATTLEGROUND_CAPTURE_AREA_CAPTURED_OWN_TEAM
BATTLEGROUND_CAPTURE_AREA_SPAWNED
BATTLEGROUND_CAPTURE_AREA_MOVED
BATTLEGROUND_COUNTDOWN_FINISH
BATTLEGROUND_FINAL_ROUND_STARTING
BATTLEGROUND_MATCH_WON
BATTLEGROUND_NEARING_VICTORY
CHALLENGE_DIFFICULTY_CHANGE_DIFFICULTY_BUTTON_CLICKED
CHAMPTION_POINTS_GAINED
CHAMPTION_POINTS_COMMITED
--]]

local savedVariables 

FS.reelInSound = nil
FS.addonLoaded = false
FS.playerLoaded = false
FS.disableFishingSound = false


-- Available bite sounds: { technical SOUNDS key, human-readable label }.
-- The dropdown shows the labels but stores the technical key.
FS.soundOptions = {
    { "ABILITY_SYNERGY_READY",                                 "Synergy Ready" },
    { "ABILITY_ULTIMATE_READY",                                "Ultimate Ready" },
    { "ACTIVE_SKILL_MORPH_CHOSEN",                             "Skill Morph Chosen" },
    { "ANTIQUITIES_FANFARE_COMPLETED",                         "Antiquities Fanfare" },
    { "ARMORY_OPEN",                                           "Armory Open" },
    { "AVA_GATE_OPENED",                                       "Keep Gate Opened" },
    { "BATTLEGROUND_CAPTURE_AREA_CAPTURED_OTHER_TEAM",         "BG: Area Captured (Enemy)" },
    { "BATTLEGROUND_CAPTURE_AREA_CAPTURED_OWN_TEAM",           "BG: Area Captured (Ally)" },
    { "BATTLEGROUND_CAPTURE_AREA_SPAWNED",                     "BG: Area Spawned" },
    { "BATTLEGROUND_CAPTURE_AREA_MOVED",                       "BG: Area Moved" },
    { "BATTLEGROUND_COUNTDOWN_FINISH",                         "BG: Countdown Finish" },
    { "BATTLEGROUND_FINAL_ROUND_STARTING",                     "BG: Final Round Starting" },
    { "BATTLEGROUND_MATCH_WON",                                "BG: Match Won" },
    { "BATTLEGROUND_NEARING_VICTORY",                          "BG: Nearing Victory" },
    { "CHALLENGE_DIFFICULTY_CHANGE_DIFFICULTY_BUTTON_CLICKED", "Difficulty Button Click" },
    { "CHAMPION_POINTS_COMMITTED",                             "Champion Points Committed" },
}


-- Play a sound once so the user can preview it. Guards against
-- invalid/unknown SOUNDS keys (PlaySound(nil) would just be silent).
local function previewSound(soundKey)
    local soundId = soundKey and SOUNDS[soundKey]
    if soundId then
        PlaySound(soundId)
    end
end


------------------------------------------------------------
--  METHODS: SAVED VARIABBLES METHODS
------------------------------------------------------------


local function getDisableFishingSound()
    if savedVariables then
        return savedVariables.disableFishingSound
    else
        return false
    end
end     


local function setDisableFishingSound(value)
    if savedVariables then
        savedVariables.disableFishingSound = value
    end
end



local function getReelInSound()
    if savedVariables then
        return savedVariables.reelInSound
    else
        return "ABILITY_SYNERGY_READY"
    end
end


local function setReelInSound(value)
    if savedVariables then
        savedVariables.reelInSound = value
    end
end


------------------------------------------------------------
--  METHODS: BACKEND METHODS
------------------------------------------------------------



local function OnVibration(eventCode, p1, p2, p3, p4, p5)
    
    if getDisableFishingSound() == false then 

        --d(string.format("Vibration: %s | %s | %s | %s | %s", p1, p2, p3, p4, p5))

        -- Fishing bite detection
        if p1 == 2500 and p2 > 0 and p3 > 0 then
                --d("Fishing bite detected!")

                PlaySound(SOUNDS[getReelInSound()])
        end

    end 
end




local function FS_TryInitialize()
        
        --d("FishingSound: TryInitialize " .. tostring(FS.addonLoaded) .. " " .. tostring(FS.playerLoaded))

        if FS.addonLoaded and FS.playerLoaded then
                --d("FishingSound: Fully initialized, registering fishing event")
                
                --LibAddonMenu2 Settings
                local LAM = LibAddonMenu2
                if not LAM then
                    d("FishingSound: LibAddonMenu-2.0 not loaded, settings panel disabled (sound still works)")
                    -- Register fishing detection anyway so the addon works without the library
                    EVENT_MANAGER:RegisterForEvent("FishingSound_Vibration", EVENT_VIBRATION, OnVibration)
                    return
                end
                local panelData = {
                    type = "panel",
                    name = "FishingSound",
                    author = "@FloIstImGame"
                }

                -- Build parallel label/value lists for the dropdown from FS.soundOptions
                local choiceLabels = {}
                local choiceValues = {}
                for i = 1, #FS.soundOptions do
                    choiceValues[i] = FS.soundOptions[i][1]
                    choiceLabels[i] = FS.soundOptions[i][2]
                end

                local optionsData = {
                      [1] =  {
                                type = "checkbox",
                                name = "Disable Fishing Sound",
                                tooltip = "Toggle the fishing sound on or off.",
                                getFunc = function() return getDisableFishingSound() end,
                                setFunc = function(value) setDisableFishingSound(value) end
                        },
                       [2] = {
                                type = "dropdown",
                                name = "Fishing Bite Sound",
                                tooltip = "Select the sound to play when a fishing bite is detected. The chosen sound is played once as a preview.",
                                choices = choiceLabels,
                                choicesValues = choiceValues,
                                getFunc = function() return getReelInSound() end,
                                setFunc = function(value)
                                    setReelInSound(value)
                                    previewSound(value)   -- one-shot preview
                                end
                        },
                       [3] = {
                                type = "button",
                                name = "Play Selected Sound",
                                tooltip = "Play the currently selected bite sound once.",
                                func = function() previewSound(getReelInSound()) end
                        }

                }
                local panel = LAM:RegisterAddonPanel("FishingSound", panelData)

                LAM:RegisterOptionControls("FishingSound", optionsData)

                -- Register for vibration events to detect fishing bites
                EVENT_MANAGER:RegisterForEvent("FishingSound_Vibration", EVENT_VIBRATION, OnVibration)


        end
end




local function FS_AddonLoaded (event, addonName)
        if addonName ~= "FishingSound"  then return end

        FS.addonLoaded = true
        EVENT_MANAGER:UnregisterForEvent("FS_AddonLoaded", EVENT_ADD_ON_LOADED)

        local defaults = {
            disableFishingSound = false ,
            reelInSound = "ABILITY_SYNERGY_READY"   -- store the SOUNDS key, not the resolved id
        }
        savedVariables = ZO_SavedVars:NewAccountWide("FishingSoundVars", 1, nil, defaults)



        FS_TryInitialize()

end


local function OnPlayerActivated()
        
        if FS.playerLoaded then return end
        
        --d("FishingSound: Player activated")
        FS.playerLoaded = true

        FS_TryInitialize()
end




------------------------------------------------------------
--  EVENTs REIGSTERING: 
------------------------------------------------------------


EVENT_MANAGER:RegisterForEvent("FS_AddonLoaded", EVENT_ADD_ON_LOADED, FS_AddonLoaded)

EVENT_MANAGER:RegisterForEvent("FishingSound_PlayerActivated", EVENT_PLAYER_ACTIVATED, OnPlayerActivated)



------------------------------------------------------------
--  SLASH COMMANDS 
------------------------------------------------------------
SLASH_COMMANDS["/fishingsoundon"] = function()
    setDisableFishingSound(false)
    d("FishingSound: Fishing sound enabled")
end

SLASH_COMMANDS["/fishingsoundoff"] = function()
    setDisableFishingSound(true)
    d("FishingSound: Fishing sound disabled")
end


