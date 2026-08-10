# Отчёт 20 — Мастерства и деревья навыков

Скрипт: `docs/grim-dawn/extract/20_skills.py`
Выход (после исправления бага покрытия, см. раздел «Обновление» ниже):
- `data/grim-dawn/skills.json` (2 238 733 байт, ~2186 KB)
- `data/grim-dawn/skills_flat.jsonl` (1 717 136 байт, ~1677 KB, 1721 строка)

**Старые цифры этого блока (до исправления)**: `skills.json` 1630 KB, `skills_flat.jsonl`
1164 KB / 1135 строк, `item_skills` 789. Везде ниже по тексту отчёта, где встречаются эти
старые числа (789 item-скиллов, 1135 плоских строк, 161 пустое имя) — это **историческая
версия задания**, оставлена как есть для истории расследования; актуальные цифры и что
именно изменилось — в разделе «Обновление» сразу под этим абзацем.

## Обновление — исправлен баг покрытия `itemskillsgdx1/2/3` (найдено кросс-валидацией 92)

**Диагноз (не мой, см. `REPORTS/92_crossval.md`, находка №1)**: скрипт сканировал только
`records/skills/itemskills/` (789 записей) и 10 мастерских деревьев. Расширенческие
неймспейсы `itemskillsgdx1/2/3` (легендарные проки Ashes of Malmouth / Forgotten Gods)
не сканировались вообще. Следствие: 555 из 21154 проверенных ссылок «предмет → скилл»
(`items.jsonl.itemSkill`) не резолвились в `skills_flat.jsonl` — 316 реальных именованных
проков легендарок дополнений («Flame Patch», «Executioner's Edge», «Blood Spout» и т.п.)
были не видны инструментам билд-планирования.

### Что сделано

1. **Домен расширен по данным, а не по хардкод-списку.** Запрос
   `WHERE name LIKE 'records/skills/itemskills%' AND type LIKE 'Skill%'` одним SQL-паттерном
   покрывает `itemskills/` + ЛЮБУЮ ветку `itemskillsgdx<N>/` (нашёл 1,2,3 по факту в БД, но
   код не завязан на конкретные номера — будущий `itemskillsgdx4` подхватится сам).
2. **Осознанно исключены подпапки, имя которых оканчивается на `modifiers`** —
   `itemskillsgdx1/skillmodifiers/` (1007), `itemskillsgdx2/skillmodifiers/` (570),
   `itemskillsgdx3/skillmodifiers/` (1833), `itemskillsgdx3/potionmodifiers/` (66) —
   итого **3476 записей исключено**. Это не гранты активного скилла игроку, а записи вида
   «модификатор X ДЛЯ УЖЕ существующего мастерского скилла/MI/зелья»
   (`Skill_Modifier`/`Skill_PotionModifier`), резолвятся отдельной парой полей
   `items.jsonl.skill_modifiers[].modifies/.modifier` (это уже работало на 100% и раньше,
   см. `92_crossval.md` находка №1: "0 misses от skill_modifiers[].modifies"). **Проверено
   по данным, не предположение**: ни одна ссылка `items.jsonl.itemSkill` не указывает в
   `*modifiers/`-подпапку — исключение не портит приёмочный критерий. Решение продолжает
   пункт 4 старого раздела «не уверен» (см. ниже) — тот текст уже сомневался в этой же
   границе, теперь граница подтверждена по данным и явно закодирована с объяснением, а не
   оставлена молча.
3. **Страховка для 1 случая вне `itemskills*`.** Один предмет (`b200_focus.dbr`,
   "Malformed Effigy") даёт не легендарный item-скилл, а прямой боевой скилл босса
   `records/skills/nonplayerskillsgdx2/bossskills/final/p1_gazeofkorvaak.dbr` ("Gaze of
   Korvaak"). Полный неймспейс `nonplayerskills(gdx1/2/3)/` (~4500 записей боевых
   скриптов монстров) НЕ тащится целиком — не относится к билд-инструментам, это
   AI-логика монстров. Но скрипт читает `items.jsonl` (если файл существует) и для КАЖДОЙ
   ссылки `itemSkill.skill`, которая не легла ни в основной item-домен, ни в мастерские
   деревья, резолвит эту конкретную запись из БД и добавляет с пометкой
   `extra_domain_note`. Это тоже не хардкод пути — граница снова определяется данными
   (реальной ссылкой предмета), а не перечислением. Если `items.jsonl` ещё не существует
   на момент запуска (порядок заданий поменяли), страховка просто пропускается с
   предупреждением в консоли — скрипт не падает и не требует `items.jsonl` как обязательную
   зависимость.
4. **Починен реальный баг резолва** (не просто «безымянные узлы», а именно дыра, см. ниже
   раздел про 161 пустое имя): 5 строк `skills_flat.jsonl` для модификаторов, зависящих
   (`skillDependancy`) сразу от НЕСКОЛЬКИХ базовых скиллов (например
   `playerclass02/passive2.dbr` = "Ulzuin's Chosen", общий для Stun Jacks/Grenado/Canister
   Bomb), попадали в плоский список для 2-го/3-го родителя как lightweight-заглушка
   `{"record":..,"shared_with":..,"note":..}` — БЕЗ `name`/`type`/`role`. Теперь такая
   строка разворачивается в полное тело (те же поля, что у основной записи под первым
   родителем) плюс новое поле `shared_with` = путь на основного родителя, где лежит
   "каноническая" версия узла. Затронуло: `playerclass02/passive2.dbr` (x2),
   `playerclass04/wpattack4.dbr` (x2), `playerclass10/passive04.dbr` (x1).
5. **Разобрался с 161 пустым `name` в старой версии `skills_flat.jsonl`.** Разбивка:
   - **156** — настоящие безымянные служебные узлы: ни `skillDisplayName`, ни
     `FileDescription` не заданы в самом `.dbr` (скрытые petmod-компоненты вида
     `mortartrap2_petmod.dbr`, вторичные бафф-триггеры типа `fieldcommand1.dbr` и т.п.).
     Тегу неоткуда взяться — это не дыра резолва. Теперь такие узлы (и все им подобные во
     всём выходе, не только эти 156) помечены `"unnamed": true` в `finalize()`, чтобы
     потребитель данных явно видел «имени нет по дизайну», а не терялся в догадках,
     баг это или нет.
   - **5** — реальный баг (заглушки `shared_with`, см. пункт 4 выше). Это единственная
     часть из 161, которая была настоящей дырой резолва, а не просто "безымянный узел" —
     не тэг не резолвился, а сам flat-row был структурно неполным.
   После фикса и расширения домена (в новый, гораздо больший состав узлов) в актуальном
   `skills_flat.jsonl` — **262** строки с `unnamed=true` (рост ожидаем: домен вырос с 1135
   до 1721 строк, в основном за счёт item-скиллов gdx1/2/3, среди которых тоже есть скрытые
   безымянные компоненты) и **0** строк с пустым `name` без флага `unnamed` (проверено
   программно по всему файлу).

### Приёмочная проверка (программно, воспроизводит методику `92_crossval.py`)

```
items.jsonl.itemSkill (1861 ссылка)            -> резолвится 1861/1861 (было 1861-555=1306)
items.jsonl.itemSkill+augments+skill_modifiers.modifies (21154 ссылки, метод 92_crossval) -> 21154/21154, 0 промахов (было 555 промахов)
affixes.jsonl.proc.skill (496 ссылок)          -> 494/496 -- НЕ ИЗМЕНИЛОСЬ (2 мёртвые legacy-ссылки
                                                   в данных игры, не наша дыра, см. 92_crossval.md находка №2)
```
Оба числа перепроверены прогоном отдельного скрипта поверх свежих `skills_flat.jsonl` +
`items.jsonl` + `affixes.jsonl` (та же логика, что в `92_crossval.py`), а не только
внутренней самопроверкой `20_skills.py` (которая тоже встроена в скрипт и печатается при
каждом запуске — `meta.acceptance_check_item_skill_grants_resolve` в `skills.json`).

### Новые/изменённые числа

| Метрика | Было | Стало |
|---|---|---|
| `item_skills` (source=item) | 789 | **1375** (789 itemskills/ + 224 gdx1 + 187 gdx2 + 174 gdx3 + 1 nonplayerskillsgdx2) |
| Плоских строк `skills_flat.jsonl` | 1135 | **1721** |
| Нерезолвленных `items.jsonl.itemSkill` | 555 | **0** |
| Пустых `name` без объяснения | 161 (не различалось, баг/не баг) | **0** (262 честно помечены `unnamed=true`, разбивка причины в meta) |
| Исключено как `*modifiers` (задокументировано, не молча) | не проверялось | 3476 записей |

### Новые поля в схеме (аддитивно, ничего не переименовано)

| Поле | Где | Смысл |
|---|---|---|
| `item_namespace` | узлы `source=item` | 3-й сегмент пути: `itemskills`/`itemskillsgdx1`/`itemskillsgdx2`/`itemskillsgdx3`/`nonplayerskillsgdx2` |
| `extra_domain_note` | только у страховочных узлов вне `itemskills*` | почему узел вообще попал в выход, если он не из основного домена |
| `unnamed` | любой узел дерева без `name`/`name_tag` | `true`, если узел осознанно безымянный в самих данных игры (см. раздел выше); отсутствует (не `false`), если у узла есть имя |
| `shared_with` | flat-строка модификатора/трансмутера с >1 родителем (кроме первого) | путь на родителя, под которым лежит канонический/первый экземпляр узла — раньше на этом месте была почти пустая заглушка (баг, исправлен) |
| `meta.item_skills_by_namespace`, `meta.item_skills_excluded_modifier_folders`, `meta.item_skills_extra_domain_added/still_missing`, `meta.acceptance_check_item_skill_grants_resolve`, `meta.flat_rows_unnamed`, `meta.flat_rows_shared_modifier_fixed_stubs` | `skills.json.meta` | новые счётчики для прозрачности исправления, см. сам файл |

`source` по-прежнему принимает только 2 значения — `"mastery"` (узел мастерского дерева,
включая доп. родителей через `shared_with`) и `"item"` (скилл, реально гранту­емый
предметом, независимо от того, в каком неймспейсе БД он физически лежит — `itemskills/`,
`itemskillsgdx{1,2,3}/` или страховочный внедоменный случай). Третьего значения не
понадобилось: все узлы, дошедшие до выхода, однозначно относятся к одной из двух
категорий по построению (либо лежат в мастерском дереве, либо являются item-скиллом).

### Что осталось неопределённым/не проверялось (честно, продолжение раздела ниже)

- **Домен `itemskills/test/`** (6 записей, только базовая игра — `flamestrike1.dbr`,
  `test_npcdialogue.dbr` и т.п., явно dev-заглушки) остался включён в `item_skills`
  (как и до фикса — это не часть бага, который чинили). Ни одна из 6 не референсится
  ни из одного JSONL пайплайна — вероятно, чистый мусор, но трогать пре-существующий
  (уже провалидированный в DoD прошлого прогона) домен `itemskills/` вне рамок этой
  задачи не стал.
- **`itemskillsgdx2/runes/`** (54 записи — активные скиллы рун типа "Leap"/"Teleport"/
  "Disengage", есть настоящие `skillDisplayName`-теги) включены в домен, хотя ни одна
  не референсится из `items.jsonl.itemSkill` напрямую (вероятно, гранту­ются через
  механику сокет-рун, не покрытую полем `itemSkill` в задании 10). Решил оставить —
  это явно настоящие player-facing скиллы, а не служебный мусор, судя по тегам/типам.
  Не проверял, как именно игрок их получает (не było в рамках задачи).
- Не проверял вручную все 316 новых легендарных item-скиллов на честность имён — сверил
  выборочно 4 (Executioner's Edge, Flame Patch x3 варианта, Blood Spout) + страховочный
  Gaze of Korvaak, все резолвятся корректно.

## Сверка со схемой полей (`field_schema.json`, прислана координатором после начала работы)

Координатор распаковал `database/templates.arc` в `data/grim-dawn/field_schema.json`
(18968 полей: `type`/`class`/`description`/`groups`/`templates`) уже ПОСЛЕ того, как скрипт
был написан и прогнан по данным. Я не переписывал скрипт под неё, а сверил ей уже сделанные
выводы — все подтвердились, ничего не пришлось откатывать:

- **`skillMasteryLevelRequired`** — схема прямо говорит `description: "Mastery level to add
  first point"` — это ТОЧНО то поле, о котором просит бриф («уровень мастерства для
  разблокировки»). Пересчитал по всем 782 `Skill*`-записям в `records/skills/playerclass*`:
  **645 имеют значение `0`, 137 не имеют поля вовсе, ни одной ненулевой записи.** Значит поле
  семантически верное, но реально не заполнено ни у одного скилла ни одной мастерской в
  релизной игре — вывод №1 из раздела «не уверен» ниже подтверждён схемой, а не только
  выборочной проверкой.
- **`skillDependancy`** — схема: `type: file_dbr, class: array, template: skill_base` — общее
  поле, доступное любому скиллу, ровно с той семантикой («от каких скиллов зависит»), которую
  я вывел эмпирически по playerclass04/playerclass10. Подтверждено.
- **Массивы по уровням** (`weaponDamagePct`, `skillManaCost`, `skillCooldownTime`,
  `offensive<Type><Min|Max|Modifier>`, `characterStrength/Dexterity/...` и т.п.) — в схеме
  помечены `"class": ["array"]`. Парсер `gdlib.ARZ.record()` уже разворачивает multi-value
  поля .arz в python-списки на уровне чтения байт (независимо от схемы), поэтому все такие
  поля и так сохранены в выходе ЦЕЛИКОМ (в `extra` или в промотированных ключах) — требование
  брифа «сохрани массивы целиком» выполнено без дополнительного кода, схема это подтвердила
  постфактум.

## Как устроено дерево (обнаружено, не выдумано — см. ниже пруфы)

```
records/skills/playerclassNN/_classtraining_classNN.dbr   тип Skill_Mastery  -- сама мастерская
records/skills/playerclassNN/_classtree_classNN.dbr       тип SkillTree     -- порядок дерева:
    поля skillName1..skillNameK (K до 46) перечисляют .dbr узлов панели по порядку.
    skillName1 == сама _classtraining (проверено на всех 10 классах).
```

**Важная находка**: один и тот же путь может встречаться в `skillNameK` НЕСКОЛЬКО РАЗ
(визуальный артефакт панели навыков — иконка модификатора/трансмутера отражается в
нескольких ячейках грида для отрисовки соединительных линий). Пример: у Wereraven
(playerclass10) `wereraven1b.dbr` встречается на позициях 14, 18 и 21. Дедуплицировано
по первому вхождению. Классы с дублями: `playerclass02` (2), `playerclass04` (2),
`playerclass07` (1), `playerclass10` (3).

**Родитель модификатора/трансмутера/секретного эффекта** восстанавливается двумя способами:

1. **Явное поле `skillDependancy`** (да, с опечаткой прямо в игре) — строка или список путей,
   от которых узел явно зависит. Есть примерно у 13 игровых узлов из ~800 (в основном
   weapon-pool цепочка Nightblade и shapeshift-цепочки Berserker). Используется как
   АВТОРИТЕТНЫЙ источник, когда есть. Живой пример: `playerclass10/passive04.dbr`
   («Form of the Beast») имеет `skillDependancy: [wereraven1.dbr, werewolf1.dbr]` —
   это единый модификатор для ОБЕИХ форм оборотня. В выходе он лежит полным телом под
   Wereraven и лёгкой ссылкой `{"record":..., "shared_with":..., "note":...}` под Werewolf
   (чтобы не дублировать контент).
2. **Позиционная эвристика** (когда `skillDependancy` нет — это большинство): модификатор/
   трансмутер/secondary вешается на ближайший предыдущий узел с ролью
   active/passive/toggle/shapeshift/summon в дедуплицированном списке дерева. Проверено на
   Cadence, Blade Arc, Shield Hammer, War Cry, Onslaught (Berserker) — везде совпадает с
   известной игровой логикой. **Важно**: до того как я нашёл поле `skillDependancy`, чисто
   позиционная эвристика ошибочно вешала модификатор `wereraven2.dbr` («Glacial Talons») на
   гранту-подскилл «Ice Talons» вместо самого Wereraven — явное поле это исправило. Это
   прямое доказательство, что позиционная эвристика **не 100% надёжна** и её стоит
   перепроверять там, где есть `skillDependancy`.

**Скрытый buff-компонент** резолвится через явное поле `buffSkillName` на
`SkillSecondary_*` узле → `SkillBuff_*` запись. Пример: `cadence3.dbr` (без имени/иконки,
не отображается в UI как отдельный узел) → `buffSkillName` → `cadence3_buff.dbr`
(«Deadly Momentum», реальный видимый эффект). Такие компоненты НЕ входят в список дерева
отдельной строкой.

## Роль узла (`role`) — по Class-полю .dbr

| .dbr тип (префикс) | role | Смысл |
|---|---|---|
| `Skill_Mastery` | (обрабатывается отдельно, не в `role`) | сама мастерская |
| `Skill_Transmuter`, `Skill_ProjectileTransmuter`, `Skill_SpawnPetTransmuter` | `transmuter` | превращает урон/механику базового скилла |
| `Skill_Modifier`, `Skill_ProjectileModifier`, `Skill_RefreshCooldown`, `Skill_GiveBonus` | `modifier` | доп. очки в базовый скилл, апгрейд эффекта |
| `SkillSecondary_*` | `secondary` | скрытый авто-эффект (часто без имени/иконки) |
| `SkillBuff_*`, `SkillActivated_Suicide` | `buff` | сам эффект-баф/дебаф, обычно цель `buffSkillName` |
| что-то с `Passive` в имени | `passive` | пассивный скилл/пассивная часть |
| что-то с `Toggled` в имени | `toggle` | стойка/тумблер-аура |
| `Skill_Shapeshift` | `shapeshift` | трансформация (Wereraven/Werewolf) |
| `Skill_SpawnPet`, `Skill_TargetedSpawnPet`, `Skill_SpawnMiniPet` | `summon` | призыв петомца |
| остальное (`Skill_Attack*`, `Skill_WPAttack_*`, `Skill_WeaponPool_*`, `Skill_BuffSelfDuration` и т.п.) | `active` | активный скилл с кастом |

Счётчик по факту (все построенные узлы, включая item-скиллы):
`active: 649, buff: 119, modifier: 98, passive: 75, toggle: 69, summon: 41,
transmuter: 39, secondary: 38, shapeshift: 2`.

## Схема выхода `skills.json`

```
{
  "meta": {
    masteries: 10, skills_top_level: 152, item_skills: 789, flat_rows: 1135,
    role_counts: {...},
    note_tree_duplicates / note_mastery_unlock_level / note_modifier_parent  -- текстовые
        пояснения находок (см. выше), продублированы в самом файле для тех, кто не читает отчёт
  },
  "masteries": [
    {
      record, number (1..10), name, name_tag, description, description_tag,
      src,                          # base|gdx1|gdx2|gdx3 -- кто выиграл при слиянии
      max_mastery_level,            # из skillMaxLevel мастерской записи (у всех 10 == 50)
      attribute_scaling_per_level: {strength, dexterity, intelligence, life, mana},
                                    # массивы по 100 значений (уровень мастерской 1..100),
                                    # из characterStrength/Dexterity/Intelligence/Life/Mana
      skills: [ <skill node>, ... ]  # только "первичные" узлы дерева, без модификаторов сверху
    }, ...
  ],
  "item_skills": [ <skill node с source="item", item_category>, ... ]
}
```

### Схема одного узла скилла (поле → откуда взято)

| Поле выхода | .dbr поле | Комментарий |
|---|---|---|
| `record` | путь записи | нормализованный (lowercase, /) |
| `name` / `name_tag` | тэг `skillDisplayName` | резолвится через tags_en.json |
| `description` / `description_tag` | тэг `skillBaseDescription` | — |
| `type` | Class-поле .dbr | сырой тип, см. таблицу ролей |
| `role` | вычислено из `type` | см. таблицу выше |
| `source` | вычислено | `"mastery"` (из дерева мастерской) или `"item"` |
| `tier` | `skillTier` | позиция в панели (1..9), НЕ уровень персонажа/мастерской |
| `max_level` | `skillMaxLevel` | обычно 12/16 (актив), иногда меньше у модификаторов |
| `ultimate_level` | `skillUltimateLevel` | ультимативный кэп (обычно 22/26) |
| `mana_cost` | `skillManaCost` | массив по уровням, если есть |
| `cooldown` | `skillCooldownTime` | — |
| `duration` | `skillActiveDuration` | — |
| `instant_cast` | `instantCast` | bool |
| `weapon_damage_pct` | `weaponDamagePct` | массив по уровням (в брифе назван `skillWeaponDamage` — реальное имя поля другое) |
| `modifiers[]` | — | подвешенные `Skill_Modifier`-узлы (см. правила родителя выше) |
| `transmuters[]` | — | подвешенные `Skill_Transmuter`-узлы |
| `secondary_effects[]` | — | подвешенные `SkillSecondary_*`/`SkillBuff_*`, с вложенным `buff_component` |
| `buff_component` | `buffSkillName` | скрытый узел-баф, резолвленный отдельно |
| `extra{}` | все прочие ненулевые поля .dbr | см. таблицу частых полей ниже — **не интерпретировано**, оставлено как есть по правилу «не выдумывай семантику» |
| `item_category` | 4-й сегмент пути (только у item-скиллов) | `legendary`/`relics`/`consumableskills`/`componentskills`/`granted`/`(root)`/... |
| `item_namespace` **(добавлено фиксом)** | 3-й сегмент пути (только у item-скиллов) | `itemskills`/`itemskillsgdx1`/`itemskillsgdx2`/`itemskillsgdx3`/`nonplayerskillsgdx2` |
| `unnamed` **(добавлено фиксом)** | вычислено | `true`, если ни `name`, ни `name_tag` не заданы в `.dbr` (осознанно безымянный служебный узел, не дыра резолва) |
| `shared_with` **(добавлено фиксом)** | вычислено | только у flat-строки модификатора/трансмутера с >1 родителем через `skillDependancy`: путь на родителя, где лежит канонический/первый экземпляр |
| `extra_domain_note` **(добавлено фиксом)** | вычислено | только у страховочных item-скиллов вне `itemskills*`-неймспейсов: почему узел попал в выход |

## Таблица самых частых полей в `extra` (для остальных заданий)

Топ-25 по частоте среди всех построенных узлов (mastery + item). Колонка `class` — из
`field_schema.json` (пришла от координатора после написания скрипта, использована для
пост-проверки, а не для генерации кода):

| Поле | N | class (схема) | Смысл |
|---|---|---|---|
| `distanceProfile` | 607 | picklist | категория дистанции атаки: Melee/Short/Moderate/Long/Maximum/Boss |
| `characterBaseAttackSpeedTag` | 570 | variable | тег скорости анимации (для отображения, не число) |
| `skillTargetRadius` | 221 | array | радиус действия/поражения ("Radius and Projectiles") |
| `skillProjectileName` | 157 | array,variable | ссылка на .dbr снаряда |
| `targetingMode` | 156 | picklist | режим наведения: Default/Point/Object/Target |
| `projectileExplosionRadius` | 143 | array | радиус взрыва снаряда |
| `offensiveFireMin` / `offensivePhysicalMin` / `offensiveColdMin` / ... | 90-115 | array | минимум урона соотв. типа за уровень |
| `ragDollPush` | 92 | picklist | сила отбрасывания при попадании |
| `expansionTime` | 91 | variable (сек.) | время расширения радиусной атаки |
| `radiusEffectName` | 90 | array | ссылка на визуальный радиус-эффект (FxPak) |
| `skillProjectileNumber` | 80 | array,variable | число выпускаемых снарядов |
| `debufSkill` | 73 | static,variable | флаг «это дебафф» |
| `offensiveSlowFireDurationMin` / `offensiveSlowBleedingMin` и т.п. | 60-65 | array (сек. для Duration) | DOT-урон/длительность (ожог/кровотечение) за уровень |
| `characterManaLimitReserve` | 63 | array | резерв маны, занимаемый тумблом |
| `projectilePiercingChance` | 59 | array | шанс пробития снарядом |

**Промежуточные `offensive<Type><Min|Max|Modifier>` и `defensive*`/`retaliation*` поля**
(десятки вариантов урона/сопротивлений/лайфлича) намеренно НЕ переименованы в
`damage`/`resist` и т.п. — это прямая цитата схемы `.tpl` шаблонов игры, семантика
Min/Max/Modifier (аддитивный %) стандартна для всей игры и уже подтверждена в отчёте по
девоушенам (`REPORTS/21_devotions.md`), переизобретать не стал. Схема (`field_schema.json`)
у всех них показывает `class: array` — подтверждает, что это массивы по уровню скилла и
`gdlib` уже сохраняет их целиком без дополнительной работы.

## Счётчики (актуальные, после исправления бага покрытия — см. «Обновление»)

- Масте­рских: **10** (все 10, включая Berserker из GDX3).
- Уникальных скиллов верхнего уровня (без модификаторов/трансмутеров/секретных эффектов): **152**.
- Скиллов от предметов (`source: "item"`, из `records/skills/itemskills*/*`, только
  `Skill*`-типы, без petbonus/Pet-заглушек, без `*modifiers/`-подпапок): **1375**
  (789 `itemskills/` + 224 `itemskillsgdx1/` + 187 `itemskillsgdx2/` + 174 `itemskillsgdx3/`
  + 1 страховочный `nonplayerskillsgdx2/` — было **789** до фикса).
- Плоских строк в `skills_flat.jsonl`: **1721** (было **1135** до фикса) — мастерские
  скиллы + все вложенные модификаторы/трансмутеры/secondary/buff + item-скиллы.
- Скиллов по мастерским (top-level, для проверки на глаз, не изменилось фиксом):
  Soldier 19, Demolitionist 11, Occultist 11, Nightblade 17, Arcanist 16, Shaman 15,
  Inquisitor 15, Necromancer 15, Oathkeeper 14, Berserker 19.
- Пропущено/не резолвилось: **0** узлов дерева (все 10 деревьев полностью резолвятся
  в БД без дыр).
- **Приёмочный критерий фикса**: `items.jsonl.itemSkill` — 1861/1861 резолвится (было
  1306/1861, 555 промахов). Расширенная проверка методом `92_crossval.py`
  (itemSkill+augments+skill_modifiers.modifies, 21154 ссылки) — 21154/21154 (было
  20599/21154).

## Что не удалось / в чём не уверен (обязательный раздел)

1. **Уровень мастерства для разблокировки скилла НЕ найден в статических `.dbr`,
   хотя правильное поле для этого существует.**
   Бриф просил `maxLevel`/`ultimateLevel` — они есть (`skillMaxLevel`/`skillUltimateLevel`,
   промотированы в выход). Но «на каком уровне мастерства открывается точка» — нет, и это
   подтверждено ДВАЖДЫ:
   - Поле-кандидат `skillLevelN` в `_classtree_classNN.dbr` присутствует у всех 10 классов,
     но **везде равно 0** (проверено на всех 10 деревьях полностью, не выборочно).
   - После того как координатор прислал `field_schema.json`, нашёлся точно тот самый по
     смыслу field — **`skillMasteryLevelRequired`**, схема прямым текстом описывает его как
     `"Mastery level to add first point"`. Пересчитал по всем 782 `Skill*`-записям
     `playerclass*`: **0 ненулевых значений** (645 записей = 0, 137 без поля).
   Вывод: поле для этого в игре ЕСТЬ по дизайну шаблона, но разработчики никогда не
   заполнили его в релизнутых данных — вероятно, разблокировка тира считается движком по
   номеру колонки в панели (`skillTier`) через хардкод в UI/клиенте, а не через БД. Я не
   выдумываю эту формулу и не подставляю её в выход. В выходе сохранён только `tier`
   (сырое `skillTier`, позиция в панели 1..9) без привязки к уровню мастерской.

2. **Связь модификатор/трансмутер → базовый скилл в основном (>95% узлов) — эвристика,
   не факт из `.dbr`.** Явное поле `skillDependancy` есть только у ~13 узлов из ~800. Для
   всех остальных родитель восстановлен по смежности в дереве (см. выше). Я перепроверил
   эвристику на всех местах, где нашёлся `skillDependancy`, и в одном случае
   (`playerclass10/wereraven2.dbr`) она **изначально ошиблась** — это единственное
   расхождение, которое удалось поймать и исправить фактическими данными; для остальных
   ~700+ модификаторов у меня нет способа проверить эвристику иначе, чем сверкой с
   игровым UI вручную (не делал построково для всех, сверил только Soldier и Berserker
   целиком, см. спот-чек).

3. **Расхождение со спот-чеком из брифа.** В задании написано: «Cadence... модификаторы
   Fighting Spirit и Deadly Momentum». По факту в данных:
   - `cadence2.dbr` (Skill_Modifier) = **«Fighting Form»**, не «Fighting Spirit».
   - «Fighting Spirit» (`fightingspirit1.dbr`, тип `Skill_PassiveOnHitBuffSelf`) —
     ПОЛНОСТЬЮ ОТДЕЛЬНЫЙ пассивный скилл Soldier, никак не связанный с Cadence
     (ни по `skillDependancy`, ни по смежности в дереве — между ними в списке дерева
     несколько других скиллов).
   - «Deadly Momentum» (`cadence3_buff.dbr`) — это НЕ инвестируемый модификатор, а
     скрытый `buff_component` секретного эффекта `cadence3.dbr` (сам 3-й-удар-бонус
     Cadence, встроен, отдельных очков не требует).
   Я привожу дерево так, как оно лежит в данных, а не подгоняю под формулировку брифа —
   см. рекомендацию рулбука не выдумывать семантику. Возможно, автор задания имел в виду
   игровой термин по памяти неточно; фактическая структура показана в примере ниже.

4. **[ИСПРАВЛЕНО, см. раздел «Обновление» вверху отчёта] Границы `source: "item"`** —
   изначально включил только `records/skills/itemskills/**` (789 записей типа `Skill*`),
   не подхватив `itemskillsgdx{1,2,3}/**` вовсе — это оказалось реальным багом покрытия
   (найден кросс-валидацией, задание 92: 555 нерезолвленных ссылок `items.jsonl.itemSkill`).
   Домен расширен на все `itemskills*`-неймспейсы; граница со `skillmodifiers/**`
   (proc-модификаторы для существующих мастерских скиллов — например
   `.../necklace_d111_cadence_deadlymomentum.dbr`) подтверждена как правильная и раньше
   интуиция была верна: эти записи по-прежнему НЕ входят в `item_skills` (это домен
   заданий 10/11), но теперь это явное, проверенное по данным решение (0 ссылок
   `itemSkill` ведут в `skillmodifiers/`), а не непроверенная догадка.

5. **[Число выросло до 1375 после фикса покрытия, суть пункта не изменилась] Item-скиллы
   не имеют собственной иерархии** (в отличие от мастерских скиллов):
   не резолвил их `modifiers`/`buffSkillName`/`petBonusName` и т.п. цепочки — только
   плоский список с `extra`. Если для заданий по предметам нужна их внутренняя структура —
   не переиспользуйте этот файл вслепую, там она не построена.

6. **Дубли в `_classtree`** (4 класса) я трактовал как визуальный артефакт панели и
   дедуплицировал по первому вхождению. Не проверял на 100% что это никогда не значит
   «два РАЗНЫХ визуальных представления одного скилла с разными данными» — по всем
   найденным случаям тела записей идентичны (это один и тот же путь), так что дедуп
   не теряет данные, только порядок обхода.

7. **`extra{}` — сырые поля без интерпретации.** Сотни `offensive*/defensive*/retaliation*`
   полей оставлены как есть (см. правило «не выдумывай семантику»). Таблица топ-25 в
   отчёте — ориентир, не полный словарь; для точной семантики каждого поля надо смотреть
   `database/templates/*.tpl` (не парсились в этом задании).

## Живые примеры

### 1. Cadence (Soldier, playerclass01) — как просил спот-чек брифа

```json
{
  "record": "records/skills/playerclass01/cadence1.dbr",
  "name": "Cadence", "role": "active", "tier": 1, "max_level": 16, "ultimate_level": 26,
  "weapon_damage_pct": [130, 150, ... , 550]  // 26 значений, по уровням
  "modifiers": [
    {"record": ".../cadence2.dbr", "name": "Fighting Form", "role": "modifier", "tier": 4}
  ],
  "transmuters": [
    {"record": ".../cadence1b.dbr", "name": "Discord", "role": "transmuter", "tier": 2,
     "extra": {"conversionInType": "Physical", "conversionOutType": "Elemental",
               "conversionPercentage": [33, 66, 100]}}
  ],
  "secondary_effects": [
    {"record": ".../cadence3.dbr", "name": null, "role": "secondary",
     "buff_component": {"record": ".../cadence3_buff.dbr", "name": "Deadly Momentum",
                         "role": "buff", "duration": 5.0,
                         "extra": {"offensivePhysicalMin": [12, 19, ...]}}}
  ]
}
```
См. расхождение с брифом (модификатор — «Fighting Form», не «Fighting Spirit») в разделе
«не уверен» выше.

### 2. Berserker (playerclass10, GDX3) — второй спот-чек: подтверждение подхвата gdx3

`mastery.src == "gdx3"` — подтверждено программно и вручную (см. счётчики). Дерево:
19 top-level скиллов, включая shapeshift-цепочки:

```
Wereraven (shapeshift)
  modifiers: Everwinter, Form of the Beast (shared c Werewolf через skillDependancy), Glacial Talons
  transmuters: Talons of Ch'thon
Ice Talons (active, гранта Wereraven)
  modifiers: (пусто — Glacial Talons корректно ушёл к Wereraven, не сюда)
Werewolf (shapeshift)
  modifiers: [ref -> Form of the Beast @ Wereraven], Recklessness, Voracity
  transmuters: Blight of Ch'thon
```

### 3. Item-скилл: Spark of Ultos (relic/legendary proc)

```json
{
  "record": "records/skills/itemskills/legendary/item_sparkofultos.dbr",
  "name": "Spark of Ultos", "type": "Skill_BuffSelfToggled", "role": "toggle",
  "source": "item", "item_category": "legendary", "max_level": 2, "instant_cast": true,
  "extra": {"offensiveLightningModifier": [55, 120], "retaliationLightningMax": [487, 750],
            "petBonusName": ".../item_sparkofultos_petbonus.dbr"}
}
```

## Спот-чек (Definition of Done)

- **Cadence**: воспроизведено дерево из `skills.json` (пример 1 выше). Активный скилл,
  усиливает каждый 3-й удар (подтверждено текстом описания из тэга), 1 модификатор
  (Fighting Form, не Fighting Spirit — расхождение задокументировано), 1 трансмутер
  (Discord = `cadence1b.dbr`, путь совпадает с брифом), скрытый бонусный баф Deadly
  Momentum через `cadence3`/`cadence3_buff`.
- **Berserker (playerclass10)**: `src == "gdx3"` подтверждён программно
  (`con.execute("SELECT src FROM records WHERE name=...")`) — Fangs of Asterkarn
  подхвачен. 19 top-level скиллов, имена (Onslaught, Rallying Cry, Bonechilling Cry,
  Wereraven/Werewolf, Leap, Winds of Asterkarn, Bloodborne, Heart of Asterkarn) совпадают
  с реальной мастерской Berserker в игре.
