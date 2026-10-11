return {
	PlaceObj('ModItemOptionToggle', {
		'name', "SortStash",
		'DisplayName', "Сортировать стэш",
		'Help', "Предметы в стэше сектора идут по типу (в порядке вкладок инвентаря, затем по группе предмета), потом по имени, потом по состоянию. Работает с учётом выбранной вкладки.",
		'DefaultValue', true,
	}),
	PlaceObj('ModItemOptionToggle', {
		'name', "StackItems",
		'DisplayName', "Собирать стаки",
		'Help', "Одинаковые предметы-стаки (патроны, медикаменты, части, гранаты...) в стэше сектора сливаются в полные стаки при открытии стэша.",
		'DefaultValue', true,
	}),
	PlaceObj('ModItemCode', {
		'name', "StashSort",
		'CodeFileName', "Code/StashSort.lua",
	}),
}
