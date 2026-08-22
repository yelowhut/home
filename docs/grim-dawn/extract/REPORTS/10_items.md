# Отчёт: задание 10 — Предметы (экипировка)

Скрипт: `10_items.py`. Выход: `data/grim-dawn/items.jsonl` (8.71 MB, 7719 строк),
`data/grim-dawn/items_summary.json` (367 KB).

Это продолжение прерванного захода. Скрипт и данные уже существовали; в этом
проходе я перепроверил каждое допущение предыдущего автора против реальных
данных `gd.sqlite`, нашёл и исправил несколько реальных ошибок (см. ниже),
перезапустил скрипт и сделал требуемые спот-чеки.

## Правки предыдущего захода

1. **ItemArtifact ошибочно исключался из выхода.** Предыдущий автор посчитал,
   что `ItemRelic` и `ItemArtifact` — оба крафтовые компоненты (домен задания 40),
   и не включил ни один из них. Проверка полей показала, что это верно только
   для `ItemRelic`:
   - `ItemRelic` (`records/items/materia/comp*.dbr`) — реально имеет флаг
     `craftingMaterial=1`, `dropSound=...itemdropcraftingpart...`; это сырые
     материалы для завершения реликвии по формуле. Домен задания 40, оставлен
     не включённым.
   - `ItemArtifact` (`records/items/gearrelic/*.dbr`) — это **готовые,
     надеваемые в отдельный слот "Relic"** предметы: `artifactClassification`
     Lesser/Greater/Divine, `itemClassification` Rare/Epic/Legendary, реальные
     статы (`characterLife`, `offensivePhysicalMin/Max`...), `itemSkillName`,
     **без** `craftingMaterial`. Пример — «Blademaster's Talisman»
     (`d022_relic.dbr`, Legendary, itemLevel 60, дающий скилл «Mutilate»).
     **Добавлен в область** со слотом `"relic"` — это дало +91 предмет.
   - Для `ItemArtifact` также отключена эвристика `is_mi` (базовый тир этих
     предметов имеет `itemClassification=Rare` не потому что это monster-infrequent
     дроп, а потому что это стартовый крафтовый тир — иначе все 21 Rare-артефакта
     ложно попадали бы в `is_mi=true`).

2. **`weapon_damage` вводил в заблуждение на не-оружейных слотах.** Поля
   `offensive<Тип>Min/Max/Modifier/Chance` в `.dbr` — общие для всех типов
   предметов: на оружии это реальный урон оружия, но на кольце/амулете/броне
   те же поля значат «+X% урона типа T» или «+X-Y доп. урона типа T» (аффикс),
   а не «оружие бьёт на X-Y». Старая версия помещала их в `weapon_damage` для
   ЛЮБОГО предмета — например, у амулета «Warmaster's Pride» получалось
   `"weapon_damage": {"Physical": {"offensivePhysicalModifier": 8.0}}`, что
   бессмысленно для украшения. Исправлено: `weapon_damage` строится только для
   предметов в оружейных слотах (`weapon1h/weapon2h/*_ranged/offhand_shield` —
   офф-шилд оставлен, т.к. у 188 из 367 щитов реально есть shield-bash урон
   `offensivePhysicalMin/Max`); на остальных слотах поля остаются как есть в
   `stats` под исходным именем.

3. **`resolve_skill` терял ~17% имён скиллов.** Многие `Skill_*` записи (типа
   `playerclass03/bloodofdreeg1.dbr` — да, это реальный "Blood of Dreeg") сами
   не содержат `skillDisplayName`/`description` — имя лежит в связанной
   `..._buff.dbr` записи через поле `buffSkillName` (для пет-модификаторов —
   через `petSkillName`). Раньше это давало `"skill_name": null` в 2426 из
   14439 записей `augments` (16.8%). Добавлена рекурсия на 1-3 шага через
   `buffSkillName`/`petSkillName`/`alternatePetModifierSkillName` с защитой от
   циклов — после фикса **null-имён в augments не осталось (0 из 14439)**.
   Аналогично добавлено резолвление `itemSkillName`/`augmentSkillName*`/
   `augmentMasteryName*` **внутри бонусов сетов** (`bonuses_by_pieces`) —
   раньше там оставался только сырой путь.

