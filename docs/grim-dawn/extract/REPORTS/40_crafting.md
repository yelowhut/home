# Отчёт 40 — Крафт: компоненты, аугменты, рецепты, фракции

Скрипт: `docs/grim-dawn/extract/40_crafting.py`
Запуск: `python 40_crafting.py` из `docs/grim-dawn/extract` — отработал без ошибок за ~6 секунд
(дважды: до и после появления `field_schema.json`, см. ниже).

По ходу работы координатор сообщил про распакованный `data/grim-dawn/field_schema.json`
(18968 полей: type/class/groups/description/default, из `database/templates.arc`) и
`template_types.json`. Использовал его, чтобы **проверить**, а не выдумать, семантику
самых спорных полей — прежде всего порядок 8 уровней репутации фракций (см. раздел
"Неуверенности", пункт 1) и тип поля `artifactCreationCost` (пункт 7). Уже сделанное
(структура компонентов/аугментов/рецептов) не переписывал — только сверил.

Выходы (все в `data/grim-dawn/`, старый `docs/grim-dawn/components.json` не тронут):

| Файл | Записей | Размер |
|---|---|---|
| `components.json` | 107 | 301 KB |
| `augments.jsonl` | 428 (386 enchantment + 30 faction_booster + 12 faction_warrant) | 274 KB |
| `recipes.jsonl` | 988 | 1115 KB |
| `recipes_summary.json` | (счётчики + 4 "прочих" типа) | 39 KB |
| `factions.json` | 29 фракций | 168 KB |

## Как устроена схема

### Общие приёмы (одинаковые во всех типах)
- Имя сущности — поле **`description`** (НЕ `itemNameTag`, как у носимых предметов из
  задания 10!) → резолвится тэгом. `itemText` — второй тэг, это лор/описание, не имя.
  Проверено на ItemRelic/ItemArtifact/ItemEnchantment/ItemArtifactFormula — паттерн
  одинаков везде.
- `record` — путь к `.dbr` есть у каждой сущности (правило 2 брифа).
- Нулевые/пустые поля выброшены; всё нераспознанное падает в `stats` (сырые имена
  полей `.dbr`, без домысливания).
- **"Где падает/продаётся"** (`drop_sources`) — построен один reverse-index по ВСЕЙ
  БД (82132 записи, один проход, ~5.3 c): для каждой из 1523 целевых записей собраны
  все места, где её путь встречается как значение поля в любой другой записи.
  Категории: `vendor` (поле `marketStaticItems` — вендор, часто фракционный),
  `monster` (поле `lootMisc*`/`loot*` в записи типа `Monster`), `loot_table` (тип
  начинается на `Loot`), `used_as_reagent_in` (используется как ингредиент в другом
  рецепте). Это **ссылки**, не проценты/веса дропа — резолв вероятностей это домен
  задания 30, я его сознательно не трогал.

### `components.json` (`ItemRelic`, craftingMaterial=1, 107/107)
Надмножество старой схемы `tools/build_components.py` — **все старые ключи сохранены**
(`desc`, `slots`, `resists`, `grants_skill`, `health`, `health_pct`, `armor`, `armor_pct`,
`armor_absorb_pct`), добавлено:
- `record`, `name`/`name_tag` (резолв тэга)
- `itemLevel`, `levelRequirement`, `itemCost`, `itemClassification`, `completedRelicLevel`
- `skill: {record, name, levelEq}` — если `itemSkillName` непусто (55/107 компонентов
  дают скилл, было раньше просто `grants_skill: true` без деталей)
- `stats` — **полный** нераспознанный остаток (напр. `conversionInType/OutType/
  Percentage` — конверсия типа урона, раньше терялась; `characterOffensiveAbility` и т.п.)
- `recipe` — рецепт сборки: найден через `ItemArtifactFormula`, где `artifactName`
  указывает на этот компонент (`reagents`, `creation_cost`, уровень бланка).
  84/107 компонентов имеют найденный рецепт; 23 — нет (см. "Неуверенности").
