-- Bar Auras — панель настроек (LibAddonMenu-2.0).

local BA = BarAuras

local function Refresh()
    BA.RefreshLayout()
end

local function FrameOptions(kind)
    local function sv()
        return (kind == "buff") and BA.sv.buffs or BA.sv.debuffs
    end

    local controls = {
        {
            type    = "checkbox",
            name    = "Включить фрейм",
            getFunc = function() return sv().enabled end,
            setFunc = function(v) sv().enabled = v; Refresh() end,
        },
        {
            type          = "dropdown",
            name          = "Расположение",
            tooltip       = "Иконки выстраиваются в ряд по горизонтали или в столбец по вертикали.",
            choices       = { "Ряд", "Столбец" },
            choicesValues = { "row", "column" },
            getFunc       = function() return sv().orientation end,
            setFunc       = function(v) sv().orientation = v; Refresh() end,
        },
        {
            type    = "slider",
            name    = "Размер иконки",
            min     = 20, max = 96, step = 2,
            getFunc = function() return sv().iconSize end,
            setFunc = function(v) sv().iconSize = v; Refresh() end,
        },
        {
            type    = "slider",
            name    = "Промежуток между иконками",
            min     = 0, max = 30, step = 1,
            getFunc = function() return sv().spacing end,
            setFunc = function(v) sv().spacing = v; Refresh() end,
        },
        {
            type    = "slider",
            name    = "Размер шрифта таймера",
            min     = 10, max = 40, step = 1,
            getFunc = function() return sv().fontSize end,
            setFunc = function(v) sv().fontSize = v; Refresh() end,
        },
        {
            type    = "checkbox",
            name    = "Показывать названия",
            tooltip = "Подпись под иконкой. Ест место, но в начале помогает запомнить иконки.",
            getFunc = function() return sv().showNames end,
            setFunc = function(v) sv().showNames = v; Refresh() end,
        },
        {
            type    = "checkbox",
            name    = "Показывать неактивные (серые)",
            tooltip = "Ауры, у которых есть источник (бар, сет или пассивка), но которые " ..
                      "сейчас не висят, показываются тусклой иконкой. Позиции не прыгают, " ..
                      "сразу видно, чего не хватает.",
            getFunc = function() return sv().showInactive end,
            setFunc = function(v) sv().showInactive = v; Refresh() end,
        },
        {
            type          = "dropdown",
            name          = "Порядок",
            tooltip       = "Фиксированный — иконки всегда на одном месте. По времени — " ..
                            "ближайшие к истечению первыми, но иконки скачут.",
            choices       = { "Фиксированный", "По времени" },
            choicesValues = { "fixed", "time" },
            getFunc       = function() return sv().sort end,
            setFunc       = function(v) sv().sort = v; Refresh() end,
        },
        {
            type          = "dropdown",
            name          = "Постоянные ауры",
            tooltip       = "Ауры без отсчёта: Restoring Aura, пока она в слоте, вся пачка с " ..
                            "Oakensoul Ring, бафы от пассивок. Прожимать их не надо, поэтому " ..
                            "по умолчанию они уезжают в конец, чтобы не разрывать ряд " ..
                            "тех, за которыми следишь.",
            choices       = { "В общем порядке", "В конце", "Скрывать" },
            choicesValues = { "inline", "last", "hide" },
            getFunc       = function() return sv().permanent end,
            setFunc       = function(v) sv().permanent = v; Refresh() end,
        },
        {
            type     = "slider",
            name     = "Размер постоянных, % от обычного",
            tooltip  = "Позволяет держать их мельче: висят всегда, следить за ними не нужно.",
            min      = 40, max = 100, step = 5,
            disabled = function() return sv().permanent == "hide" end,
            getFunc  = function() return sv().permScale end,
            setFunc  = function(v) sv().permScale = v; Refresh() end,
        },
        {
            type    = "slider",
            name    = "Предупреждать при остатке, сек",
            tooltip = "Таймер краснеет, когда осталось меньше указанного. 0 — выключить.",
            min     = 0, max = 15, step = 1,
            getFunc = function() return sv().warnAt end,
            setFunc = function(v) sv().warnAt = v end,
        },
        {
            type    = "checkbox",
            name    = "Десятые доли под конец",
            tooltip = "При остатке меньше 5 секунд показывать 4.3 вместо 5.",
            getFunc = function() return sv().decimals end,
            setFunc = function(v) sv().decimals = v end,
        },
        {
            type    = "checkbox",
            name    = "Радиальное затемнение иконки",
            tooltip = "Иконка затемняется по кругу по мере истечения ауры.",
            getFunc = function() return sv().radial end,
            setFunc = function(v) sv().radial = v; Refresh() end,
        },
        {
            type     = "slider",
            name     = "Сила затемнения, %",
            tooltip  = "0 — затемнения не видно, 90 — иконка под ним почти чёрная.",
            min      = 0, max = 90, step = 5,
            disabled = function() return not sv().radial end,
            getFunc  = function() return sv().radialAlpha end,
            setFunc  = function(v) sv().radialAlpha = v end,
        },
        {
            type    = "slider",
            name    = "Непрозрачность, %",
            min     = 10, max = 100, step = 5,
            getFunc = function() return sv().alpha end,
            setFunc = function(v) sv().alpha = v; BA.RefreshVisibility() end,
        },
        {
            type    = "checkbox",
            name    = "Гасить вне боя",
            getFunc = function() return sv().fadeOOC end,
            setFunc = function(v) sv().fadeOOC = v; BA.RefreshVisibility() end,
        },
        {
            type     = "slider",
            name     = "Непрозрачность вне боя, %",
            min      = 0, max = 100, step = 5,
            disabled = function() return not sv().fadeOOC end,
            getFunc  = function() return sv().oocAlpha end,
            setFunc  = function(v) sv().oocAlpha = v; BA.RefreshVisibility() end,
        },
        {
            type     = "slider",
            name     = "Задержка гашения, сек",
            min      = 0, max = 30, step = 1,
            disabled = function() return not sv().fadeOOC end,
            getFunc  = function() return sv().fadeDelay end,
            setFunc  = function(v) sv().fadeDelay = v end,
        },
        {
            type    = "checkbox",
            name    = "Прятать в городах",
            tooltip = "Город/интерьер определяется как субзона без типа контента. В бою фрейм " ..
                      "показывается всегда.",
            getFunc = function() return sv().hideInTown end,
            setFunc = function(v) sv().hideInTown = v; BA.RefreshVisibility() end,
        },
        {
            type    = "checkbox",
            name    = "Прятать, когда пусто",
            getFunc = function() return sv().hideEmpty end,
            setFunc = function(v) sv().hideEmpty = v; Refresh() end,
        },
    }

    if kind == "debuff" then
        local extra = {
            {
                type    = "checkbox",
                name    = "Только мои дебаффы",
                tooltip = "Скрывать дебаффы, наложенные не тобой (например, Major Breach от танка).",
                getFunc = function() return sv().onlyMine end,
                setFunc = function(v) sv().onlyMine = v end,
            },
            {
                type    = "checkbox",
                name    = "Только враждебные цели",
                tooltip = "Не показывать фрейм при наведении на своих и нейтральных NPC.",
                getFunc = function() return sv().hostileOnly end,
                setFunc = function(v) sv().hostileOnly = v end,
            },
            {
                type    = "slider",
                name    = "Держать последнюю цель, сек",
                tooltip = "Сколько секунд оставлять дебаффы на экране после того, как увёл прицел. " ..
                          "0 — очищать сразу.",
                min     = 0, max = 15, step = 1,
                getFunc = function() return sv().keepTarget end,
                setFunc = function(v) sv().keepTarget = v end,
            },
        }
        for _, c in ipairs(extra) do controls[#controls + 1] = c end
    end

    return controls
end

local function CopyFromCharacterOptions()
    local chars = BA.CollectCharacters()
    if #chars == 0 then
        return {
            {
                type = "description",
                text = "В сохранёнках пока нет других персонажей. Персонаж попадает туда после " ..
                       "того, как заходил в игру с включённым аддоном.",
            },
        }
    end

    local names = {}
    for i, c in ipairs(chars) do names[i] = c.name end
    local selected = names[1]

    return {
        {
            type    = "description",
            text    = "Переносит всё: раскладку обоих фреймов, их позиции, видимость и галки по " ..
                      "отдельным аурам. Текущие настройки персонажа при этом затираются.",
        },
        {
            type    = "dropdown",
            name    = "Персонаж-источник",
            choices = names,
            getFunc = function() return selected end,
            setFunc = function(v) selected = v end,
            width   = "full",
        },
        {
            type        = "button",
            name        = "Скопировать настройки",
            warning     = "Настройки текущего персонажа будут перезаписаны.",
            isDangerous = true,
            width       = "full",
            func        = function()
                for _, c in ipairs(chars) do
                    if c.name == selected then
                        if BA.CopySettingsFrom(c.data) then
                            d(string.format("|cffcc00Bar Auras|r: настройки скопированы с %s.", c.name))
                        end
                        return
                    end
                end
            end,
        },
    }
end

local function AuraToggles(kind)
    local byCat, catOrder = {}, {}
    for _, a in ipairs(BA.AURAS) do
        if a.kind == kind then
            if not byCat[a.cat] then
                byCat[a.cat] = {}
                catOrder[#catOrder + 1] = a.cat
            end
            local list = byCat[a.cat]
            list[#list + 1] = a
        end
    end

    local controls = {}
    for _, cat in ipairs(catOrder) do
        controls[#controls + 1] = { type = "header", name = BA.CAT_NAMES[cat] or cat }
        for _, a in ipairs(byCat[cat]) do
            local key = a.key
            controls[#controls + 1] = {
                type    = "checkbox",
                width   = "half",
                name    = zo_iconFormat(a.icon, 24, 24) .. " " .. a.name,
                tooltip = function()
                    if not BA.available[kind][key] then
                        return "Источник не найден: ни бары, ни сеты, ни пассивки её не дают."
                    end
                    local parts = {}
                    for i, s in ipairs(BA.sources[kind][key] or {}) do
                        parts[i] = string.format("%s (%s)", s.name,
                                                 BA.ORIGIN_LABEL[s.origin] or s.origin)
                    end
                    return "Источники: " .. table.concat(parts, ", ")
                end,
                getFunc = function() return BA.sv.show[key] ~= false end,
                setFunc = function(v) BA.sv.show[key] = v or nil; Refresh() end,
            }
        end
    end
    return controls
end

function BA.BuildMenu()
    local LAM = LibAddonMenu2
    if not LAM then return end

    LAM:RegisterAddonPanel("BarAurasOptions", {
        type               = "panel",
        name               = "Bar Auras",
        displayName        = "|cffcc00Bar Auras|r",
        author             = "yelowhut",
        version            = BA.version,
        registerForRefresh = true,
    })

    local options = {
        {
            type = "description",
            text = "Показывает Major/Minor ауры, которые могут навесить скилы, стоящие сейчас " ..
                   "на твоих барах (скрайбинг учитывается). Команды: |cffcc00/baraura|r — " ..
                   "разблокировать фреймы для перетаскивания, |cffcc00/baraura list|r — что " ..
                   "аддон нашёл на барах.",
        },
        {
            type    = "button",
            name    = "Разблокировать / зафиксировать фреймы",
            tooltip = "В разблокированном виде фреймы тащатся мышью и показывают все доступные ауры.",
            func    = function() BA.ToggleUnlock() end,
            width   = "full",
        },
        { type = "header", name = "Источники" },
        {
            type    = "checkbox",
            name    = "Учитывать оба бара",
            tooltip = "Выключено — учитывается только активный бар. Баффы с заднего бара часто " ..
                      "висят и после свапа, так что по умолчанию включено.",
            getFunc = function() return BA.sv.scanBothBars end,
            setFunc = function(v) BA.sv.scanBothBars = v; BA.QueueScan("bar") end,
        },
        {
            type    = "checkbox",
            name    = "Учитывать надетые сеты",
            tooltip = "Разбираются тексты бонусов, у которых набралось нужное число частей. " ..
                      "Так находятся Oakensoul Ring, Berserking Warrior и прочие ауры от шмота.",
            getFunc = function() return BA.sv.useSets end,
            setFunc = function(v) BA.sv.useSets = v; BA.Rebuild() end,
        },
        {
            type    = "checkbox",
            name    = "Учитывать изученные пассивки",
            tooltip = "Пассивки часто дают Minor-ауры по условию. Если от этого в ряду " ..
                      "становится слишком людно — выключи.",
            getFunc = function() return BA.sv.usePassives end,
            setFunc = function(v) BA.sv.usePassives = v; BA.Rebuild() end,
        },
        {
            type    = "checkbox",
            name    = "Скрывать ауры без известного источника",
            tooltip = "Аура, которую не дают ни бары, ни сеты, ни пассивки (групповой бафф, " ..
                      "зелье), по умолчанию всё равно показывается, раз она на тебе висит. " ..
                      "Включи, чтобы видеть строго своё.",
            getFunc = function() return BA.sv.hideForeign end,
            setFunc = function(v) BA.sv.hideForeign = v; Refresh() end,
        },
        {
            type    = "checkbox",
            name    = "Подсказки при наведении",
            tooltip = "Название ауры и список скиллов с баров, которые её дают. Видна, когда " ..
                      "в игре показан курсор (в меню или в режиме перемещения фреймов).",
            getFunc = function() return BA.sv.tooltips end,
            setFunc = function(v) BA.sv.tooltips = v; Refresh() end,
        },
        {
            type    = "slider",
            name    = "Период обновления, мс",
            tooltip = "Чаще — плавнее таймеры и чуть выше нагрузка.",
            min     = 50, max = 250, step = 10,
            getFunc = function() return BA.sv.pollMs end,
            setFunc = function(v) BA.sv.pollMs = v; BA.RestartPoll() end,
        },
        {
            type    = "button",
            name    = "Пересканировать источники",
            func    = function() BA.QueueScan() end,
        },
        {
            type     = "submenu",
            name     = "Баффы на себе",
            controls = FrameOptions("buff"),
        },
        {
            type     = "submenu",
            name     = "Дебаффы на цели",
            controls = FrameOptions("debuff"),
        },
        {
            type     = "submenu",
            name     = "Скопировать настройки с другого персонажа",
            controls = CopyFromCharacterOptions(),
        },
        {
            type     = "submenu",
            name     = "Какие баффы показывать",
            controls = AuraToggles("buff"),
        },
        {
            type     = "submenu",
            name     = "Какие дебаффы показывать",
            controls = AuraToggles("debuff"),
        },
    }

    LAM:RegisterOptionControls("BarAurasOptions", options)
end