4. **Имя реликвий бралось не из того поля.** У `ItemArtifact` нет поля
   `itemNameTag` — имя лежит в поле `description` (тот же паттерн-тэг, что и
   `itemNameTag` у остальных предметов; см. `gdlib.Tags.item_name()`, которая
   уже пробует именно эту пару полей). Без фикса все 91 реликвии брали имя из
   `FileDescription` — для `b016_relic.dbr` это редакторская пометка
   `"Quest Reward - Lost Elder"` вместо настоящего игрового имени
   **"Sacred Talisman"**. Проверено, что на обычном оружии/броне `description`
   всегда лишь lore-текст (например, у `c016_sword.dbr` — `"The edge of this
   blade never dulls."`) и никогда не используется как имя, если есть
   `itemNameTag` — так что фолбэк `itemNameTag or description` безопасен
   (проверено на 3473 записях вне области реликвий: 0 ложных срабатываний).

5. **Мелкое:** в `ARMOR_FIELDS`/`BLOCK_FIELDS` не хватало реальных полей
   `defensiveProtectionModifierChance` и `characterDefensiveBlockRecoveryReduction`
   (утекали в общий `stats` вместо секций `armor`/`block`) — добавлены.

Всё остальное в исходном скрипте (маппинг слотов, `ATTR_MAP` strength/dexterity/
intelligence → Physique/Cunning/Spirit, обработка сетов через `itemSetName`,
фильтр debug/placeholder записей) при проверке оказалось верным — оставлено
без изменений.

## Схема выхода (`items.jsonl`, одна строка = один предмет)

| Поле | Смысл | Источник в `.dbr` |
|---|---|---|
| `record` | путь к исходной записи | ключ `name` в `gd.sqlite` |
| `name` / `name_tag` / `name_source` | резолвленное имя, тэг-ключ, источник (`tag`/`file_description`/`record_name`) | `itemNameTag` или `description` → тэг; иначе `FileDescription`; иначе путь |
| `type` / `src` | тип записи, победивший `.arz` (base/gdx1/gdx2/gdx3) | из `gd.sqlite` |
| `slot` | слот экипировки, выведен из `type` | см. `SLOT_BY_TYPE` в скрипте |
| `itemClassification` | Broken/Common/Magical/Rare/Epic/Legendary (+`None` — 7 NPC-only записей без поля) | `itemClassification` |
| `is_mi` | эвристика Monster Infrequent (см. «Неуверенности») | вычислено |
| `itemLevel` / `levelRequirement` | уровень предмета / требуемый уровень персонажа | одноимённые поля |
| `physiqueRequirement` / `cunningRequirement` / `spiritRequirement` | требования атрибутов (наследие Titan Quest в именах) | `strengthRequirement`/`dexterityRequirement`/`intelligenceRequirement` |
| `weapon_damage` | `{ТипУрона: {offensive[Base]<Тип>Min/Max/Modifier/Chance: значение}}` — **только для оружейных слотов** | `offensive*`/`offensiveBase*` полей 9 типов урона |
| `armor` | защита брони | `defensiveProtection[Chance/Modifier/ModifierChance]`, `defensiveBonusProtection` |
| `block` | блок щита | `blockAbsorption`, `blockRecoveryTime`, `defensiveBlock[Chance/Modifier/AmountModifier]`, `characterDefensiveBlockRecoveryReduction` |
| `itemSkill` | активный скилл, дающийся предметом | `itemSkillName`(→имя)/`itemSkillLevelEq`/`itemSkillAutoController` |
| `augments` | +N к конкретному скиллу | `augmentSkillName1..5`/`augmentSkillLevel1..5` |
| `mastery_augments` | +N ко всем скиллам мастерства | `augmentMasteryName1..3`/`augmentMasteryLevel1..3` |
| `augmentAllLevel` | +N ко всем скиллам сразу | `augmentAllLevel` |
| `skill_modifiers` | модификаторы поведения конкретного скилла (обычно MI/легендарки) | `modifiedSkillName1..6` + `modifierSkillName1..6` |
| `set` | ссылка на сет | `itemSetName` (путь на запись с полями `setName`/`setMembers`, тип записи в БД — пустая строка, а не `SetPiece`, как ошибочно указано в брифе задания) |
| `stats` | всё остальное ненулевое, сырые имена полей `.dbr` | всё, что не промотировано выше |

`items_summary.json`: счётчики (`counts`), примеры исключённых записей
(`excluded_examples`), справочник сетов `sets` (набор → members + `name` +
`bonuses_by_pieces`, где индекс `i` массива = бонус при `(i+1)` надетых частях
сета — подтверждено на 6+ разных сетах: длина массива всегда равна числу
`setMembers`), и `top_stat_fields` — частотный список сырых полей в `stats`.

### Таблица «поле → человеческий смысл» (частые сырые поля `stats`)