- `drop_sources` — 107/107 (100%) имеют хотя бы одну найденную ссылку.

### `augments.jsonl`
Три вида в одном файле, различаются полем `kind`:
- `"enchantment"` (386, `ItemEnchantment`) — `slots` (куда применим), `stats`,
  `faction: {id, name}` из поля `factionSource` (если есть — резолв тэгом
  `tagFactionUser<N>`), `vendor_tiers` (список репутационных тиров, на которых
  аугмент продаётся фракционным вендором — из `drop_sources.vendor`).
- `"faction_booster"` (30, `ItemFactionBooster`) и `"faction_warrant"`
  (12, `ItemFactionWarrant`) — расходники, повышающие/понижающие скорость
  набора репутации: `boosted_faction`, `boosted_multiplier` (напр. 1.5x/3x).
  Warrant — те же поля, что booster, отличие класса игровое, не смог найти
  геймплейного различия в самих данных (см. "Неуверенности").

### `recipes.jsonl` (`ItemArtifactFormula`, 988/988)
`output` (что производит, с резолвом имени), `forced_random_output` (если рецепт
выдаёт случайный предмет из пула, напр. фракционные аксессуары), `reagents`
(`reagent1..6BaseName/Quantity` + `reagentBaseBaseName/Quantity` — база вроде
Scrap/Iron Ingot), `blueprint_cost` (цена самого чертежа) отдельно от
`creation_cost` (стоимость активации у Верстака), `itemLevel`,
`levelRequirement`, `itemClassification`, `forced_relic_completion`.

### `recipes_summary.json`
Счётчики + по 3 примера и краткое описание для `ItemTransmuter` (59, косметика —
меняет только визуал), `ItemTransmuterSet` (24, то же на несколько слотов),
`ItemAscensionFormula` (9, reroll аффиксов Ascended-предметов FG), `ItemRerollFormula`
(3, reroll обычных предметов; `reagent1Quantity`/`rerollCost` — параллельные массивы,
цена растёт с числом попыток).

### `factions.json`
29 фракций — ровно столько контроллеров `records/controllers/factions/*.dbr`
(поле `myFaction` = id: `Player`, `Survivors`, `Aetherials`, `Cthonians`, `Outlaws`,
`Beasts`, `User0`..`User22`). Для `UserN`: `name` резолвится тэгом
`tagFactionUser<N>`, `info` — тэгом `...Info`, `reward_tiers` — 8 записей из тэгов
`tagFactionUser<N>Rewards1..8` (что открывается на уровне). Для 15 фракций
дополнительно найден `vendor_slug` и `vendor_unlocks` — реальный список предметов
по тирам `friendly/respected/honored/revered`, взятый из
`records/creatures/npcs/merchants/factiontables/<slug>_<tier>_01.dbr`
(поле `marketStaticItems`). Слаг → id фракции определяется **автоматически**
(без ручных догадок): беру любой предмет из таблицы тира и смотрю его
`factionSource`/`boostedFaction`.

## Спот-чек (из брифа)

Слоты компонентов (сверка со старым `components.json`, не должны были сломаться):

| Компонент | Ожидание | Получено |
|---|---|---|
| Frozen Heart (`compa_frozenheart`) | только кольца | `["ring"]` ✅ |
| Chains of Oleron (`compb_chainsofoleron`) | только торс | `["chest"]` ✅ |
| Mark of the Myrmidon (`compb_markofthemyrmidon`, не `compa_`!) | только щит | `["shield"]` ✅, плюс новое: `grants_skill: true`, скилл "Blade Barricade" |
| Runestone (`compa_runestone`) | только голова | `["head"]`, резисты `{poison:12, aether:12, elemental_all:12}` ✅ |

Дополнительно (собственная память по игре, не из брифа): Frozen Heart в игре даёт
+70 здоровья и 10% сопротивления холоду — в выходе `health: 70`, `resists.cold: 10`.
Совпадает.

