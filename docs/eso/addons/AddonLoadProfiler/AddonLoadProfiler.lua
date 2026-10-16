-- Addon Load Profiler
-- Shows how much time every enabled addon costs while the character loads.
--
-- No script profiler: profiling a whole load made it 6x slower and got the
-- character disconnected (2026-09-29). Instead two cheap measurements:
--
-- 1. Handlers. EVENT_MANAGER's RegisterForEvent/RegisterForUpdate are wrapped
--    on the EVENT_MANAGER object itself, so every handler registered
--    after this file ran is timed with GetGameTimeMilliseconds (it advances
--    inside a frame, unlike the frame clock). The owner is taken from the
--    call stack at registration time, or guessed from the namespace.
--
-- 2. Gaps. The game runs all addon files first and then fires every
--    EVENT_ADD_ON_LOADED in one burst. Our own handler sees each of those
--    events; the time between two of them that no wrapped handler accounts
--    for is charged to the addon the later event is for: the game loading
--    its saved variables right before the event, plus its own handler if the
--    addon loaded before us (its registration could not be wrapped).

local ADDON_NAME = "AddonLoadProfiler"
local SAVED_VARS_NAME = "AddonLoadProfiler_SV"

local ALP = { name = ADDON_NAME }
ADDON_LOAD_PROFILER = ALP

local clock = GetGameTimeMilliseconds
local fileTime = clock()

local MAX_RUNS = 5
local DEFAULT_SETTLE_MS = 5000

-- statistics columns
local PRE = 1		-- gap before the addon's EVENT_ADD_ON_LOADED
local INIT = 2		-- wrapped handlers before EVENT_PLAYER_ACTIVATED
local AFTER = 3		-- wrapped handlers in the settle window after it

local BUCKET_ESO = "[ESO UI]"					-- the game's own UI modules (ZO_Ingame...)
local BUCKET_FILES = "[files after ALP]"		-- addon files that ran after this one
local BUCKET_WORLD = "[engine / world]"			-- after the burst until the character appears
ALP.BUCKET_ESO = BUCKET_ESO

local defaults =
{
	settleMs = DEFAULT_SETTLE_MS,
	runs = { },		-- newest first
}

local sv

local function Print(text, ...)
	d("|c88ccff[ALP]|r " .. string.format(text, ...))
end

---------------------------------------------------------------------------
-- Enabled addons and ownership
---------------------------------------------------------------------------
local addonInfo = { }			-- name -> { title, isLibrary }
local ownerByRoot = { }			-- "harvestmapdata/modules/harvestad/" -> addon name
local addonNames = { }			-- for namespace guessing, longest first

local function NormalizePath(path)
	return ((path or ""):lower():gsub("\\", "/"):gsub("^@", ""))
end

local function StripColors(text)
	return (text:gsub("|[cC]%x%x%x%x%x%x", ""):gsub("|[rR]", ""))
end

