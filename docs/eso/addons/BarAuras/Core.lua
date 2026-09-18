-- Bar Auras — ядро: реестр источников (что могут дать бары) и трекер активных эффектов.

local BA = BarAuras

BA.name    = "BarAuras"
BA.version = "1.0"

local EM      = EVENT_MANAGER
local strfind = string.find

-- Резолв канонических аур -----------------------------------------------------

BA.byKey     = {}   -- key -> запись из BA.AURAS (с .name/.icon)
BA.keyByName = {}   -- локализованное имя -> key
BA.keyById   = {}   -- canonical abilityId -> key

local function Fmt(name)
    return zo_strformat(SI_ABILITY_NAME, name or "")
end
BA.Fmt = Fmt

function BA.ResolveAuras()
    BA.byKey, BA.keyByName, BA.keyById = {}, {}, {}
    for _, a in ipairs(BA.AURAS) do
        local id   = a.id
        local name = Fmt(GetAbilityName(id))
        if (name == "" or name == nil) and a.alt then
            id   = a.alt
            name = Fmt(GetAbilityName(id))
        end
        a.resolvedId = id
        a.name       = (name ~= "" and name) or a.key
        a.icon       = GetAbilityIcon(id)
        BA.byKey[a.key] = a
        if name ~= "" then BA.keyByName[name] = a.key end
        BA.keyById[a.id] = a.key
        if a.alt then BA.keyById[a.alt] = a.key end
    end
end

-- Реестр источников: что могут навесить скилы с баров --------------------------

BA.available = { buff = {}, debuff = {} }
BA.sources   = { buff = {}, debuff = {} }   -- key -> список имён скиллов, которые её дают
BA.barSkills = {}                           -- abilityId -> имя скилла

-- Скрайбленный грим лежит в слоте как craftedAbilityId (маленькое число), а не как
-- обычный abilityId. GetAbilityIdForCraftedAbilityId учитывает вставленные скрипты,
-- поэтому описание у полученного ID уже со всеми эффектами скриптов.
local function SlotAbilityId(slot, hotbar)
    local id = GetSlotBoundId(slot, hotbar)
    if not id or id == 0 then return nil end
    local slotType = GetSlotType(slot, hotbar)
    if slotType == ACTION_TYPE_CRAFTED_ABILITY or (id < 13 and IsCraftedAbilityScribed(id)) then
        local real = GetAbilityIdForCraftedAbilityId(id)
        if real and real ~= 0 then id = real end
    end
    return id
end

-- Источники собираются тремя независимыми сканерами в свои корзины, а потом
-- сливаются в BA.available/BA.sources. Каждый сканер пересчитывается только когда
-- его данные поменялись: бары дёргаются часто, сеты редко, пассивки почти никогда.
local collected = {
    bar     = { buff = {}, debuff = {} },
    set     = { buff = {}, debuff = {} },
    passive = { buff = {}, debuff = {} },
}

local function ClearBucket(bucket)
    for _, kind in pairs(bucket) do
        for k in pairs(kind) do kind[k] = nil end
    end
end

