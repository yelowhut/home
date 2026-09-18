-- Bar Auras — отрисовка: два фрейма (баффы на себе / дебаффы на цели).
--
-- Иерархия контролов:
--   tlw (top level, двигается мышью)
--     bg     — подложка, видна только в режиме настройки
--     holder — на нём меняется прозрачность (у tlw ею управляет HUD-фрагмент сцены)
--       icon[i]
--         tex / cd / timer / label

local BA = BarAuras
local WM = WINDOW_MANAGER

BA.frames   = {}
BA.unlocked = false

local NAME_HEIGHT_RATIO = 0.40   -- высота подписи в долях от размера иконки

local function FontString(size, bold)
    return string.format("%s|%d|soft-shadow-thick", bold and "$(BOLD_FONT)" or "$(MEDIUM_FONT)", size)
end

local function FormatTime(remain, decimals)
    if remain >= 60 then
        return string.format("%d:%02d", remain / 60, remain % 60)
    elseif decimals and remain < 5 then
        return string.format("%.1f", remain)
    end
    return string.format("%d", zo_ceil(remain))
end

-- Подсказка ---------------------------------------------------------------------

local TOOLTIP_TITLE_FONT = "$(BOLD_FONT)|20|soft-shadow-thick"
local TOOLTIP_LINE_FONT  = "$(MEDIUM_FONT)|16|soft-shadow-thin"

-- цвет строки источника говорит, откуда он: скилл с бара, сет или пассивка
local ORIGIN_COLOR = {
    bar     = { 0.95, 0.95, 0.95 },
    set     = { 0.55, 0.80, 1.00 },
    passive = { 0.70, 0.70, 0.62 },
}

local function OnIconEnter(c)
    local a = c.aura
    if not a then return end

    InitializeTooltip(InformationTooltip, c, BOTTOM, 0, -8)
    InformationTooltip:AddLine(a.name, TOOLTIP_TITLE_FONT, 1, 0.82, 0.10)

    local sources = BA.sources[a.kind][a.key]
    if sources and #sources > 0 then
        for _, s in ipairs(sources) do
            local color = ORIGIN_COLOR[s.origin] or ORIGIN_COLOR.bar
            local label = BA.ORIGIN_LABEL[s.origin]
            local text  = (s.origin == "bar") and s.name
                          or string.format("%s (%s)", s.name, label or s.origin)
            InformationTooltip:AddLine(text, TOOLTIP_LINE_FONT, color[1], color[2], color[3])
        end
    else
        InformationTooltip:AddLine("Источник не найден", TOOLTIP_LINE_FONT, 0.6, 0.6, 0.6)
    end
end

local function OnIconExit()
    ClearTooltip(InformationTooltip)
end

-- Создание контролов -----------------------------------------------------------

local function CreateIcon(f, index)
    local base = f.tlw:GetName() .. "Icon" .. index
    local c    = WM:CreateControl(base, f.holder, CT_CONTROL)

    c.tex = WM:CreateControl(base .. "Tex", c, CT_TEXTURE)
    c.tex:SetAnchor(TOPLEFT, c, TOPLEFT, 0, 0)

    c.cd = WM:CreateControl(base .. "CD", c, CT_COOLDOWN)
    c.cd:SetAnchor(TOPLEFT, c, TOPLEFT, 0, 0)
    c.cd:SetHidden(true)

    c.timer = WM:CreateControl(base .. "Timer", c, CT_LABEL)
    c.timer:SetAnchor(CENTER, c.tex, CENTER, 0, 0)
    c.timer:SetHorizontalAlignment(TEXT_ALIGN_CENTER)
    c.timer:SetVerticalAlignment(TEXT_ALIGN_CENTER)
    c.timer:SetDrawLayer(DL_OVERLAY)

    c.label = WM:CreateControl(base .. "Name", c, CT_LABEL)
    c.label:SetAnchor(TOP, c.tex, BOTTOM, 0, 1)
    c.label:SetHorizontalAlignment(TEXT_ALIGN_CENTER)

    c:SetHandler("OnMouseEnter", OnIconEnter)
    c:SetHandler("OnMouseExit", OnIconExit)

    -- Иконка с включённой мышью перехватывает клик у top-level окна, и фрейм перестаёт
    -- таскаться. Поэтому в режиме настройки тащим родителя руками.
    c:SetHandler("OnMouseDown", function(_, button)
        if BA.unlocked and button == MOUSE_BUTTON_INDEX_LEFT then
            f.tlw:StartMoving()
        end
    end)
    c:SetHandler("OnMouseUp", function(_, button)
        if BA.unlocked and button == MOUSE_BUTTON_INDEX_LEFT then
            f.tlw:StopMovingOrResizing()
            f.sv.x = f.tlw:GetLeft()
            f.sv.y = f.tlw:GetTop()
        end
    end)

    f.icons[index] = c
    return c
