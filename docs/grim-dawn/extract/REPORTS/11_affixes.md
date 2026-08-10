# Отчёт 11 — Аффиксы (префиксы/суффиксы) и правила их роллов

Скрипт: `docs/grim-dawn/extract/11_affixes.py`
Выходы:
- `data/grim-dawn/affixes.jsonl` — 7984 записи, 15 751 KB (16 129 132 байт)
- `data/grim-dawn/affix_tables.json` — 13 341 KB (13 661 332 байт)

Запуск: `python 11_affixes.py` из `docs/grim-dawn/extract`, без аргументов. Отработал
без ошибок за 2.9 c.

Это вторая итерация задания. Добавлено обогащение по `field_schema.json` (новый
авторитетный словарь схемы `.dbr`-полей из `templates.arc`) и исправлена опровергнутая
гипотеза из первой итерации про «наследование дефолтов из templates.arc» — см. раздел
«Исправленная гипотеза» ниже.

## Как устроена связь «предмет -> аффикс» (без изменений с прошлой итерации)

Проверил на `ArmorProtective_Chest` и `WeaponMelee_Sword` (по несколько записей каждого) —
на самом предмете нет поля вроде `prefixTables`/`suffixTables`. Связь хранится в отдельном
типе записей:

```
LootRandomizer (7984)              — сам аффикс: имя, статы, вес/стоимость/уровень.
    путь records/items/lootaffixes/<folder>/*.dbr, folder = kind

LootRandomizerTable (1081)         — пул: randomizerName{i}/Weight{i}/LevelMin{i}/Max{i}
    путь records/items/lootaffixes/<folder>/<folder>tables/*.dbr, folder = тот же kind

LootItemTable_DynWeight (2663)     — ГЛАВНОЕ ЗВЕНО: "какой предмет тянет какой пул"
    records/items/loottables/<slot>/tdyn_*.dbr
      lootName{i}/lootWeight{i}                  -> какие БАЗОВЫЕ предметы может выдать
      prefixTableName{i}/Weight{i}/LevelMin/Max{i}       -> обычный пул префиксов
      suffixTableName{i}/...                             -> обычный пул суффиксов
      rarePrefixTableName{i}/... , rareSuffixTableName{i}/... -> усиленный пул для Rare
      brokenTableName{i}                                  -> пул для Broken-качества
      noPrefixNoSuffix/prefixOnly/suffixOnly/bothPrefixSuffix/rarePrefixOnly/
      rareSuffixOnly/rarePrefixNormalSuffix/normalPrefixRareSuffix/
      rareBothPrefixSuffix/brokenOnly                     -> веса комбинации качества
      minItemLevelEquation/maxItemLevelEquation/targetLevelEquation -> формулы уровня
                                                              (сохранены как текст, не вычисляются)

ItemAscensionFormula (9)           — крафт "Ascension" (Forgotten Gods): добавляет ВТОРОЙ
    аффикс поверх легендарки. Поля вида <slot>TablesAffix/<slot>TablesMastery
    -> LootRandomizerTable в lootaffixes/ascended/...
```

Проверено на 6+ примерах разных слотов (мечи, топоры, щиты, шлемы, перчатки, ожерелья) —
паттерн стабильный.

### Что нашлось и вне прямой области, но упомянуто (не задублировано — домен задания 40)
- `ItemRelic.bonusTableName` (83 записи) -> `lootaffixes/completion/*` — бонус за «завершение»
  реликвии.
- `NpcCrafter.enhancementTable` (19 записей, кузнецы) -> `lootaffixes/crafting/*` — «усиление»
  предмета у кузнеца.

## Исправленная гипотеза: почему 1600 из 2663 `LootItemTable_DynWeight` без явных пулов

**Прошлый отчёт был неверен.** Там утверждалось, что эти записи «наследуют дефолты из
`database/templates.arc`». Это опровергнуто: в `field_schema.json` (авторитетный дамп схемы
из `templates.arc`) все 18 полей `prefixTableName*`/`suffixTableName*`/`rarePrefixTableName*`/
`rareSuffixTableName*`/`brokenTableName*` имеют **пустой `default`** — шаблон описывает форму
поля (тип `file_dbr`, группу `Randomizer Prefix`/`Randomizer Suffix`), но не поставляет
значение по умолчанию. Наследовать оттуда было решительно нечего — прошлый вывод был
домыслом без проверки.

