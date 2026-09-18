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
--  VIGNETTE: DEFAULTS AND SAVED VARIABLE ACCESS
------------------------------------------------------------

-- Screen-edge vignette that blinks while a fish is on the hook.
-- It is four plain quads, one per screen edge, whose corner vertices carry the
-- colour: the two outer ones at full alpha, the two inner ones at alpha 0, so
-- the engine interpolates the gradient for us. No texture art is involved,
-- which is exactly why any colour the user picks renders correctly.

-- An empty texture path makes the engine draw a plain white quad, and that
-- white is the neutral base the vertex colours tint. If a future patch ever
-- stops rendering untextured controls, point this at a white .dds instead.
local VIGNETTE_TEXTURE = ""

FS.vignetteDefaults = {
    vignetteEnabled = true,
    vignetteColor   = { r = 1, g = 0.45, b = 0.12 },
    vignetteAlpha   = 0.65,
    vignetteSize    = 12,     -- % of screen height (top/bottom) or width (sides)
    vignetteSpeed   = 700,    -- ms for one full blink cycle
    vignetteStyle   = "pulse",
    vignetteTimeout = 20,     -- seconds; hard stop if a bite is never resolved
    vignetteEdges   = { top = true, bottom = true, left = true, right = true },
}

FS.vignetteStyles = {
    { "pulse",  "Pulse (smooth)" },
    { "strobe", "Strobe (hard on/off)" },
    { "solid",  "Solid (fade in, hold)" },
}


local function getVar(key)
    if savedVariables and savedVariables[key] ~= nil then
        return savedVariables[key]
    end
    return FS.vignetteDefaults[key]
end


local function setVar(key, value)
    if savedVariables then
        savedVariables[key] = value
    end
end


------------------------------------------------------------
--  VIGNETTE: UI CONSTRUCTION
------------------------------------------------------------

local V = { edges = {} }
FS.vignette = V

local EDGE_ORDER = { "top", "bottom", "left", "right" }

-- Which two corners of each strip are opaque and which two fade out.
local EDGE_VERTICES = {
    top = {
        solid = { VERTEX_POINTS_TOPLEFT,    VERTEX_POINTS_TOPRIGHT },
        fade  = { VERTEX_POINTS_BOTTOMLEFT, VERTEX_POINTS_BOTTOMRIGHT },
    },
    bottom = {
        solid = { VERTEX_POINTS_BOTTOMLEFT, VERTEX_POINTS_BOTTOMRIGHT },
        fade  = { VERTEX_POINTS_TOPLEFT,    VERTEX_POINTS_TOPRIGHT },
    },
    left = {
        solid = { VERTEX_POINTS_TOPLEFT,    VERTEX_POINTS_BOTTOMLEFT },
        fade  = { VERTEX_POINTS_TOPRIGHT,   VERTEX_POINTS_BOTTOMRIGHT },
    },
    right = {
        solid = { VERTEX_POINTS_TOPRIGHT,   VERTEX_POINTS_BOTTOMRIGHT },
        fade  = { VERTEX_POINTS_TOPLEFT,    VERTEX_POINTS_BOTTOMLEFT },
    },
}


