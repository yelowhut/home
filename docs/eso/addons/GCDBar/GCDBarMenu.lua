GCDBar = GCDBar or { }
local gb = GCDBar

local lockUI = true

function gb.buildMenu()
	local LAM = LibAddonMenu2

	local panelData = {
		type = "panel",
		name = "GCD Bar",
		displayName = "|cff0c4dG|rCD Bar",
		author = "Wheels",
		version = ""..gb.version,
		registerForRefresh = true,
	}

	LAM:RegisterAddonPanel(gb.name.."Options", panelData)

	local options = {
		{
			type = "header",
			name = "Display Options",
		},
		{
			type = "checkbox",
			name = "Lock UI",
			tooltip = "Enable repositioning and resizing of the cooldown bar",
			getFunc = function() return lockUI end,
			setFunc = function(value)
				gb.UI.setHudToggle(value and not gb.savedVars.hideFrame or false)
				gb.UI.gbFrame:SetMouseEnabled(not value)
				gb.UI.gbFrame:SetMovable(not value)
				gb.UI.gbFrame:SetHidden(value)
				lockUI = value
				gb.editing = not value
				if gb.editing then
					gb.UI.setChildAlpha(1)
				else
					gb.UI.setProperties()
					gb.updateVisibility(false)
				end
			end,
		},
		{
			type = "checkbox",
			name = "Hide Bar",
			tooltip = "Hides the GCD 'bar' itself, in case you just want the skill icon cooldowns",
			getFunc = function() return gb.savedVars.hideFrame end,
			setFunc = function(value)
				gb.savedVars.hideFrame = value
				gb.updateVisibility(false)
			end,
		},
		{
			type = "checkbox",
			name = "Toggle Action Bar Cooldowns",
			tooltip = "Toggles radial cooldowns on the action bar",
			getFunc = function() return gb.savedVars.abCooldown end,
			setFunc = function(value)
				ZO_ActionButtons_ToggleShowGlobalCooldown()
				gb.savedVars.abCooldown = value
			end,
		},
		{
			type = "checkbox",
			name = "Reverse Bar Direction",
			tooltip = "Reverses the direction that the bar counts down in",
			getFunc = function() return gb.savedVars.reverse end,
			setFunc = function(value)
				gb.savedVars.reverse = value
				gb.UI.setProperties()
			end,
		},
		{
			type = "colorpicker",
			name = "Bar Color",
			tooltip = "Color of the GCD Bar (what did you think it was?)",
			getFunc = function() return unpack(gb.savedVars.color) end,
			setFunc = function(r,g,b,a)
				gb.savedVars.color = {r,g,b,a}
				gb.UI.setProperties()
			end,
		},
		{
			type = "colorpicker",
			name = "Background Color",
			tooltip = "Color and opacity of the bar background (default - black, 25%)",
			getFunc = function() return unpack(gb.savedVars.backColor) end,
			setFunc = function(r,g,b,a)
				gb.savedVars.backColor = {r,g,b,a}
				gb.UI.setProperties()
			end,
		},
		{
			type = "header",
			name = "Size",
		},
		{
			type = "slider",
			name = "Width",
			tooltip = "Bar width in pixels (also adjustable by dragging the corner while unlocked)",
			min = 50,
			max = 500,
			step = 1,
			getFunc = function() return math.floor(gb.savedVars.width) end,
			setFunc = function(value)
				gb.savedVars.width = value
				gb.UI.setProperties()
			end,
		},
		{
			type = "slider",
			name = "Height",
			tooltip = "Bar height in pixels (also adjustable by dragging the corner while unlocked)",
			min = 20,
			max = 100,
			step = 1,
			getFunc = function() return math.floor(gb.savedVars.height) end,
			setFunc = function(value)
				gb.savedVars.height = value
				gb.UI.setProperties()
			end,
		},
		{
			type = "slider",
			name = "Scale (%)",
			tooltip = "Overall scale of the bar, from 50% to 300%",
			min = 50,
			max = 300,
			step = 1,
			getFunc = function() return math.floor((gb.savedVars.scale or 1) * 100) end,
			setFunc = function(value)
				gb.savedVars.scale = value / 100
				gb.UI.setProperties()
			end,
		},
		{
			type = "header",
			name = "Visibility",
		},
		{
			type = "checkbox",
			name = "Fade out of combat",
			tooltip = "ON - the bar smoothly fades to a reduced opacity while out of combat, and returns to full opacity in combat",
			getFunc = function() return gb.savedVars.hideOutOfCombat end,
			setFunc = function(value)
				gb.savedVars.hideOutOfCombat = value
				gb.updateVisibility(false)
			end,
		},
		{
			type = "slider",
			name = "Out-of-combat opacity (%)",
			tooltip = "Opacity to fade to when out of combat (0 = fully invisible, 100 = no fade)",
			min = 0,
			max = 100,
			step = 1,
			disabled = function() return not gb.savedVars.hideOutOfCombat end,
			getFunc = function() return gb.savedVars.outOfCombatAlpha end,
			setFunc = function(value)
				gb.savedVars.outOfCombatAlpha = value
				gb.updateVisibility(false)
			end,
		},
		{
			type = "slider",
			name = "Fade delay after combat (sec)",
			tooltip = "How many seconds to wait after leaving combat before fading out",
			min = 0,
			max = 30,
			step = 1,
			disabled = function() return not gb.savedVars.hideOutOfCombat end,
			getFunc = function() return gb.savedVars.outOfCombatDelay end,
			setFunc = function(value) gb.savedVars.outOfCombatDelay = value end,
		},
		{
			type = "checkbox",
			name = "Hide in cities / safe zones",
			tooltip = "ON - the bar is fully hidden in cities and interiors (load-screened subzones). It still appears if you enter combat there. Note: open-world settlements without a load screen are not detected as towns.",
			getFunc = function() return gb.savedVars.hideInTowns end,
			setFunc = function(value)
				gb.savedVars.hideInTowns = value
				gb.evaluateInTown()
				gb.updateVisibility(false)
			end,
		},
		--{
		--	type = "checkbox",
		--	name = "Fast GCD",
		--	tooltip = "Simulates a 900ms GCD to help with queuing skills at the correct time (slighly visually buggy but it works)",
		--	getFunc = function() return gb.savedVars.fastGCD end,
		--	setFunc = function(value) gb.savedVars.fastGCD = value end,
		--},
		--{
		--	type = "slider",
		--	name = "Advanced Fast GCD",
		--	tooltip = "The number selected here will determine how early the GCD timer ends. If 150 is selected, the timer will end 150 ms early, simulating a 850 ms GCD.",
		--	min = 0,
		--	max = 200,
		--	step = 1,
		--	getFunc = function() return gb.savedVars.advTime end,
		--	setFunc = function(value) gb.savedVars.advTime = value end,
		--},
	}

	LAM:RegisterOptionControls(gb.name.."Options", options)
end
