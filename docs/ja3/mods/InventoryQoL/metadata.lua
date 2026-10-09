return PlaceObj('ModDef', {
	'title', "Inventory QoL",
	'description', "Подписи калибров на патронах, массовая разборка двойным кликом и удобный крафт патронов/взрывчатки (идеи из Interface tweaks, без его остальных правок).\n\n- Над патронами, снарядами и гранатами - калибр и тип (5.45x39 AP, 7.62N TR, 12g BR, C4 Prox).\n- Двойной клик по предмету в стэше / контейнере / трупе врага разбирает его и все такие же предметы с таким же или худшим состоянием. Alt + двойной клик - как в ванили.\n- Крафт: иконки рецептов меньше, правый клик по рецепту добавляет его в очередь, по рецепту в очереди - убирает.",
	'id', "InventoryQoL",
	'author', "yelow",
	'version_major', 1,
	'version', 1,
	'lua_revision', 233360,
	'saved_with_revision', 366685,
	'code', {
		"Code/AmmoLabels.lua",
		"Code/BulkScrap.lua",
		"Code/CraftQueue.lua",
	},
	'default_options', {
		CaliberLabels = true,
		HideAmmoTypeIcon = true,
		DoubleClickScrap = true,
		ScrapInBulk = true,
		CraftTileSize = "56",
		RightClickQueue = true,
	},
})