local function buildVignette()
    if V.container then return end

    local wm = WINDOW_MANAGER

    local tlw = wm:CreateTopLevelWindow("FishingSoundVignette")
    tlw:SetAnchor(TOPLEFT, GuiRoot, TOPLEFT, 0, 0)
    tlw:SetAnchor(BOTTOMRIGHT, GuiRoot, BOTTOMRIGHT, 0, 0)
    tlw:SetMouseEnabled(false)
    tlw:SetDrawTier(DT_MEDIUM)
    tlw:SetDrawLayer(DL_OVERLAY)

    local container = wm:CreateControl("FishingSoundVignetteContainer", tlw, CT_CONTROL)
    container:SetAnchor(TOPLEFT, tlw, TOPLEFT, 0, 0)
    container:SetAnchor(BOTTOMRIGHT, tlw, BOTTOMRIGHT, 0, 0)
    container:SetMouseEnabled(false)
    container:SetAlpha(0)
    container:SetHidden(true)

    for i = 1, #EDGE_ORDER do
        local key = EDGE_ORDER[i]
        local strip = wm:CreateControl("FishingSoundVignette_" .. key, container, CT_TEXTURE)
        strip:SetTexture(VIGNETTE_TEXTURE)
        strip:SetMouseEnabled(false)
        V.edges[key] = strip
    end

    -- Two anchors per strip fix its length; the thickness is set in applyVignette().
    V.edges.top:SetAnchor(TOPLEFT, container, TOPLEFT, 0, 0)
    V.edges.top:SetAnchor(TOPRIGHT, container, TOPRIGHT, 0, 0)

    V.edges.bottom:SetAnchor(BOTTOMLEFT, container, BOTTOMLEFT, 0, 0)
    V.edges.bottom:SetAnchor(BOTTOMRIGHT, container, BOTTOMRIGHT, 0, 0)

    V.edges.left:SetAnchor(TOPLEFT, container, TOPLEFT, 0, 0)
    V.edges.left:SetAnchor(BOTTOMLEFT, container, BOTTOMLEFT, 0, 0)

    V.edges.right:SetAnchor(TOPRIGHT, container, TOPRIGHT, 0, 0)
    V.edges.right:SetAnchor(BOTTOMRIGHT, container, BOTTOMRIGHT, 0, 0)

    -- Keeps the overlay out of menus, inventory and loading screens.
    local fragment = ZO_SimpleSceneFragment:New(tlw)
    HUD_SCENE:AddFragment(fragment)
    HUD_UI_SCENE:AddFragment(fragment)

    local timeline = ANIMATION_MANAGER:CreateTimeline()
    local animation = timeline:InsertAnimation(ANIMATION_ALPHA, container)
    animation:SetAlphaValues(0, 1)

    V.tlw       = tlw
    V.container = container
    V.timeline  = timeline
    V.animation = animation
end


-- Push the current settings into the controls. Called on every start, so a
-- resolution change or a settings tweak is picked up without extra plumbing.
local function applyVignette()
    if not V.container then return end

    local color     = getVar("vignetteColor")
    local alpha     = getVar("vignetteAlpha")
    local edges     = getVar("vignetteEdges")
    local thickness = getVar("vignetteSize") / 100
    local r, g, b   = color.r, color.g, color.b

    local width  = GuiRoot:GetWidth()  * thickness
    local height = GuiRoot:GetHeight() * thickness

    for i = 1, #EDGE_ORDER do
        local key   = EDGE_ORDER[i]
        local strip = V.edges[key]

        strip:SetHidden(not edges[key])

        if key == "top" or key == "bottom" then
            strip:SetHeight(height)
        else
            strip:SetWidth(width)
        end

        local vertices = EDGE_VERTICES[key]
        for j = 1, #vertices.solid do
            strip:SetVertexColors(vertices.solid[j], r, g, b, alpha)
        end
        for j = 1, #vertices.fade do
            strip:SetVertexColors(vertices.fade[j], r, g, b, 0)
        end
    end
end


------------------------------------------------------------
--  VIGNETTE: PLAYBACK
------------------------------------------------------------

local STROBE_UPDATE = "FishingSound_VignetteStrobe"
local WATCH_UPDATE  = "FishingSound_VignetteWatch"


local function stopVignette()
    EVENT_MANAGER:UnregisterForUpdate(STROBE_UPDATE)
    EVENT_MANAGER:UnregisterForUpdate(WATCH_UPDATE)

    if not V.container then return end

    if V.timeline:IsPlaying() then
        V.timeline:Stop()
    end

    V.container:SetAlpha(0)
    V.container:SetHidden(true)
    V.active = false
end


