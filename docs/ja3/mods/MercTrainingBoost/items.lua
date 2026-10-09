return {
	PlaceObj('ModItemOptionChoice', {
		'name', "TrainingSpeed",
		'DisplayName', "Скорость обучения",
		'Help', "Сессия обучения заканчивается быстрее, прирост характеристики за сессию не меняется. 0% - как в ванили (48 часов), +100% - вдвое быстрее (24 часа).",
		'DefaultValue', "0%",
		'ChoiceList', {
			"0%",
			"+25%",
			"+50%",
			"+75%",
			"+100%",
		},
	}),
	PlaceObj('ModItemOptionChoice', {
		'name', "StatGainBonus",
		'DisplayName', "Прирост характеристик",
		'Help', "Бонус к прогрессу характеристики, который ученики получают при обучении. 0% - как в ванили, +100% - вдвое больше.",
		'DefaultValue', "0%",
		'ChoiceList', {
			"0%",
			"+25%",
			"+50%",
			"+75%",
			"+100%",
		},
	}),
	PlaceObj('ModItemCode', {
		'name', "MercTrainingBoost",
		'CodeFileName', "Code/MercTrainingBoost.lua",
	}),
}
