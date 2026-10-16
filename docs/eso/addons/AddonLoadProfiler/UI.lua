-- Results window: one row per addon, averaged over the stored loads or for a
-- single load, sortable by any column. Hovering a row explains the numbers.

local ALP = ADDON_LOAD_PROFILER

local ROW_TYPE = 1
local ROW_HEIGHT = 24

local COLUMNS =
{
	{ key = "title", control = "Name", label = "Addon" },
	{ key = "pre", control = "Pre", label = "Pre-event ms" },
	{ key = "init", control = "Init", label = "Init ms" },
	{ key = "after", control = "After", label = "After ms" },
	{ key = "total", control = "Total", label = "Total ms" },
	{ key = "share", control = "Share", label = "Share" },
}

local COLOR_BUCKET = "9FA8FF"
local COLOR_LIB = "8F8F8F"
local COLOR_HEAVY = "FF6A5C"
local COLOR_NOTABLE = "FFD24D"
local COLOR_PLAIN = "FFFFFF"

local window, list, summary, viewButton, header
local viewIndex = 0		-- 0 = average of all stored loads
local sortKey, sortAscending = "total", false

local function FormatMs(ms)
	if ms < 0.05 then return "-" end
	if ms >= 10 then return string.format("%.0f", ms) end
	return string.format("%.1f", ms)
end

local function Colorize(color, text)
	return string.format("|c%s%s|r", color, text)
end

local function SetupRow(control, row)
	control.row = row
	GetControl(control, "Rank"):SetText(row.rank)

	local name
	if row.name:sub(1, 1) == "[" then
		name = Colorize(COLOR_BUCKET, row.title)
	else
		name = row.title
		if row.lib then name = name .. Colorize(COLOR_LIB, " (lib)") end
		-- loaded before ALP: only the gap before its event is visible
		if row.early > 0 then name = name .. Colorize(COLOR_LIB, " *") end
	end
	GetControl(control, "Name"):SetText(name)

	GetControl(control, "Pre"):SetText(FormatMs(row.pre))
	GetControl(control, "Init"):SetText(FormatMs(row.init))
	GetControl(control, "After"):SetText(FormatMs(row.after))
	GetControl(control, "Total"):SetText(FormatMs(row.total))

	local color = row.share >= 0.10 and COLOR_HEAVY or row.share >= 0.03 and COLOR_NOTABLE or COLOR_PLAIN
	GetControl(control, "Total"):SetColor(ZO_ColorDef:New(color):UnpackRGBA())
	GetControl(control, "Share"):SetText(row.share >= 0.001 and string.format("%.1f%%", row.share * 100) or "-")
end

local function CompareRows(a, b)
	local va, vb = a[sortKey], b[sortKey]
	if sortKey == "title" then
		va, vb = va:lower(), vb:lower()
	end
	if va == vb then
		return a.name < b.name
	end
	if sortAscending then
		return va < vb
	end
	return va > vb
end

local function UpdateHeader()
	for _, column in ipairs(COLUMNS) do
		local label = header:GetNamedChild(column.control)
		local arrow = column.key == sortKey and (sortAscending and " ^" or " v") or ""
		label:SetText(column.label .. arrow)
	end
end