local function playVignette()
    local style  = getVar("vignetteStyle")
    local period = getVar("vignetteSpeed")

    V.container:SetHidden(false)

    if style == "strobe" then
        -- Hard on/off, no easing at all, so drive the alpha directly.
        local lit = true
        V.container:SetAlpha(1)
        EVENT_MANAGER:RegisterForUpdate(STROBE_UPDATE, period / 2, function()
            lit = not lit
            V.container:SetAlpha(lit and 1 or 0)
        end)

    elseif style == "solid" then
        V.container:SetAlpha(0)
        V.animation:SetDuration(period / 2)
        V.animation:SetEasingFunction(ZO_EaseInQuadratic)
        V.timeline:SetPlaybackType(ANIMATION_PLAYBACK_ONE_SHOT, 0)
        V.timeline:PlayFromStart()

    else -- "pulse"
        V.container:SetAlpha(0)
        V.animation:SetDuration(period / 2)
        V.animation:SetEasingFunction(ZO_EaseInOutQuadratic)
        V.timeline:SetPlaybackType(ANIMATION_PLAYBACK_PING_PONG, LOOP_INDEFINITELY)
        V.timeline:PlayFromStart()
    end
end


-- testSeconds > 0 runs the vignette outside of fishing (settings preview):
-- the fishing-interaction check is skipped and it simply times out.
local function startVignette(testSeconds)
    if not getVar("vignetteEnabled") then return end

    buildVignette()
    stopVignette()
    applyVignette()

    playVignette()
    V.active = true

    local now      = GetGameTimeMilliseconds()
    local deadline = now + (testSeconds or getVar("vignetteTimeout")) * 1000
    -- The bite event can land a frame before the interaction is queryable,
    -- so do not trust GetInteractionType() for the first moments.
    local graceUntil = now + 500

    EVENT_MANAGER:RegisterForUpdate(WATCH_UPDATE, 100, function()
        local time = GetGameTimeMilliseconds()

        if time > deadline then
            stopVignette()
            return
        end

        -- Still fishing means the fish is still on the hook. Anything else --
        -- reeled in, interrupted, walked away -- ends the blinking.
        if not testSeconds and time > graceUntil and GetInteractionType() ~= INTERACTION_FISH then
            stopVignette()
        end
    end)
end


FS.StartVignette = startVignette
FS.StopVignette  = stopVignette


------------------------------------------------------------
--  METHODS: BACKEND METHODS
------------------------------------------------------------



local function OnVibration(eventCode, p1, p2, p3, p4, p5)

    --d(string.format("Vibration: %s | %s | %s | %s | %s", p1, p2, p3, p4, p5))

    -- Fishing bite detection
    if p1 == 2500 and p2 > 0 and p3 > 0 then
            --d("Fishing bite detected!")

            if getDisableFishingSound() == false then
                PlaySound(SOUNDS[getReelInSound()])
            end

            startVignette()
    end
end




