return PlaceObj('ModDef', {
	'title', "Satellite Map: All Icons",
	'description', "Режим карты по умолчанию показывает сразу всё: отряды, Intel (левый нижний угол сектора), квестовый значок Notes (центр нижнего края) и счётчик предметов в стеше (правый нижний угол).\nОстальные фильтры карты работают как в оригинале.",
	'id', "SatelliteMapIcons",
	'author', "yelow",
	'version_major', 1,
	'version', 1,
	'lua_revision', 233360,
	'saved_with_revision', 366685,
	'code', {
		"Code/SatelliteMapIcons.lua",
	},
	'default_options', {
		ShowIntel = true,
		ShowAllQuests = true,
		ShowStash = true,
	},
})