end

local function CreateFrame(kind)
    local sv  = (kind == "buff") and BA.sv.buffs or BA.sv.debuffs
    local tlw = WM:CreateTopLevelWindow("BarAuras_" .. kind)
    tlw:SetClampedToScreen(true)
    tlw:SetMouseEnabled(false)
    tlw:SetMovable(false)
    tlw:SetDimensions(200, 60)
    tlw:ClearAnchors()
    tlw:SetAnchor(TOPLEFT, GuiRoot, TOPLEFT, sv.x, sv.y)

    local bg = WM:CreateControl(tlw:GetName() .. "BG", tlw, CT_BACKDROP)
    bg:SetAnchorFill(tlw)
    bg:SetCenterColor(0, 0, 0, 0.45)
    bg:SetEdgeColor(1, 0.8, 0.2, 0.8)
    bg:SetHidden(true)

    local holder = WM:CreateControl(tlw:GetName() .. "Holder", tlw, CT_CONTROL)
    holder:SetAnchorFill(tlw)

    local f = {
        kind   = kind,
        sv     = sv,
        tlw    = tlw,
        bg     = bg,
        holder = holder,
        icons  = {},
        list   = {},
        pool   = {},
    }

    tlw:SetHandler("OnMoveStop", function()
        f.sv.x = tlw:GetLeft()
        f.sv.y = tlw:GetTop()
    end)

    f.fragment = ZO_HUDFadeSceneFragment:New(tlw)
    HUD_SCENE:AddFragment(f.fragment)
    HUD_UI_SCENE:AddFragment(f.fragment)

    BA.frames[kind] = f
    return f
end

function BA.BuildFrames()
    CreateFrame("buff")
    CreateFrame("debuff")
    BA.RefreshLayout()
end

-- Раскладка --------------------------------------------------------------------

-- Постоянные ауры могут рисоваться мельче, поэтому размер считается на каждую
-- иконку отдельно, а якоря идут по центральной линии (LEFT->RIGHT / TOP->BOTTOM),
-- иначе иконки разного размера разъехались бы по краю.
local function LayoutIcons(f, list)
    local sv       = f.sv
    local gap      = sv.spacing
    local vertical = sv.orientation == "column"
    local count    = #list
    local permK    = (sv.permScale or 100) / 100

    local total, cross = 0, 0
    for i = 1, count do
        local c    = f.icons[i] or CreateIcon(f, i)
        local size = list[i].perm and zo_max(12, zo_round(sv.iconSize * permK)) or sv.iconSize
        local font = list[i].perm and zo_max(8, zo_round(sv.fontSize * permK)) or sv.fontSize
        local nameH = sv.showNames and zo_round(size * NAME_HEIGHT_RATIO) or 0
        local cellH = size + nameH

        c:SetMouseEnabled(BA.sv.tooltips)
        c:SetDimensions(size, cellH)
        c.tex:SetDimensions(size, size)
        c.cd:SetDimensions(size, size)
        c.timer:SetFont(FontString(font, true))
        c.label:SetFont(FontString(zo_max(10, zo_round(font * 0.7)), false))
        c.label:SetDimensions(size + gap, nameH)
        c.label:SetHidden(not sv.showNames)

        c:ClearAnchors()
        if vertical then
            if i == 1 then
                c:SetAnchor(TOP, f.holder, TOP, 0, 0)
            else
                c:SetAnchor(TOP, f.icons[i - 1], BOTTOM, 0, gap)
            end
            total = total + cellH + (i > 1 and gap or 0)
            cross = zo_max(cross, size)
        else
            if i == 1 then
                c:SetAnchor(LEFT, f.holder, LEFT, 0, 0)
            else
                c:SetAnchor(LEFT, f.icons[i - 1], RIGHT, gap, 0)
            end
            total = total + size + (i > 1 and gap or 0)
            cross = zo_max(cross, cellH)
        end
    end

    for i = count + 1, #f.icons do
        f.icons[i]:SetHidden(true)
    end

    if vertical then
        f.tlw:SetDimensions(zo_max(cross, 32), zo_max(total, 32))
    else
        f.tlw:SetDimensions(zo_max(total, 32), zo_max(cross, 32))
    end
end

-- Сброс кэша раскладки: следующий апдейт переанкорит всё заново
function BA.RefreshLayout()
    for _, f in pairs(BA.frames) do
        f.layoutKey = nil
        f.tlw:ClearAnchors()
        f.tlw:SetAnchor(TOPLEFT, GuiRoot, TOPLEFT, f.sv.x, f.sv.y)
    end
    BA.RefreshVisibility()
    if BA.sv then BA.UpdateFrames() end
