return PlaceObj('ModDef', {
	'title', "Merc Training Boost",
	'description', "Ускоряет операцию обучения мерков (Train Mercs).\nСкорость обучения: сессия заканчивается быстрее, а прирост характеристики за сессию остаётся прежним. +100% - сессия 24 часа вместо 48.\nПрирост характеристик: ученики получают больше очков прогресса к следующему +1. Действует только на учеников.\n0% - как в ванили. Эффекты перемножаются: +100% и +100% дают в 4 раза больше прироста в час.",
	'id', "MercTrainingBoost",
	'author', "yelow",
	'version_major', 1,
	'version', 1,
	'lua_revision', 233360,
	'saved_with_revision', 366685,
	'code', {
		"Code/MercTrainingBoost.lua",
	},
	'default_options', {
		TrainingSpeed = "0%",
		StatGainBonus = "0%",
	},
})
