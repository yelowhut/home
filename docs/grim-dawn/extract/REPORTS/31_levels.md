# Отчёт 31 — СПАЙК: география мира (где кого искать)

Скрипт: `docs/grim-dawn/extract/31_levels.py`
Выход: `data/grim-dawn/regions.json` (17 071 206 байт, ~16.3 MB)

Статус: **успешная разведка через БД, дважды** — сначала через Proxy/
DungeonEntrance (п.3 задания), затем координатор подкинул дамп
`database/templates.arc` (`field_schema.json`/`template_types.json`), который
вывел на **гораздо более авторитетный источник**: UI-таблицу мировой карты
`records/ui/riftgatemap/riftgate_mastertable.dbr` с готовым списком локаций,
человеческими именами и даже 2D-координатами подписей на карте (см. раздел
"Мировая карта (world_map)" ниже — это главное обновление отчёта).
Бинарный формат `.map` (п.4) частично вскрыт (заголовок + первая структурная
секция), но НЕ дореверсен до конца — см. отдельный раздел ниже.

**Уточнение по координатам**: 3D-координат игрока/объектов в мире (то, что
лежит в нереверсенном `world001.map`) как не было, так и нет — это осталось
под явным запретом задания. Но `world_map.shrines[].position` и
`world_map.map_labels[].position` — это **реальные 2D пиксельные координаты**
подписей/иконок на текстуре UI-карты мира, взятые из полей `WindowLocationX/Y`
и `labelX/YN` записи `riftgate_mastertable.dbr` (не придуманы, не 3D, но и не
ничего — честно указываю обе стороны).

## Порядок действий (как в задании, от дешёвого к дорогому)

### 1. `Grim Dawn Modding Guide.pdf`

Сконвертировал в текст (`pdftotext`, poppler из Git for Windows — штатный
`Read` не смог из-за отсутствия `pdftoppm`). Результат:
- **Формата `.map` в PDF нет вообще** — гайд описывает только работу в
  `Editor.exe` (Region → Add New Terrain, Build → Rebuild Selected Map), без
  единого слова про экспорт/дамп в текстовый или иной читаемый формат.
- Зато нашёл **точное текстовое описание семантики `Proxy`/`ProxyAmbush`/
  `Spawn Pool`** (раздел "Spawning Monsters"): `Chance to Run`, `Placement
  Extents`, `Faction Required/Standing`, `Difficulty At Least`, `Pool #`/
  `Weight #`, для Ambush — `Alert Area`, `Min/Max Spawn/Delay Time`, `Min/Max
  Group Size`, `Spawn Threshold`; для Spawn Pool — `Spawn Min/Max`, `Champion
  Min/Max/Chance`, `Proxy Pool Equation`. Это дословно совпало с полями
  `chanceToRun/placementExtents/alertArea/minGroupSize/maxGroupSize/
  spawnThreshold/spawnMin/spawnMax/championMin/championMax/championChance/
  proxyPoolEquation` в `.dbr`-записях — прямое подтверждение семантики без
  необходимости гадать (см. п.3 ниже).

### 2. CLI-утилиты игры

- `ArchiveTool.exe` без аргументов — печатает полный `Usage`, никакой команды
  экспорта карты в читаемый формат нет (`-add/-replace/-update/-remove/
  -extract/-database/-removeMissing/-compact/-list/-stats`).
- `MapCompiler.exe` без аргументов — только `"Not Enough Arguments"`, без
  подсказки по флагам. Просканировал бинарник на предмет строк `usage`/`.map`/
  `argument` — ничего, кроме самого сообщения об ошибке.
- `AssetManager.exe` без аргументов — открывает GUI (не CLI-инструмент для
  дампа), пришлось `taskkill` процесс.
- Вывод: документированного/CLI-way экспорта `.map` в читаемый вид **нет**.
  Переходим к п.3 (гарантированный результат).

### 3. `gd.sqlite`: Proxy / ProxyEndless / ProxyAmbush / DungeonEntrance (основной результат)

Ключевое разведочное открытие: **пути записей содержат закономерность
`area<буква>`**, которая надёжно коррелирует с источником данных (`src`):

