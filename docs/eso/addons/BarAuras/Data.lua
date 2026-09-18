-- Канонические ID общих (shared) аур Major/Minor.
--
-- Имя и иконка резолвятся рантаймом через GetAbilityName/GetAbilityIcon, поэтому таблица
-- не зависит от языка клиента: в ней только числа. alt — запасной ID на случай, если у
-- основного GetAbilityName вернёт пустоту (у части аур в игре несколько равнозначных ID,
-- источники в комьюнити расходятся).
--
-- kind: buff  — вешается на игрока, идёт в верхний фрейм
--       debuff — вешается на цель, идёт в нижний фрейм
-- cat:  только для группировки в настройках и порядка вывода.

BarAuras = BarAuras or {}
local BA = BarAuras

BA.AURAS = {
    -- ---- урон ----------------------------------------------------------
    { key = "majorBerserk",     id = 62195,  alt = 61745, kind = "buff",   cat = "damage" },
    { key = "minorBerserk",     id = 61744,               kind = "buff",   cat = "damage" },
    { key = "majorSlayer",      id = 93109,  alt = 93442, kind = "buff",   cat = "damage" },
    { key = "minorSlayer",      id = 147226, alt = 76617, kind = "buff",   cat = "damage" },
    { key = "majorForce",       id = 61747,               kind = "buff",   cat = "damage" },
    { key = "minorForce",       id = 61746,               kind = "buff",   cat = "damage" },
    { key = "empower",          id = 61737,               kind = "buff",   cat = "damage" },

    -- ---- сила оружия/заклинаний ----------------------------------------
    { key = "majorBrutality",   id = 61665,               kind = "buff",   cat = "power" },
    { key = "minorBrutality",   id = 61662,               kind = "buff",   cat = "power" },
    { key = "majorSorcery",     id = 61687,               kind = "buff",   cat = "power" },
    { key = "minorSorcery",     id = 61685,               kind = "buff",   cat = "power" },
    { key = "majorSavagery",    id = 61667,               kind = "buff",   cat = "power" },
    { key = "minorSavagery",    id = 61666,               kind = "buff",   cat = "power" },
    { key = "majorProphecy",    id = 61689,               kind = "buff",   cat = "power" },
    { key = "minorProphecy",    id = 61691,               kind = "buff",   cat = "power" },
    { key = "majorCourage",     id = 109966,              kind = "buff",   cat = "power" },
    { key = "minorCourage",     id = 147417,              kind = "buff",   cat = "power" },

    -- ---- защита ---------------------------------------------------------
    { key = "majorResolve",     id = 61694,               kind = "buff",   cat = "defense" },
    { key = "minorResolve",     id = 61693,               kind = "buff",   cat = "defense" },
    { key = "majorProtection",  id = 61722,               kind = "buff",   cat = "defense" },
    { key = "minorProtection",  id = 61721,               kind = "buff",   cat = "defense" },
    { key = "majorEvasion",     id = 61716,               kind = "buff",   cat = "defense" },
    { key = "minorEvasion",     id = 184933, alt = 61715, kind = "buff",   cat = "defense" },
    { key = "majorAegis",       id = 93123,  alt = 93444, kind = "buff",   cat = "defense" },
    { key = "minorAegis",       id = 147225, alt = 76618, kind = "buff",   cat = "defense" },
    { key = "minorToughness",   id = 88490,               kind = "buff",   cat = "defense" },

    -- ---- восстановление / поддержка ------------------------------------
    { key = "majorIntellect",   id = 61707,               kind = "buff",   cat = "sustain" },
    { key = "minorIntellect",   id = 61706,               kind = "buff",   cat = "sustain" },
    { key = "majorEndurance",   id = 61705,               kind = "buff",   cat = "sustain" },
    { key = "minorEndurance",   id = 61704,               kind = "buff",   cat = "sustain" },
    { key = "majorFortitude",   id = 68405,  alt = 61698, kind = "buff",   cat = "sustain" },
    { key = "minorFortitude",   id = 61697,               kind = "buff",   cat = "sustain" },
    { key = "majorHeroism",     id = 61709,               kind = "buff",   cat = "sustain" },
    { key = "minorHeroism",     id = 61708,               kind = "buff",   cat = "sustain" },
    { key = "majorMending",     id = 61711,               kind = "buff",   cat = "sustain" },
    { key = "minorMending",     id = 61710,               kind = "buff",   cat = "sustain" },
    { key = "majorVitality",    id = 61713,               kind = "buff",   cat = "sustain" },
    { key = "minorVitality",    id = 61549,               kind = "buff",   cat = "sustain" },

    -- ---- подвижность ----------------------------------------------------
    { key = "majorExpedition",  id = 61736,               kind = "buff",   cat = "mobility" },
    { key = "minorExpedition",  id = 61735,               kind = "buff",   cat = "mobility" },
    -- Major Gallop (63569) намеренно не отслеживается: это баф скорости маунта, к бою
    -- отношения не имеет и висит постоянно. Вернуть — расскомментировать строку.
    -- { key = "majorGallop",   id = 63569,               kind = "buff",   cat = "mobility" },

    -- ---- дебаффы на цели ------------------------------------------------
    { key = "majorBreach",      id = 61743,               kind = "debuff", cat = "resist" },
    { key = "minorBreach",      id = 61742,               kind = "debuff", cat = "resist" },
    { key = "majorBrittle",     id = 145977,              kind = "debuff", cat = "resist" },
    { key = "minorBrittle",     id = 145975,              kind = "debuff", cat = "resist" },
    { key = "majorVulnerability", id = 106754,            kind = "debuff", cat = "resist" },
    { key = "minorVulnerability", id = 79717,             kind = "debuff", cat = "resist" },
    { key = "majorMaim",        id = 61725,               kind = "debuff", cat = "offense" },
    { key = "minorMaim",        id = 61723,               kind = "debuff", cat = "offense" },
    { key = "majorCowardice",   id = 147643,              kind = "debuff", cat = "offense" },
    { key = "minorCowardice",   id = 79867,               kind = "debuff", cat = "offense" },
    { key = "majorDefile",      id = 61727,               kind = "debuff", cat = "offense" },
    { key = "minorDefile",      id = 61726,               kind = "debuff", cat = "offense" },
    { key = "minorEnervation",  id = 79907,               kind = "debuff", cat = "offense" },
    { key = "minorUncertainty", id = 79895,               kind = "debuff", cat = "offense" },
    { key = "minorTimidity",    id = 140699,              kind = "debuff", cat = "offense" },
    { key = "minorMangle",      id = 61733,               kind = "debuff", cat = "offense" },
    { key = "minorLifesteal",   id = 86304,               kind = "debuff", cat = "utility" },
    { key = "minorMagickasteal", id = 88401,              kind = "debuff", cat = "utility" },
}

BA.CAT_NAMES = {
    damage   = "Урон",
    power    = "Сила оружия и заклинаний",
    defense  = "Защита",
    sustain  = "Восстановление",
    mobility = "Подвижность",
    resist   = "Сопротивления цели",
    offense  = "Урон и лечение цели",
    utility  = "Прочее",
}