local function Average(selected, group, key)
	local sum = 0
	for _, run in ipairs(selected) do
		sum = sum + (run[group][key] or 0)
	end
	return sum / math.max(1, #selected) / 1000
end

local function BuildSummary(selected, runs)
	local lines = { }
	if #selected == 0 then
		lines[1] = "No measured loads yet. Every relog or /reloadui is measured while ALP is enabled."
	else
		if viewIndex == 0 then
			local reloads = 0
			for _, run in ipairs(selected) do
				if run.reload then reloads = reloads + 1 end
			end
			lines[1] = string.format("Average of %d load(s): %d relog, %d /reloadui.", #selected, #selected - reloads, reloads)
		else
			local run = selected[1]
			lines[1] = string.format("Load %d of %d: %s, %s, %s.", viewIndex, #runs, GetDateStringFromTimestamp(run.time),
				run.character or "?", run.reload and "/reloadui" or "relog")
		end
		local files, burst, world = Average(selected, "wall", "files"), Average(selected, "wall", "burst"), Average(selected, "wall", "world")
		lines[2] = string.format("From ALP's own file to the character: %.1fs = files after ALP %.1fs + EVENT_ADD_ON_LOADED burst %.1fs + engine/world %.1fs.",
			files + burst + world, files, burst, world)
		lines[3] = "Pre-event: gap before the addon's own load event (saved variables; for * addons loaded before ALP also their init). Init/After: their event handlers before/after the character appeared."
	end
	lines[#lines + 1] = "Status: " .. ALP.GetStatus()
	return table.concat(lines, "\n")
end

function ALP.RefreshWindow()
	if not window or window:IsHidden() then return end

	local runs = ALP.GetRuns()
	if viewIndex > #runs then viewIndex = 0 end
	local rows, selected = ALP.BuildRows(viewIndex)
	table.sort(rows, CompareRows)

	ZO_ScrollList_Clear(list)
	local dataList = ZO_ScrollList_GetDataList(list)
	for i, row in ipairs(rows) do
		row.rank = i
		dataList[i] = ZO_ScrollList_CreateDataEntry(ROW_TYPE, row)
	end
	ZO_ScrollList_Commit(list)

	summary:SetText(BuildSummary(selected, runs))
	viewButton:SetText(viewIndex == 0 and "View: average" or string.format("View: load %d/%d", viewIndex, #runs))
	UpdateHeader()
end

function ALP.SortBy(key)
	if key == sortKey then
		sortAscending = not sortAscending
	else
		sortKey = key
		sortAscending = key == "title"
	end
	ALP.RefreshWindow()
end

function ALP.CycleView()
	viewIndex = (viewIndex + 1) % (#ALP.GetRuns() + 1)
	ALP.RefreshWindow()
end

function ALP.ToggleWindow()
	SCENE_MANAGER:ToggleTopLevel(window)
	if not window:IsHidden() then
		SCENE_MANAGER:SetInUIMode(true)
		ALP.RefreshWindow()
	end
end

function ALP.OnRowMouseEnter(control)
	ZO_ScrollList_MouseEnter(list, control)
	local row = control.row
	if not row then return end

	InitializeTooltip(InformationTooltip, control, RIGHT, -10, 0, LEFT)
	SetTooltipText(InformationTooltip, row.title)
	if row.title ~= row.name then
		InformationTooltip:AddLine(row.name, "ZoFontGameSmall")
	end
	InformationTooltip:AddLine(string.format("%.0f measured handler calls per load", row.calls), "ZoFontGameSmall")
	if row.early > 0 then
		InformationTooltip:AddLine("* Loaded before ALP: its handlers were registered before the hooks, so only the gap before its load event is measured (that gap includes its own OnAddOnLoaded).", "ZoFontGameSmall")
	end
end

function ALP.OnRowMouseExit(control)
	ZO_ScrollList_MouseExit(list, control)
	ClearTooltip(InformationTooltip)
end

function ALP.InitializeWindow()
	window = AddonLoadProfilerWindow
	list = window:GetNamedChild("List")
	summary = window:GetNamedChild("Summary")
	viewButton = window:GetNamedChild("View")
	header = window:GetNamedChild("Header")

	for _, column in ipairs(COLUMNS) do
		header:GetNamedChild(column.control).sortKey = column.key
	end

	ZO_ScrollList_AddDataType(list, ROW_TYPE, "AddonLoadProfilerRow", ROW_HEIGHT, SetupRow)
	ZO_ScrollList_EnableHighlight(list, "ZO_ThinListHighlight")
	SCENE_MANAGER:RegisterTopLevel(window, false)
end