Настоящая картина (перепроверено запросом по `gd.sqlite` в этой итерации, счётчики
совпадают с тем, что вывел сам скрипт — см. `meta.loot_item_tables_excluded_by_folder`):

```
исключено по папкам: damagetables 1078, weapons 133, gearaccessories 80,
randomsettdyns 61, blueprints 53, misc 48, materia 33, gearhead 32,
gearshoulders 21, enemyspecific 12, gearfeet 10, gearhands 10, gearlegs 10,
mastery 10, geartorso 9   (итого 1600)
```

1. **`damagetables` (1078), `randomsettdyns` (61), `enemyspecific` (12), `blueprints` (53),
   `misc` (48), `materia` (33), `mastery` (10)** — это не предметные таблицы со случайными
   аффиксами вообще: элементальные варианты уже апгрейженных предметов, привязка сетов/боссов,
   чертежи (`ItemArtifactFormula`), компоненты, таблицы под конкретное мастерство. Им и не
   положено иметь `prefixTableName*`/`suffixTableName*` — они этой системой не пользуются.

2. **Оставшиеся ~305 таблиц из «geartype»-папок** (`weapons` 133, `gearaccessories` 80,
   `gearhead` 32, `gearshoulders` 21, `gearfeet`/`gearhands`/`gearlegs` по 10, `geartorso` 9) —
   **исследовательская задача этого захода**: проверить гипотезу «это таблицы для предметов,
   которые в принципе не роллят аффиксы (легендарки/эпики/MI)».

   **Проверено запросом по `gd.sqlite`** (см. `meta.loot_item_tables_excluded_equipment_investigation`
   в `affix_tables.json` — счётчик реально посчитан скриптом, не выдумка): взял все 305 таких
   таблиц, резолвил у каждой ВСЕ ссылки `lootName{i}` на конкретные предметы и посмотрел их
   `itemClassification`.

   ```
   tables_examined: 305
   lootName_refs_resolved_by_itemClassification: {"Legendary": 3247, "Epic": 3061}
   dangling_lootName_refs: 1
   ```

   Итого 6309 ссылок `lootName*`, 6308 резолвились — и **100% из них Legendary или Epic**.
   Ни одной ссылки на предмет с `itemClassification` Common/Magical/Rare не найдено (1 ссылка
   битая: `records/items/loottables/gearhead/tdyn_head_c02_theexile.dbr` ->
   `records/items/faction/head/f001a_head.dbr`, такой записи в базе просто нет — не связано
   с гипотезой, отдельный дефект данных).

   **Гипотеза подтверждена фактами, без контрпримеров.** Legendary и Epic (MI, Monster
   Infrequent) — это как раз те классы предметов, у которых фиксированные статы и нет
   системы случайных префиксов/суффиксов в игре. Отсутствие `prefixTableName*`/
   `suffixTableName*` у этих 305 таблиц — корректные игровые данные, а не пробел парсинга.
   Заодно нашлась косвенная находка: среди `lootName*` этих таблиц встречаются и ссылки на
   `ItemArtifactFormula` (чертежи, 6 из 6309) — например
   `records/items/loottables/gearhead/tdyn_head_d02_witchgodguardian.dbr` ссылается на
   `records/items/crafting/blueprints/armor/craft_headd21_eldritchgaze.dbr`
   (`itemClassification: Legendary`) — это чертёж, по которому крафтится конкретная легендарка
   с фиксированными статами, что только усиливает вывод: содержимое этих таблиц целиком не
   аффиксируемое.

   Не нашёл ни одной таблицы обычных (Common/Magical/Rare) предметов среди исключённых
   equip-таблиц — «настоящей находки» (таблица с обычными предметами, ошибочно оставшаяся
   без пула) не случилось. Это негативный, но проверенный результат.

**Итог**: `item_drop_tables` в `affix_tables.json` (1063 записи) — это ПОЛНАЯ картина того,
что реально роллит случайные аффиксы. Оставшиеся 1600 записей `LootItemTable_DynWeight`
исключены заслуженно: у них либо нет предметного домена вообще, либо предметы фиксированы
(Legendary/Epic) и не участвуют в системе случайных аффиксов.

## Новое: обогащение статов категориями из `field_schema.json`

