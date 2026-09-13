-- Stand-in for the parts of the ESO API, CustomCompassPins and Lost Treasure
-- that LostTreasureDistance touches, so the compass label path can be
-- exercised without launching the client.

--------------------------------------------------------------------------
-- controls
--------------------------------------------------------------------------
CT_LABEL = 6
TOP, BOTTOM = "TOP", "BOTTOM"
TEXT_ALIGN_CENTER, TEXT_ALIGN_TOP = 1, 2

local Control = { }
Control.__index = Control

function Control.New(parent)
	return setmetatable({ parent = parent, hidden = true, anchors = 0, text = "" }, Control)
end

function Control:GetParent() return self.parent end
function Control:SetHorizontalAlignment(value) self.horizontalAlignment = value end
function Control:SetVerticalAlignment(value) self.verticalAlignment = value end
function Control:SetColor(r, g, b, a) self.color = { r, g, b, a } end
function Control:SetFont(font) self.font = font end
function Control:ClearAnchors() self.anchors = 0 end
function Control:SetAnchor(point, relativeTo, relativePoint, offsetX, offsetY)
	self.anchors = self.anchors + 1
	self.anchor = { point, relativeTo, relativePoint, offsetX, offsetY }
end
function Control:SetText(text) self.text = text end
function Control:SetHidden(hidden) self.hidden = hidden end
function Control:IsHidden() return self.hidden end

WINDOW_MANAGER =
{
	CreateControl = function(self, name, parent, controlType)
		return Control.New(parent)
	end,
}

ZO_HIGHLIGHT_TEXT = { UnpackRGBA = function() return 1, 1, 1, 1 end }

--------------------------------------------------------------------------
-- misc API
--------------------------------------------------------------------------
SLASH_COMMANDS = { }

TEST_CHAT = { }
function d(message) TEST_CHAT[#TEST_CHAT + 1] = tostring(message) end
function GetCVar(name) return "ru" end
function zo_round(value) return math.floor(value + 0.5) end
function zo_sqrt(value) return math.sqrt(value) end

TEST_FRAME_TIME = 0
function GetFrameTimeMilliseconds() return TEST_FRAME_TIME end

TEST_MAP_ID = 1
function GetCurrentMapId() return TEST_MAP_ID end

TEST_PLAYER_X, TEST_PLAYER_Y = 0.5, 0.5
function GetMapPlayerPosition(unitTag) return TEST_PLAYER_X, TEST_PLAYER_Y end

EVENT_ADD_ON_LOADED = 65536
EVENT_PLAYER_ACTIVATED = 32769

local registered = { }
EVENT_MANAGER =
{
	RegisterForEvent = function(self, namespace, event, callback)
		registered[namespace .. event] = callback
	end,
	UnregisterForEvent = function(self, namespace, event)
		registered[namespace .. event] = nil
	end,
}

function FireAddOnLoaded(addOnName)
	local callback = registered["LostTreasureDistance" .. EVENT_ADD_ON_LOADED]
	if callback then
		callback(EVENT_ADD_ON_LOADED, addOnName)
	end
end

function FirePlayerActivated()
	local callback = registered["LostTreasureDistance" .. EVENT_PLAYER_ACTIVATED]
	if callback then
		callback(EVENT_PLAYER_ACTIVATED)
	end
	return callback ~= nil
end

ZO_SavedVars =
{
	NewAccountWide = function(self, name, version, namespace, defaults)
		local db = { }
		for key, value in pairs(defaults) do
			db[key] = value
		end
		return db
	end,
}

--------------------------------------------------------------------------
-- LibGPS
--------------------------------------------------------------------------
-- A map whose measurement makes one normalized unit 2000 m across and 1000 m
-- down. The non-zero offsets are deliberate: local (0,0) is not global (0,0),
-- so a scale probe that forgets to subtract the origin gets caught.
TEST_SCALE_X, TEST_SCALE_Y = 0.02, 0.01
TEST_OFFSET_X, TEST_OFFSET_Y = 0.31, 0.42
TEST_GLOBAL_TO_METERS = 100000		-- global distance 1.0 = the whole world
TEST_HAS_MEASUREMENT = true
TEST_IS_MEASURING = false
TEST_GPS_CALLS = 0

LibGPS3 =
{
	IsMeasuring = function(self) return TEST_IS_MEASURING end,
	LocalToGlobal = function(self, x, y)
		TEST_GPS_CALLS = TEST_GPS_CALLS + 1
		if not TEST_HAS_MEASUREMENT then
			return nil
		end
		return x * TEST_SCALE_X + TEST_OFFSET_X, y * TEST_SCALE_Y + TEST_OFFSET_Y
	end,
	GetGlobalDistanceInMeters = function(self, x1, y1, x2, y2)
		TEST_GPS_CALLS = TEST_GPS_CALLS + 1
		local dx, dy = x1 - x2, y1 - y2
		return math.sqrt(dx * dx + dy * dy) * TEST_GLOBAL_TO_METERS
	end,
	-- The real one is broken (it square-roots the scale factors that
	-- Measurement:ToWorld multiplies), so the addon must never call it.
	GetLocalDistanceInMeters = function()
		error("GetLocalDistanceInMeters is inaccurate and must not be used")
	end,
}

--------------------------------------------------------------------------
-- CustomCompassPins / Lost Treasure
--------------------------------------------------------------------------
COMPASS_PINS = { pinLayouts = { }, pinManager = { pinData = { } } }

LOST_TREASURE = { }
LOST_TREASURE_PIN_TYPE_DATA =
{
	treasure = { pinName = "LostTreasure_TreasureMapPin" },
	survey = { pinName = "LostTreasure_SurveyReportPin" },
	clue = { pinName = "LostTreasure_TributeCluePin" },
}

-- Records that the original Lost Treasure callbacks still run after wrapping.
TEST_ORIGINAL_UPDATE_CALLS = 0
TEST_ORIGINAL_RESET_CALLS = 0

for _, pinTypeData in pairs(LOST_TREASURE_PIN_TYPE_DATA) do
	COMPASS_PINS.pinLayouts[pinTypeData.pinName] =
	{
		maxDistance = 0.05,
		additionalLayout =
		{
			[1] = function() TEST_ORIGINAL_UPDATE_CALLS = TEST_ORIGINAL_UPDATE_CALLS + 1 end,
			[2] = function() TEST_ORIGINAL_RESET_CALLS = TEST_ORIGINAL_RESET_CALLS + 1 end,
		},
	}
end

-- Mimics CompassPinManager:GetNewPin(): a pooled ZO_MapPin control.
function NewCompassPin(xLoc, yLoc)
	local pin = Control.New(nil)
	pin.xLoc = xLoc
	pin.yLoc = yLoc
	return pin
end

--------------------------------------------------------------------------
-- LibAddonMenu
--------------------------------------------------------------------------
TEST_PANEL_OPTIONS = nil

LibAddonMenu2 =
{
	RegisterAddonPanel = function(self, name, data) end,
	RegisterOptionControls = function(self, name, options) TEST_PANEL_OPTIONS = options end,
}