end

-- Обновление содержимого --------------------------------------------------------

-- Записи списка тоже переиспользуются: BuildList вызывается на каждом тике опроса.
local function PushEntry(f, n, aura, act, remain)
    local e = f.pool[n]
    if not e then
        e = {}
        f.pool[n] = e
    end
    e.aura, e.act, e.remain = aura, act, remain
    f.list[n] = e
    return e
end

-- Постоянная аура — та, у которой игра не даёт отсчёта: Restoring Aura, пока она
-- в слоте, вся пачка с Oakensoul Ring, бафы от пассивок. Игра отдаёт у них
-- timeStarted == timeEnding (часто оба нулевые), так же это определяет Srendarr.
local function IsPermanent(act)
    return act.finish == 0 or act.finish <= act.start
end
BA.IsPermanent = IsPermanent

local function ConsiderAura(f, a, store, avail, sv, now, permMode, wantPermanent)
    if a.kind ~= f.kind or BA.sv.show[a.key] == false then return end

    local act  = store[a.key]
    local perm = (act ~= nil) and IsPermanent(act) or false

    if perm then
        if permMode == "hide" then return end
        if permMode == "last" and not wantPermanent then return end
    elseif permMode == "last" and wantPermanent then
        return
    end

    local fromBars = avail[a.key]
    local include
    if act then
        include = fromBars or not BA.sv.hideForeign
    else
        -- в режиме настройки плейсхолдеры показываем всегда, чтобы фрейм
        -- в анлоке не оказался короче, чем он же в залоченном виде
        include = (sv.showInactive or BA.unlocked) and fromBars
    end
    if not include then return end

    local remain = -1
    if act then
        remain = perm and 99999 or zo_max(0, act.finish - now)
    end

    local e = PushEntry(f, #f.list + 1, a, act, remain)
    e.perm = perm
end

local function BuildList(f)
    local sv       = f.sv
    local store    = (f.kind == "buff") and BA.activeBuff or BA.activeDebuff
    local avail    = BA.available[f.kind]
    local now      = GetGameTimeSeconds()
    local list     = f.list
    local permMode = sv.permanent or "inline"

    ZO_ClearNumericallyIndexedTable(list)

    for _, a in ipairs(BA.AURAS) do
        ConsiderAura(f, a, store, avail, sv, now, permMode, false)
    end
    if permMode == "last" then
        for _, a in ipairs(BA.AURAS) do
            ConsiderAura(f, a, store, avail, sv, now, permMode, true)
        end
    end

    -- в режиме настройки фрейм не должен быть пустым, иначе его не за что схватить
    if BA.unlocked and #list == 0 then
        for _, a in ipairs(BA.AURAS) do
            if a.kind == f.kind then
                local e = PushEntry(f, #list + 1, a, nil, -1)
                e.perm = false
                if #list >= 5 then break end
            end
        end
    end

    if sv.sort == "time" then
        table.sort(list, function(l, r)
            if (l.act ~= nil) ~= (r.act ~= nil) then return l.act ~= nil end
            if l.remain ~= r.remain then return l.remain < r.remain end
            return l.aura.key < r.aura.key
        end)
    end

    return list
end

function BA.UpdateFrame(f)
    local sv = f.sv
    if not sv.enabled then
        f.tlw:SetHidden(true)
        return
    end

    local list = BuildList(f)
    local n    = #list

    -- в ключ входит и маска «какая иконка постоянная»: от неё зависят их размеры.
    -- Маска числовая и в двух половинах — склеивать строку на каждом тике накладно,
    -- а 60 бит в один double точно не влезут.
    local m1, m2 = 0, 0
    for i = 1, n do
        local bit = list[i].perm and 1 or 0
        if i <= 26 then m1 = m1 * 2 + bit else m2 = m2 * 2 + bit end
    end

    local key = string.format("%d.%d|%d|%s|%d|%d|%d|%s|%d", m1, m2, n, sv.orientation,
                              sv.iconSize, sv.spacing, sv.fontSize, tostring(sv.showNames),
                              sv.permScale or 100)
    if f.layoutKey ~= key then
        LayoutIcons(f, list)
        f.layoutKey = key
    end

    local now = GetGameTimeSeconds()
    for i = 1, n do
        local e = list[i]
        local a = e.aura
        local c = f.icons[i]
        c:SetHidden(false)
        c.aura = a
        c.tex:SetTexture((e.act and e.act.icon ~= "" and e.act.icon) or a.icon)
        c.label:SetText(a.name)

        if e.act then
            c.tex:SetDesaturation(0)
            c.tex:SetColor(1, 1, 1, 1)
            c.label:SetColor(1, 1, 1, 1)
            if not e.perm then
                local remain = zo_max(0, e.act.finish - now)
                c.timer:SetText(FormatTime(remain, sv.decimals))
                if remain <= sv.warnAt then
                    c.timer:SetColor(1, 0.3, 0.2, 1)
                else
                    c.timer:SetColor(1, 1, 1, 1)
                end
                if sv.radial then
                    local dur = zo_max(0.1, e.act.finish - e.act.start)
                    c.cd:SetHidden(false)
                    -- без явного цвета контрол заливает иконку светлым и она пропадает;
                    -- цвет сбрасывается стартом кулдауна, поэтому ставим каждый тик
                    c.cd:SetFillColor(0, 0, 0, (sv.radialAlpha or 55) / 100)
                    c.cd:StartCooldown(remain * 1000, dur * 1000, CD_TYPE_RADIAL, CD_TIME_TYPE_TIME_UNTIL, false)
                else
                    c.cd:SetHidden(true)
                end
            else
                c.timer:SetText("")
                c.cd:SetHidden(true)
            end
        else
            c.tex:SetDesaturation(1)
            c.tex:SetColor(1, 1, 1, 0.3)
            c.label:SetColor(1, 1, 1, 0.3)
            c.timer:SetText("")
            c.cd:SetHidden(true)
        end
    end

    for i = n + 1, #f.icons do
        f.icons[i]:SetHidden(true)
    end

    if not BA.unlocked and sv.hideEmpty and n == 0 then
        f.holder:SetHidden(true)
    else
        f.holder:SetHidden(false)
    end
end

function BA.UpdateFrames()
    for _, f in pairs(BA.frames) do
        BA.UpdateFrame(f)
    end
end

-- Видимость ---------------------------------------------------------------------

local fadeHandle = {}

local function ApplyAlpha(f, alpha)
    f.holder:SetAlpha(alpha / 100)
end

function BA.RefreshFrameVisibility(f)
    local sv = f.sv

    if BA.unlocked then
        f.tlw:SetHidden(false)
        ApplyAlpha(f, 100)
        return
    end

    if BA.forceHidden or not sv.enabled or (sv.hideInTown and BA.isInTown and not BA.inCombat) then
        f.tlw:SetHidden(true)
        return
    end
    f.tlw:SetHidden(false)

    if BA.inCombat or not sv.fadeOOC then
        ApplyAlpha(f, sv.alpha)
    else
        -- вне боя гасим с задержкой
        fadeHandle[f.kind] = (fadeHandle[f.kind] or 0) + 1
        local token = fadeHandle[f.kind]
        zo_callLater(function()
            if fadeHandle[f.kind] == token and not BA.inCombat and not BA.unlocked then
                ApplyAlpha(f, zo_min(sv.alpha, sv.oocAlpha))
            end
        end, (sv.fadeDelay or 0) * 1000)
    end
end

function BA.RefreshVisibility()
    if not BA.frames or not BA.sv then return end
    for _, f in pairs(BA.frames) do
        BA.RefreshFrameVisibility(f)
    end
end

-- Режим настройки ----------------------------------------------------------------

function BA.SetUnlocked(state)
    BA.unlocked = state
    for _, f in pairs(BA.frames) do
        f.tlw:SetMovable(state)
        f.tlw:SetMouseEnabled(state)
        f.bg:SetHidden(not state)
        if state then
            -- иначе фрагмент сцены спрячет фрейм, пока открыто меню настроек
            HUD_SCENE:RemoveFragment(f.fragment)
            HUD_UI_SCENE:RemoveFragment(f.fragment)
            f.tlw:SetHidden(false)
        else
            HUD_SCENE:AddFragment(f.fragment)
            HUD_UI_SCENE:AddFragment(f.fragment)
        end
        f.layoutKey = nil
    end
    BA.RefreshVisibility()
    BA.UpdateFrames()
end

function BA.ToggleUnlock()
    BA.SetUnlocked(not BA.unlocked)
    d(BA.unlocked and "|cffcc00Bar Auras|r: фреймы разблокированы, тащи мышью."
                   or "|cffcc00Bar Auras|r: фреймы зафиксированы.")
end

-- Кейбинд (Настройки → Управление → Bar Auras)
BA.forceHidden = false

function BA.ToggleFrames()
    BA.forceHidden = not BA.forceHidden
    BA.RefreshVisibility()
end

ZO_CreateStringId("SI_BINDING_NAME_BARAURAS_TOGGLE_FRAMES", "Показать/скрыть фреймы")
