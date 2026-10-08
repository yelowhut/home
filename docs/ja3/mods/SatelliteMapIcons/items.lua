return {
	PlaceObj('ModItemOptionToggle', {
		'name', "ShowIntel",
		'DisplayName', "Intel всегда",
		'Help', "Показывать значок Intel (левый нижний угол сектора) в режиме по умолчанию, а не только в фильтре Notes.",
		'DefaultValue', true,
	}),
	PlaceObj('ModItemOptionToggle', {
		'name', "ShowAllQuests",
		'DisplayName', "Все квесты сектора",
		'Help', "Квестовый значок по центру нижнего края показывает все квесты сектора, как фильтр Notes. Выключено - только отслеживаемый квест (как в оригинале), но тоже по центру.",
		'DefaultValue', true,
	}),
	PlaceObj('ModItemOptionToggle', {
		'name', "ShowStash",
		'DisplayName', "Предметы в стеше",
		'Help', "Показывать значок стеша с количеством предметов (правый нижний угол сектора) в режиме по умолчанию. Клик открывает стеш.",
		'DefaultValue', true,
	}),
	PlaceObj('ModItemCode', {
		'name', "SatelliteMapIcons",
		'CodeFileName', "Code/SatelliteMapIcons.lua",
	}),
}