| Поле / паттерн | Смысл |
|---|---|
| `character<X>` (`characterLife`, `characterOffensiveAbility`, ...) | плоский бонус к характеристике/ресурсу персонажа |
| `defensive<Тип>` | % сопротивления урону типа `<Тип>` |
| `retaliation<Тип>Min/Max/Modifier` | урон типа `<Тип>`, наносимый в ответ атакующему (retaliation/thorns) |
| `offensiveSlow<Тип>...` | **не** то же самое, что `offensive<Тип>` — это урон/бонус DoT-варианта (`SlowFire`=горение, `SlowPoison`=яд-DoT, `SlowBleeding`=кровотечение, `SlowLife`=истощение жизненной силы), название "Slow" — наследие движка Titan Quest, где DoT реализован как "замедленный" эффект |
| `conversionInType`/`conversionOutType`/`conversionPercentage[2]` | конверсия X% урона одного типа в другой (напр. Physical→Fire); может быть 2 независимых конверсии на предмет (суффикс `2`) |
| `itemCostName`/`itemCost` | ссылка на формулу цены в магазине / сама цена |
| `attributeScalePercent` | множитель масштабирования итемлевела для роллов на этом шаблоне (влияет на разброс аффиксов при генерации, не является статом самого предмета) |
| `armorClassification` | Light/Medium/Heavy — класс брони (влияет на визуал/требования, не на числа) |
| `soulbound` | предмет привязывается к персонажу после подбора |
| `itemStyleTag` | визуальный тир иконки/рамки (Unique Tier 2 и т.п.), косметика |

## Спот-чек (обязательный пункт)

**1. Sunherald's Claymore** (`tagGDX2WeaponMelee2hB209`, встречается 7 раз —
записи `b209a..b209f/records/items/gearweapons/melee2h/`, разные itemLevel
20/40/55/70/84/94 — это стандартный паттерн шкалирования Monster Infrequent
по сложности). Пример записи (уровень 94):

```json
{
 "record": "records/items/gearweapons/melee2h/b209f_sword2h.dbr",
 "name": "Sunherald's Claymore",
 "type": "WeaponMelee_Sword2h", "slot": "weapon2h",
 "itemClassification": "Rare", "is_mi": true,
 "itemLevel": 94, "levelRequirement": 94,
 "weapon_damage": {"Fire": {"offensiveBaseFireMin": 258.0, "offensiveBaseFireMax": 440.0,
                            "offensiveFireMin": 34.0, "offensiveFireModifier": 95.0}},
 "itemSkill": {"skill_name": "Solar Nova", "levelEq": "6", ...},
 "augments": [{"skill_name": "Blast Shield", "level": 4}, {"skill_name": "Menhir's Bulwark", "level": 4}],
 "skill_modifiers": [...]
}
```

Подтверждение: двуручный меч (`weapon2h`), Monster Infrequent (`is_mi=true`,
подтверждено тэгом-источником `tagGDX2Miniboss_Side_06 = "Astros the
Sunherald"` — это и есть монстр, с которого падает предмет), даёт +4 к Blast
Shield/Menhir's Bulwark (Солдат) — всё сходится с ожиданием игрока
(конверсия физ→огонь идёт через **прописанный напрямую Fire-урон оружия**
`offensiveBaseFireMin/Max`, а не через отдельное поле `conversionInType/
conversionPercentage` — на этом конкретном предмете такого поля просто нет:
оружие изначально не имеет физического компонента урона вообще, эффект
«конверсии» достигается тем, что базовый урон задан сразу как Fire).
Это стоит иметь в виду: «конверсия» в описании предмета в игре — не всегда
буквальное поле `conversionPercentage` в БД.

**2. Сет "The Unseeing Eye"** (`itemset_c009.dbr`, 5 частей: голова, торс,
амулет, булава, меч). Голова сета — «Cowl of the Blind Assassin»
(`gearhead/c019_head.dbr`, Epic, itemLevel 70) — `entity["set"]["record"]`
верно указывает на `itemset_c009.dbr`. В `items_summary.json → sets` для
этого сета `bonuses_by_pieces` содержит массивы длиной 5 (= число частей):
например `offensivePierceModifier: [0,70,70,70,70]` (бонус активен уже с 2
частей) и `conversionPercentage: [0,0,0,0,30]` (Cold→Pierce конверсия
разблокируется только на полном комплекте из 5 частей) плюс резолвленные
имена: `augmentMasteryName1_resolved: "Nightblade"`, `itemSkillName_resolved:
"Eye of Thaddeus"`. Значения выглядят осмысленно для Occultist/Nightblade-сета.

