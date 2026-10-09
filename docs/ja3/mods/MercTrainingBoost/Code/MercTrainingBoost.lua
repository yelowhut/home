-- Patches the TrainMercs sector operation (Data/SectorOperation.lua) on the preset object itself:
--   * TrainingSpeed: ProgressPerTick is scaled, so the 48h session (ProgressCompleteThreshold) ends sooner.
--     GetActorOperationTimeLeft (Lua/Satellite/SatelliteSectorOperations.lua) uses the same method, so ETAs match.
--     Students get stat progress per 15-min tick, so a shorter session would also give less progress -
--     the stat progress rate is scaled by the same factor to keep the gain per session vanilla.
--   * StatGainBonus: extra stat progress for students.
-- Both are applied through the "learning_speed" param, which is only used in Tick as the student's
-- threshold for +1 stat: dividing the threshold by k is the same as multiplying the progress by k, and the
-- Teacher perk, HardLessons, solo practice and the teacher/max stat caps stay vanilla.
-- Options are read on every call, so changes apply without reloading.

local OptionValues = {
	["0%"] = 0,
	["+25%"] = 25,
	["+50%"] = 50,
	["+75%"] = 75,
	["+100%"] = 100,
}

local function GetBonus(name)
	local value = CurrentModOptions and CurrentModOptions[name]
	return Clamp(OptionValues[value] or 0, 0, 100)
end

local function PatchTrainMercs()
	local op = SectorOperations and SectorOperations.TrainMercs
	if not op or op.MercTrainingBoostPatched then
		return
	end
	op.MercTrainingBoostPatched = true

	local origProgressPerTick = op.ProgressPerTick
	op.ProgressPerTick = function(self, ...)
		local progress = origProgressPerTick(self, ...)
		return MulDivRound(progress, 100 + GetBonus("TrainingSpeed"), 100)
	end

	local origResolveValue = op.ResolveValue
	op.ResolveValue = function(self, key, ...)
		local value = origResolveValue(self, key, ...)
		if key == "learning_speed" and value then
			local mul = (100 + GetBonus("TrainingSpeed")) * (100 + GetBonus("StatGainBonus"))
			return Max(1, MulDivRound(value, 100 * 100, mul))
		end
		return value
	end
end

PatchTrainMercs()

function OnMsg.DataLoaded()
	PatchTrainMercs()
end