Главная доработка этой итерации. Раньше `stats` был просто `{имя_поля: значение}` — чтобы
понять, что даёт `offensiveSlowFireModifier`, нужно было знать формат `.dbr`. Теперь каждый
стат сопоставлен с человекочитаемой категорией из авторитетного словаря полей.

- `stat_groups` — `{поле: [группы...]}`, группы — из `field_schema.json[field]["groups"]`
  без общей для всех `"All Groups"`. Пример: `offensiveSlowFireModifier` ->
  `["Offensive Duration", "Offensive Parameters", "Offensive Slow Fire"]`.
- `categories` — плоский отсортированный список уникальных групп по ВСЕМ статам записи —
  быстрый ответ «что вообще даёт этот аффикс» без разбора имён полей (например
  `["Character Ability", "Character Bio", ..., "Defensive Stun", ...]`).

**Покрытие: 100%.** Из 197 различных имён полей, встречающихся в статах 7984 аффиксов, ВСЕ
197 нашлись в `field_schema.json` (18968 полей). Скрипт печатает и пишет в `meta` список
незнакомых полей (`stat_fields_unknown_in_field_schema`) — сейчас пустой, но механизм
проверки не убран, если в будущих итерациях данных появится незнакомое поле, это будет
видно, а не тихо пропущено.

### Побочная находка при сверке с `field_schema.json`: раскрыт «proc»-скилл

При переборе полей через схему обнаружились три поля, которые раньше молча лежали в `stats`
как сырые пути/строки, потому что скрипт не знал, что с ними делать: `itemSkillName`
(`type: file_dbr`, группа `Skill Augment`), `itemSkillAutoController` (`file_dbr`,
`Skill Augment`) и `itemSkillLevelEq` (`equation`, `Skill Augment`). Это не то же самое, что
`augmentSkillName{1,2}` (даёт очки существующего скилла игрока) — это **условный «proc»-скилл**
(срабатывает по триггеру, напр. «20% шанс при получении удара»), у 496 из 7984 аффиксов
(6.2%). Теперь это отдельное поле `proc` в каждой записи:

```json
"proc": {
  "skill": "records/skills/itemskills/item_warcry.dbr",
  "skill_name": "Applies Warcry aoe buff",
  "level_eq": "itemLevel/4+1",
  "controller": "records/controllers/itemskills/cast_@selfonanyhit_20%.dbr",
  "trigger": {"chanceToRun": 20, "triggerType": "HitByEnemy", "targetType": "Self", "autoTargetRadius": 5.0}
}
```
`trigger.*` — сырые поля `skillautocastcontroller`-записи (`chanceToRun`/`triggerType`/
`targetType`/`autoTargetRadius`), прочитаны напрямую, не домысливались. `itemSkillName`/
`itemSkillAutoController`/`itemSkillLevelEq` добавлены в `PROMOTED` (больше не дублируются
в `stats`).

## Схема `affixes.jsonl` (по одной записи на `LootRandomizer`)

| Поле | Источник .dbr | Смысл |
|---|---|---|
| `record` | имя записи | путь-первоисточник |
| `kind` | папка в пути (`.../lootaffixes/<folder>/...`) | `prefix`\|`suffix`\|`prefix_unique`\|`suffix_unique`\|`ascended`\|`completion`\|`completion_relic`\|`crafting`\|`broken` |
| `src` | `src` из gd.sqlite | какой .arz победил (base/gdx1/gdx2/gdx3) |
| `name_tag` / `name` / `name_source` | `lootRandomizerName` | резолв тэга; `name=null` если тэга нет (см. «Неуверенности») |
| `dev_note` | `FileDescription` | **не игровое имя** — внутренняя пометка дизайнера (число/%/класс), сохранена отдельно, чтобы не спутать с `name` |
| `itemClassification` | как есть | Magical/Rare/Epic/Legendary — влияет, в каком «качестве» ролла доступен аффикс |
| `levelRequirement` | как есть | |
| `cost` | `lootRandomizerCost` | вероятно «бюджет сложности» для формулы `itemCostName` — не проверено |
| `jitter_pct` | `lootRandomizerJitter` | % разброса ролла; обратная зависимость от тира подтверждена статистически |
| `marketAdjustmentPercent` | как есть | |
| `augments` | `augmentSkillName{1,2}`/`augmentSkillLevel{1,2}` | грант очков скилла игрока, скилл резолвлен в имя |
| `proc` | `itemSkillName`/`itemSkillAutoController`/`itemSkillLevelEq` | **новое поле**: условный скилл-эффект по триггеру (шанс на удар/каст), не путать с `augments` |
| `ascended_modifiers` | `modifiedSkillName{1..3}`/`modifierSkillName{1..3}` | только у `kind=ascended`: аффикс МОДИФИЦИРУЕТ существующий скилл, а не даёт новый |
| `pet_bonus` | `petBonusName` | ссылка на бонус для питомцев, резолвлена в имя |
| `stats` | всё остальное ненулевое | сырые имена полей `.dbr` (сопротивления/OA-DA/%урона/конверсии/реталиация и т.д.), пары `X`/`XModifier`/`XChance`/`XMin`/`XMax` не разорваны |
| `stat_groups` | **новое**, из `field_schema.json` | `{поле: [человекочитаемые группы]}` — категория каждого стата |
| `categories` | **новое**, агрегат `stat_groups` | плоский уникальный список групп по всей записи — «что вообще даёт этот аффикс» одним взглядом |
| `tables` | обратный индекс из `LootRandomizerTable` | `[{table, weight, levelMin, levelMax}]` — в какие пулы входит этот аффикс и с каким весом/уровневым окном |