Аугмент с требованием по фракции/репутации (пример из выхода, см. `augments.jsonl`):
```json
{
  "record": "records/items/enchants/a21a_enchant.dbr",
  "kind": "enchantment", "name": "Voidvine Powder",
  "slots": ["sword","mace","axe","dagger","scepter","ranged1h","offhand","shield"],
  "faction": {"id": "User2", "name": "Homestead"},
  "stats": {"offensiveFireMin": 8, "offensiveFireModifier": 25},
  "vendor_tiers": ["honored"]
}
```
Значит: продаётся вендором Homestead при репутации "Honored" — ожидаемо: в игре
фракционные аугменты открываются на предпоследнем тире репутации.

## Ещё два живых примера

Компонент с рецептом (Blessed Steel — All Weapons):
```json
{
  "record": "records/items/materia/compa_blessedsteel.dbr",
  "name": "Blessed Steel", "slots": ["sword","sword2h","mace","mace2h","axe","axe2h",
    "dagger","scepter","spear2h","ranged1h","ranged2h","offhand","shield"],
  "skill": {"name": "Sacred Strike", "levelEq": "1"},
  "stats": {"conversionInType": "Physical", "conversionOutType": "Elemental",
            "conversionPercentage": 10, "offensiveElementalMin": 5,
            "offensiveElementalModifier": 18},
  "recipe": {"reagents": [
    {"name": "Imbued Silver", "quantity": 3}, {"name": "Scrap", "quantity": 3}],
    "creation_cost": "1500"}
}
```

Рецепт (Frozen Heart):
```json
{
  "name": "Frozen Heart",
  "output": {"record": "records/items/materia/compa_frozenheart.dbr",
             "name": "Frozen Heart", "quantity": 1},
  "forced_relic_completion": true,
  "reagents": [
    {"name": "Polished Emerald", "quantity": 1},
    {"name": "Battered Shell", "quantity": 1},
    {"name": "Aether Crystal", "quantity": 1}]
}
```

## Что не удалось / в чём не уверен (обязательный раздел)

1. **[ОБНОВЛЕНО после дополнения к фундаменту] Порядок 8 уровней репутации —
   теперь подтверждён авторитетно**, не просто реконструкцией по индукции.
   Изначально (до появления `field_schema.json`) я реконструировал порядок
   вручную и ошибся в двух позициях (предполагал `Hostile`/`Neutral`).
   После того как в БД появился распакованный словарь схемы полей
   `data/grim-dawn/field_schema.json` (редакторские шаблоны из
   `database/templates.arc`), проверил picklist поля `factionStanding`
   (шаблоны `dungeonentrance`/`proxy`) и `commonMonsterGainReductionStart`
   (шаблон `factionpack`) — оба дают один и тот же официальный enum из 8
   значений: **`Nemesis, Hated, Despised, Tolerated, Friendly, Respected,
   Honored, Revered`**. Это и есть порядок `Rewards1..8`. Сходится с
   наблюдаемым в самих данных: `Rewards4` (Tolerated) везде "Empty" — нейтральная
   стартовая позиция; `Rewards5..8` (Friendly/Respected/Honored/Revered)
   совпадают с папками `factiontables/<faction>_<tier>_01.dbr`. Записано в
   `factions.json.reward_tier_order` уже не как гипотеза, а с указанием
   источника. Численные ПОРОГИ (сколько очков репутации нужно для каждого
   уровня) в `field_schema.json` не описаны (это не словарь значений, а
   словарь имён/типов полей) и в `.dbr`-записях тоже не встретились —
   подозреваю, что вычисляются в `Game.dll` (аналогично риску, отмеченному
   в задании 50 для формул).