## Сверка с авторитетной схемой полей (`field_schema.json`)

После первого прохода координатор распаковал `database/templates.arc` →
`data/grim-dawn/field_schema.json` (18968 полей: `type`/`class`/`groups`/
`description` из самих редакторских `.tpl`). Прогнал по нему все ключевые
поля, на которые опирается скрипт и этот отчёт — **ни одного случая
выдуманной семантики не нашлось**, наоборот, схема независимо подтвердила
каждое из сделанных выше допущений:

| Поле | `groups` из схемы | Подтверждает |
|---|---|---|
| `craftingMaterial` | `Item Parameters`, описание **"Reagent"** | ItemRelic — крафтовый реагент, не гир (правка №1) |
| `artifactClassification` | `Artifact Config`, шаблон `itemartifact` | ItemArtifact — отдельный, самостоятельный тип предмета (правка №1) |
| `completedRelicLevel` | `Relic Config`, шаблон `itemrelic` | у ItemRelic свой шаблон `itemrelic.tpl`, отличный от `itemartifact.tpl` |
| `buffSkillName` | `Skill Config`, шаблоны `skill_buffradius`/`skill_attackbuffradius`/... | законное поле-ссылка на "настоящую" именованную запись (правка №3) |
| `petSkillName`, `alternatePetModifierSkillName` | `Pet Modifier`, описание **"Skill that modifies the parent pet"** | та же правка №3, для pet-модификаторов |
| `itemSetName` | `Item Parameters`, описание **"ItemSet"** | подтверждает, что бриф ошибся, назвав целевой тип `SetPiece` — на деле это отдельная сущность ItemSet без строкового `type` в БД |
| `setMembers` | `Config`, описание **"max pieces"** | подтверждает трактовку `bonuses_by_pieces`: длина массива = число частей сета |
| `offensiveSlow<Тип>*` | `Offensive Duration` (а не `Offensive Absolute`, как у обычных `offensive<Тип>*`) | подтверждает, что это отдельная, duration/DoT-категория стата, а не дубль обычного урона |
| `bonusTableName` | `Artifact Config`, `Relic Config`; описание **"LootRandomizerTable"** | подтверждает, что это ссылка на отдельную таблицу генерации бонусов по уровню — законно оставлена нерезолвленной (см. «Неуверенности», п. 6) |
| `modifiedSkillName1`/`modifierSkillName1` | `Skill Modifiers` | отдельная от `Skill Augment` категория — подтверждает, что это не то же самое, что `augmentSkillName*` |
| `defensiveProtectionModifierChance`, `characterDefensiveBlockRecoveryReduction` | `Defensive Protection` / `Character Ability` | оба реальные поля своих категорий — подтверждает правку №5 (были упущены) |

Единственное расхождение: у поля `description` схема не перечисляет шаблоны
`itemartifact`/`itemrelic` среди `templates` (только `achievement`, `actor`,
`skilllocation` и т.п.) — вероятно, схема не разворачивает наследование
`.tpl` (например `itemartifact.tpl` включает базовый `actor.tpl`, где и
объявлено `description`), поэтому напрямую в дампе не отражена связь. Проверку
безопасности фолбэка `itemNameTag or description` (правка №4) я делал не по
схеме, а эмпирически — по всем 3473 записям вне `ItemArtifact` (см. выше,
0 ложных срабатываний), так что вывод не зависит от этого пробела в схеме.

## Что не удалось / в чём не уверен

1. **`is_mi` — эвристика, не 100% точная.** Правило: `itemClassification ==
   "Rare"`, путь не содержит `storyelements`/`quest`, `FileDescription` не
   пуст/не «blank»/«template»/«none». Даёт 2727 из 2982 Rare-предметов как MI.
   234 Rare-предмета НЕ помечены (в основном квестовые награды и несколько
   безымянных «базовых» записей типа `b100_necklace.dbr` с `name_source=
   "record_name"` — вероятно, недоделанные/неиспользуемые шаблонные записи,
   не отфильтрованные текущим regex'ом заглушек, т.к. их `FileDescription`
   пуст, а не содержит слово «blank»). Не проверял вручную все 2727 против
   вики — только 1 конкретный кейс (Sunherald).
2. **7 предметов с `itemClassification: null`** — все это `ArmorProtective_Chest
   "Ragged Tunic"` (`geartorso/m01_torso001*.dbr`). Похоже на NPC-only
   косметическую одежду без игровой классификации (не лут для игрока), но я
   не проверял по игре/вики, реально ли она когда-либо выпадает игроку —
   оставил в выходе, т.к. явного признака "не для игрока" (типа `cannotPickUp`)
   на этих записях нет.