do
	local manager = GetAddOnManager()
	for i = 1, manager:GetNumAddOns() do
		local name, title, _, _, enabled, state, _, isLibrary = manager:GetAddOnInfo(i)
		if enabled and state == ADDON_STATE_ENABLED then
			addonInfo[name] = { title = StripColors(title ~= "" and title or name), isLibrary = isLibrary }
			addonNames[#addonNames + 1] = name
			local root = NormalizePath(manager:GetAddOnRootDirectoryPath(i)):match("addons/(.*)$")
			if root then
				if root:sub(-1) ~= "/" then root = root .. "/" end
				ownerByRoot[root] = name
			end
		end
	end
	table.sort(addonNames, function(a, b) return #a > #b end)
end

-- The longest addon root folder the path starts with, so nested addons
-- (HarvestMapData/Modules/...) win over their container and libs embedded in
-- an addon's folder count for that addon.
local function OwnerOfFile(path)
	local rel = NormalizePath(path):match("addons/(.*)$")
	if not rel then return nil end
	local owner
	local pos = 1
	while true do
		local slash = rel:find("/", pos, true)
		if not slash then break end
		owner = ownerByRoot[rel:sub(1, slash)] or owner
		pos = slash + 1
	end
	return owner
end

local function OwnerOfNamespace(namespace)
	if type(namespace) ~= "string" then return "[?]" end
	local lower = namespace:lower()
	for _, name in ipairs(addonNames) do
		local candidate = name:lower()
		if lower == candidate or (#candidate >= 4 and lower:sub(1, #candidate) == candidate) then
			return name
		end
	end
	return "[ns] " .. namespace
end

local traceback = type(debug) == "table" and debug.traceback
local ownerSources = { stack = 0, namespace = 0 }

-- The first addon frame on the stack that is not ours. The game's own frames
-- (zo_callLater and the like) are skipped on the way.
local function CallerOwner(namespace)
	if traceback then
		local ok, stack = pcall(traceback)
		if ok and type(stack) == "string" then
			for path in stack:gmatch("[Aa]dd[Oo]ns/[^:\n]+") do
				local owner = OwnerOfFile(path)
				if owner and owner ~= ADDON_NAME then
					ownerSources.stack = ownerSources.stack + 1
					return owner
				end
			end
		end
	end
	ownerSources.namespace = ownerSources.namespace + 1
	return OwnerOfNamespace(namespace)
end

---------------------------------------------------------------------------
-- Measurement state
---------------------------------------------------------------------------
local measuring = true
local column = INIT
local wrappedTotal = 0		-- all wrapped handler time so far, for the gaps
local stats = { }			-- owner -> { pre, init, after, calls = n }
local earlyAddons = { }		-- addons loaded before us: handlers not wrapped
local handlerOrder = { fifo = 0, lifo = 0 }
local currentEvent			-- the EVENT_ADD_ON_LOADED name our handler saw last

local function Charge(owner, target, ms)
	local entry = stats[owner]
	if not entry then
		entry = { 0, 0, 0, calls = 0 }
		stats[owner] = entry
	end
	entry[target] = entry[target] + ms
	return entry
end

local function Finish(owner, start, ...)
	local ms = clock() - start
	wrappedTotal = wrappedTotal + ms
	local entry = Charge(owner, column, ms)
	entry.calls = entry.calls + 1
	return ...
end

-- If the callback errors, Finish is skipped and nothing is left half-done.
local function Wrap(owner, callback)
	return function(...)
		if not measuring then
			return callback(...)
		end
		return Finish(owner, clock(), callback(...))
	end
end

-- EVENT_ADD_ON_LOADED handlers also tell us in which order the game calls
-- handlers: an addon handling its own event after our handler saw that event
-- means registration order (what the gap attribution assumes).
local function WrapAddOnLoaded(owner, callback)
	local timed = Wrap(owner, callback)
	return function(event, name, ...)
		if measuring and name == owner then
			if currentEvent == name then
				handlerOrder.fifo = handlerOrder.fifo + 1
			else
				handlerOrder.lifo = handlerOrder.lifo + 1
			end
		end
		return timed(event, name, ...)
	end
end

---------------------------------------------------------------------------
-- Hooks
---------------------------------------------------------------------------
local originalRegisterForEvent = EVENT_MANAGER.RegisterForEvent
local originalRegisterForUpdate = EVENT_MANAGER.RegisterForUpdate
local hooked = false

-- The wrappers go on the EVENT_MANAGER object itself (GetEventManager()
-- returns the same object), not into the metatable the engine shares for the
-- class: the least invasive place that still catches every addon.
do
	local function HookedRegisterForEvent(self, namespace, event, callback, ...)
		if measuring and type(callback) == "function" then
			local owner = CallerOwner(namespace)
			if event == EVENT_ADD_ON_LOADED then
				callback = WrapAddOnLoaded(owner, callback)
			else
				callback = Wrap(owner, callback)
			end
		end
		return originalRegisterForEvent(self, namespace, event, callback, ...)
	end

	local function HookedRegisterForUpdate(self, namespace, interval, callback, ...)
		if measuring and type(callback) == "function" then
			callback = Wrap(CallerOwner(namespace), callback)
		end
		return originalRegisterForUpdate(self, namespace, interval, callback, ...)
	end

	local ok = pcall(function()
		EVENT_MANAGER.RegisterForEvent = HookedRegisterForEvent
		EVENT_MANAGER.RegisterForUpdate = HookedRegisterForUpdate
	end)
	-- only count it as hooked when the object really hands out our functions;
	-- otherwise measure the gaps alone rather than dig into the metatable
	hooked = ok and EVENT_MANAGER.RegisterForEvent == HookedRegisterForEvent
		and EVENT_MANAGER.RegisterForUpdate == HookedRegisterForUpdate
		and GetEventManager().RegisterForEvent == HookedRegisterForEvent
end

---------------------------------------------------------------------------
-- Gaps between EVENT_ADD_ON_LOADED events
---------------------------------------------------------------------------
local firstEventTime, lastEventTime, lastWrapped
local userAddonEvents, ownPosition = 0, nil

local function OnAnyAddOnLoaded(_, name)
	if not measuring then return end
	local now = clock()
	local owner = addonInfo[name] and name or BUCKET_ESO
	if not lastEventTime then
		-- the files of every addon loaded after us, and the game's work before
		-- the first event: cannot be split
		firstEventTime = now
		Charge(BUCKET_FILES, PRE, now - fileTime)
	else
		local gap = (now - lastEventTime) - (wrappedTotal - lastWrapped)
		Charge(owner, PRE, math.max(0, gap))
	end
	lastEventTime = now
	lastWrapped = wrappedTotal
	currentEvent = name

	if addonInfo[name] then
		userAddonEvents = userAddonEvents + 1
		if name == ADDON_NAME then
			ownPosition = userAddonEvents
		elseif not ownPosition then
			earlyAddons[name] = true
		end
	end
end

originalRegisterForEvent(EVENT_MANAGER, ADDON_NAME .. "Gaps", EVENT_ADD_ON_LOADED, OnAnyAddOnLoaded)

---------------------------------------------------------------------------
-- Results
---------------------------------------------------------------------------
local reloadedUI = false
local activatedTime

local function Round(ms)
	return math.floor(ms * 10 + 0.5) / 10
end

local function SaveRun()
	measuring = false
	EVENT_MANAGER:UnregisterForEvent(ADDON_NAME .. "Gaps", EVENT_ADD_ON_LOADED)

	local burstStart = firstEventTime or activatedTime
	local burstEnd = lastEventTime or activatedTime
	local run =
	{
		time = GetTimeStamp(),
		character = GetUnitName("player"),
		reload = reloadedUI,
		position = ownPosition,
		numAddons = userAddonEvents,
		wall =
		{
			files = Round(burstStart - fileTime),
			burst = Round(burstEnd - burstStart),
			world = Round(activatedTime - burstEnd),
			after = Round(sv.settleMs),
		},
		order = { fifo = handlerOrder.fifo, lifo = handlerOrder.lifo },
		owners = { stack = ownerSources.stack, namespace = ownerSources.namespace },
		addons = { },
	}

	for owner, entry in pairs(stats) do
		local info = addonInfo[owner]
		run.addons[owner] =
		{
			p = Round(entry[PRE]),
			i = Round(entry[INIT]),
			a = Round(entry[AFTER]),
			c = entry.calls,
			lib = info and info.isLibrary or nil,
			t = info and info.title ~= owner and info.title or nil,
			early = earlyAddons[owner] or nil,
		}
	end
	-- enabled addons that cost nothing measurable still belong in the list
	for name, info in pairs(addonInfo) do
		if not run.addons[name] then
			run.addons[name] = { p = 0, i = 0, a = 0, c = 0, lib = info.isLibrary or nil,
				t = info.title ~= name and info.title or nil, early = earlyAddons[name] or nil }
		end
	end

	table.insert(sv.runs, 1, run)
	while #sv.runs > MAX_RUNS do
		table.remove(sv.runs)
	end

	Print("Load measured (ALP loaded %s of %d addons). /alp for the table.", tostring(ownPosition or "?"), userAddonEvents)
	ALP.PrintTop(5, 1)
	ALP.RefreshWindow()
end

---------------------------------------------------------------------------
-- Aggregation for display
---------------------------------------------------------------------------
function ALP.GetRuns()
	return sv and sv.runs or { }
end

-- viewIndex 0 averages all stored runs, otherwise it picks runs[viewIndex].
-- Returns the rows (unsorted), the selected runs and the sum of all totals.
function ALP.BuildRows(viewIndex)
	local runs = ALP.GetRuns()
	local selected = viewIndex == 0 and runs or { runs[viewIndex] }
	local rows, byName = { }, { }
	for _, run in ipairs(selected) do
		for name, a in pairs(run.addons) do
			local row = byName[name]
			if not row then
				row = { name = name, title = a.t or name, lib = a.lib, pre = 0, init = 0, after = 0, calls = 0, early = 0 }
				byName[name] = row
				rows[#rows + 1] = row
			end
			row.pre = row.pre + math.max(0, a.p)
			row.init = row.init + math.max(0, a.i)
			row.after = row.after + math.max(0, a.a)
			row.calls = row.calls + a.c
			if a.early then row.early = row.early + 1 end
		end
	end

	local count = math.max(1, #selected)
	local grand = 0
	for _, row in ipairs(rows) do
		row.pre = row.pre / count
		row.init = row.init / count
		row.after = row.after / count
		row.calls = row.calls / count
		row.total = row.pre + row.init + row.after
		grand = grand + row.total
	end
	for _, row in ipairs(rows) do
		row.share = grand > 0 and row.total / grand or 0
	end
	return rows, selected, grand
end

function ALP.PrintTop(count, viewIndex)
	local rows, selected = ALP.BuildRows(viewIndex or 0)
	if #selected == 0 then
		Print("No measured loads yet - relog or /reloadui.")
		return
	end
	table.sort(rows, function(a, b) return a.total > b.total end)
	Print("Top %d of %s:", count, viewIndex == 1 and "the last load" or string.format("%d load(s), averaged", #selected))
	for i = 1, math.min(count, #rows) do
		local row = rows[i]
		d(string.format("  %d. %s - %.0f ms (%.0f%%): pre-event %.0f, init %.0f, after %.0f",
			i, row.title, row.total, row.share * 100, row.pre, row.init, row.after))
	end
end

function ALP.GetStatus()
	if not hooked then
		return "EVENT_MANAGER could not be hooked - only the gaps are measured"
	elseif measuring then
		return "measuring this load"
	end
	return "idle until the next load (measures every relog and /reloadui)"
end

---------------------------------------------------------------------------
-- Slash command
---------------------------------------------------------------------------
local function PrintHelp()
	Print("/alp - show the results window")
	d("  /alp top [n] - print the heaviest addons (average of stored loads)")
	d("  /alp settle <sec> - how long to keep measuring after the character appears (now " .. sv.settleMs / 1000 .. "s)")
	d("  /alp clear - forget stored loads")
	d("  /alp status - state and diagnostics")
end

local function OnSlashCommand(args)
	local command, argument = args:match("^%s*(%S*)%s*(.-)%s*$")
	command = command:lower()
	if command == "" or command == "show" then
		ALP.ToggleWindow()
	elseif command == "top" then
		ALP.PrintTop(tonumber(argument) or 10)
	elseif command == "settle" then
		local seconds = tonumber(argument)
		if seconds then
			sv.settleMs = zo_clamp(seconds, 0, 60) * 1000
		end
		Print("Settle window: %.0fs (applies from the next load).", sv.settleMs / 1000)
	elseif command == "clear" then
		sv.runs = { }
		ALP.RefreshWindow()
		Print("Stored loads cleared.")
	elseif command == "status" then
		Print(ALP.GetStatus())
		local run = sv.runs[1]
		if run then
			d(string.format("  last load: ALP loaded %s of %d; handler owners from stack %d, from namespace %d",
				tostring(run.position or "?"), run.numAddons, run.owners.stack, run.owners.namespace))
			d(string.format("  handler order check: registration order %d, reverse %d (gap attribution assumes registration order)",
				run.order.fifo, run.order.lifo))
		end
	else
		PrintHelp()
	end
end

---------------------------------------------------------------------------
-- Startup
---------------------------------------------------------------------------
local function OnPlayerActivated(_, initial)
	EVENT_MANAGER:UnregisterForEvent(ADDON_NAME, EVENT_PLAYER_ACTIVATED)
	activatedTime = clock()
	if lastEventTime then
		local gap = (activatedTime - lastEventTime) - (wrappedTotal - lastWrapped)
		Charge(BUCKET_WORLD, PRE, math.max(0, gap))
	end
	reloadedUI = not initial
	column = AFTER
	zo_callLater(SaveRun, sv.settleMs)
end

local function OnAddOnLoaded(_, name)
	if name ~= ADDON_NAME then return end
	EVENT_MANAGER:UnregisterForEvent(ADDON_NAME, EVENT_ADD_ON_LOADED)

	sv = _G[SAVED_VARS_NAME]
	if type(sv) ~= "table" then
		sv = { }
		_G[SAVED_VARS_NAME] = sv
	end
	for key, value in pairs(defaults) do
		if sv[key] == nil then
			sv[key] = type(value) == "table" and { } or value
		end
	end
	-- leftovers of the profiler version (1.0.0)
	if sv.armed then
		sv.armed = nil
		SetCVar("StartLuaProfilingOnUILoad", "0")
	end
	for i = #sv.runs, 1, -1 do
		if type(sv.runs[i].wall) ~= "table" or sv.runs[i].wall.burst == nil then
			table.remove(sv.runs, i)
		end
	end

	ALP.InitializeWindow()
	SLASH_COMMANDS["/alp"] = OnSlashCommand
end

originalRegisterForEvent(EVENT_MANAGER, ADDON_NAME, EVENT_ADD_ON_LOADED, OnAddOnLoaded)
originalRegisterForEvent(EVENT_MANAGER, ADDON_NAME, EVENT_PLAYER_ACTIVATED, OnPlayerActivated)
