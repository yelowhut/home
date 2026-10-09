-- Vanilla (Lua/Mod.lua) calls ConsoleSetEnabled(AreModdingToolsActive()) on every ChangeMapDone.
-- AreModdingToolsActive() (CommonLua/Classes/Mod.lua) is also true when Game.testModGame is set,
-- and Game.testModGame is stored in the save when a campaign was started while the mod editor or
-- mod manager was open (Lua/GameSession.lua). Such a campaign shows the console log forever.
-- Clear the flag and hide the log unless the modding tools are really open.

local function ClearTestModGame()
	if Game and Game.testModGame then
		Game.testModGame = false
	end
	if not AreModdingToolsActive() then
		ConsoleSetEnabled(false)
	end
end

OnMsg.LoadGame = ClearTestModGame
OnMsg.NewGame = ClearTestModGame
OnMsg.ChangeMapDone = ClearTestModGame