-- Единственное место, где описание превращается в список аур.
local function MatchDescription(desc, bucket, sourceName)
    if not desc or desc == "" or not sourceName or sourceName == "" then return end
    for _, a in ipairs(BA.AURAS) do
        if a.name and a.name ~= "" and strfind(desc, a.name, 1, true) then
            local list = bucket[a.kind][a.key]
            if not list then
                list = {}
                bucket[a.kind][a.key] = list
            end
            -- один сет может дать ауру несколькими бонусами, скилл — двумя барами
            local dup = false
            for _, n in ipairs(list) do
                if n == sourceName then dup = true break end
            end
            if not dup then list[#list + 1] = sourceName end
        end
    end
end

function BA.ScanBars()
    local bucket = collected.bar
    ClearBucket(bucket)
    local skills = {}

    local bars
    local activeBar = GetActiveHotbarCategory()
    if BA.sv.scanBothBars then
        bars = { HOTBAR_CATEGORY_PRIMARY, HOTBAR_CATEGORY_BACKUP }
        -- оборотень/вампир/ЧП подменяют хотбар целиком — он не PRIMARY и не BACKUP
        if activeBar ~= HOTBAR_CATEGORY_PRIMARY and activeBar ~= HOTBAR_CATEGORY_BACKUP then
            bars[#bars + 1] = activeBar
        end
    else
        bars = { activeBar }
    end

    local seen = {}
    for _, hotbar in ipairs(bars) do
        for slot = 3, 8 do
            local id = SlotAbilityId(slot, hotbar)
            if id and not seen[id] then
                seen[id] = true
                local skillName = Fmt(GetAbilityName(id))
                skills[id] = skillName
                MatchDescription(GetAbilityDescription(id, MAX_RANKS_PER_ABILITY, "player"),
                                 bucket, skillName)
            end
        end
    end

    BA.barSkills = skills
end

-- Надетые сеты: для каждого активного бонуса (набралось нужное число частей)
-- разбирается его текст. Мифики вроде Oakensoul Ring — это сет из одной части.
function BA.ScanGear()
    local bucket = collected.set
    ClearBucket(bucket)

    local seenSet = {}
    for slot = EQUIP_SLOT_ITERATION_BEGIN, EQUIP_SLOT_ITERATION_END do
        local link = GetItemLink(BAG_WORN, slot)
        if link and link ~= "" then
            local hasSet, setName, numBonuses, numEquipped = GetItemLinkSetInfo(link)
            local id = setName or link
            if hasSet and not seenSet[id] then
                seenSet[id] = true
                setName = zo_strformat(SI_UNIT_NAME, setName)
                for bonus = 1, (numBonuses or 0) do
                    local numRequired, desc = GetItemLinkSetBonusInfo(link, false, bonus)
                    if numRequired and numEquipped >= numRequired then
                        MatchDescription(desc, bucket, setName)
                    end
                end
            end
        end
    end
end

-- Изученные пассивки всех линий умений. Считается редко: только смена билда,
-- респек или покупка нового ранга.
function BA.ScanPassives()
    local bucket = collected.passive
    ClearBucket(bucket)

    for skillType = 1, GetNumSkillTypes() do
        for lineIndex = 1, GetNumSkillLines(skillType) do
            for abilityIndex = 1, GetNumSkillAbilities(skillType, lineIndex) do
                local name, _, _, passive, _, purchased
                    = GetSkillAbilityInfo(skillType, lineIndex, abilityIndex)
                if passive and purchased then
                    local id = GetSkillAbilityId(skillType, lineIndex, abilityIndex, false)
                    if id and id ~= 0 then
                        MatchDescription(GetAbilityDescription(id, MAX_RANKS_PER_ABILITY, "player"),
                                         bucket, Fmt(name))
                    end
                end
            end
        end
    end
end

-- Слияние корзин в то, чем пользуются фреймы и подсказки.
local ORIGIN_ORDER = { "bar", "set", "passive" }

BA.ORIGIN_LABEL = { bar = "скилл", set = "сет", passive = "пассивка" }

function BA.Rebuild()
    local avail = { buff = {}, debuff = {} }
    local srcs  = { buff = {}, debuff = {} }

    for _, origin in ipairs(ORIGIN_ORDER) do
        local enabled = (origin == "bar")
                        or (origin == "set" and BA.sv.useSets)
                        or (origin == "passive" and BA.sv.usePassives)
        if enabled then
            for kind, byKey in pairs(collected[origin]) do
                for key, names in pairs(byKey) do
                    avail[kind][key] = true
                    local list = srcs[kind][key]
                    if not list then
                        list = {}
                        srcs[kind][key] = list
                    end
                    for _, name in ipairs(names) do
                        list[#list + 1] = { name = name, origin = origin }
                    end
                end
            end
        end
    end

    BA.available = avail
    BA.sources   = srcs
    if BA.RefreshLayout then BA.RefreshLayout() end
end

-- Пересканирование пачкой: событий смены слота или предмета прилетает много подряд.
local dirty = { bar = true, set = true, passive = true }
local rescanQueued = false

function BA.QueueScan(what)
    if what then
        dirty[what] = true
    else
        dirty.bar, dirty.set, dirty.passive = true, true, true
    end
    if rescanQueued then return end
    rescanQueued = true
    zo_callLater(function()
        rescanQueued = false
        BA.ScanNow()
    end, 250)
end

function BA.ScanNow()
    if dirty.bar then BA.ScanBars() end
    if dirty.set then BA.ScanGear() end
    if dirty.passive then BA.ScanPassives() end
    dirty.bar, dirty.set, dirty.passive = false, false, false
    BA.Rebuild()
end

-- Трекер активных эффектов ----------------------------------------------------

BA.activeBuff   = {}   -- key -> { finish, start, icon, stacks, castByPlayer }
BA.activeDebuff = {}
BA.lastTargetAt = 0
BA.hasTarget    = false

-- Записи переиспользуются между тиками: опрос идёт 10 раз в секунду, и создавать
-- таблицу на каждый эффект — это лишний мусор для сборщика.
local function ScanUnit(unitTag, store, onlyMine)
    for _, rec in pairs(store) do rec.seen = false end

    local n = GetNumBuffs(unitTag)
    for i = 1, n do
        local name, start, finish, _, stacks, icon, _, _, _, _, abilityId, _, castByPlayer
            = GetUnitBuffInfo(unitTag, i)
        local key = BA.keyByName[Fmt(name)] or BA.keyById[abilityId]
        if key and not (onlyMine and not castByPlayer) then
            local rec = store[key]
            if not rec then
                rec = {}
                store[key] = rec
            end
            -- одну и ту же ауру могут держать несколько источников: берём ту, что дольше.
            -- Постоянная (timeStarted == timeEnding) выигрывает всегда.
            local isPerm  = (finish == 0) or (finish <= start)
            local recPerm = rec.seen and ((rec.finish == 0) or (rec.finish <= rec.start))
            if not rec.seen or isPerm or (not recPerm and finish > rec.finish) then
                rec.finish, rec.start        = finish, start
                rec.icon, rec.stacks         = icon, stacks
                rec.castByPlayer             = castByPlayer
            end
            rec.seen = true
        end
    end

    for key, rec in pairs(store) do
        if not rec.seen then store[key] = nil end
    end
end

local function TargetIsValid()
    if not DoesUnitExist("reticleover") then return false end
    if IsUnitDead("reticleover") then return false end
    if BA.sv.debuffs.hostileOnly and not IsUnitAttackable("reticleover") then return false end
    return true
end

function BA.Poll()
    ScanUnit("player", BA.activeBuff, false)

    local dsv = BA.sv.debuffs
    if dsv.enabled then
        if TargetIsValid() then
            ScanUnit("reticleover", BA.activeDebuff, dsv.onlyMine)
            BA.lastTargetAt = GetGameTimeSeconds()
            BA.hasTarget    = true
        else
            local keep = dsv.keepTarget or 0
            if keep <= 0 or GetGameTimeSeconds() - BA.lastTargetAt > keep then
                for k in pairs(BA.activeDebuff) do BA.activeDebuff[k] = nil end
                BA.hasTarget = false
            end
        end
    end

    BA.UpdateFrames()
end

function BA.RestartPoll()
    EM:UnregisterForUpdate(BA.name .. "Poll")
    EM:RegisterForUpdate(BA.name .. "Poll", BA.sv.pollMs or 100, BA.Poll)
end

-- Состояние окружения ----------------------------------------------------------

BA.inCombat = false
BA.isInTown = false

local function OnCombatState(_, inCombat)
    BA.inCombat = inCombat
    BA.RefreshVisibility()
end

local function OnPlayerActivated()
    -- как в GCDBar: город/интерьер = субзона без типа контента (данж = зона + DUNGEON)
    BA.isInTown = (GetMapType() == MAPTYPE_SUBZONE) and (GetMapContentType() == MAP_CONTENT_NONE)
    BA.inCombat = IsUnitInCombat("player")
    BA.QueueScan()
    BA.RefreshVisibility()
end

-- Инициализация ----------------------------------------------------------------

BA.defaults = {
    scanBothBars = true,
    useSets      = true,
    usePassives  = true,
    hideForeign  = false,
    tooltips     = true,
    pollMs       = 100,
    show         = {},
    buffs = {
        enabled      = true,
        x            = 500,
        y            = 700,
        orientation  = "row",
        iconSize     = 42,
        spacing      = 4,
        fontSize     = 18,
        showNames    = false,
        showInactive = true,
        sort         = "fixed",
        warnAt       = 3,
        decimals     = true,
        radial       = true,
        radialAlpha  = 55,
        alpha        = 100,
        fadeOOC      = false,
        oocAlpha     = 40,
        fadeDelay    = 3,
        hideInTown   = false,
        hideEmpty    = false,
        permanent    = "last",
        permScale    = 100,
    },
    debuffs = {
        enabled      = true,
        x            = 500,
        y            = 770,
        orientation  = "row",
        iconSize     = 42,
        spacing      = 4,
        fontSize     = 18,
        showNames    = false,
        showInactive = true,
        sort         = "fixed",
        warnAt       = 3,
        decimals     = true,
        radial       = true,
        radialAlpha  = 55,
        alpha        = 100,
        fadeOOC      = false,
        oocAlpha     = 40,
        fadeDelay    = 3,
        hideInTown   = false,
        hideEmpty    = true,
        permanent    = "last",
        permScale    = 100,
        onlyMine     = false,
        hostileOnly  = true,
        keepTarget   = 0,
    },
}

local function OnAddOnLoaded(_, addonName)
    if addonName ~= BA.name then return end
    EM:UnregisterForEvent(BA.name, EVENT_ADD_ON_LOADED)

    BA.sv = ZO_SavedVars:NewCharacterIdSettings("BarAurasSV", 1, nil, BA.defaults)

    BA.ResolveAuras()
    BA.BuildFrames()
    BA.BuildMenu()

    EM:RegisterForEvent(BA.name .. "Combat", EVENT_PLAYER_COMBAT_STATE, OnCombatState)
    EM:RegisterForEvent(BA.name .. "Zone",   EVENT_PLAYER_ACTIVATED,    OnPlayerActivated)

    -- Каждая корзина пересобирается только по своим событиям: бары дёргаются часто,
    -- сеты редко, пассивки почти никогда.
    local rescanEvents = {
        bar = {
            EVENT_ACTION_SLOTS_ALL_HOTBARS_UPDATED,
            EVENT_ACTION_SLOTS_ACTIVE_HOTBAR_UPDATED,
            EVENT_ACTION_SLOT_UPDATED,
            EVENT_ACTIVE_WEAPON_PAIR_CHANGED,
            EVENT_HOTBAR_SLOT_STATE_UPDATED,
            EVENT_CRAFTED_ABILITY_LOCK_STATE_CHANGED,
            EVENT_CRAFTED_ABILITY_SCRIPT_LOCK_STATE_CHANGED,
        },
        passive = {
            EVENT_SKILLS_FULL_UPDATE,
            EVENT_SKILL_RANK_UPDATE,
            EVENT_SKILL_POINTS_CHANGED,
            EVENT_SKILL_LINE_ADDED,
            EVENT_SKILL_RESPEC_RESULT,
        },
    }
    for what, events in pairs(rescanEvents) do
        for i, ev in ipairs(events) do
            EM:RegisterForEvent(BA.name .. what .. i, ev, function()
                BA.QueueScan(what)
            end)
        end
    end

    -- смена надетого: фильтр по BAG_WORN, иначе прилетит каждый предмет в сумке
    EM:RegisterForEvent(BA.name .. "Worn", EVENT_INVENTORY_SINGLE_SLOT_UPDATE, function()
        BA.QueueScan("set")
    end)
    EM:AddFilterForEvent(BA.name .. "Worn", EVENT_INVENTORY_SINGLE_SLOT_UPDATE,
                         REGISTER_FILTER_BAG_ID, BAG_WORN)

    -- восстановление билда из армори меняет разом и бары, и сеты, и пассивки
    EM:RegisterForEvent(BA.name .. "Armory", EVENT_ARMORY_BUILD_RESTORE_RESPONSE, function()
        BA.QueueScan()
    end)

    BA.ScanNow()
    BA.RestartPoll()
    BA.RefreshVisibility()

    SLASH_COMMANDS["/baraura"]  = BA.SlashCommand
    SLASH_COMMANDS["/barauras"] = BA.SlashCommand
end

EM:RegisterForEvent(BA.name, EVENT_ADD_ON_LOADED, OnAddOnLoaded)

-- Копирование настроек с другого персонажа ---------------------------------------

-- Структура файла сохранёнок: BarAurasSV["Default"]["@аккаунт"]["<characterId>"].
-- Обход не завязан на имена уровней: ищем таблицы, у которых есть $LastCharacterName,
-- который ZO_SavedVars проставляет каждому персонажу сам.
function BA.CollectCharacters()
    local found = {}
    local raw = BarAurasSV
    if type(raw) ~= "table" then return found end

    local current = tostring(GetCurrentCharacterId())
    for _, profile in pairs(raw) do
        if type(profile) == "table" then
            for _, account in pairs(profile) do
                if type(account) == "table" then
                    for charId, data in pairs(account) do
                        if type(data) == "table" and data["$LastCharacterName"]
                           and tostring(charId) ~= current then
                            found[#found + 1] = {
                                id   = tostring(charId),
                                name = zo_strformat(SI_UNIT_NAME, data["$LastCharacterName"]),
                                data = data,
                            }
                        end
                    end
                end
            end
        end
    end

    table.sort(found, function(l, r) return l.name < r.name end)
    return found
end

local COPY_SCALARS = { "scanBothBars", "useSets", "usePassives", "hideForeign", "tooltips", "pollMs" }

-- Значения переписываются на месте: фреймы держат ссылки на BA.sv.buffs/.debuffs,
-- и подмена таблицы целиком оставила бы их со старыми настройками.
function BA.CopySettingsFrom(src)
    if type(src) ~= "table" then return false end

    for _, k in ipairs(COPY_SCALARS) do
        if src[k] ~= nil then BA.sv[k] = src[k] end
    end

    for _, group in ipairs({ "buffs", "debuffs" }) do
        if type(src[group]) == "table" then
            local dst = BA.sv[group]
            for k in pairs(BA.defaults[group]) do
                if src[group][k] ~= nil then dst[k] = src[group][k] end
            end
        end
    end

    if type(src.show) == "table" then
        local dst = BA.sv.show
        for k in pairs(dst) do dst[k] = nil end
        for k, v in pairs(src.show) do dst[k] = v end
    end

    BA.RestartPoll()
    BA.RefreshLayout()
    return true
end

-- Слэш-команды ------------------------------------------------------------------

function BA.SlashCommand(arg)
    arg = string.lower(arg or "")
    if arg == "list" then
        d("|cffcc00Bar Auras|r — скилы на барах:")
        for id, name in pairs(BA.barSkills) do
            d(string.format("  %s (%d)", name, id))
        end

        d("|cffcc00Найденные источники:|r")
        for _, a in ipairs(BA.AURAS) do
            local sources = BA.sources[a.kind][a.key]
            if sources then
                local parts = {}
                for i, s in ipairs(sources) do
                    parts[i] = string.format("%s (%s)", s.name, BA.ORIGIN_LABEL[s.origin] or s.origin)
                end
                d(string.format("  [%s] %s  <- %s", a.kind, a.name, table.concat(parts, ", ")))
            end
        end

        -- висит, но источник не найден: групповой бафф, зелье или промах разбора
        d("|cffcc00Активно сейчас, но источник не найден:|r")
        local found = false
        for _, a in ipairs(BA.AURAS) do
            local store = (a.kind == "buff") and BA.activeBuff or BA.activeDebuff
            if store[a.key] and not BA.available[a.kind][a.key] then
                found = true
                d(string.format("  [%s] %s", a.kind, a.name))
            end
        end
        if not found then d("  (пусто)") end
    elseif arg == "ids" then
        -- проверка канонических ID: если имя выглядит не как название ауры, ID промахнулся
        d("|cffcc00Bar Auras|r — резолв ID:")
        for _, a in ipairs(BA.AURAS) do
            d(string.format("  %s = %d -> %s", a.key, a.resolvedId, a.name))
        end
    elseif arg == "scan" then
        BA.QueueScan()
        d("|cffcc00Bar Auras|r: источники пересканируются.")
    else
        BA.ToggleUnlock()
    end
end
