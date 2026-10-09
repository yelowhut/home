return PlaceObj('ModDef', {
	'title', "Console Log Off",
	'description', "Убирает с экрана отладочный лог (print-сообщения в левом нижнем углу).\nЛог включается, если кампания начата при открытом редакторе/менеджере модов: флаг Game.testModGame сохраняется в сейв. Мод снимает этот флаг при загрузке.",
	'id', "ConsoleLogOff",
	'author', "yelow",
	'version_major', 1,
	'version', 1,
	'lua_revision', 233360,
	'saved_with_revision', 366685,
	'code', {
		"Code/ConsoleLogOff.lua",
	},
})
