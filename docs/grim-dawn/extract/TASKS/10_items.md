# Задание 10 — Предметы (экипировка)

Скрипт: `10_items.py` → `data/grim-dawn/items.jsonl` (+ `items_summary.json`)
Отчёт: `REPORTS/10_items.md`

## Цель

Полный каталог всей носимой экипировки: оружие, броня, украшения, щиты, оффхенды,
реликвии, артефакты (компоненты/аугменты — в задании 40, не дублируй).

## Область

Типы записей (проверь актуальный список сам через `SELECT type,COUNT(*) FROM records GROUP BY type`):
`WeaponMelee_*`, `WeaponHunting_Ranged1h/2h`, `WeaponArmor_Shield`, `WeaponArmor_Offhand`,
`ArmorProtective_*` (Head/Chest/Shoulders/Hands/Legs/Feet/Waist),
`ArmorJewelry_Ring/Amulet/Medal`, `ItemRelic`, `ItemArtifact`.

## Что вытащить на каждый предмет

- `record`, `name` + `name_tag`, `type`, `src` (base/gdx1/gdx2/gdx3)
- **Качество/редкость**: поле `itemClassification` (Broken/Common/Rare/Epic/Legendary/Quest).
  Разберись, как отличать Monster Infrequent (MI) — обычно Rare-класс без аффиксов,
  выпадающий с конкретного монстра. Пометь флагом `is_mi` (если не уверен — опиши в отчёте).
- **Требования**: `levelRequirement`, `physiqueRequirement`, `cunningRequirement`,
  `spiritRequirement`, `itemLevel`
- **Слот**: к какому слоту относится (выведи из типа записи; для колец/оружия учти 2 слота)
- **Базовые статы**: урон оружия (min/max по типам урона), броня, блок (`blockChance`,
  `blockAbsorption`, `blockRecoveryTime`)
- **Все модификаторы**: сопротивления, +скиллы, OA/DA, %урона, конверсии, статы.
  Собери их в словарь `stats` с исходными именами полей `.dbr` — переименовывать не надо,
  но составь в отчёте таблицу «поле .dbr → человеческий смысл» для встреченных полей.
- **Диапазоны**: многие статы имеют пару `X` и `XChance`/`XMax`/`XModifier`. Не теряй вторую половину.
- **Гранты скиллов**: `itemSkillName` (+ `itemSkillLevel`, `itemSkillAutoController`),
  а также поля вида `augmentSkill1..N` / `augmentSkillLevel1..N`,
  `augmentMasteryLevel1..N` (+skill к мастерству) и `augmentAllLevel` (+все скиллы).
  Резолвь путь скилла в его имя через тэг.
- **Сеты**: `itemSetName` → запись `SetPiece`. Плюс отдельный файл или секция
  `sets` в `items_summary.json`: набор → предметы, бонусы за 2/3/4 части.

## На что обратить внимание

- Один и тот же предмет может быть в нескольких `.arz` — `gd.sqlite` уже отдаёт победителя,
  просто используй `src` как справку.
- Скипай явно не-игровые/отладочные записи (пути с `test`, `debug`, `_dev`),
  но **сосчитай и перечисли их в отчёте**, не выбрасывай тихо.
- `itemNameTag` может отсутствовать — тогда имя из `FileDescription`. Пометь такие `name_source`.

## Спот-чек

Проверь по 2 известным легендаркам (например `Sunherald's Claymore` — двуручный меч
с конверсией физ→огонь, и любой сет-предмет): что имя, требования, конверсия и
гранты скиллов в твоём выходе выглядят осмысленно.
