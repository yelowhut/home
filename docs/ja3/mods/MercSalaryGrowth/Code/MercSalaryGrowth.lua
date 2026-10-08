-- Replaces GetDailyMercSalary (Lua/Mercenary.lua). The vanilla compounding formula is kept as is;
-- the part of the salary gained above the starting level is cut by the GrowthReduction option:
--   100% -> salary stays at the starting-level price, 0% -> vanilla growth.
-- Game rules (CheaperPros, Unionization) still apply, as they live in the merc getters.

function GetDailyMercSalary(merc, level)
	local startingLevel = merc:GetProperty("StartingLevel")
	local currentLevel = level or merc:GetLevel()

	local salaryAtStartingLevel = merc:GetMercStartingSalary()

	local salaryIncrease = merc:GetSalaryIncreaseProp()
	local currentSalary = salaryAtStartingLevel
	for level = startingLevel, currentLevel - 1 do
		local increaseAmount = MulDivRound(currentSalary, salaryIncrease, 1000)
		currentSalary = currentSalary + increaseAmount
	end

	local reduction = Clamp(CurrentModOptions and CurrentModOptions.GrowthReduction or 100, 0, 100)
	local growth = currentSalary - salaryAtStartingLevel
	if growth <= 0 then
		return currentSalary
	end
	return salaryAtStartingLevel + MulDivRound(growth, 100 - reduction, 100)
end
