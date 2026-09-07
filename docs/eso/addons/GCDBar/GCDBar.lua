GCDBar = GCDBar or { }
local gb = GCDBar

local EM = GetEventManager()

local defaults = {
	["frameX"] = 500,
	["frameY"] = 500,
	["width"] = 175,
	["height"] = 50,
	["scale"] = 1,
	["color"] = {1, 0, 0, .7},
	["abCooldown"] = false,
	["fastGCD"] = false,
	["advTime"] = 0,
	["reverse"] = false,
	["hideFrame"] = false,
	-- Visual / visibility additions
	["backColor"] = {0, 0, 0, .25},
	["hideOutOfCombat"] = false,
	["outOfCombatAlpha"] = 30,
	["outOfCombatDelay"] = 3,
	["hideInTowns"] = false,
}

gb.name = "GCDBar"
gb.version = "2.7"
local cd = 0
local dur = 1

local function cdHandler()
	local remain, duration, global, globalSlotType = GetSlotCooldownInfo(3)
	local r2, d2, _, _ = GetSlotCooldownInfo(4)
	if (r2 > remain) or ( d2 > duration ) then
		remain = r2
		duration = d2
	end
	--cd = cd - 20
	--if gb.savedVars.fastGCD then cd = cd - 2 end -- count down 10% faster
	--if gb.savedVars.advTime > 0 then cd = cd - (gb.savedVars.advTime/dur)*20 end
	if duration < 1 then duration = 1 end
	gb.UI.gbFront:SetDimensions((remain/duration)*gb.savedVars.width, gb.savedVars.height)
end

--local function rebuildFunction()
--	local updateCooldown = ActionButton.UpdateCooldown
--
--	function ActionButton:UpdateCooldown(options)
--		local slotNum = self:GetSlot()
--		local remain, duration, global, globalSlotType = GetSlotCooldownInfo(slotNum)
--		if slotNum == 3 and remain > 0 and global then
--			cd = remain
--			dur = (duration > 0) and duration or 1
--		end
--
--		updateCooldown(self, options)
--	end
--end

-- Target opacity for the bar right now, based on combat state and settings.
function gb.getTargetAlpha()
	if gb.savedVars.hideOutOfCombat and not IsUnitInCombat("player") then
		return (gb.savedVars.outOfCombatAlpha or 100) / 100
	end
	return 1
end

-- Cities/interiors are subzone maps with no special content; dungeons are ZONE + DUNGEON.
-- Evaluated on zone load, where the world map is synced to the player and safe to query.
function gb.evaluateInTown()
	if not (ZO_WorldMap_IsWorldMapShowing and ZO_WorldMap_IsWorldMapShowing()) then
		SetMapToPlayerLocation()
	end
	gb.isInTown = (GetMapType() == MAPTYPE_SUBZONE) and (GetMapContentType() == MAP_CONTENT_NONE)
end

-- Central show/hide + opacity decision. useFade => animate opacity transitions.
function gb.updateVisibility(useFade)
	if not gb.UI or not gb.UI.gbFrame then return end
	if gb.editing then
		gb.UI.setChildAlpha(1)
		return
	end
	local inCombat = IsUnitInCombat("player")
	if gb.savedVars.hideFrame or (gb.savedVars.hideInTowns and gb.isInTown and not inCombat) then
		gb.UI.setHudToggle(false)
		gb.UI.gbFrame:SetHidden(true)
		return
	end
	gb.UI.setHudToggle(true)
	gb.UI.gbFrame:SetHidden(false)
	local target = gb.getTargetAlpha()
	if useFade then gb.UI.fadeTo(target) else gb.UI.setChildAlpha(target) end
end

function gb.onCombatState(_, inCombat)
	if gb.editing then return end
	gb.ocFadeId = (gb.ocFadeId or 0) + 1
	local myId = gb.ocFadeId
	if inCombat then
		gb.updateVisibility(true)
	else
		local delayMs = (gb.savedVars.outOfCombatDelay or 0) * 1000
		if delayMs <= 0 then
			gb.updateVisibility(true)
		else
			zo_callLater(function()
				if myId == gb.ocFadeId and not IsUnitInCombat("player") then
					gb.updateVisibility(true)
				end
			end, delayMs)
		end
	end
end

function gb.init(e, addonName)
	if addonName ~= gb.name then return end
	gb.savedVars = ZO_SavedVars:NewCharacterIdSettings("GCDBarSavedVars", 1, nil, defaults)
	gb.editing = false
	gb.UI.buildUI()
	gb.UI.setProperties()
--	rebuildFunction()
	EM:RegisterForUpdate(gb.name.."cooldown", 20, cdHandler)
	gb.buildMenu()
	EM:RegisterForEvent(gb.name.."Combat", EVENT_PLAYER_COMBAT_STATE, gb.onCombatState)
	EM:RegisterForEvent(gb.name.."Activated", EVENT_PLAYER_ACTIVATED, function()
		gb.evaluateInTown()
		gb.updateVisibility(false)
	end)
	if gb.savedVars.abCooldown then ZO_ActionButtons_ToggleShowGlobalCooldown() end
	gb.evaluateInTown()
	gb.updateVisibility(false)
end

EM:RegisterForEvent(gb.name.."Load", EVENT_ADD_ON_LOADED, gb.init)

