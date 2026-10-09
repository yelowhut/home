return PlaceObj('ModDef', {
	'title', "Stat Gain Points Fix",
	'description', "Патч для Field Experience Unchained: очки прокачки (statGainingPoints) больше не уходят в минус.\nFEU не требует очков для роста статов, но всё равно списывает их, из-за чего у активных мерков счётчик становится отрицательным: не срабатывает Pity System, а после удаления FEU мерк перестаёт расти от опыта, пока не наберёт очки обратно.\nМод не даёт счётчику опуститься ниже нуля и при загрузке сейва обнуляет уже накопленный минус. Без FEU ничего не меняет.",
	'id', "StatGainPointsFix",
	'author', "yelow",
	'version_major', 1,
	'version', 1,
	'lua_revision', 233360,
	'saved_with_revision', 366685,
	'code', {
		"Code/StatGainPointsFix.lua",
	},
})
