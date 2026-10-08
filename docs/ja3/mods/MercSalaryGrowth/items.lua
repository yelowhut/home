return {
	PlaceObj('ModItemOptionNumber', {
		'name', "GrowthReduction",
		'DisplayName', "Снижение роста цены найма, %",
		'Help', "100% - цена не растёт с уровнем (как на стартовом уровне мерка). 0% - стандартный рост. Промежуточные значения пропорционально уменьшают надбавку за уровни.",
		'DefaultValue', 100,
		'MinValue', 0,
		'MaxValue', 100,
		'StepSize', 5,
	}),
	PlaceObj('ModItemCode', {
		'name', "MercSalaryGrowth",
		'CodeFileName', "Code/MercSalaryGrowth.lua",
	}),
}