3. **`skill_modifiers.modifier_name` почти всегда `null`** (это ожидаемо и
   не баг): записи `Skill_Modifier`, на которые ссылаются `modifierSkillName*`
   (обычно "MI mod" — визуальный/поведенческий довесок к скиллу мастерства,
   типа `sword2h_b209_blastshield.dbr`), в игре не имеют собственного
   отображаемого имени — они меняют поведение уже названного скилла
   (`modifies_name`), а не являются отдельным скиллом. Оставил `null` как
   есть — резолвить их в отдельное «имя» значило бы придумывать несуществующую
   семантику.
4. **200 из 207 реально существующих `records/items/lootsets/*.dbr` попали
   в `items_summary.json → sets`** — 7 сетов не задеты, т.к. ни один их член
   не попал в нашу область типов (либо все части такого сета отфильтрованы
   как debug/placeholder, либо сет целиком относится к типам вне области,
   например к компонентам). Не разбирал эти 7 отдельно.
5. **`conversionPercentage`/`conversionInType`/`conversionOutType`** (и `*2`)
   оставлены в `stats` как есть без промоушена в отдельную секцию — брифом
   явно не требовалось выносить их отдельно («конверсии» упомянуты в списке
   для `stats`), но если для следующего задания понадобится собранная
   секция `conversions`, её сейчас в выходе нет отдельным полем — придётся
   парсить `stats` по этим трём ключам.
6. **Поле `bonusTableName`** на `ItemArtifact`/`ItemRelic` (ссылка на таблицу
   `completionbonus_*` с уровне-зависимыми бонусами) оставлено как сырой путь
   в `stats`, не резолвится и не разворачивается — это отдельная сущность
   (таблица бонусов по уровню), разбор её содержимого выходит за рамки этого
   задания, зафиксировано только как сырая ссылка.
7. Список `DAMAGE_TYPES` (9 типов: Physical/Pierce/Fire/Cold/Lightning/Poison/
   Life/Aether/Chaos) сверен через полный обход `offensiveBase*Min` полей по
   всем оружейным типам — это все базовые типы, что реально встречаются как
   "urонoruжия" в `.dbr`. Но не проверял, есть ли ещё скрытые типы урона,
   которые встречаются ТОЛЬКО как `offensive<Тип>Modifier` без парного
   `Min/Max` где-либо в игре (маловероятно, но не исключаю). Также
   `field_schema.json` показывает, что `conversionInType`/`conversionOutType`
   допускают ещё значения `Elemental` и `Stun`, которых я не встретил ни на
   одном предмете в области — не проверял, действительно ли они нигде не
   используются, или просто не попались в выборке.
8. **Один найденный, но не обработанный отдельно артефакт схемы**: в наборе
   `itemset_c302.dbr` (Awakened Bloodmane) шестой слот `augmentSkillName6`
   фактически содержит путь на **мастерство** (`_classtraining_class04.dbr`,
   "Nightblade"), а не на конкретный скилл — то есть игра иногда переиспользует
   "Skill Augment"-слот для мастерства, когда слоты `augmentMasteryName1..3`
   уже заняты. Поле резолвится общим механизмом (см. правку №3) и попадает в
   `sets["...c302..."]["bonuses_by_pieces"]["augmentSkillName6_resolved"] =
   "Nightblade"` — технически корректно, но при разборе вниз по пайплайну
   стоит не полагаться на то, что `augmentSkillName*` — всегда именно скилл,
   а не мастерство. На отдельных предметах экипировки (не сетах) поле
   `augmentSkillName6` не встретилось ни разу.

## Счётчики

- Записей в области типов: 8116; записано: 7719.
- Пропущено как debug/sandbox путь: 203; как заглушка (BASE BLANK/TEMPLATE): 194.
- `is_mi=true`: 2727. Сетов: 200. Уникальных сырых полей в `stats`: 295.
- По слотам: weapon1h 1348, head 810, chest 721, shoulders 711, offhand 508,
  weapon2h 465, amulet 421, medal 407, ring 391, offhand_shield 347, waist 300,
  weapon2h_ranged 289, legs 279, weapon1h_ranged 231, hands 217, feet 183,
  **relic 91 (новое)**.
- По классификации: Rare 2982, Epic 1678, Legendary 1614, Common 1392,
  Magical 36, Broken 10, None 7.
