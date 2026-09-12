-- RUSSIAN LANGUAGE LOCALIZATION

-- Collect
SurveyZoneList.lang.collectFindName = {
    "карта сокровищ (.*)", --treasure map
    ".*: (.*)",
}

SurveyZoneList.lang.surveyAction = {
    "Рубить",
    "Взять",
    "Собрать",
    "Добыть"
}

SurveyZoneList.lang.nodeName = {
    "^нетронутый",
    "^изобилие",
    "^залежи",
    "^ловушка меховщика$",
    "^богатый",
    "^многогранный",
    "^bulging herbalist's satchel$", --Apocrypha (fixed in u39 only ? to check)
    "^большая", --Apocrypha
    "бархата$", --Apocrypha
    
    -- bois
    -- Survey : [03:58] [03:58] Рубить / Нетронутый багряный ясень
    -- Normal : [03:59] [03:59] Рубить / Багряный ясень

    -- enchantement
    -- survey : [04:27] [04:27] Взять / Многогранный рунный камень
    -- normal : [04:02] [04:02] Взять / Рунный камень

    -- couture
    -- survey : [04:21] [04:21] Взять / Изобилие шелка предков
    --          [04:21] [04:21] Взять / Ловушка меховщика
    --          [00:11]         Взять / обрывок бархата (apocrypha)
    -- normal : [03:58] [03:58] Взять / Шелк предков
    --          [00:13]         Взять / обрывок ткани (apocrypha)

    -- alchimie
    -- survey : [04:03] [04:03] Собрать / Изобилие василька
    --          [04:03] [04:03] Собрать / Изобилие полыни
    --          [04:03] [04:03] Собрать / Изобилие водосбора
    --          [04:03] [04:03] Собрать / Изобилие драконьего шипа
    --          [00:26]         Собрать / большая сумка травника
    -- normal : [03:59] [03:59] Взять / Горноцвет
    --          [04:14] [04:14] Взять / Водный гиацинт
    --          [04:14] [04:14] Взять / Полынь
    --                                / сумка травника (apocrypha)

    -- forge
    -- survey : [04:18] [04:18] Добыть / Залежи рубедитовой руды
    -- normal : [03:57] [03:57] Добыть / Рубедитовая руда

    -- joaillerie
    -- survey : [04:24] [04:24] Добыть / Богатый платиновый пласт
    -- normal : [03:57] [03:57] Добыть / Платиновый пласт
}

-- Settings : Craft breakdown (issue #10)
ZO_CreateStringId("SI_SURVEYZONELIST_SETTINGS_DISPLAY_CRAFT", "Показывать разбивку по ремёслам")
ZO_CreateStringId("SI_SURVEYZONELIST_SETTINGS_DISPLAY_CRAFT_DESC", "Показывает в каждой строке зоны по столбцу на ремесло с количеством исследований этого ремесла.")
ZO_CreateStringId("SI_SURVEYZONELIST_SETTINGS_TEXT_WIDTH", "Ширина текста зоны")
ZO_CreateStringId("SI_SURVEYZONELIST_SETTINGS_TEXT_WIDTH_DESC", "Ширина, отведённая под текст зоны. Столбцы ремёсел добавляются сверх неё.")

-- Settings : Bank (issue #12)
ZO_CreateStringId("SI_SURVEYZONELIST_SETTINGS_BANK_TITLE", "Банк")
ZO_CreateStringId("SI_SURVEYZONELIST_SETTINGS_BANK_DESC", "Содержимое банка можно считать вместе с рюкзаком, чтобы знать, что забрать перед выходом.")
ZO_CreateStringId("SI_SURVEYZONELIST_SETTINGS_BANK_READ", "Читать исследования и в банке")
ZO_CreateStringId("SI_SURVEYZONELIST_SETTINGS_BANK_READ_DESC", "Считает исследования и карты сокровищ в банке учётной записи. Оповещения и счётчик точек по-прежнему используют только рюкзак.")

-- Settings : Champion points (issue #13)
ZO_CreateStringId("SI_SURVEYZONELIST_SETTINGS_CP_TITLE", "Очки чемпиона")
ZO_CreateStringId("SI_SURVEYZONELIST_SETTINGS_CP_DESC", "«Обильный урожай» даёт шанс собрать дополнительные ресурсы, поэтому исследование без него частично пропадает зря.")
ZO_CreateStringId("SI_SURVEYZONELIST_SETTINGS_CP_WARN", "Предупреждать, если «Обильный урожай» не вставлен")
ZO_CreateStringId("SI_SURVEYZONELIST_SETTINGS_CP_WARN_DESC", "Показывает строку предупреждения в окне, пока звезда чемпиона «Обильный урожай» не куплена или не вставлена в слот.")

-- Settings : Zone detection (issue #14)
ZO_CreateStringId("SI_SURVEYZONELIST_SETTINGS_ZONE_TITLE", "Определение зоны")
ZO_CreateStringId("SI_SURVEYZONELIST_SETTINGS_ZONE_DESC", "LibTreasure знает настоящую зону каждого исследования, что избавляет от дублей зон, которые создавал разбор названия предмета.")
ZO_CreateStringId("SI_SURVEYZONELIST_SETTINGS_ZONE_LIBTREASURE", "Определять зоны через LibTreasure")
ZO_CreateStringId("SI_SURVEYZONELIST_SETTINGS_ZONE_LIBTREASURE_DESC", "Если LibTreasure не знает предмет, например в совсем новой зоне, вместо этого разбирается название предмета.")

-- GUI : Champion point warning (issue #13)
ZO_CreateStringId("SI_SURVEYZONELIST_CP_WARNING", "«Обильный урожай» не вставлен")

-- Collect : craft of a survey, used only when LibTreasure does not know the item
SurveyZoneList.lang.craftFindName = {
    blacksmith = {"кузнец"},
    clothier   = {"портн"},
    woodworker = {"столяр", "дерев"},
    enchanter  = {"зачаров"},
    alchemist  = {"алхими"},
    jewelry    = {"ювелир"},
}

SurveyZoneList.lang.championPlentifulHarvest = "Обильный урожай"
