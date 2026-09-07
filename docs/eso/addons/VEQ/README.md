# VEQ (Vestige's Epic Quest) — кастомная правка

Форк аддона **Vestige's Epic Quest** (автор @Masteroshi430). Резервная копия правки: при
обновлении аддона оригинал перезапишет изменение, поэтому после апдейта его нужно накатить
заново отсюда.

Только изменённый файл `VEQ.lua`. Остальные файлы (`Includes/`, `Langs/`, `Bindings/`,
`.addon`) не менялись — их вернёт свежая установка.

## Проблема

Альтернативный мини-квест-трекер VEQ (тот, что рисуется поверх интерфейса) перестал
обновлять **счётчики прогресса шага** — при задании «собрать 4 предмета» строка обновлялась
1/4 → 2/4 → 3/4 только в момент, когда шаг менялся целиком, а не на каждый подобранный предмет.

## Причина

Счётчик шага в мини-трекере обновляется только по событию
`EVENT_QUEST_CONDITION_COUNTER_CHANGED` (VEQ.lua). Его обработчик в конце вызывал
`VEQ.SetFocusedQuest(qindex)`, а эта функция (`Includes/functions.lua:344`) в самом начале
делает ранний выход:

```lua
if not GetSetting_Bool(SETTING_TYPE_UI, UI_SETTING_AUTOMATIC_QUEST_TRACKING) then return end
```

То есть при **выключенной** в игре опции «Автоматическое отслеживание заданий» (Настройки →
Интерфейс) функция выходит сразу и `VEQ.QuestsListUpdate` (перестройку трекера) не вызывает.
Поэтому счётчики не обновлялись.

Смена самого шага при этом работала, потому что она идёт по другим событиям
(`EVENT_QUEST_ADVANCED` / `EVENT_QUEST_OPTIONAL_STEP_ADVANCED`), которые повешены напрямую на
`VEQ.QuestsListUpdate` без этой проверки.

Регресс появился при рефакторинге: раньше на событие счётчика был повешен прямой
`VEQ.QuestsListUpdate` (эти строки остались закомментированы в коде), потом его заменили на
`SetFocusedQuest`.

## Правка

В обработчике `EVENT_QUEST_CONDITION_COUNTER_CHANGED` (VEQ.lua) финальный вызов
`VEQ.SetFocusedQuest(qindex)` заменён на ветвление:

```lua
if GetSetting_Bool(SETTING_TYPE_UI, UI_SETTING_AUTOMATIC_QUEST_TRACKING) then
    VEQ.SetFocusedQuest(qindex)   -- авто-трекинг вкл: прежнее поведение (авто-ассист + апдейт)
else
    VEQ.QuestsListUpdate(1)       -- авто-трекинг выкл: обновляем трекер напрямую (счётчики живые)
end
```

При включённом авто-отслеживании поведение не меняется. При выключенном — мини-трекер теперь
перестраивается на каждый тик счётчика.

## Как переустановить после обновления аддона

Скопировать файл обратно и сделать `/reloadui`:

```
docs/eso/addons/VEQ/VEQ.lua
  → C:/Users/<user>/Documents/Elder Scrolls Online/live/AddOns/VEQ/VEQ.lua
```

SavedVariables (`VEQSavedVars`) не затрагиваются.
