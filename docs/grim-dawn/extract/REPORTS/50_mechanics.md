# Отчёт 50 — Механики, константы, формулы

Скрипт: `docs/grim-dawn/extract/50_mechanics.py`
Выход: `data/grim-dawn/mechanics.json` (572 554 байт, ~559 KB)

Задание отдельное от контента (предметы/скиллы/монстры) — это «правила игры»:
константы движка, формулы боя/опыта, таблица уровней, и главное — таблица
соответствия «имя поля `.dbr` → тип урона/сопротивление/модификатор», нужная
всем остальным экстракторам.

## Важное дополнение координатора (учтено)

В процессе работы координатор дал доступ к `D:/git/home/data/grim-dawn/field_schema.json`
(18 968 полей, распакованы из `database/templates.arc` — редакторских шаблонов
самой игры, скрипт `02_templates.py`, не моя работа). Это авторитетный ответ
на «что значит поле X» (официальные `type/class/groups/description` из
самого движка), в отличие от частотного анализа по данным, который я до этого
использовал как единственный источник. **Скрипт переписан** так, чтобы:

1. `field_schema.json` — основной источник смысла (`groups`/`description`
   тянутся в каждый узел таблицы через `schema_of()`).
2. Частотный анализ по `gd.sqlite` (как было изначально) — теперь ПРОВЕРКА
   покрытия и источник живых примеров-подтверждений, а не единственная опора.
3. Добавлен раздел `from_db.schema_coverage_check`, который явно сверяет два
   источника: сколько полей из групп Offensive/Defensive/Retaliation/
   Conversion схемы реально встречаются в живых данных, и сколько из них
   попало в мою итоговую таблицу. **После доводки — 832 из 832 (100%)**
   реально используемых в игре полей этих семейств учтены явно (см. ниже).
4. Благодаря `field_schema.json` нашлось и было исправлено:
   - официальные "Index by difficulty 0 to 2" пометки на 18 полях
     `gameengine.dbr` (кэпы скорости атаки/каста/бега, `monsterLevelGapFixer`
     и т.д.) — раньше я видел только сырые 3-элементные массивы и
     предполагал, что это Normal/Elite/Ultimate; теперь это подтверждено
     самой игрой, а не моей догадкой;
   - официальные названия групп `Elemental Damage Reduction Percent` vs
     `Elemental Resistance Reduction Percent` — раньше я различал эти два
     поля только по именам скиллов-источников, теперь это официальные,
     разные категории в самой схеме движка;
   - picklist `conversionInType`/`conversionOutType` со списком из 11
     официальных типов (`Physical;Pierce;Elemental;Cold;Fire;Poison;
     Lightning;Life;Chaos;Aether;Stun`) — раньше список типов конверсии я
     собирал только по найденным в данных примерам;
   - целое семейство `offensiveBase<Type>` (группа "Item Base Damage" —
     врождённый базовый урон оружия до % бонусов) и `retaliationSlow<Type>`
     (DoT-версия retaliation), которые я изначально пропустил;
   - уточнение по `characterDodgePercent`/`DodgeChance` (см. `known_gaps`
     ниже — раньше я писал "не найдено вообще", что было неверно: поле
     есть, но только на монстрах/AI-контроллерах, не на игроке).

## Как построена главная таблица (damage_type_table / status_effect_table)

Ничего не подставлено по памяти. Порядок был такой:

1. Один проход по всем 82 132 записям БД → частотный словарь ВСЕХ 14 904
   встретившихся имён полей + первый живой (ненулевой) пример на каждое.
2. Из этого словаря вручную выделены поля с префиксами `offensive*`,
   `defensive*`, `retaliation*` (852 варианта) и сгруппированы по стеблю
   после вычитания стандартных суффиксов (`Min/Max/Chance/Modifier/Global/
   XOR/Duration/MaxResist/...`).
