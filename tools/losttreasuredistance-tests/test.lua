-- Smoke test for LostTreasureDistance.
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

loadFile("LostTreasureDistance.lua")
FireAddOnLoaded("LostTreasureDistance")

local layout = COMPASS_PINS.pinLayouts["LostTreasure_TreasureMapPin"]
local update = layout.additionalLayout.update
local reset = layout.additionalLayout.reset

check("update callback installed", type(update), "function")
check("reset callback installed", type(reset), "function")
check("legacy numeric keys kept", layout.additionalLayout[1], update)
check("settings panel registered", type(TEST_PANEL_OPTIONS), "table")

-- ------------------------------------------------------- distance and label
-- 0.01 units right of the player at 2000 m per unit, 0.02 down at 1000 m per
-- unit: sqrt(20^2 + 20^2) = 28.28 m.
TEST_PLAYER_X, TEST_PLAYER_Y = 0.50, 0.50
local pin = NewCompassPin(0.51, 0.52)

TEST_FRAME_TIME = 1000
update(pin, 0, 0, 0.2)

check("original update still runs", TEST_ORIGINAL_UPDATE_CALLS, 1)
check("label created", type(pin.ltdDistanceLabel), "table")
check("label visible", pin.ltdDistanceLabel:IsHidden(), false)
check("distance text", pin.ltdDistanceLabel.text, "28 м")
check("label anchored below the pin", pin.ltdDistanceLabel.anchor[3], BOTTOM)
check("label parented to the pin", pin.ltdDistanceLabel:GetParent(), pin)

-- The map scale is probed once per map and then cached, so the compass
-- OnUpdate handler never re-enters LibGPS.
local callsAfterFirstUpdate = TEST_GPS_CALLS
check("map scale probed once per map", callsAfterFirstUpdate, 5)

-- ------------------------------------------------------------- throttling
TEST_PLAYER_X = 0.40
TEST_FRAME_TIME = 1100
update(pin, 0, 0, 0.2)
check("text throttled within 200 ms", pin.ltdDistanceLabel.text, "28 м")

TEST_FRAME_TIME = 1300
update(pin, 0, 0, 0.2)
-- sqrt((0.11 * 2000)^2 + (0.02 * 1000)^2) = 220.9 m
check("text refreshed after 200 ms", pin.ltdDistanceLabel.text, "221 м")
check("map scale stayed cached", TEST_GPS_CALLS, callsAfterFirstUpdate)

-- ----------------------------------------------------------------- reset
-- The pin pool is shared with every other compass addon, so reset has to clean
-- up any pin it is handed, including ones that never carried a label.
reset(pin)
check("original reset still runs", TEST_ORIGINAL_RESET_CALLS, 1)
check("label hidden on reset", pin.ltdDistanceLabel:IsHidden(), true)
check("throttle cleared on reset", pin.ltdNextUpdate, nil)

local foreignPin = NewCompassPin(0.1, 0.1)
local ok, err = pcall(reset, foreignPin)
check("reset survives a foreign pin", ok, true)
if not ok then
	print("      " .. tostring(err))
end

-- --------------------------------------------------- no LibGPS measurement
TEST_MAP_ID = 2			-- an unmeasured map, so the scale cache misses
TEST_IS_MEASURING = true
TEST_FRAME_TIME = 2000
update(pin, 0, 0, 0.2)
check("label hidden while measuring", pin.ltdDistanceLabel:IsHidden(), true)

TEST_IS_MEASURING = false
TEST_HAS_MEASUREMENT = false		-- LocalToGlobal returns nil without a measurement
TEST_FRAME_TIME = 3000
update(pin, 0, 0, 0.2)
check("label hidden without measurement", pin.ltdDistanceLabel:IsHidden(), true)
TEST_HAS_MEASUREMENT = true

-- ----------------------------------------------------------- kilometres
TEST_MAP_ID = 3
TEST_SCALE_X, TEST_SCALE_Y = 1, 1		-- 100 km per normalized unit
TEST_PLAYER_X, TEST_PLAYER_Y = 0.50, 0.50
TEST_FRAME_TIME = 4000
update(pin, 0, 0, 0.2)
check("kilometres above 1000 m", pin.ltdDistanceLabel.text, "2.2 км")

-- ------------------------------------------------------------ the toggle
local enabledOption
for _, option in ipairs(TEST_PANEL_OPTIONS) do
	if option.type == "checkbox" then
		enabledOption = option
	end
end

enabledOption.setFunc(false)
TEST_FRAME_TIME = 5000
update(pin, 0, 0, 0.2)
check("label hidden when disabled", pin.ltdDistanceLabel:IsHidden(), true)

enabledOption.setFunc(true)
TEST_FRAME_TIME = 6000
update(pin, 0, 0, 0.2)
check("label back when re-enabled", pin.ltdDistanceLabel:IsHidden(), false)

-- ---------------------------------------------------------- /ltdistance
-- Map 1 was measured at 2000 x 1000 m per unit at the top of the test and is
-- still cached, so the treasure pin is the same 28 m as above.
TEST_MAP_ID = 1
TEST_PLAYER_X, TEST_PLAYER_Y = 0.50, 0.50
COMPASS_PINS.pinManager.pinData =
{
	treasureTag = { pinType = "LostTreasure_TreasureMapPin", pinName = "Auridon Treasure Map I", xLoc = 0.51, yLoc = 0.52 },
	skyshardTag = { pinType = "SkyShards", pinName = "Skyshard", xLoc = 0.60, yLoc = 0.60 },
}

TEST_CHAT = { }
SLASH_COMMANDS["/ltdistance"]()
check("slash command skips foreign pins", #TEST_CHAT, 2)
check("slash command prints the distance", TEST_CHAT[2]:match("28 м") ~= nil, true)

-- ------------------------------------------- late registration fallback
-- DependsOn should always put Lost Treasure first, but if its compass pins are
-- not there yet we retry once after the load screen instead of staying idle.
COMPASS_PINS.pinLayouts = { }
loadFile("LostTreasureDistance.lua")
FireAddOnLoaded("LostTreasureDistance")
check("nothing hooked without pin layouts", COMPASS_PINS.pinLayouts["LostTreasure_TreasureMapPin"], nil)

COMPASS_PINS.pinLayouts["LostTreasure_TreasureMapPin"] = { maxDistance = 0.05 }
check("retry armed", FirePlayerActivated(), true)
local lateLayout = COMPASS_PINS.pinLayouts["LostTreasure_TreasureMapPin"].additionalLayout
check("hooked on player activated", type(lateLayout and lateLayout.update), "function")

print(string.format("\n%d checks, %d failures", checks, failures))
if failures > 0 then
	error(string.format("%d failing checks", failures))
end
