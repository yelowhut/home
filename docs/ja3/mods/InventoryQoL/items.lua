return {
	PlaceObj('ModItemOptionToggle', {
		'name', "CaliberLabels",
		'DisplayName', "Подписи калибров",
		'Help', "Калибр и тип над патронами, снарядами и гранатами - в инвентаре и в окне крафта.",
		'DefaultValue', true,
	}),
	PlaceObj('ModItemOptionToggle', {
		'name', "HideAmmoTypeIcon",
		'DisplayName', "Скрывать иконку типа патрона",
		'Help', "Тип патрона (AP, HP, TR...) уже есть в подписи, маленькая иконка в углу ей мешает.",
		'DefaultValue', true,
	}),
	PlaceObj('ModItemOptionToggle', {
		'name', "DoubleClickScrap",
		'DisplayName', "Двойной клик разбирает",
		'Help', "Двойной клик по предмету в стэше сектора, контейнере или на трупе врага разбирает его на части (без подтверждения!). Предметы без частей (гранаты, бомбы) уничтожаются. Alt + двойной клик - ванильное действие. Патроны, части и прочее для сумки отряда не разбираются.",
		'DefaultValue', true,
	}),
	PlaceObj('ModItemOptionToggle', {
		'name', "ScrapInBulk",
		'DisplayName', "Разбирать все такие же",
		'Help', "Двойной клик разбирает все предметы того же типа в этом контейнере с таким же или худшим состоянием. Выключено - только тот предмет (стак), по которому кликнули.",
		'DefaultValue', true,
	}),
	PlaceObj('ModItemOptionChoice', {
		'name', "CraftTileSize",
		'DisplayName', "Размер иконок рецептов",
		'Help', "Размер плиток в списке рецептов крафта патронов и взрывчатки. 72 - как в ванили.",
		'DefaultValue', "56",
		'ChoiceList', {
			"72",
			"64",
			"56",
			"48",
		},
	}),
	PlaceObj('ModItemOptionToggle', {
		'name', "RightClickQueue",
		'DisplayName', "Правый клик - в очередь крафта",
		'Help', "Правый клик по рецепту добавляет его в очередь крафта, по рецепту в очереди - убирает из неё.",
		'DefaultValue', true,
	}),
	PlaceObj('ModItemCode', {
		'name', "AmmoLabels",
		'CodeFileName', "Code/AmmoLabels.lua",
	}),
	PlaceObj('ModItemCode', {
		'name', "BulkScrap",
		'CodeFileName', "Code/BulkScrap.lua",
	}),
	PlaceObj('ModItemCode', {
		'name', "CraftQueue",
		'CodeFileName', "Code/CraftQueue.lua",
	}),
}