3. Для каждого предполагаемого «типа» (Fire, Cold, Stun, Petrify, …)
   гипотеза о смысле проверена на конкретных живых записях (не выдумана):
   - `defensiveFire/Cold/Lightning/Poison/Pierce/Bleeding/Life/Aether/
     Physical/Chaos` — сверено с `tagStatsResistance01..10` и их
     `...Desc` (официальные игровые описания сопротивлений из `tags_en.json`,
     например `tagStatsResistance04Desc` = "Resistance to foul poisons and
     potent acids that deal Acid or Poison damage.").
   - `offensiveSlow<Type>` (DoT) — проверено на
     `records/skills/nonplayerskills/bossskills/ghoul_plagius_plague.dbr`
     (босс Plagius, скилл "Plague") — `offensiveSlowPoisonMin/Max` +
     `offensiveSlowPoisonDurationMin/Max`, что однозначно читается как
     "яд-DoT длительностью N сек" — совпадает с тем, что Plagius известен
     как ядовитый гуль с DoT-атакой.
   - `defensive<Type>MaxResist` (прибавка к КЭПУ резиста) — проверено на
     `records/items/gearaccessories/medals/c007_medal.dbr` ("Mark of Oaths",
     `defensiveFireMaxResist=2.0`) и на компонентном скилле
     `comp_radiantshield_01.dbr` (`defensiveFireMaxResist=10.0`).
   - `conversionInType/conversionOutType/conversionPercentage` (конверсия
     урона) — проверено на щите `b003d_shield.dbr` (Physical→Life 15%),
     на нескольких `_gun*.dbr`/`_sword*.dbr` (Physical→Cold/Chaos/Aether/
     Lightning 15-45%) и на монстрском скилле `caster_b017_doombolt.dbr`
     (Chaos→Lightning 100%). Найдено **84** уникальных пары (In,Out).
   - `offensivePierceRatio` — проверено на `Ghavlin's Crossbow`
     (`b008c_gun2h.dbr`): `offensivePierceMin=22`, `offensivePierceRatioMin=100`
     — согласуется с известной механикой "% урона Pierce, игнорирующего броню".
   - CC-статусы (`Stun/Freeze/Petrify/Sleep/Trap/Fumble`) — проверено по
     именам скиллов-источников: `timewarped_petrifyingburst` (Petrify),
     `item_defensesleepnova_01` (Sleep), `item_slimeball` (Trap),
     `loghorrean_barfx` (Fumble, атака финального босса Loghorrean).
   - RR (снижение сопротивления цели) — проверено на
     `records/skills/playerclass01/warcry2.dbr` (Soldier, "War Cry" —
     `offensivePhysicalResistanceReductionAbsoluteMin`, известный флэт-RR
     скилл) и `records/skills/devotion/tier2_01c_skill.dbr`
     (`offensiveElementalResistanceReductionAbsoluteMin`).
4. Только после этого построена итоговая таблица — программно, а не руками:
   для каждого проверенного типа скрипт **сам** проверяет по частотному
   словарю, какие из шаблонных полей (`offensive{Type}Min`,
   `defensive{Type}MaxResist`, …) реально существуют в БД, и подтягивает
   первый живой пример с указанием записи-источника.

## Схема выхода JSON

```
{
  "meta": {source_db, source_field_schema, total_records_scanned,
            distinct_field_names_seen, distinct_field_names_in_editor_schema},
  "from_db": {
    "engine_constants":        { record, fields{...} },   # gameengine.dbr;
        # 18 "Index by difficulty 0-2" полей уже переразмечены как
        # {by_difficulty:{Normal,Elite,Ultimate}, schema_description}
    "combat_formulas":         { record, fields{...}, crit_pth_table[...] },
    "experience_formulas":     { record, fields{...} },
    "resource_regen":          { record, fields{...} },   # life/mana regen
    "player_score_formula":    { record, fields{...} },
    "level_system":            { maxPlayerLevel, maxDevotionPoints,
                                  experienceLevelEquation, ..., skill_points_
                                  from_leveling_1_to_max, attribute_points_
                                  from_leveling_1_to_max, ... },
    "base_character_stats_lvl1": { record_male/female, male{...}, female{...} },
    "difficulty_player_resist_penalty": {
        record, resist_penalty_by_difficulty: {
          Fire: {by_difficulty:{Normal,Elite,Ultimate}, field, raw_12}, ...
        } },
    "difficulty_monster_scaling": { record, monster_buffs_by_difficulty{...} },
    "damage_type_table": [
      { type, category, resist_name, resist_desc,
        offensive_base_weapon_damage{...}, offensive_instant{...},
        offensive_dot{...}, defensive_resist{...}, retaliation{...},
        retaliation_dot{...} }, ... × 10
    ],
    "status_effect_table": [ ... × 25, та же форма без resist_name/desc ],
    "resistance_reduction_and_global_modifiers": { <field>: {schema,
        records_using, example} }, # 126 полей: Total/Physical/Elemental RR
        (Absolute/Percent), AllResistance/AllMaxResist, CrowdControl-резист,
        PierceRatio (полное семейство), Protection/Absorption/BonusProtection
        (формула брони), CritDamageModifier, LifeLeech, ManaBurn, "Elemental"
        псевдо-тип, и т.д.
    "schema_coverage_check": { note, schema_fields_in_..._groups: 941,
        of_those_actually_used_in_live_data: 832,
        captured_in_this_output: 832, missed_count: 0 },
    "damage_conversion": { fields{...}, authoritative_types[11] (из picklist
        схемы), distinct_in_out_pairs_found_in_data: 84, examples[...] },
    "item_cost_formulas": { record, fields{...} }
  },
  "known_gaps": [ ...8 пунктов... ],
  "spot_check": { max_character_level, resist_cap_on_ultimate,
                  oa_per_1_point_dexterity }
}
```

Каждое поле `offensive_instant.instant_min` и т.п. внутри `damage_type_table`
имеет вид `{"field": "offensiveFireMin", "schema": {type, class, groups,
description, default}, "records_using": 24415, "in_editor_schema_but_
unused_in_data": false, "example": {"record": ..., "type": ..., "value": ...}}`
— то есть и официальное определение поля из схемы движка, и прямая ссылка на
реальную запись-источник, а не придуманное число.

## Счётчики

- Записей просканировано: **82 132**, различных имён полей в живых данных:
  **14 904**; в редакторской схеме (`field_schema.json`): **18 968**.
- `damage_type_table`: **10** типов урона (Physical, Pierce, Fire, Cold,
  Lightning, Poison, Life/Vitality, Aether, Chaos, Bleeding), для каждого
  — до 5 семейств (offensive base weapon damage, offensive instant, offensive
  DoT, defensive resist, retaliation, retaliation DoT) × до 9 вариантов полей,
  каждое поле — с официальными `groups`/`description` из схемы плюс живым
  примером записи-источника из данных.
- `status_effect_table`: **25** статусов/CC (Stun, Freeze, Petrify, Sleep,
  Trap, Taunt, Confusion, Fear, Convert, Knockdown, Disruption, Fumble,
  ProjectileFumble, PercentCurrentLife, ManaBurn, SlowLifeLeach/ManaLeach,
  DefensiveAbility/OffensiveAbility-debuff, DefensiveReduction/
  OffensiveReduction, AttackSpeed/RunSpeed/TotalSpeed-debuff, DamageMult).
- Конверсия урона: **84** уникальных пары (In→Out) в данных; **11**
  официальных типов конверсии из picklist схемы (`authoritative_types`).
- `resistance_reduction_and_global_modifiers`: **126** полей (Total/Physical/
  Elemental RR Absolute/Percent, Protection/Absorption/BonusProtection брони,
  PierceRatio, ManaBurn, CritDamageModifier, LifeLeech и др.).
- `schema_coverage_check`: **832 из 832** (100%) полей из групп Offensive/
  Defensive/Retaliation/Conversion схемы, реально встречающихся в живых
  данных, учтены явно в таблицах выше (после нескольких итераций доводки —
  подробности в разделе про `field_schema.json` выше).
- `known_gaps`: **8** пунктов.
- Размер выхода: **572 554 байт**.

## Спот-чек (обязательный)

### 1. Максимальный уровень персонажа
`records/creatures/pc/playerlevels.dbr` → `maxPlayerLevel = 100`.
Совпадает с общеизвестным (кап 100 в текущей версии игры с FG/expansion 3).

### 2. Кэп сопротивлений на Ultimate
**Явного поля-кэпа в БД нет.** Нашёл только штраф к ТЕКУЩЕМУ сопротивлению
игрока по сложности в `records/game/balancingadjustment_mp+difficulty_players01.dbr`
(массивы `defensive<Type>` длины 12 = 3 сложности × 4 размера пати,
подтверждено — внутри каждой четвёрки значения одинаковы, т.е. от размера
пати штраф игроку не зависит):

| Тип | Normal | Elite | Ultimate |
|---|---|---|---|
| Fire / Cold / Lightning / Pierce / Poison | 0% | −25% | −50% |
| Aether / Chaos / Life(Vitality) / Bleeding / SlowLifeLeach | 0% | 0% | −25% |
| Physical | 0 (не массив, скаляр 0 на всех сложностях) | | |

Базовый КЭП резиста (в игре общеизвестен как 80%, из общих источников, но
это НЕ проверено этим заданием и не должно считаться фактом из БД) как
константа в `.arz` не найден — видимо зашит в `Game.dll`. Что БД
подтверждает — это МЕХАНИЗМ повышения кэпа: поля `defensive<Type>MaxResist`
на конкретных предметах/скиллах (пример: медаль "Mark of Oaths" даёт
`defensiveFireMaxResist = 2.0`, компонентный скилл Radiant Shield —
`10.0`). Раздел `known_gaps` явно фиксирует эту дыру.

### 3. Сколько OA даёт 1 очко Хитрости (Dexterity)
`records/game/combatformulas.dbr` → `offensiveAbilityEquation`:
```
(offensiveAbilityDV + (characterLevelDV * 12) + ((dexterityDV + bonusDV) *0.5))
  * (1 + (offensiveAbilityModifierDV / 100)) + 53
```
Коэффициент при `dexterityDV` — **0.5**, то есть 1 очко Хитрости даёт
**0.5 OA** до применения % модификаторов. Аналогично `defensiveAbilityEquation`
даёт коэффициент 0.5 при `strengthDV` (1 очко Силы → 0.5 DA).

**Оговорка (честно указана и в JSON, и здесь):** контрольная запись
персонажа 1 уровня (`records/creatures/pc/malepc01.dbr`) показывает
`characterDexterity=50`, `characterOffensiveAbility=65` — это НЕ сходится
арифметически при подстановке формулы "в лоб" (12+25+53=90≠65). Значит
`dexterityDV`/`characterLevelDV`/`offensiveAbilityDV` в реальном движке —
не сырые видимые статы персонажа, а отдельно нормализованные "derived
values", которых нет напрямую в `.dbr`. Коэффициент 0.5 при Dexterity
в формуле — факт из БД; абсолютная сходимость с итоговым OA на экране
персонажа данными из статического дампа не проверяется. Это прямо
прописано и в `spot_check.oa_per_1_point_dexterity.explanation`, и в
`known_gaps`.

## Что не удалось / в чём не уверен

1. **Базовый кэп сопротивлений (80%?)** не найден как явная константа —
   см. спот-чек №2 выше. Проверено и по `field_schema.json`: ни у одного
   поля нет `description`, упоминающего "resist"+"cap" — значит константа
   не задокументирована даже в редакторских шаблонах, только в `Game.dll`.
   **Уклонение (dodge)** — уточнено через схему: поле `characterDodgePercent`
   существует (группа "Character Ability"), но в живых данных встречается
   ТОЛЬКО на записях `Monster`/`ControllerMonster`/`ControllerGraeae`
   (пример: `records/creatures/anomalies/anomaly_a01.dbr`, 25%; боссовский
   контроллер `controller_boss_witchgodguardian_dreegeye.dbr`, `DodgeChance`
   =80) — это AI-механика уклонения монстров/боссов (когда и куда отскочить
   от атаки), а не итемизируемый защитный стат игрока: ни одного предмета/
   скилла/девоушена с ненулевым `characterDodgePercent` на стороне игрока не
   нашлось. Похоже, в этой версии GD у игрока в принципе нет статистического
   "уклонения" как отдельного механизма (защита игрока — только через
   DA/резисты/блок/абсорб/протекшн). Кэп блока тоже не найден числом — есть
   только формула `meleeBlockEquation = blockChanceDV + blockChanceModifierDV`
   без верхней границы ни в данных, ни в схеме.
2. **`defensive<Type>Duration`** (поле есть у каждого типа урона в таблице)
   — по `field_schema.json` не имеет собственного `description`, только
   групповую метку наравне с самим ресистом; текста тултипа, прямо
   поясняющего смысл, не нашлось. Разница между `offensive<Type>
   ReductionPercent` и `offensive<Type>ResistanceReductionPercent` теперь
   ПОДТВЕРЖДЕНА официальными group-метками схемы (не только именами
   скиллов): `Elemental Damage Reduction Percent` (ослабляет урон,
   наносимый целью) — это отдельная от `Elemental Resistance Reduction
   Percent` (RR, снижает сопротивление цели) категория в самой игре, что
   снимает часть неуверенности из первой версии этого отчёта. Задание явно
   просило 3 типа RR (flat/% reduced/% reduction) — и в данных, и в схеме
   нашлось ровно 2 официальных RR-механизма на семейство ("Absolute" и
   "Percent", для Total/Physical/Elemental); третий вариант из брифа не
   идентифицирован как отдельная механика ни там, ни там.
3. **`characterModifierPoints = 1`** (очко атрибута за уровень) — это
   скаляр на всю игру (в отличие от `skillModifierPoints`, который убывает
   по уровням: 3→2→1). Из левелинга 1-100 выходит 100 очков атрибутов и
   238 очков навыков (посчитано скриптом из реальных массивов, не по
   памяти). Это НЕ включает бонусные очки от квестов — поле
   `bonusSkillPoints`/`bonusAttributePoints` встретилось только на
   сундуках/дверях/контейнерах со значением 0; реальные квестовые награды
   хранятся в `.qst`-файлах вне `.arz`, которые этот пайплайн не парсит.
   Соответственно 238/100 — это база "от левелинга", а не то число, что
   видит игрок в конце игры (оно больше за счёт квестов).
4. **`LevelTable` (упомянутый в задании как "1268 записей")** — на
   практике этот тип записей в БД используется для **лут-таблиц по
   уровню предмета** (`records/items/loottables/*`), а не для таблицы
   роста статов персонажа по уровню, как можно было подумать из названия.
   Реальный источник данных о прогрессии персонажа —
   `records/creatures/pc/playerlevels.dbr` (`experienceLevelEquation`,
   инкременты статов, массив очков навыков). Не выдумывал соответствие —
   прямая формула "Life(уровень)" в БД просто отсутствует: рост Life/Mana
   идёт исключительно через вложение очков атрибутов (`lifeIncrement=20`
   за очко Физики, `lifeIncrementDexterity=8`/`lifeIncrementIntelligence=12`
   — побочный прирост от Хитрости/Духа, `manaIncrement=16` за очко Духа),
   не как функция от уровня напрямую.
5. **Crucible / Shattered Realm / Nemesis-скейлинг** практически не
   расшифрован — в `records/game/` нашлись только
   `challengeareas/challengelayer*.dbr` (тип `ChallengeArea`) и
   `challengelayerscaling_*.dbr` (тип `AttributePak`, структура похожа на
   `balancingadjustment_mp+difficulty_*`, но не распарсена подробно в этом
   задании — вне заявленного фокуса "механики, не контент", и по объёму
   тянет на отдельное под-задание). Явных формул скейлинга волн/раундов
   Crucible или уровней Shattered Realm не нашёл.
6. **`offensive<Type>Global`/`XOR`** — поля есть почти у каждого типа
   (тысячи записей), их смысл — служебные флаги генератора случайных чисел
   для увязки роллов между несколькими статами одной записи лута (общий
   RNG-сид), это стандартное соглашение схемы `.dbr`/движка Titan Quest'а,
   на котором построен GD, а не игровой геймплейный параметр — включил в
   таблицу для полноты (видно, что поле существует), но не расписывал
   отдельно как "дамаг/резист", подтверждения через конкретный игровой
   тултип не искал (не геймплейная величина).

## Спот-чек по данным (что "видел глазами")

Открыл `mechanics.json`, проверил:
- `from_db.damage_type_table[Fire]` — все 4 семейства полей (offensive
  instant/DoT, defensive resist, retaliation) заполнены с живыми примерами
  записей (`item_elementalforce.dbr`, `ghoul_plagius_plague.dbr`-подобные
  DoT-примеры, `chthonianfiend_h05.dbr` резист 50%, `d008_torso.dbr`
  retaliation 180).
- `from_db.difficulty_player_resist_penalty` — таблица штрафов по
  Normal/Elite/Ultimate для 10 типов, числа −25/−50 повторяются
  консистентно для "основных пяти" (Fire/Cold/Lightning/Pierce/Poison) и
  −25 только на Ultimate для "поздних" типов (Aether/Chaos/Life/Bleeding).
- `from_db.level_system` — maxPlayerLevel=100, maxDevotionPoints=55,
  skill_points_from_leveling_1_to_max=238, attribute_points...=100.
- `from_db.damage_conversion.examples` — 8+ живых примеров конверсии
  (щиты/оружие/скиллы), проценты 15-100%, типы Physical→{Life,Cold,Poison,
  Chaos,Aether,Lightning,Fire}.

## Определение готовности (DoD) — самопроверка

- [x] Скрипт реально запущен (`python 50_mechanics.py`), вывод видел (в
      финальной версии, после интеграции `field_schema.json`): "field_schema.json
      загружен: 18968 полей .dbr", "всего записей: 82132, различных полей:
      14904", "Записано: ... (572554 байт)", "damage_type_table: 10 типов",
      "status_effect_table: 25 статусов/CC", "resistance_reduction/global
      fields: 126", "conversion пар найдено: 84", "known_gaps: 8". Также
      проверил `schema_coverage_check` в самом JSON: 832/832 (100%).
- [x] Выходной файл существует (`data/grim-dawn/mechanics.json`), открыл и
      глазами проверил 3+ записи (Fire-таблица целиком, difficulty-штрафы,
      level_system, conversion examples — см. выше).
- [x] Спот-чек: макс. уровень (100), резист-штраф на Ultimate (−50%/−25%
      по типам, с честной оговоркой про отсутствие явного КЭПА), OA за
      очко Хитрости (0.5, коэффициент из формулы, с оговоркой про
      несходимость абсолютных чисел) — все три с указанием записи-источника.
- [x] Отчёт написан, раздел «что не удалось» — 6 пунктов, честно, плюс
      `known_gaps` (8 пунктов) прямо в самом JSON-выходе для потребителей.