Промотированы (исключены из `stats`): `FileDescription`, `itemClassification`,
`levelRequirement`, `lootRandomizerName/Cost/Jitter/Scale`, `marketAdjustmentPercent`,
`augmentSkillName{1,2}`/`Level{1,2}`, `modifiedSkillName{1..3}`, `modifierSkillName{1..3}`,
`petBonusName`, `itemSkillName`, `itemSkillAutoController`, `itemSkillLevelEq` (последние
три — новое, см. раздел про «proc» выше). Чисто метаданные (`templateName`, `Class`,
`characterBaseAttackSpeedTag` — константа `CharacterAttackSpeedAverage` во всех 7984
записях, `brokenDropSound`) выброшены совсем.

## Схема `affix_tables.json`

```
{
  "meta": {счётчики + новое: field_schema_fields_total, stat_fields_unknown_in_field_schema,
           loot_item_tables_excluded_note, loot_item_tables_excluded_equipment_investigation},
  "tables": {
     "<record LootRandomizerTable>": {
        record, kind, file_description,
        entries: [{affix, weight, levelMin, levelMax}, ...]
     }, ...
  },
  "item_drop_tables": {                      # только LootItemTable_DynWeight с явными полями
     "<record LootItemTable_DynWeight>": {
        record,
        item_types: {"WeaponMelee_Sword": N, ...},   # агрегат по типам предметов из lootName*
        items: [{item, type, weight}, ...],           # сами базовые предметы + вес
        prefix_pools / suffix_pools / rare_prefix_pools / rare_suffix_pools / broken_pools:
            [{table, weight, levelMin, levelMax}, ...],
        quality_weights: {noPrefixNoSuffix, prefixOnly, ..., brokenOnly},  # веса комбинаций
        level_equations: {min, max, target},          # формулы как текст, не вычислены
        allow_ascension, force_highest_level, disable_level_limits
     }, ...
  },
  "ascension_formulas": [ {record, <slot>TablesAffix: [...], <slot>TablesMastery: [...], affixWeight, ...} ]
}
```

## Счётчики

- `LootRandomizer`: **7984** обработано, 0 пропущено.
  - по `kind`: suffix 3409, prefix 2782, ascended 993, completion_relic 315, prefix_unique 208,
    completion 139, suffix_unique 77, crafting 56, broken 5.
  - без резолвящегося `name_tag`: **1788** (см. пояснение в прошлом отчёте — 100% полей
    `kind` completion/completion_relic/crafting/prefix_unique/suffix_unique/ascended не имеют
    `lootRandomizerName` вообще, у suffix/prefix/broken тэг есть всегда).
  - с `proc` (условный скилл-эффект, новое поле): **496** (6.2%).
- `field_schema.json`: **18968** полей загружено. Стат-полей аффиксов, отсутствующих в
  словаре: **0 из 197** уникальных имён — полное покрытие.
