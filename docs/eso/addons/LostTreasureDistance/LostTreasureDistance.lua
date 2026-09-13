-- Lost Treasure Distance
-- Adds a distance label under every Lost Treasure compass pin.
--
-- It does not fork Lost Treasure: the compass pin layouts registered by
-- LOST_TREASURE in int/Pins.lua are wrapped, so the original behaviour
-- (the pin name in the compass center label) keeps working.

local ADDON_NAME = "LostTreasureDistance"
local SAVED_VARS_NAME = "LostTreasureDistance_SavedVars"
local SAVED_VARS_VERSION = 1

local LTD = { }
LOST_TREASURE_DISTANCE = LTD

local wm = WINDOW_MANAGER
local LibGPS = LibGPS3

local UPDATE_INTERVAL_MS = 200

local defaults =
{
	enabled = true,
	fontSize = 15,
	offsetY = 2,
}

local UNITS =
{
	en = { meter = "m", kilometer = "km" },
	de = { meter = "m", kilometer = "km" },
	fr = { meter = "m", kilometer = "km" },
	es = { meter = "m", kilometer = "km" },
	ru = { meter = "м", kilometer = "км" },
	jp = { meter = "m", kilometer = "km" },
	zh = { meter = "m", kilometer = "km" },
}
local units = UNITS[GetCVar("language.2")] or UNITS.en

local db
local labels = { }		-- every label control we created, to restyle them on settings change

---------------------------------------------------------------------------
-- Map scale
---------------------------------------------------------------------------
-- Two probes along the unit square give us the meters per normalized map unit
-- on each axis, which is all the per-pin math needs. Caching them per map keeps
-- the library (which may trigger a map measurement) out of the compass
-- OnUpdate handler.
--
-- LibGPS' GetLocalDistanceInMeters() is deliberately NOT used: it computes
-- sqrt(dx^2 * scaleX * worldSizeX + ...), taking the square root of the very
-- factors that Measurement:ToWorld() multiplies to reach world coordinates. It
-- therefore reports distances off by a factor of sqrt(scaleX * worldSizeX) - in
-- Auridon-sized zones roughly twice too much. The global variant matches
-- ToWorld, so we convert to global coordinates first.
local scaleCache = { }

local function GetCurrentMapScale()
	local mapId = GetCurrentMapId()
	local cached = scaleCache[mapId]
	if cached then
		return cached[1], cached[2]
	end

	if not LibGPS or LibGPS:IsMeasuring() then
		return nil
	end

	local originX, originY = LibGPS:LocalToGlobal(0, 0)
	if not originX then
		return nil		-- no measurement available (yet), retry on the next update
	end
	local unitXGlobalX, unitXGlobalY = LibGPS:LocalToGlobal(1, 0)
	local unitYGlobalX, unitYGlobalY = LibGPS:LocalToGlobal(0, 1)

	local metersPerUnitX = LibGPS:GetGlobalDistanceInMeters(originX, originY, unitXGlobalX, unitXGlobalY)
	local metersPerUnitY = LibGPS:GetGlobalDistanceInMeters(originX, originY, unitYGlobalX, unitYGlobalY)
	if metersPerUnitX == 0 or metersPerUnitY == 0 then
		return nil
	end

	scaleCache[mapId] = { metersPerUnitX, metersPerUnitY }
	return metersPerUnitX, metersPerUnitY
end

---------------------------------------------------------------------------
-- Player position (cached per frame, the compass updates every pin in one go)
---------------------------------------------------------------------------
local lastPositionFrame, playerX, playerY = 0, 0, 0

local function GetPlayerPosition()
	local now = GetFrameTimeMilliseconds()
	if now ~= lastPositionFrame then
		lastPositionFrame = now
		playerX, playerY = GetMapPlayerPosition("player")
	end
	return playerX, playerY
end

---------------------------------------------------------------------------
-- Labels
---------------------------------------------------------------------------
local function GetFontString()
	return string.format("$(MEDIUM_FONT)|%d|soft-shadow-thick", db.fontSize)
end

local function ApplyLabelStyle(label)
	label:SetFont(GetFontString())
	label:ClearAnchors()
	label:SetAnchor(TOP, label:GetParent(), BOTTOM, 0, db.offsetY)