| код в пути | что это | proxy-записей | src |
|---|---|---|---|
| `records/proxies/area001/*` | весь мир базовой игры (не разбит на буквы в путях proxy) | 306 | 100% `base` |
| `...areae/*` | зона gdx1 №1 | 90 | 100% `gdx1` |
| `...areaf/*` | зона gdx1 №2 | 53 | 100% `gdx1` |
| `...areag/*` | зона gdx2 | 162 | 100% `gdx2` |
| `...areah/*` | зона gdx3 | 146 | 100% `gdx3` |
| `...areavoid/*` | отдельный бонусный контент | 31 | 100% `gdx1` |

Проверено не на 1-2, а на всех записях каждой группы (см. таблицу — 100%
чистые по `src`), плюс независимо подтверждено через `quests/gdarea<b..h>/*.qst`
пути (буквы b/c/d встречаются только в base+доп. квесты аддонов, e/f впервые
в gdx1, g впервые в gdx2, h впервые в gdx3 — ни разу раньше своего аддона).

Для `DungeonEntrance` та же буква находится не в папке, а **подстрокой в имени
файла** (`ugdoor_areae_caveentcarraxus_doorglow.dbr`, `..._areah_beronathshortcutrift...`)
— применил ту же регулярку к полному пути, и она сработала одинаково для обоих
типов записей (проверено на 10+ примерах, включая скрипт-хуки `onAddToWorld`
вида `gd.quests.areaFQuestMalmouthFactory...`, `gd.quests.areaGSolaelFaction...`,
которые независимо подтверждают букву зоны).

`DungeonEntrance.description` — тэг с человекочитаемым названием входа. Для
многих записей (особенно gdx1-3) это **осмысленное имя локации**, не просто
тип двери: *Den of Carraxus, Freyoll Valley, Elderveil, Candle District,
Steelcap District, Map Room of Rahn, Mammoth Burial Grounds, Rift to Kurnhold,
Tomb of the Eldritch Sun Entrance* и т.д. (68 различных резолвленных описаний
на 363 входа). Часть — общие типы дверей без конкретики (`Cave Entrance` ×24,
`Escape the Threshold?` ×123 — это, судя по всему, дефолтная подпись для
generic riftgate/шорткат-дверей, а не название места).

`ProxyPool` (на что ссылается `poolN`/`poolEpicN`/`poolLegendaryN`) содержит
`nameK`/`nameChampionK` — путь к записи `Monster`, `weightK`/`weightChampionK`
— вес выпадения, `spawnMin/Max`, `championMin/Max/Chance` — числа спавна.
`Monster.description` — тэг с реальным именем монстра (для героев вместо
этого часто заполнено `FileDescription` прямым текстом, напр. `"Uglak"` — тэг
`tagTrollHeroH01` резолвится в `"Uglak, the Immortal"`, оба варианта дают
совпадающий результат — перепроверено).

### 3b. Мировая карта: `riftgate_mastertable.dbr` (найдено благодаря подсказке координатора)

Координатор распаковал `database/templates.arc` в `field_schema.json` (18968
описаний полей `.dbr`-шаблонов) и `template_types.json` (шаблон → список его
полей). Поиск по этим файлам ключевых слов `region`/`zone`/`location` дал:

- шаблон `zone.tpl` — поля `ZoneNameTag`, `TeleportNameTag`, `WindowLocationX/Y`;
- шаблон `ingameui/worldmapwindow.tpl` — поля `Region00NZoneList`,
  `Region00NShrineList` (списки ссылок), `labelTagN`/`labelXN`/`labelYN`.

Поиск записей с такими полями в `gd.sqlite` (`fields LIKE '%ZoneList%'` и
`%ZoneNameTag%`) нашёл ровно один экземпляр каждого шаблона:

- **`records/ui/riftgatemap/riftgate_mastertable.dbr`** (`worldmapwindow.tpl`) —
  единственная запись, у неё есть только `Region001*` (не 002+, то есть в игре
  всё сведено в одну общую таблицу, а не по региону на аддон).
  - `Region001ZoneList` — **73** пути вида
    `records/ui/riftgatemap/locations/riftgatemap1<буква>_<slug>.dbr` — это
    точки быстрого перемещения (риftгейты), см. PDF-гайд, раздел о Riftgates
    ("used to link all of the Riftgates in the world so they become a network
    for fast travel"). Каждая ссылается на запись-`zone.tpl` с полем
    `ZoneNameTag`/`TeleportNameTag` → тэг → **настоящее человекочитаемое имя
    локации** (`tagRiftDevilsCrossing` → *"Devil's Crossing"*,
    `tagGDX3WorldMapKurnhold`-подобные и т.д.).
  - `Region001ShrineList` — **62** пути к записям `shrineicon.tpl`
    (девоушен-святилища на карте); имя лежит **прямо в `FileDescription`**
    (не тэг), плюс пиксельные `WindowLocationX/Y` и флаги
    `ruinedShrine`/`corruptedShrine` (состояние святилища).
  - `labelTagN`/`labelXN`/`labelYN` (N = 0..117, **118** подписей) — все
    надписи, которые видно прямо на текстуре карты мира, с тэгом имени и
    пиксельной позицией. Покрывает вообще все аддоны (`tagWorldMap*`,
    `tagGDX1WorldMap*`, `tagGDX2WorldMap*`, `tagGDX3WorldMap*`).

**Буква "chapter"** в пути риftгейта (`riftgatemap1<буква>_...`) — **это не
то же самое**, что `region_code` из раздела 3 выше. Здесь буквы
`a, b, f, g, h, i, j, k` (нет c/d/e), там — `b, c, d, e, f, g, h` (нет a).
Проверил на всех 73 записях (см. таблицу разбивки в скрипте/выводе) — это два
параллельных внутренних индекса Crate (один — для UI карты быстрого
перемещения, другой — видимо, исторический индекс регионов кода/квестов),
которые не совпадают и не должны смешиваться. Сопоставил с уже найденными
DungeonEntrance-именами лишь как независимую перекрёстную проверку (не как
формальное отображение одно-в-одно):
- риftгейт `chapter=k`, slug `kurnhold` → имя **"Kurnhold Rift"**;
  ранее (раздел 3) в `region_code=area_h` (gdx3) среди DungeonEntrance был
  вход с именем **"Rift to Kurnhold"** — независимое совпадение имени между
  двумя разными таблицами БД, без подгонки, укрепляет доверие к обеим.
- аналогично `chapter=k`, slug `verdantvalley` → **"Freyoll Valley Rift"**,
  и в разделе 3 у `area_h` уже был `DungeonEntrance` с именем **"Freyoll
  Valley"** — снова независимое совпадение.

**Привязка риftгейтов к конкретным Proxy/DungeonEntrance (спавнерам) —
best-effort, низкий recall.** Пробовал точное вхождение `slug` риftгейта
(например `kurnhold`, `devilscrossing`) как подстроки в путь ЛЮБОГО
`Proxy`/`ProxyEndless`/`ProxyAmbush`/`DungeonEntrance` (без ограничения на
`region_code`) — совпало только **21 из 73** (29%). Например, `kurnhold` не
совпал ни с одним путём напрямую (входы для этой локации названы иначе —
`beronathshortcutrift.dbr`, без слова "kurnhold" в самом файле, только в
тэге-описании), а `devilscrossing` совпал сразу с 4 путями
(`proxy_devilscrossingattack_outlaw_n.dbr` и т.д.) — то есть само совпадение
зависит от того, называл ли разработчик файл в честь локации или в честь
сюжетного события. Результат — в `world_map.riftgates[].
possible_spawn_records_best_effort` **только там, где совпадение нашлось**,
без попытки притянуть остальные 52 силой (это было бы выдумыванием связи).

### 4. Бинарный `world001.map` (частично, в рамках бюджета)

`ArchiveTool.exe "resources/Levels.arc" -extract <dir>` работает, извлёк
`world001.map` (819 018 649 → фактически **818 929 034 байта**, monolithic,
как и заявлено в задании).

Что вскрыл (несколько шагов hex/struct-анализа, дальше не пошёл):

- Сигнатура: `4D 41 50 09` = `b'MAP\t'` (магическое число + байт версии `9`).
- Дальше 4×int32 (little-endian): `(470615, 27, 9181, 255)`.
  - Поле №4 (`255`) — это **количество записей** следующей таблицы.
  - Поле №3 (`9181`) — **размер этой секции в байтах**, считая от начала
    самого поля-счётчика: проверил — секция реально заканчивается ровно на
    вычисленном смещении (`16 + 9181 = 9197`, парсер тоже остановился на 9197).
    Это значит в файле есть служебные "длина следующего блока" поля, которые
    в принципе позволяют скипать секции, не понимая их содержимое целиком.
  - Первая секция (255 строк, формат как в `.arz`: int32-длина + байты) —
    **список путей `Quests/*.qst`**, судя по всему квесты, задействованные
    в этом мире (`Quests/bounties/bl/bq_bl01.qst`, `Quests/sq_witchgods.qst`
    и т.д.) — не даёт региональной привязки сама по себе.
  - Сразу за ней начинается **вторая секция** — вперемешку с нераскодированными
    числовыми полями там встречаются: (а) уникальные имена размещённых
    объектов (`QP_GazerA01`, `LC_BarricadeZombies01_UNQ`, `WM_Camp01_UNF`,
    `LC_TownCenterZombie01_UNQ`, ...), (б) метки типа группы, **дословно
    совпадающие с терминологией PDF-гайда** — `"Unique Entities"`,
    `"Unified Entities"` (это те самые Group Link Tool категории из раздела
    про паттерны, см. п.1), (в) пути к `.dbr`-записям, которые уже резолвятся
    через нашу БД (`records/proxies/area001/questproxy_gazera01.dbr`,
    `records/proxies/area001/zombie_e_20m.dbr`,
    `records/level art/setpieces/setpiece_campgroble_02a.dbr`).

**Что НЕ удалось**: не восстановил точный побайтовый layout записи одной
"сущности" (сколько байт до/после строки-имени, где именно лежат позиция/
поворот-float'ы, где кончается одна запись и начинается следующая — между
распознанными строками остаются нерасшифрованные числовые поля переменной
длины). Без этого нельзя ни посчитать общее число размещённых объектов в
819 МБ файле, ни тем более извлечь координаты. Префиксы имён (`LC_`, `WM_`,
`QP_`, `Spawn_`) выглядят как аббревиатуры конкретных локаций/типов событий,
но я **не расшифровываю их значение** — это была бы попытка добавить
семантику, которую я не могу подтвердить по файлам (не беру из памяти об игре
по прямому требованию задания). Дальнейшее продвижение потребовало бы
значительно большего реверса (это уже "дорогая" часть, которую задание просит
не форсировать, если п.1-3 дали результат — они дали).

## Схема выхода `regions.json`

```
{
  "meta": {
    world_map_riftgates, world_map_shrines, world_map_labels, world_map_chapters,
    proxies_total, proxies_assigned_to_region, proxies_unclassified,
    entrances_total, entrances_assigned_to_region, entrances_unclassified,
    monster_refs_unresolved, pool_refs_unresolved, regions_found, note
  },
  "world_map": {
    "riftgates": [   # 73, из Region001ZoneList записи riftgate_mastertable.dbr
      {
        record, chapter ("a".."k", СВОЯ буква, не совпадает с region_code),
        order_in_chapter, slug,           # <- разобрано из имени файла
        name, name_tag,                   # <- ZoneNameTag/TeleportNameTag
        possible_spawn_records_best_effort: [...]  # опционально, см. текст отчёта
      }, ...
    ],
    "shrines": [      # 62, из Region001ShrineList
      {record, chapter, order_in_chapter, name,   # <- FileDescription (не тэг)
       position: {x, y},                          # <- WindowLocationX/Y (пиксели UI)
       ruined, corrupted}                         # <- ruinedShrine/corruptedShrine
    ],
    "map_labels": [   # 118, из labelTagN/labelXN/labelYN
      {index, name, name_tag, position: {x, y}}
    ],
    "chapters": [     # риftгейты, сгруппированные по "chapter"
      {chapter, riftgate_count, riftgate_names: [...]}
    ]
  },
  "regions": [
    {
      "region_code": "area001" | "area_b".."area_h" | "areavoid",
      "src_counts": {"base"|"gdx1"|"gdx2"|"gdx3": N},
      "proxy_count", "dungeon_entrance_count", "distinct_monsters_seen",
      "distinct_location_names": [...],   # уникальные резолвленные description
      "dungeon_entrances": [
        {record, src, name, name_tag, locked, on_add_to_world}
      ],
      "proxies": [
        {
          record, type ("Proxy"|"ProxyEndless"|"ProxyAmbush"), src,
          chance_to_run_pct,      # <- chanceToRun
          placement_extents,      # <- placementExtents
          alert_area,             # <- alertArea (только ProxyAmbush)
          min_group_size, max_group_size,   # <- minGroupSize/maxGroupSize (Ambush)
          pools: [
            {
              pool_record, tier ("normal"|"Epic"|"Legendary"|"LegendaryVeteran"),
              spawn_min, spawn_max,             # <- spawnMin/spawnMax
              champion_min, champion_max, champion_chance_pct,
              monsters: [
                {champion, weight, record, monster_type, name, name_tag, resolved}
              ]  # отсортировано по убыванию weight
            }
          ]
        }
      ]
    }, ...
  ],
  "unclassified": {
    "note": "...",
    "proxies_by_category": {категория: {count, src_counts}},
    "proxies": {категория: [полные записи, как выше]},
    "dungeon_entrances": [входы без определимой буквы зоны]
  }
}
```

Все поля — прямой резолв соответствующих `.dbr`-полей (см. таблицу выше и
докстринг `31_levels.py`), нулевые/пустые значения выброшены (`compact()`).

## Счётчики

- **Мировая карта**: **73** риftгейта (человеческое имя есть у всех, кто
  резолвится через `ZoneNameTag`/`TeleportNameTag` — резолвилось 73/73),
  **62** святилища (имя — прямой текст `FileDescription`, тоже 73/73... то
  есть 62/62), **118** подписей на текстуре карты, **8** глав
  (`a, b, f, g, h, i, j, k`; см. ниже почему не все 10 возможных букв
  задействованы). Best-effort привязка к спавнерам монстров нашлась для
  **21 из 73** риftгейтов (29%) — честно помечено как best-effort, не факт.
- Proxy-подобных записей всего (`Proxy`+`ProxyEndless`+`ProxyAmbush`): **1903**
  - привязано к региону (буква зоны нашлась в пути): **1076**
  - не привязано: **827** — из них 294 endless dungeon (отдельный roguelike-режим,
    не имеет фиксированного места в мире, поэтому географии тут в принципе нет),
    143 loot-chest прокси (`records/items/lootchests/*` — не монстры), остальное
    — категории `boss&quest*`/`factionspawns*`/`devotion`/`monstertotem`/`special`/
    песочницы разработчиков (`records/sandbox/*` — тестовые записи), у которых
    буква зоны либо не встречается в пути, либо запись межрегиональна.
- `DungeonEntrance` всего: **363** (по `src`: base 64, gdx1 35, gdx2 85,
  **gdx3 179** — совпало один-в-один с ориентиром "~179" из самого задания,
  это и есть спот-чек на уровне счётчиков).
  - привязано к региону: **240**, не привязано: **123** (в основном старые
    base-записи, где буква зоны не зашита в имя файла).
- Регионов найдено: **9** (`area001, area_b, area_c, area_d, area_e, area_f,
  areavoid, area_g, area_h`) — `area_a` не встретился ни разу ни в путях
  proxy/entrance, ни в `quests/gdarea*` (возможно, буква "A" в игре зарезервирована
  под что-то без Proxy/DungeonEntrance записей, например туториал/интро — не
  проверял отдельно, за рамками задания).
- Монстров, на которых сослался pool, но которых нет в БД: **12** (мелкий шум).
- Пулов, на которые сослался proxy, но которых нет в БД: **241** — **все 241
  без исключения** относятся к `records/endlessdungeon/proxies/proxy_common/
  proxy_blank.dbr` и подобным тестовым/placeholder-записям Endless Dungeon
  (`poolsbasic/aaa_t1.dbr`, `_t2.dbr`... `jjj_t1.dbr` — буквально алфавитные
  заглушки), проверено полным скриптом: **0** нерезолвленных пулов вне
  `endlessdungeon` (см. проверку в процессе работы). Это девелоперский мусор/
  шаблон, не влияет на географию мира.

## Живые примеры из выхода

**1. `area_h` (зона gdx3), один из proxy:**
```json
{
  "record": "records/proxies/areah/kurnhuman+chthonian_t.dbr",
  "type": "Proxy", "src": "gdx3",
  "chance_to_run_pct": 100.0, "placement_extents": 12.0,
  "pools": [{
    "pool_record": "records/proxies/poolsgdx3/p_kurnhuman+chthonian_t.dbr",
    "tier": "normal", "spawn_min": 4, "spawn_max": 6,
    "champion_max": 2, "champion_chance_pct": 100.0,
    "monsters": [
      {"champion": true, "weight": 450, "name": "Kurn Bloodbound ~ Berserker",
       "name_tag": "tagGDX3EnemyHumanKurnVoid_B01", "resolved": true, ...},
      {"champion": true, "weight": 250, "name": "Chthonian Portent",
       "name_tag": "tagGDX3EnemyChthonianHerald_B01", "resolved": true, ...},
      ...
    ]
  }]
}
```
`region_code="area_h"` для этого файла содержит и вход `"Rift to Kurnhold"` в
`distinct_location_names` того же региона — имя proxy (`kurnhuman`) и имя
локации (`Kurnhold`) согласуются между собой, что говорит в пользу корректности
привязки по региону (это не было запрограммировано напрямую, совпадение
вылезло из независимых полей).

**2. `area_h`, фрагмент `distinct_location_names`** (31 вход в регионе):
`"Ascend to the Roof of the World"`, `"Elderveil"`, `"Freyoll Valley"`,
`"Mammoth Burial Grounds"`, `"Rift to Kurnhold"`, `"Black Lodge Exit"`,
`"Chaos Tear"` и т.д.

**3. `unclassified.proxies_by_category`** (фрагмент — честно показывает, что
не влезло в географию):
```json
"endlessdungeon": {"count": 294, "src_counts": {"gdx2": 166, "gdx3": 128}},
"records/items/lootchests": {"count": 143, "src_counts": {"base": 65, "gdx1": 31, "gdx2": 22, "gdx3": 25}},
"boss&quest": {"count": 56, "src_counts": {"base": 56}}
```

**4. `world_map.riftgates`, запись с best-effort привязкой к спавнерам:**
```json
{
  "record": "records/ui/riftgatemap/locations/riftgatemap1a_devilscrossing.dbr",
  "chapter": "a", "slug": "devilscrossing",
  "name": "Devil's Crossing Rift", "name_tag": "tagRiftDevilsCrossing",
  "possible_spawn_records_best_effort": [
    "records/proxies/boss&quest/proxy_devilscrossingattack_outlaw_n.dbr",
    "records/proxies/boss&quest/proxy_devilscrossingattack_aetherial_n.dbr",
    "records/proxies/boss&quest/proxy_devilscrossingattack_aetherial_t.dbr",
    "records/proxies/boss&quest/proxy_devilscrossing_zombiemutanta01.dbr"
  ]
}
```

**5. `world_map.shrines[0]`** — реальные пиксельные координаты, без выдумки:
```json
{"record": "records/ui/riftgatemap/devotionshrines/riftgatemapa01_shrine.dbr",
 "chapter": "a", "order_in_chapter": 1, "name": "Burial Hill",
 "position": {"x": 342, "y": 742}, "ruined": true}
```

## Спот-чек (обязательный)

Задание прямо запрещает сверять локации с собственной памятью об игре
("не бери данные о локациях из своей памяти об игре"), поэтому проверка —
на внутреннюю согласованность и на независимо данные заданием ориентиры,
а не на "я помню, что там должно быть N":

1. **Число `DungeonEntrance` в gdx3.** Задание заранее называет ориентир
   "~179 записей в gdx3". Фактический подсчёт по `src` дал **ровно 179** —
   точное совпадение с независимо данным числом, не подогнанное постфактум
   (`src`-разбивка считалась одним SQL-запросом до того, как писался этот
   раздел отчёта).
2. **Семантика полей Proxy/Pool против PDF.** Гайд моддинга (не игровая
   память, а официальный документ разработчика) описывает `Spawn Pool` как
   набор `Regular`/`Champion` записей с весами и `Champion Chance`. Проверил
   на 3 разных пулах (`p_trollhalf_n.dbr`, `p_troll_t.dbr`, `p_yeti_t.dbr`):
   во всех трёх `championChance`/`championMin`/`championMax`/`weightN`/
   `weightChampionN`/`spawnMin`/`spawnMax` присутствуют и осмысленно
   заполнены (проценты 0-100, положительные веса, spawnMin ≤ spawnMax) —
   структура полностью совпадает с документированной, ни одного отклонения.
3. **Перекрёстная сверка `world_map` против `regions`/`DungeonEntrance` —
   без использования памяти об игре, только двумя независимыми таблицами
   БД.** Три независимых поля одной и той же локации совпали без подгонки:
   - риftгейт `chapter=k, slug=kurnhold` → `name="Kurnhold Rift"`; в разделе
     `regions[area_h].distinct_location_names` (посчитано отдельным блоком
     кода, до того как я смотрел на риftгейты) уже был `"Rift to Kurnhold"`.
   - риftгейт `chapter=k, slug=verdantvalley` → `"Freyoll Valley Rift"`; тот
     же `area_h` уже содержал `"Freyoll Valley"`.
   - святилище `chapter=a, order=3` → `FileDescription="Burrwitch Outskirts"`;
     `labelTag7` в той же таблице → тэг `tagWorldMapBurrwitchOutskirts`, что
     резолвится в `"Burrwitch{^n}Outskirts"` (`{^n}` — служебный маркер
     переноса строки в тэге, не мой артефакт) — то же имя, две независимые
     таблицы (`Region001ShrineList` и `labelTagN`) той же записи
     `riftgate_mastertable.dbr`.
   Три независимых совпадения между как минимум двумя разными механизмами
   резолва (тэг vs. прямой текст, разные списки одной записи, разные
   .dbr-таблицы) — это не доказательство "истинности" названий (сама игра не
   запускалась), но сильный сигнал, что резолв работает правильно и данные
   не перепутаны.

## Что не удалось / в чём не уверен (главный раздел)

1. **Бинарный `.map` не дореверсен.** Нашёл сигнатуру, схему заголовка (4
   int32, включая пару "размер секции в байтах" + "число записей") и первую
   секцию (строки квестов), плюс начало второй секции (список именованных
   размещённых объектов вперемешку с нерасшифрованными числовыми полями,
   явно включая ссылки на те же `.dbr`, что и в БД). Не нашёл: границы одной
   "записи-объекта" в байтах, где лежат позиция/поворот (координаты), общее
   число объектов в файле. Файл 819 МБ — полный проход по нему с текущим
   уровнем понимания формата невозможен без ещё одной итерации реверса
   заметно большего объёма, чем позволяет бюджет спайка.
2. **`area_a` (буква из раздела 3, `region_code`) не найден нигде** в путях
   proxy/entrance/`quests/gdarea*`. Это НЕ то же самое, что `chapter="a"` в
   `world_map` (там она есть, 10 риftгейтов — Devil's Crossing, Burrwitch
   Village и т.д., буквы из разных систем!). Рабочая гипотеза (не проверена
   до конца, честно оставляю как гипотезу): содержимое, которое на
   UI-карте помечено `chapter="a"`, физически хранится в коде под
   `records/proxies/area001/` (единая, не разбитая по буквам папка для всей
   базовой игры) — то есть `region_code=area001` из раздела 3, вероятно,
   ФИЗИЧЕСКИ ПЕРЕКРЫВАЕТ и `chapter="a"`, и `chapter="b"` мировой карты
   одновременно (там 306 proxy на весь базовый мир без дальнейшего деления).
   Прямого поля, которое доказывало бы это 1:1, в БД не нашёл — это
   правдоподобная, но не подтверждённая связь.
3. **Регион `area001` (весь базовый мир) не разбивается дальше.** Ни один
   `Proxy` базовой игры не лежит в подпапке с буквой зоны — все 306 в одной
   плоской `area001/`. Значит для базовой игры (без аддонов) в этом выходе
   нет более мелкой географической группировки монстров, чем "весь мир
   Cairn" целиком — несмотря на то что `DungeonEntrance`/квесты базовой игры
   всё же иногда несут буквы `b/c/d` (когда буква есть в имени файла входа
   или в `onAddToWorld`, вход попадает в `area_b/c/d`, но соответствующие
   proxy-спавнеры там не встретятся, т.к. они физически лежат в `area001`).
   То есть для base game связка "монстр из area001 -> конкретный вход из
   area_b/c/d" **не восстановлена** — это два параллельных, не пересекающихся
   по коду пути среза одних и тех же путей.
4. **123 из 363 `DungeonEntrance` не привязаны ни к одному региону** — в
   основном старые (`base`) записи, где имя файла не содержит буквы зоны
   вообще (общие типы дверей: `Cave Entrance`, `Fort Entrance` и т.п.),
   плюс часть `gdx1-3` с общими шаблонными именами. Они лежат в
   `unclassified.dungeon_entrances`, не выброшены, но и не сгруппированы.
5. **827 из 1903 proxy-подобных записей не привязаны к региону** — большая
   часть (294) это Endless Dungeon (у него в принципе нет фиксированной точки
   в открытом мире, это генерируемый роглайк-режим — географии там нет по
   определению режима, не пробел в разборе), остальное — loot-chest прокси
   (не монстры), boss/quest/faction/devotion/totem/special категории и
   несколько записей в `records/sandbox/<имя разработчика>/*` (явно тестовые
   файлы разработчиков, не игровой контент — видно по пути).
   Все они сохранены целиком в `unclassified.proxies` по категориям, просто
   не привязаны географически.
6. **`region_code` (раздел 3) — не официальный игровой термин**, а
   закономерность, которую я заметил и проверил в путях файлов. Она стабильно
   совпадает с `src` (100% чистая по каждой букве), но это внутренний индекс
   кода/квестов, не название акта в интерфейсе игры. `world_map.chapters`
   (раздел 3b) ближе к "официальному" делению, потому что построен из
   реальной UI-таблицы карты мира, но и его буква (`chapter`) — это тоже имя
   поля/файла Crate, а не подписанный в игре номер акта; сам номер акта
   (Act 1/2/...) в БД нигде текстом не встретился.
7. **2D-координаты подписей карты есть, 3D-координат игрока нет.**
   `world_map.shrines[].position` и `world_map.map_labels[].position` —
   настоящие числа из `WindowLocationX/Y` и `labelX/YN`, но это пиксельные
   позиции на UI-текстуре карты (масштаб/начало координат этой текстуры я не
   искал и не знаю), а не 3D-координаты в игровом мире — те остаются
   недоступны, как и требовало задание.
8. **Best-effort привязка риftгейтов к спавнерам — низкий recall (21/73,
   29%), не пытался повышать искусственно.** Пробовал только точное
   вхождение "slug" в путь; частичное/нечёткое совпадение (например, по
   резолвленным именам входов) дало ещё хуже результат (5/73 при пробной
   попытке) и в выход не пошло, чтобы не плодить произвольные привязки.
   52 из 73 риftгейтов остаются без автоматической ссылки на конкретные
   Proxy/DungeonEntrance — это честная граница метода, не забытый баг.

## Определение готовности (DoD) — самопроверка

- [x] Скрипт реально запущен (`python 31_levels.py` из папки `extract`), вывод
      в stdout видел дважды (до и после подсказки координатора про
      `riftgate_mastertable.dbr`) — разбивка по мировой карте + 9 регионам +
      счётчики покрытия.
- [x] Выходной файл существует (`data/grim-dawn/regions.json`, 17 071 206
      байт), открыл и глазами проверил записи (raw-примеры выше + отдельные
      `json.load` проверки `meta`/`world_map`/`region["area_h"]`/`unclassified`).
- [x] Спот-чек — переориентирован под требование задания не использовать
      память об игре: (а) независимо данный заданием ориентир (179
      DungeonEntrance в gdx3 — совпало точно); (б) документированная (PDF)
      семантика полей `Proxy`/`ProxyPool` (совпало на 3 пулах без отклонений);
      (в) тройная перекрёстная сверка имён локаций между `world_map.riftgates`,
      `world_map.shrines`, `world_map.map_labels` и `regions[].
      distinct_location_names` — три независимых совпадения без подгонки
      (Kurnhold, Freyoll Valley, Burrwitch Outskirts).
- [x] Отчёт написан, раздел «что не удалось» — 8 честных пунктов, включая
      главный незакрытый вопрос (формат `.map` дореверсен частично) и честную
      границу best-effort привязки риftгейтов к спавнерам (29%).