- `LootRandomizerTable`: **1081** обработано, битых ссылок на `LootRandomizer` — **0**.
- `LootItemTable_DynWeight`: **2663** всего.
  - включено (есть явные поля `*TableName*`): **1063**.
  - исключено: **1600** — из них **1295** вне предметного домена аффиксов, **305**
    equip-таблиц (проверено: 100% Legendary/Epic содержимого, см. раздел выше).
- `ItemAscensionFormula`: **9** обработано (весь тип).
- Кросс-ссылки, не задублированные (домен задания 40): `ItemRelic.bonusTableName` — 83,
  `NpcCrafter.enhancementTable` — 19.

## Спот-чек

**`of Attack`** (16 вариантов-тиров одного суффикса): `records/items/lootaffixes/suffix/a018b_ch_oa_07.dbr` —
`stats: {"characterOffensiveAbility": 112.0}`, `categories: ["Character Ability", "Character
Parameters", "Config"]`, `levelRequirement: 85`, входит в таблицу
`suffixtables/suffixa01_ch_accessory_ability01.dbr` (вес 500, окно 85-94). Прогрессия по
уровню и величине сходится с прошлой проверкой.

**`of Kings`** (суффикс, kind=suffix, с новым полем `proc`):
`records/items/lootaffixes/suffix/b_ar035_ar_c.dbr` — `itemClassification: Rare`,
`augments: [{skill: "War Cry", level: 2}]` (даёт очки скилла) ПЛЮС отдельно
`proc: {skill_name: "Applies Warcry aoe buff", trigger: {chanceToRun: 20,
triggerType: "HitByEnemy", targetType: "Self"}}` (20%-й шанс сработать AoE-баффом при
получении удара) — раньше это была слепая зона: путь на `item_warcry.dbr` лежал бы в
`stats` нерасшифрованным. `stats: {characterDefensiveAbility: 26, characterLife: 350,
defensiveStun: 25}`, `categories` включают `Character Ability`, `Defensive Stun`,
`Natural Resistance` — сразу видно профиль аффикса (танк/утилити), не читая имена полей.

**`Warrior's`** (81 вариант, класс-префикс Soldier): `b_class011_soldier08_je.dbr` —
`stats: {defensiveLife: 15, offensivePhysicalModifier: 20, offensiveSlowBleedingModifier: 20,
skillCooldownReduction: 4}`, теперь с `stat_groups` — например
`offensiveSlowBleedingModifier -> ["Offensive Duration", "Offensive Parameters",
"Offensive Slow Bleeding"]` (сразу ясно: это модификатор ДЛИТЕЛЬНОСТИ кровотечения от
персонажа, а не % урона кровотечением напрямую — раньше это надо было знать по памяти),
грант скилла `Field Command` ур.2, уровень требования 42, входит в 2 таблицы класса
(caster/armor), окно уровней 36-500.

## Демонстрация: «какой максимальный роллабельный бонус к X на слоте Y на уровне Z» (ключевой вопрос задания)

Схема отвечает на вопрос join'ом трёх файлов (без изменений с прошлой итерации, всё ещё
актуально с новыми полями). Пример запроса (реально прогнан):

```python
# Максимальный %огненного урона (offensiveFireModifier) суффиксом на 1H-мече на уровне 50
best = None
for dt in item_drop_tables.values():
    if 'WeaponMelee_Sword' not in dt['item_types']:
        continue
    for pool in dt['suffix_pools'] + dt['rare_suffix_pools']:
        if LEVEL не в [pool.levelMin, pool.levelMax]: continue
        table = tables[pool['table']]
        for e in table['entries']:
            if LEVEL не в [e.levelMin, e.levelMax]: continue
            aff = affixes[e['affix']]
            v = aff['stats'].get('offensiveFireModifier')
            best = max(best, v)
```

Результат прогона (не изменился): **50.0%** — `records/items/lootaffixes/suffix/a030c_off_dmg%fire_03_we.dbr`
(«of Scorching»), через таблицу `records/items/loottables/weapons/tdyn_sword1h_a04.dbr`. Теперь
дополнительно можно фильтровать сразу по `categories` (например «покажи все суффиксы с
категорией `Offensive Fire`» без знания конкретных имён полей `offensiveFireModifier` vs
`offensiveFireMin`/`Max` vs `offensiveSlowFireModifier`).

## Что не удалось / в чём не уверен (обязательный раздел)