end

local function GetOrCreateLabel(pin)
	local label = pin.ltdDistanceLabel
	if not label then
		label = wm:CreateControl(nil, pin, CT_LABEL)
		label:SetHorizontalAlignment(TEXT_ALIGN_CENTER)
		label:SetVerticalAlignment(TEXT_ALIGN_TOP)
		label:SetColor(ZO_HIGHLIGHT_TEXT:UnpackRGBA())
		pin.ltdDistanceLabel = label
		labels[#labels + 1] = label
		ApplyLabelStyle(label)
	end
	return label
end

local function RefreshAllLabels()
	for _, label in ipairs(labels) do
		ApplyLabelStyle(label)
		if not db.enabled then
			label:SetHidden(true)
		end
	end
end

local function FormatDistance(meters)
	if meters >= 1000 then
		return string.format("%.1f %s", meters / 1000, units.kilometer)
	end
	return string.format("%d %s", zo_round(meters), units.meter)
end

---------------------------------------------------------------------------
-- Compass pin callbacks
---------------------------------------------------------------------------
local function HideLabel(pin)
	local label = pin.ltdDistanceLabel
	if label then
		label:SetHidden(true)
	end
end

-- Called by CustomCompassPins for Lost Treasure pins only, roughly every 20 ms.
local function UpdateDistance(pin)
	if not db.enabled then
		HideLabel(pin)
		return
	end

	local now = GetFrameTimeMilliseconds()
	if pin.ltdNextUpdate and now < pin.ltdNextUpdate then
		return
	end
	pin.ltdNextUpdate = now + UPDATE_INTERVAL_MS

	local metersPerUnitX, metersPerUnitY = GetCurrentMapScale()
	if not metersPerUnitX then
		HideLabel(pin)
		return
	end

	local px, py = GetPlayerPosition()
	local dx = (px - pin.xLoc) * metersPerUnitX
	local dy = (py - pin.yLoc) * metersPerUnitY

	local label = GetOrCreateLabel(pin)
	label:SetText(FormatDistance(zo_sqrt(dx * dx + dy * dy)))
	label:SetHidden(false)
end

-- Careful: CustomCompassPins runs the reset function of *every* registered
-- layout on *every* pin it hands out, because the control pool is shared with
-- all other compass addons. So this has to clean up unconditionally, otherwise
-- a treasure distance stays glued to a skyshard pin.
local function ResetDistance(pin)
	HideLabel(pin)
	pin.ltdNextUpdate = nil
end

local function WrapLayout(pinName)
	local layout = COMPASS_PINS.pinLayouts[pinName]
	if not layout then
		return false
	end

	local additionalLayout = layout.additionalLayout
	local originalUpdate = additionalLayout and (additionalLayout.update or additionalLayout[1])
	local originalReset = additionalLayout and (additionalLayout.reset or additionalLayout[2])

	local function update(...)
		if originalUpdate then
			originalUpdate(...)
		end
		UpdateDistance(...)
	end

	local function reset(...)
		if originalReset then
			originalReset(...)
		end
		ResetDistance(...)
	end

	-- named keys are preferred by CustomCompassPins, the numeric ones are the
	-- legacy fallback - set both so we do not depend on the library version
	layout.additionalLayout =
	{
		update = update,
		reset = reset,
		[1] = update,
		[2] = reset,
	}

	return true
end

local hookedPinNames = { }

local function HookCompassPins()
	if not (LOST_TREASURE and LOST_TREASURE_PIN_TYPE_DATA and COMPASS_PINS) then
		return false
	end

	local hooked = 0
	for _, pinTypeData in pairs(LOST_TREASURE_PIN_TYPE_DATA) do
		if WrapLayout(pinTypeData.pinName) then
			hookedPinNames[pinTypeData.pinName] = true
			hooked = hooked + 1
		end
	end
	return hooked > 0
end

---------------------------------------------------------------------------
-- /ltdistance - list every Lost Treasure pin on the current map with its
-- distance, to sanity check the numbers against a landmark in game.
---------------------------------------------------------------------------
local function PrintDistances()
	local metersPerUnitX, metersPerUnitY = GetCurrentMapScale()
	if not metersPerUnitX then
		d("[Lost Treasure Distance] no LibGPS measurement for this map yet")
		return
	end

	d(string.format("[Lost Treasure Distance] map %d: one map unit is %.0f m across, %.0f m down",
		GetCurrentMapId(), metersPerUnitX, metersPerUnitY))

	local px, py = GetMapPlayerPosition("player")
	local found = 0
	for _, pinData in pairs(COMPASS_PINS.pinManager.pinData) do
		if hookedPinNames[pinData.pinType] then
			found = found + 1
			local dx = (px - pinData.xLoc) * metersPerUnitX
			local dy = (py - pinData.yLoc) * metersPerUnitY
			d(string.format("  %s (%.2f x %.2f): %s", pinData.pinName or pinData.pinType,
				pinData.xLoc * 100, pinData.yLoc * 100, FormatDistance(zo_sqrt(dx * dx + dy * dy))))
		end
	end

	if found == 0 then
		d("  no Lost Treasure compass pins on this map")
	end
end

---------------------------------------------------------------------------
-- Settings
---------------------------------------------------------------------------
local function CreateSettingsPanel()
	local LAM = LibAddonMenu2
	if not LAM then
		return
	end

	LAM:RegisterAddonPanel(ADDON_NAME .. "Panel",
	{
		type = "panel",
		name = "Lost Treasure Distance",
		displayName = "Lost Treasure Distance",
		author = "yelowhut",
		version = "1.0.1",
		registerForRefresh = true,
		registerForDefaults = true,
	})

	LAM:RegisterOptionControls(ADDON_NAME .. "Panel",
	{
		{
			type = "checkbox",
			name = "Show distance on compass pins",
			tooltip = "Shows the distance from you to every Lost Treasure compass pin.",
			getFunc = function() return db.enabled end,
			setFunc = function(value)
				db.enabled = value
				RefreshAllLabels()
			end,
			default = defaults.enabled,
		},
		{
			type = "slider",
			name = "Font size",
			min = 10,
			max = 28,
			step = 1,
			getFunc = function() return db.fontSize end,
			setFunc = function(value)
				db.fontSize = value
				RefreshAllLabels()
			end,
			default = defaults.fontSize,
		},
		{
			type = "slider",
			name = "Vertical offset",
			tooltip = "Distance between the compass icon and the label.",
			min = -20,
			max = 40,
			step = 1,
			getFunc = function() return db.offsetY end,
			setFunc = function(value)
				db.offsetY = value
				RefreshAllLabels()
			end,
			default = defaults.offsetY,
		},
	})
end

---------------------------------------------------------------------------
-- Init
---------------------------------------------------------------------------
local function OnAddOnLoaded(_, addOnName)
	if addOnName ~= ADDON_NAME then
		return
	end
	EVENT_MANAGER:UnregisterForEvent(ADDON_NAME, EVENT_ADD_ON_LOADED)

	db = ZO_SavedVars:NewAccountWide(SAVED_VARS_NAME, SAVED_VARS_VERSION, nil, defaults)
	LTD.db = db
	SLASH_COMMANDS["/ltdistance"] = PrintDistances

	if HookCompassPins() then
		CreateSettingsPanel()
		return
	end

	-- Lost Treasure registers its compass pins from its own EVENT_ADD_ON_LOADED
	-- handler, which DependsOn puts ahead of ours, so we should never get here.
	-- Retry once after the load screen in case that order ever changes.
	EVENT_MANAGER:RegisterForEvent(ADDON_NAME, EVENT_PLAYER_ACTIVATED, function()
		EVENT_MANAGER:UnregisterForEvent(ADDON_NAME, EVENT_PLAYER_ACTIVATED)
		if HookCompassPins() then
			CreateSettingsPanel()
		else
			d("[Lost Treasure Distance] no Lost Treasure compass pins found, the addon stays idle.")
		end
	end)
end

EVENT_MANAGER:RegisterForEvent(ADDON_NAME, EVENT_ADD_ON_LOADED, OnAddOnLoaded)
