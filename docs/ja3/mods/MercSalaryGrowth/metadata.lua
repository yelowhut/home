return PlaceObj('ModDef', {
	'title', "Merc Salary Growth Control",
	'description', "Настраивает рост стоимости найма мерков с уровнем.\n100% - роста нет (цена как на стартовом уровне), 0% - стандартный рост.",
	'id', "MercSalaryGrowth",
	'author', "yelow",
	'version_major', 1,
	'version', 1,
	'lua_revision', 233360,
	'saved_with_revision', 366685,
	'code', {
		"Code/MercSalaryGrowth.lua",
	},
	'default_options', {
		GrowthReduction = 100,
	},
})