local function FS_TryInitialize()

        --d("FishingSound: TryInitialize " .. tostring(FS.addonLoaded) .. " " .. tostring(FS.playerLoaded))

        if FS.addonLoaded and FS.playerLoaded then
                --d("FishingSound: Fully initialized, registering fishing event")

                buildVignette()

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

                local styleLabels = {}
                local styleValues = {}
                for i = 1, #FS.vignetteStyles do
                    styleValues[i] = FS.vignetteStyles[i][1]
                    styleLabels[i] = FS.vignetteStyles[i][2]
                end

                -- One checkbox per screen edge, built from the same list the
                -- renderer iterates so the two can never drift apart.
                local edgeLabels = { top = "Top", bottom = "Bottom", left = "Left", right = "Right" }
                local edgeControls = {}
                for i = 1, #EDGE_ORDER do
                    local key = EDGE_ORDER[i]
                    edgeControls[i] = {
                        type = "checkbox",
                        name = edgeLabels[key] .. " Edge",
                        width = "half",
                        getFunc = function() return getVar("vignetteEdges")[key] end,
                        setFunc = function(value)
                            getVar("vignetteEdges")[key] = value
                            applyVignette()
                        end,
                        disabled = function() return not getVar("vignetteEnabled") end,
                    }
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
                        },
                       [4] = {
                                type = "divider"
                        },
                       [5] = {
                                type = "header",
                                name = "Screen Vignette"
                        },
                       [6] = {
                                type = "description",
                                text = "Blinks a coloured glow along the screen edges while a fish is on the hook. It stops by itself the moment you reel in, move away or get interrupted."
                        },
                       [7] = {
                                type = "checkbox",
                                name = "Enable Vignette",
                                tooltip = "Show the screen-edge vignette on a fishing bite.",
                                getFunc = function() return getVar("vignetteEnabled") end,
                                setFunc = function(value)
                                    setVar("vignetteEnabled", value)
                                    if not value then stopVignette() end
                                end
                        },
                       [8] = {
                                type = "colorpicker",
                                name = "Colour",
                                tooltip = "Colour of the vignette.",
                                getFunc = function()
                                    local c = getVar("vignetteColor")
                                    return c.r, c.g, c.b
                                end,
                                setFunc = function(r, g, b)
                                    local c = getVar("vignetteColor")
                                    c.r, c.g, c.b = r, g, b
                                    applyVignette()
                                end,
                                disabled = function() return not getVar("vignetteEnabled") end
                        },
                       [9] = {
                                type = "slider",
                                name = "Opacity",
                                tooltip = "How opaque the vignette gets right at the screen edge.",
                                min = 5, max = 100, step = 5,
                                getFunc = function() return math.floor(getVar("vignetteAlpha") * 100 + 0.5) end,
                                setFunc = function(value)
                                    setVar("vignetteAlpha", value / 100)
                                    applyVignette()
                                end,
                                disabled = function() return not getVar("vignetteEnabled") end
                        },
                      [10] = {
                                type = "slider",
                                name = "Thickness",
                                tooltip = "Depth of the gradient, in percent of the screen.",
                                min = 2, max = 40, step = 1,
                                getFunc = function() return getVar("vignetteSize") end,
                                setFunc = function(value)
                                    setVar("vignetteSize", value)
                                    applyVignette()
                                end,
                                disabled = function() return not getVar("vignetteEnabled") end
                        },
                      [11] = {
                                type = "dropdown",
                                name = "Blink Style",
                                tooltip = "Pulse fades in and out, strobe snaps on and off, solid fades in once and holds until you reel in.",
                                choices = styleLabels,
                                choicesValues = styleValues,
                                getFunc = function() return getVar("vignetteStyle") end,
                                setFunc = function(value) setVar("vignetteStyle", value) end,
                                disabled = function() return not getVar("vignetteEnabled") end
                        },
                      [12] = {
                                type = "slider",
                                name = "Blink Speed",
                                tooltip = "Length of one blink cycle in milliseconds. Ignored by the solid style.",
                                min = 200, max = 2000, step = 50,
                                getFunc = function() return getVar("vignetteSpeed") end,
                                setFunc = function(value) setVar("vignetteSpeed", value) end,
                                disabled = function() return not getVar("vignetteEnabled") end
                        },
                      [13] = {
                                type = "slider",
                                name = "Safety Timeout",
                                tooltip = "Hard stop, in seconds, in case a bite is never resolved.",
                                min = 5, max = 60, step = 5,
                                getFunc = function() return getVar("vignetteTimeout") end,
                                setFunc = function(value) setVar("vignetteTimeout", value) end,
                                disabled = function() return not getVar("vignetteEnabled") end
                        },
                      [14] = {
                                type = "submenu",
                                name = "Active Edges",
                                controls = edgeControls
                        },
                      [15] = {
                                type = "button",
                                name = "Test Vignette",
                                tooltip = "Run the vignette for four seconds with the current settings.",
                                func = function() startVignette(4) end
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
        for key, value in pairs(FS.vignetteDefaults) do
            defaults[key] = value
        end
        savedVariables = ZO_SavedVars:NewAccountWide("FishingSoundVars", 1, nil, defaults)



        FS_TryInitialize()

end


local function OnPlayerActivated()

        -- Also fires after every loading screen, and any bite we were blinking
        -- for is long gone by then.
        stopVignette()

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

EVENT_MANAGER:RegisterForEvent("FishingSound_PlayerDead", EVENT_PLAYER_DEAD, function() stopVignette() end)



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

SLASH_COMMANDS["/fishingvignette"] = function()
    local enabled = not getVar("vignetteEnabled")
    setVar("vignetteEnabled", enabled)
    if not enabled then stopVignette() end
    d("FishingSound: Vignette " .. (enabled and "enabled" or "disabled"))
end

SLASH_COMMANDS["/fishingvignettetest"] = function()
    if not getVar("vignetteEnabled") then
        d("FishingSound: Vignette is disabled, use /fishingvignette to enable it")
        return
    end
    startVignette(4)
end