1. **~33% суффиксов (1123 из 3409) не входят ни в одну `LootRandomizerTable`.** Проверил на
   нескольких примерах (`a081d_off_dmg%burn_01_we2h.dbr`, `a060a_off_dmg%firecold_03_fo.dbr`,
   `a036a_def_%armor_01.dbr`) полнотекстовым поиском по ВСЕЙ базе — их путь не встречается
   нигде, кроме них самих. Похоже на легаси/вырезанный контент прошлых патчей. Та же картина
   у `prefix` (86 из 2782). Не переисследовал в этой итерации — вывод не менялся с прошлого
   отчёта.
2. **Точная формула применения `jitter_pct` и `cost` не проверена.** Обратная зависимость
   `jitter` от тира подтверждена статистически, но КАК движок использует % при генерации
   ролла — не знаю, в `Game.dll` не лазил. `lootRandomizerCost` растёт с тиром, похоже на
   «бюджет сложности» для `itemCostName` (задание 10), формула не подтверждена.
3. **`groups` в `field_schema.json` — это НЕ единая иерархическая категория, а плоский
   алфавитно отсортированный список всех «путей» поля в дереве групп редактора** (проверил на
   нескольких полях — порядок всегда алфавитный, не по специфичности). Из-за этого `stat_groups`
   для одного поля иногда содержит и специфичную группу («Offensive Slow Fire»), и более общую
   родительскую («Offensive Parameters», «Offensive Duration») одновременно — я не пытался
   выбрать «главную», а отдал весь список как есть, чтобы не выдумывать приоритет, которого нет
   в исходных данных. Для агрегата `categories` это означает некоторую «зашумлённость» общими
   ярлыками вроде `* Parameters` — сознательный трейд-офф в пользу честности данных.
4. **`description` есть только у части полей `field_schema.json`** (1637 из 18968 по брифу);
   я не стал добавлять описание в `stat_groups`, т.к. у большинства реально встречающихся в
   аффиксах 197 полей описания нет (то есть добавление раздуло бы объём почти без пользы) —
   если понадобится, оно доступно напрямую в `field_schema.json` по имени поля.
5. **`characterBaseAttackSpeedTag`** — константа `CharacterAttackSpeedAverage` во ВСЕХ 7984
   записях — выброшена как шаблонный мусор, не как «ноль» — честно об этом пишу.
6. **`lootRandomizerScale`** встретилась 1 раз во всей базе — не знаю семантики, оставлена в
   `stats` как есть.
7. Домен задания 40 (`ItemRelic`, `NpcCrafter`) не разворачивал полностью — только сосчитал
   связи.
8. **Исправление гипотезы про 1600 исключённых таблиц.** Раздел «Исправленная гипотеза» выше —
   в этой итерации проверено ФАКТАМИ (100% Legendary/Epic среди ~305 equip-таблиц, 0
   контрпримеров), но я не проверял оставшиеся ~1295 записей (damagetables/misc/materia/...)
   так же строго построчно — их отнесение к «не предметному домену» основано на анализе путей
   и сэмплов, а не на 100%-ном построчном резолве, как для equip-папок.

## Живые примеры из выхода

**Обычный суффикс с обратным индексом таблиц:**
```json
{
 "record": "records/items/lootaffixes/prefix/aa012a_demolitionist19_je.dbr",
 "kind": "prefix", "src": "base",
 "name_tag": "tagPrefixAA012", "name": "Demolitionist's", "name_source": "tag",
 "dev_note": "Blackwater Mod2 +1",
 "itemClassification": "Magical", "cost": 600, "jitter_pct": 40.0, "marketAdjustmentPercent": 50.0,
 "augments": [{"skill": "records/skills/playerclass02/blackwater3.dbr",
               "skill_name": "Agonizing Flames", "level": 2}],
 "stats": {"characterDexterityModifier": 4.0, "characterIntelligenceModifier": 4.0},
 "stat_groups": {
   "characterDexterityModifier": ["Character Bonus Attributes", "Character Parameters"],
   "characterIntelligenceModifier": ["Character Bonus Attributes", "Character Parameters"]
 },
 "categories": ["Character Bonus Attributes", "Character Parameters"],
 "tables": [
   {"table": "records/items/lootaffixes/prefix/prefixtables/prefixa01_classskills02.dbr",
    "weight": 320, "levelMin": 29, "levelMax": 300},
   {"table": "records/items/lootaffixes/prefix/prefixtables/prefixa01_classskills02_focus.dbr",
    "weight": 320, "levelMin": 29, "levelMax": 300}
 ]
}
```

