-- Field Experience Unchained (steam 3016462683) replaces RollForStatGaining (Lua/Mercenary.lua) and drops the
-- "statGainingPoints > 0" check, but still does statGainingPoints - 1 on every gain. Active mercs go negative,
-- which disables its pity system (it needs more than PointsPerLevel banked points) and, if FEU is removed,
-- blocks vanilla field gains until XP refills the counter.
-- Wrap whatever RollForStatGaining is current and keep the counter at zero or above. Existing negative
-- counters are cleared on load.
--
-- The wrap is done on Msg("Autorun"): it fires after the code of all mods ran (so mod load order does not
-- matter) and while Loading is still true - the mod env (CommonLua/Classes/Mod.lua, LuaModEnv) refuses to
-- assign globals once Loading is false. Core's own Autorun handler, which clears Loading, is registered
-- after ModsLoadCode() in autorun.lua and therefore runs after this one.

local function ClampPoints(obj)
	if obj and (obj.statGainingPoints or 0) < 0 then
		obj.statGainingPoints = 0
	end
end

-- Globals that may be nil are read with rawget: the mod env errors on reading a nil global.
local wrapper

function OnMsg.Autorun()
	if not Loading then return end
	local orig = RollForStatGaining
	if not orig or orig == wrapper then return end
	wrapper = function(unit, ...)
		orig(unit, ...)
		ClampPoints(unit)
		local unit_data = rawget(_G, "gv_UnitData")
		ClampPoints(unit and unit.session_id and unit_data and unit_data[unit.session_id])
	end
	RollForStatGaining = wrapper
end

local function ClampAll()
	for _, unitData in pairs(rawget(_G, "gv_UnitData") or empty_table) do
		ClampPoints(unitData)
	end
	for _, unit in pairs(rawget(_G, "g_Units") or empty_table) do
		ClampPoints(unit)
	end
end

OnMsg.LoadGame = ClampAll
OnMsg.ChangeMapDone = ClampAll