2. **23/107 компонентов не имеют найденного рецепта** (нет `ItemArtifactFormula`
   с `artifactName`, указывающим на них). Проверил вручную: это всегда компоненты
   САМОГО НИЖНЕГО тира (напр. `compa_polishedemerald`, `compa_corpsedust`,
   `compa_chippedclaw`) — базовое "сырьё", которое падает с монстров/из сундуков
   напрямую и *само* используется как ингредиент для сборки более редких
   компонентов (это видно в их `drop_sources.used_as_reagent_in`). Это ожидаемо,
   не баг, но не проверял по игре каждый из 23 индивидуально.
3. **93/988 рецептов и 10/428 аугментов не имеют `drop_sources`** — reverse-index
   не нашёл ни одной ссылки на них нигде в БД. Либо это чисто квестовые/бэкер-
   эксклюзивные предметы (не выдаются через обычный лут/вендора), либо ссылка
   существует через промежуточный уровень (напр. таблица ссылается на ДРУГУЮ
   таблицу, а не напрямую на рецепт) — я делаю только один "хоп" резолва, глубже
   не копал (это уже пересекается с доменом задания 30).
4. **id "Drifters" vs тэг "Rovers".** Контроллер `faction_drifters.dbr` имеет
   `myFaction: User0`, а `tagFactionUser0` = "Rovers". Не баг — похоже на
   легаси-имя из разработки (фракция называлась "Drifters" до переименования в
   "Rovers", внутренние имена файлов не обновили). Итоговое имя в выходе —
   "Rovers" (из тэга, актуальное), это упомянуто как находка, не как проблема.
5. **`ItemFactionBooster` vs `ItemFactionWarrant`** — структурно идентичны
   (`boostedFaction`/`boostedMultiplier`/`itemCost`), Warrant встречаются только
   для "враждебных" направлений (`boosthostile_*`). Не нашёл в данных, чем они
   отличаются геймплейно (soulbound одинаково варьируется у обоих) — вынес как
   два разных `kind` в одном файле, разница чисто по `Class` записи.
6. **Несколько сущностей (`compb_*`) имеют в имени префикс `^k`** (напр.
   `^kMark of the Myrmidon`, `^kDread Skull`) — это управляющий код цвета текста
   (подтверждено `field_schema.json`: описание поля `itemText` прямо перечисляет
   `^n/^g/^w/^b/^r` как коды форматирования), уже так лежит в `tags_en.json`
   (выход задания 00, я его не трогал и не имею права трогать чужой файл). Стоит
   иметь в виду, если имя используется для отображения — нужна отдельная
   зачистка `^X`-кодов на стороне потребителя.
7. **[ОБНОВЛЕНО] Текстовое поле там, где ожидалось число — объяснено, не баг.**
   `craft_component_base_frozenheart.dbr.artifactCreationCost` хранится в `.dbr`
   как строка `"500"`, хотя в большинстве других формул то же поле — число
   (`1500.0`). По `field_schema.json`: тип поля `artifactCreationCost` —
   **`equation`** (то же для `reroll1Quantity`/`rerollCost` и т.п.) — значение
   может быть то литеральным числом, то настоящей формулой (пример такого поля
   в других шаблонах: `"parentLevel*1+5"`). Значит это не ошибка, а нормальное
   поведение полей типа `equation`; я передаю значение как есть (`gdlib` не
   занимается приведением типов) — потребителям `recipes.jsonl` стоит явно
   приводить `creation_cost` к числу/eval-ить как формулу при необходимости.

## Счётчики (полный вывод скрипта)

```
ItemRelic всего: 107, craftingMaterial=1 (компоненты): 107, пропущено: 0
  из них с найденным рецептом: 84
ItemEnchantment: 386
ItemFactionBooster+Warrant: 42
Итого augments.jsonl: 428
ItemArtifactFormula (recipes.jsonl): 988
  ItemTransmuter: 59, ItemTransmuterSet: 24, ItemAscensionFormula: 9, ItemRerollFormula: 3
Фракций: 29 id, 29 уникальных, 15 с вендор-слагом
reverse-index: ссылки найдены на 1420/1523 целевых записей (103 без ссылок нигде в БД)
```