**Аффикс с "proc"-скиллом (новое поле, раньше терялось в сырых `stats`):**
```json
{
 "record": "records/items/lootaffixes/suffix/b_ar035_ar_c.dbr",
 "kind": "suffix", "name": "of Kings", "itemClassification": "Rare", "levelRequirement": 60,
 "augments": [{"skill": "records/skills/playerclass01/warcry1.dbr", "skill_name": "War Cry", "level": 2}],
 "proc": {
   "skill": "records/skills/itemskills/item_warcry.dbr",
   "skill_name": "Applies Warcry aoe buff",
   "level_eq": "itemLevel/4+1",
   "controller": "records/controllers/itemskills/cast_@selfonanyhit_20%.dbr",
   "trigger": {"chanceToRun": 20, "triggerType": "HitByEnemy", "targetType": "Self", "autoTargetRadius": 5.0}
 },
 "stats": {"characterDefensiveAbility": 26.0, "characterLife": 350.0, "defensiveStun": 25.0},
 "categories": ["Character Ability", "Character Bio", "Character Bonus Attributes",
                "Character Parameters", "Config", "Defensive Influence", "Defensive Parameters",
                "Defensive Stun", "Natural Resistance"]
}
```

**Запись `item_drop_tables` (мечи 1H, уровень предмета ~4-9) — без изменений с прошлой итерации:**
```json
"records/items/loottables/weapons/tdyn_sword1h_a01.dbr": {
  "item_types": {"WeaponMelee_Sword": 6},
  "items": [{"item": "records/items/gearweapons/swords1h/a01_sword001.dbr",
             "type": "WeaponMelee_Sword", "weight": 600}, ...],
  "prefix_pools": [{"table": ".../prefixa01_alldamagehigh01_we1h.dbr",
                     "weight": 1000, "levelMin": 1, "levelMax": 500}],
  "suffix_pools": [{"table": ".../suffixa01_off_%damage_we.dbr", "weight": 900, "levelMin": 1, "levelMax": 500},
                    {"table": ".../suffixa01_weapon_1h.dbr", "weight": 900, "levelMin": 1, "levelMax": 500}],
  "rare_prefix_pools": [...], "rare_suffix_pools": [...],
  "quality_weights": {"bothPrefixSuffix": 6000, "brokenOnly": 67000, "noPrefixNoSuffix": 40000,
                       "normalPrefixRareSuffix": 128, "prefixOnly": 2000, "rareBothPrefixSuffix": 7,
                       "rarePrefixNormalSuffix": 160, "rarePrefixOnly": 275, "rareSuffixOnly": 237,
                       "suffixOnly": 2000},
  "level_equations": {"min": "(parentLevel*.95)-8", "max": "parentLevel+4", "target": "(parentLevel*1)-2"}
}
```

## Итог

Путь: `D:/git/home/data/grim-dawn/affixes.jsonl` (15 751 KB, 7984 записей) и
`D:/git/home/data/grim-dawn/affix_tables.json` (13 341 KB, 1081 таблица + 1063 loot-item-table +
9 ascension-формул).

Три главные неопределённости:
1. `groups` в `field_schema.json` — плоский алфавитный список путей поля в дереве категорий
   редактора, а не единая иерархическая категория; я отдаю список как есть без выдумывания
   «главной» категории (см. п.3 выше).
2. ~33% суффиксов/часть префиксов не входят ни в одну известную таблицу (легаси-контент,
   подтверждено полнотекстовым поиском).
3. Точный механизм применения `jitter_pct`/`lootRandomizerCost` в движке не подтверждён (нет
   доступа к `Game.dll`), только статистическая корреляция с тиром.

Опровергнутая ранее гипотеза про «наследование дефолтов из templates.arc» для 1600
исключённых `LootItemTable_DynWeight` — снята. Настоящая причина: ~1295 из них вне
предметного домена аффиксов, а ~305 equip-таблиц (weapons/gear*) на 100% (0 контрпримеров
из 6308 резолвленных ссылок) ведут на Legendary/Epic-предметы, которые по игровой логике не
роллят случайные аффиксы — подтверждено прямым запросом по `gd.sqlite`, а не домыслом.
