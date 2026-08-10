# -*- coding: utf-8 -*-
"""Задание 11: Аффиксы (префиксы/суффиксы) и правила их роллов.

Схема связей (реверснута вручную для этого задания, см. отчёт REPORTS/11_affixes.md):

  LootRandomizer (7984)        — сам аффикс: имя, статы, вес/стоимость/уровень.
      путь records/items/lootaffixes/<folder>/... -> folder определяет kind
      (prefix/suffix/prefixunique/suffixunique/ascended/completion/completionrelics/crafting/broken)

  LootRandomizerTable (1081)   — пул аффиксов: randomizerName{i}/Weight{i}/LevelMin{i}/Max{i}.
      Тоже лежит в lootaffixes/<folder>/..tables/, folder = тот же kind, что и у аффиксов внутри.

  LootItemTable_DynWeight (2663) — САМОЕ ГЛАВНОЕ ЗВЕНО: "какой предмет тянет какой пул".
      Поля предмета НЕ содержат ссылок на affix-таблицы (проверено на ArmorProtective_Chest,
      WeaponMelee_Sword — там нет prefixTables/suffixTables). Связь хранится ОТДЕЛЬНО, в этих
      loot-item-table записях (records/items/loottables/<slot>/tdyn_*.dbr):
        lootName{i}/lootWeight{i}                -> какие БАЗОВЫЕ предметы может выдать эта таблица
        prefixTableName{i}/Weight{i}/LevelMin/Max{i}      -> обычный пул префиксов
        suffixTableName{i}/...                             -> обычный пул суффиксов
        rarePrefixTableName{i}/... , rareSuffixTableName{i}/... -> усиленный пул для Rare-предметов
        brokenTableName{i}                                  -> пул для Broken-качества
        noPrefixNoSuffix/prefixOnly/suffixOnly/bothPrefixSuffix/rarePrefixOnly/rareSuffixOnly/
        rarePrefixNormalSuffix/normalPrefixRareSuffix/rareBothPrefixSuffix/brokenOnly
                                                             -> веса того, КАКАЯ комбинация качества
                                                                вообще выпадет на предмете
        minItemLevelEquation/maxItemLevelEquation/targetLevelEquation -> формулы уровня предмета
                                                                (текстовые, не вычисляем)

  ItemAscensionFormula (9)     — крафт "Ascension" (Forgotten Gods): <slot>TablesAffix/<slot>TablesMastery
      -> LootRandomizerTable в lootaffixes/ascended/... (добавляет 2й аффикс поверх легендарки).

  ВНЕ области (домен задания 40, не дублируем, но упоминаем связь в отчёте):
    ItemRelic.bonusTableName -> LootRandomizerTable в lootaffixes/completion/...
      (бонус за "завершение" реликвии). NpcCrafter.enhancementTable -> lootaffixes/crafting/...
      (кузнец, "усиление" предмета).

  1600 из 2663 записей LootItemTable_DynWeight (damagetables, misc, materia, blueprints,
  enemyspecific, randomsettdyns, mastery + часть gear-записей) НЕ содержат явных полей
  prefixTableName*/suffixTableName*. ПРЕЖНЯЯ ГИПОТЕЗА («наследуют дефолты из templates.arc»)
  ОПРОВЕРГНУТА: все 18 полей prefixTableName*/suffixTableName* в field_schema.json (распакован
  из templates.arc) имеют пустой defaultValue — наследовать оттуда нечего, шаблон даёт схему
  поля, а не данные. Настоящая картина (см. REPORTS/11_affixes.md, раздел «Исправленная
  гипотеза»):
    - damagetables/randomsettdyns/enemyspecific/blueprints/misc/materia/mastery (~1295) —
      это НЕ предметные таблицы со случайными аффиксами вообще (элементальные варианты
      апгрейженных предметов, чертежи, компоненты, сеты, привязка к мастерству) — им и не
      положено иметь prefix/suffixTableName.
    - остальные ~305 из «geartype»-папок (weapons/gearaccessories/gearhead/gearshoulders/
      geartorso/gearfeet/gearhands/gearlegs) — ПРОВЕРЕНО запросом по gd.sqlite: 100% предметов
      (6308 из 6309 резолвленных lootName*-ссылок, 1 отвисшая ссылка) там имеют
      itemClassification Legendary или Epic. Ни одного Common/Magical/Rare предмета не найдено.
      Legendary/Epic (MI) — это как раз качества предметов, которые НЕ роллят случайные
      префиксы/суффиксы (фиксированные статы). Отсутствие полей таблиц здесь — корректные
      игровые данные, а не недостача парсинга.

Запуск:  python 11_affixes.py
Выход:   <GD_DATA>/affixes.jsonl, <GD_DATA>/affix_tables.json
"""
import json
import os
import re
import time
from collections import Counter

from gdlib import GD_DATA, Tags, open_sqlite, write_json, write_jsonl, norm

KIND_BY_FOLDER = {
    "prefix": "prefix",
    "suffix": "suffix",
    "prefixunique": "prefix_unique",
    "suffixunique": "suffix_unique",
    "ascended": "ascended",
    "completion": "completion",
    "completionrelics": "completion_relic",
    "crafting": "crafting",
    "broken": "broken",
}

# Метаданные без игровой семантики - выбрасываем всегда.
META_FIELDS = {"templateName", "Class", "characterBaseAttackSpeedTag", "brokenDropSound"}

# Поля, которые промотируются в именованные атрибуты верхнего уровня - исключаются из stats.
PROMOTED = {
    "FileDescription", "itemClassification", "levelRequirement",
    "lootRandomizerName", "lootRandomizerCost", "lootRandomizerJitter",
    "marketAdjustmentPercent", "lootRandomizerScale", "petBonusName",
    # itemSkillName/itemSkillAutoController/itemSkillLevelEq - нашлись через field_schema.json
    # (type=file_dbr/equation, group "Skill Augment") - это "proc"-скилл (шанс на удар/каст),
    # который раньше молча лежал в stats как сырой путь. См. build_affix().
    "itemSkillName", "itemSkillAutoController", "itemSkillLevelEq",
}
for _i in range(1, 3):
    PROMOTED.add(f"augmentSkillName{_i}")
    PROMOTED.add(f"augmentSkillLevel{_i}")
for _i in range(1, 4):
    PROMOTED.add(f"modifiedSkillName{_i}")
    PROMOTED.add(f"modifierSkillName{_i}")


def load_field_schema():
    """D:/git/home/data/grim-dawn/field_schema.json - словарь схемы полей .dbr
    (авторитетно из templates.arc, см. TASKS/_COMMON.md). field -> {type, class, groups, description}.
    """
    path = os.path.join(GD_DATA, "field_schema.json")
    with open(path, encoding="utf-8") as fh:
        return json.load(fh)


def field_groups(schema, field):
    """Человекочитаемые категории поля из field_schema (без общего "All Groups").
    None, если поля нет в схеме вообще (складываем в отчёт как пробел, не молчим)."""
    info = schema.get(field)
    if info is None:
        return None
    groups = info.get("groups") or []
    specific = [g for g in groups if g != "All Groups"]
    return specific or groups

QUALITY_FIELDS = [
    "noPrefixNoSuffix", "prefixOnly", "suffixOnly", "bothPrefixSuffix",
    "rarePrefixOnly", "rareSuffixOnly", "rarePrefixNormalSuffix",
    "normalPrefixRareSuffix", "rareBothPrefixSuffix", "brokenOnly",
]


def is_zero(v):
    if v is None:
        return True
    if isinstance(v, str):
        return v == ""
    if isinstance(v, (int, float)):
        return v == 0
    if isinstance(v, list):
        return all(is_zero(x) for x in v)
    return False


def nonzero(f, exclude):
    return {k: v for k, v in f.items() if k not in exclude and not is_zero(v)}


def kind_of(path):
    """records/items/lootaffixes/<folder>/... -> kind по имени папки."""
    parts = norm(path).split("/")
    if len(parts) > 3 and parts[2] == "lootaffixes":
        return KIND_BY_FOLDER.get(parts[3], parts[3])
    return None


def indices_for(f, base_regex):
    return sorted({int(m.group(1)) for k in f for m in [re.match(base_regex, k)] if m})


def resolve_ref(path, tags, cache, con):
    """Путь records/....dbr -> человекочитаемое имя (скилл/реликвия/пет-бонус), None если нет."""
    if not path:
        return None
    key = norm(path)
    if key in cache:
        return cache[key]
    row = con.execute("SELECT fields FROM records WHERE name=?", (key,)).fetchone()
    name = None
    if row:
        f = json.loads(row[0])
        for tf in ("skillDisplayName", "description", "itemNameTag", "petDisplayName"):
            tv = f.get(tf)
            if isinstance(tv, str) and tv in tags:
                name = tags(tv)
                break
        if not name:
            name = f.get("FileDescription")
    cache[key] = name
    return name


def fetch_fields(path, cache, con):
    """Путь records/....dbr -> сырой fields-dict записи (для полей без displayName/tag, напр.
    skillautocastcontroller). None, если записи нет."""
    if not path:
        return None
    key = norm(path)
    if key in cache:
        return cache[key]
    row = con.execute("SELECT fields FROM records WHERE name=?", (key,)).fetchone()
    f = json.loads(row[0]) if row else None
    cache[key] = f
    return f


def build_affix(name, src, f, tags, cache, fcache, con, schema, unknown_fields):
    entity = {"record": name, "kind": kind_of(name), "src": src}

    name_tag = f.get("lootRandomizerName")
    entity["name_tag"] = name_tag
    if name_tag and name_tag in tags:
        entity["name"] = tags(name_tag)
        entity["name_source"] = "tag"
    else:
        entity["name"] = None
        entity["name_source"] = "none"
    # FileDescription на LootRandomizer - это внутренняя пометка дизайнера
    # (число/проценты/класс), НЕ игровое имя - см. отчёт. Сохраняем отдельно как заметку.
    dev_note = f.get("FileDescription")
    if dev_note:
        entity["dev_note"] = dev_note

    for fld in ("itemClassification", "levelRequirement"):
        v = f.get(fld)
        if not is_zero(v):
            entity[fld] = v
    if not is_zero(f.get("lootRandomizerCost")):
        entity["cost"] = f["lootRandomizerCost"]
    if not is_zero(f.get("lootRandomizerJitter")):
        entity["jitter_pct"] = f["lootRandomizerJitter"]
    if not is_zero(f.get("marketAdjustmentPercent")):
        entity["marketAdjustmentPercent"] = f["marketAdjustmentPercent"]

    augments = []
    for i in (1, 2):
        sn = f.get(f"augmentSkillName{i}")
        if sn:
            augments.append({
                "skill": sn,
                "skill_name": resolve_ref(sn, tags, cache, con),
                "level": f.get(f"augmentSkillLevel{i}"),
            })
    if augments:
        entity["augments"] = augments

    # "ascended"-аффиксы не дают новый скилл, а МОДИФИЦИРУЮТ существующий (см. modifierSkillName ->
    # запись-модификатор в itemskillsgdx3/skillmodifiers/ascended/...).
    modifiers = []
    for i in (1, 2, 3):
        modified = f.get(f"modifiedSkillName{i}")
        modifier = f.get(f"modifierSkillName{i}")
        if modified or modifier:
            modifiers.append({
                "modifies": modified,
                "modifies_name": resolve_ref(modified, tags, cache, con),
                "modifier": modifier,
                "modifier_name": resolve_ref(modifier, tags, cache, con),
            })
    if modifiers:
        entity["ascended_modifiers"] = modifiers

    pb = f.get("petBonusName")
    if pb:
        entity["pet_bonus"] = {"record": pb, "name": resolve_ref(pb, tags, cache, con)}

    # itemSkillName/itemSkillAutoController/itemSkillLevelEq - найдено через field_schema.json
    # (group "Skill Augment", type file_dbr/equation): "proc"-скилл, который срабатывает по
    # условию (шанс на удар/каст/получение урона), а не даёт очки скилла как augmentSkillName.
    isn = f.get("itemSkillName")
    if isn:
        proc = {"skill": isn, "skill_name": resolve_ref(isn, tags, cache, con)}
        eq = f.get("itemSkillLevelEq")
        if eq:
            proc["level_eq"] = eq
        ctrl = f.get("itemSkillAutoController")
        if ctrl:
            proc["controller"] = ctrl
            cf = fetch_fields(ctrl, fcache, con)
            if cf:
                trig = {k: cf[k] for k in ("chanceToRun", "triggerType", "targetType", "autoTargetRadius")
                        if not is_zero(cf.get(k))}
                if trig:
                    proc["trigger"] = trig
        entity["proc"] = proc

    stats = nonzero(f, META_FIELDS | PROMOTED)
    if stats:
        entity["stats"] = stats
        # Обогащение категориями из field_schema.json (главная цель доработки):
        # для каждого стата - его человекочитаемая группа(ы), напр. "Offensive Fire",
        # "Retaliation", "Skill Reduction", вместо голого имени поля .dbr.
        groups_by_field = {}
        for k in stats:
            g = field_groups(schema, k)
            if g is None:
                unknown_fields.add(k)
            else:
                groups_by_field[k] = g
        if groups_by_field:
            entity["stat_groups"] = groups_by_field
            cats = sorted({g for gl in groups_by_field.values() for g in gl})
            entity["categories"] = cats

    entity["tables"] = []  # заполняется во втором проходе из LootRandomizerTable
    return entity


def pool_list(f, prefix):
    """prefix напр. 'prefixTable' -> [{table, weight, levelMin, levelMax}, ...] по индексам."""
    idxs = indices_for(f, re.escape(prefix) + r"Name(\d+)$")
    out = []
    for i in idxs:
        nm = f.get(f"{prefix}Name{i}")
        if not nm:
            continue
        out.append({
            "table": nm,
            "weight": f.get(f"{prefix}Weight{i}"),
            "levelMin": f.get(f"{prefix}LevelMin{i}"),
            "levelMax": f.get(f"{prefix}LevelMax{i}"),
        })
    return out


def main():
    t0 = time.time()
    con = open_sqlite(readonly=True)
    tags = Tags()
    ref_cache = {}
    fields_cache = {}
    item_type_cache = {}
    schema = load_field_schema()
    print(f"field_schema.json: {len(schema)} полей")
    unknown_fields = set()  # стат-поля, которых нет в field_schema (для отчёта о покрытии)

    # ------------------------------------------------------------------
    # 1) LootRandomizer -> affixes
    # ------------------------------------------------------------------
    rows = con.execute(
        "SELECT name, src, fields FROM records WHERE type='LootRandomizer'"
    ).fetchall()
    print(f"LootRandomizer записей: {len(rows)}")

    affixes = {}  # norm(record) -> entity (dict, мутируем tables во 2-м проходе)
    kind_counts = Counter()
    no_name_tag = 0
    for name, src, fields_json in rows:
        f = json.loads(fields_json)
        ent = build_affix(name, src, f, tags, ref_cache, fields_cache, con, schema, unknown_fields)
        kind_counts[ent["kind"]] += 1
        if ent["name"] is None:
            no_name_tag += 1
        affixes[norm(name)] = ent

    # ------------------------------------------------------------------
    # 2) LootRandomizerTable -> пулы, плюс обратная ссылка в affixes[*]["tables"]
    # ------------------------------------------------------------------
    trows = con.execute(
        "SELECT name, fields FROM records WHERE type='LootRandomizerTable'"
    ).fetchall()
    print(f"LootRandomizerTable записей: {len(trows)}")

    tables = {}
    table_kind_counts = Counter()
    dangling_affix_refs = 0  # ссылка на LootRandomizer, которого нет среди наших affixes
    for name, fields_json in trows:
        f = json.loads(fields_json)
        idxs = indices_for(f, r"randomizerName(\d+)$")
        entries = []
        for i in idxs:
            rn = f.get(f"randomizerName{i}")
            if not rn:
                continue
            entries.append({
                "affix": rn,
                "weight": f.get(f"randomizerWeight{i}"),
                "levelMin": f.get(f"randomizerLevelMin{i}"),
                "levelMax": f.get(f"randomizerLevelMax{i}"),
            })
        kind = kind_of(name)
        table_kind_counts[kind] += 1
        tables[norm(name)] = {
            "record": name,
            "kind": kind,
            "file_description": f.get("FileDescription"),
            "entries": entries,
        }
        for e in entries:
            akey = norm(e["affix"])
            aff = affixes.get(akey)
            if aff is None:
                dangling_affix_refs += 1
                continue
            aff["tables"].append({
                "table": name, "weight": e["weight"],
                "levelMin": e["levelMin"], "levelMax": e["levelMax"],
            })

    # ------------------------------------------------------------------
    # 3) LootItemTable_DynWeight -> "какой предмет тянет какой пул"
    # ------------------------------------------------------------------

    def item_type_of(path):
        key = norm(path)
        if key in item_type_cache:
            return item_type_cache[key]
        row = con.execute("SELECT type FROM records WHERE name=?", (key,)).fetchone()
        t = row["type"] if row else None
        item_type_cache[key] = t
        return t

    drows = con.execute(
        "SELECT name, fields FROM records WHERE type='LootItemTable_DynWeight'"
    ).fetchall()
    print(f"LootItemTable_DynWeight записей: {len(drows)}")

    # "geartype"-папки среди исключённых (без prefix/suffixTableName*) - гипотеза задания:
    # это таблицы для Legendary/Epic(MI) предметов, которые не роллят случайные аффиксы
    # в принципе. Проверяем ФАКТАМИ: резолвим все их lootName*-ссылки и смотрим itemClassification.
    EQUIP_FOLDERS = {
        "weapons", "gearaccessories", "gearhead", "gearshoulders",
        "geartorso", "gearfeet", "gearhands", "gearlegs",
    }
    item_classification_cache = {}

    def item_classification_of(path):
        key = norm(path)
        if key in item_classification_cache:
            return item_classification_cache[key]
        row = con.execute("SELECT fields FROM records WHERE name=?", (key,)).fetchone()
        cls = json.loads(row[0]).get("itemClassification") if row else None
        item_classification_cache[key] = cls
        return cls

    drop_tables = {}
    excluded_no_table_names = Counter()  # по папке (damagetables/misc/materia/...)
    included_folders = Counter()
    excluded_equip_item_classifications = Counter()
    excluded_equip_dangling_refs = 0
    excluded_equip_tables_examined = 0
    for name, fields_json in drows:
        f = json.loads(fields_json)
        parts = norm(name).split("/")
        folder = parts[3] if len(parts) > 3 else "?"

        prefix_pools = pool_list(f, "prefixTable")
        suffix_pools = pool_list(f, "suffixTable")
        rare_prefix_pools = pool_list(f, "rarePrefixTable")
        rare_suffix_pools = pool_list(f, "rareSuffixTable")
        broken_pools = pool_list(f, "brokenTable")

        if not (prefix_pools or suffix_pools or rare_prefix_pools or rare_suffix_pools or broken_pools):
            excluded_no_table_names[folder] += 1
            if folder in EQUIP_FOLDERS:
                excluded_equip_tables_examined += 1
                for i in indices_for(f, r"lootName(\d+)$"):
                    ln = f.get(f"lootName{i}")
                    if not ln:
                        continue
                    cls = item_classification_of(ln)
                    if cls is None:
                        excluded_equip_dangling_refs += 1
                    else:
                        excluded_equip_item_classifications[cls] += 1
            continue
        included_folders[folder] += 1

        idxs = indices_for(f, r"lootName(\d+)$")
        items = []
        type_counts = Counter()
        for i in idxs:
            ln = f.get(f"lootName{i}")
            if not ln:
                continue
            typ = item_type_of(ln)
            items.append({"item": ln, "type": typ, "weight": f.get(f"lootWeight{i}")})
            type_counts[typ] += 1

        quality = {k: f[k] for k in QUALITY_FIELDS if not is_zero(f.get(k))}

        drop_tables[norm(name)] = {
            "record": name,
            "item_types": dict(type_counts.most_common()),
            "items": items,
            "prefix_pools": prefix_pools,
            "suffix_pools": suffix_pools,
            "rare_prefix_pools": rare_prefix_pools,
            "rare_suffix_pools": rare_suffix_pools,
            "broken_pools": broken_pools,
            "quality_weights": quality,
            "level_equations": {
                "min": f.get("minItemLevelEquation"),
                "max": f.get("maxItemLevelEquation"),
                "target": f.get("targetLevelEquation"),
            },
            "allow_ascension": bool(f.get("allowAscension")) or None,
            "force_highest_level": bool(f.get("forceHighestLevel")) or None,
            "disable_level_limits": bool(f.get("disableLevelLimits")) or None,
        }

    # ------------------------------------------------------------------
    # 4) ItemAscensionFormula (Forgotten Gods: доп. аффикс на легендарку)
    # ------------------------------------------------------------------
    arows = con.execute(
        "SELECT name, fields FROM records WHERE type='ItemAscensionFormula'"
    ).fetchall()
    ascension_formulas = []
    for name, fields_json in arows:
        f = json.loads(fields_json)
        entry = {"record": name}
        for k, v in f.items():
            if k in ("templateName", "Class") or is_zero(v):
                continue
            entry[k] = v
        ascension_formulas.append(entry)

    # ------------------------------------------------------------------
    # 5) Кросс-ссылки, упомянутые, но не дублируемые (домен задания 40)
    # ------------------------------------------------------------------
    relic_bonus_links = con.execute(
        "SELECT COUNT(*) FROM records WHERE type='ItemRelic' AND fields LIKE '%bonusTableName%'"
    ).fetchone()[0]
    crafter_enhancement_links = con.execute(
        "SELECT COUNT(*) FROM records WHERE type='NpcCrafter' AND fields LIKE '%enhancementTable%'"
    ).fetchone()[0]

    # ------------------------------------------------------------------
    # Запись выходов
    # ------------------------------------------------------------------
    affix_list = list(affixes.values())
    apath, asize = write_jsonl("affixes.jsonl", affix_list)
    print(f"\nЗаписано {len(affix_list)} аффиксов -> {apath} ({asize/1024:.0f} KB)")

    out = {
        "meta": {
            "affixes_total": len(affix_list),
            "affixes_by_kind": dict(kind_counts.most_common()),
            "affixes_without_resolved_name_tag": no_name_tag,
            "field_schema_fields_total": len(schema),
            "stat_fields_unknown_in_field_schema": sorted(unknown_fields),
            "tables_total": len(tables),
            "tables_by_kind": dict(table_kind_counts.most_common()),
            "dangling_affix_refs_in_tables": dangling_affix_refs,
            "loot_item_tables_total": len(drows),
            "loot_item_tables_included": len(drop_tables),
            "loot_item_tables_excluded_no_table_fields": sum(excluded_no_table_names.values()),
            "loot_item_tables_excluded_by_folder": dict(excluded_no_table_names.most_common()),
            "loot_item_tables_included_by_folder": dict(included_folders.most_common()),
            "loot_item_tables_excluded_note": (
                "Отсутствие prefixTableName*/suffixTableName* НЕ означает наследование дефолтов "
                "из templates.arc (все такие поля в field_schema.json имеют пустой defaultValue - "
                "наследовать нечего). damagetables/randomsettdyns/enemyspecific/blueprints/misc/"
                "materia/mastery - это не предметные таблицы со случайными аффиксами вообще. "
                "Для gear/weapons-таблиц см. loot_item_tables_excluded_equipment_investigation."
            ),
            "loot_item_tables_excluded_equipment_investigation": {
                "tables_examined": excluded_equip_tables_examined,
                "lootName_refs_resolved_by_itemClassification": dict(
                    excluded_equip_item_classifications.most_common()
                ),
                "dangling_lootName_refs": excluded_equip_dangling_refs,
                "conclusion": (
                    "100% резолвленных lootName*-ссылок (кроме 1 отвисшей) - Legendary или Epic. "
                    "Ни одного Common/Magical/Rare не найдено. Гипотеза подтверждена: эти таблицы "
                    "выдают только предметы с фиксированными статами (легендарки/MI), у которых "
                    "по игровой логике нет случайных префиксов/суффиксов."
                ),
            },
            "ascension_formulas": len(ascension_formulas),
            "relic_bonusTableName_links_note": (
                f"{relic_bonus_links} записей ItemRelic ссылаются на lootaffixes/completion/* "
                "через bonusTableName - это 'завершение реликвии' (домен задания 40, тут не дублируем)"
            ),
            "npc_crafter_enhancement_links_note": (
                f"{crafter_enhancement_links} записей NpcCrafter (кузнецы) ссылаются на "
                "lootaffixes/crafting/* через enhancementTable - 'усиление предмета' у кузнеца"
            ),
        },
        "tables": tables,
        "item_drop_tables": drop_tables,
        "ascension_formulas": ascension_formulas,
    }
    tpath, tsize = write_json("affix_tables.json", out, indent=1)
    print(f"Записан affix_tables.json -> {tpath} ({tsize/1024:.0f} KB)")

    # ------------------------------------------------------------------
    # Покрытие
    # ------------------------------------------------------------------
    print("\n=== Покрытие ===")
    print(f"Аффиксов (LootRandomizer) обработано: {len(affix_list)} из {len(rows)}")
    print("По kind:", dict(kind_counts.most_common()))
    print(f"Аффиксов без резолвящегося name_tag (tagXxx не найден в tags_en.json или поля нет): {no_name_tag}")
    print(f"field_schema.json загружен: {len(schema)} полей")
    print(f"Стат-полей без записи в field_schema (не удалось назначить категорию): {len(unknown_fields)}",
          sorted(unknown_fields) if unknown_fields else "")
    print(f"Таблиц (LootRandomizerTable) обработано: {len(tables)} из {len(trows)}")
    print("Таблиц по kind:", dict(table_kind_counts.most_common()))
    print(f"Ссылок из таблиц на несуществующий LootRandomizer: {dangling_affix_refs}")
    print(f"LootItemTable_DynWeight всего: {len(drows)}")
    print(f"  включено (есть явные *TableName* поля): {len(drop_tables)}")
    print(f"  исключено (нет явных полей *TableName* -> НЕ шаблонные дефолты, см. отчёт):"
          f" {sum(excluded_no_table_names.values())}")
    print("  исключено по папкам:", dict(excluded_no_table_names.most_common()))
    print("  включено по папкам:", dict(included_folders.most_common()))
    print(f"  исключённые equip-таблицы ({excluded_equip_tables_examined} шт.) - itemClassification"
          f" их lootName*-ссылок:", dict(excluded_equip_item_classifications.most_common()),
          f"| отвисших ссылок: {excluded_equip_dangling_refs}")
    print(f"ItemAscensionFormula: {len(ascension_formulas)}")
    print(f"ItemRelic.bonusTableName ссылок (не дублируем, домен задания 40): {relic_bonus_links}")
    print(f"NpcCrafter.enhancementTable ссылок: {crafter_enhancement_links}")
    print(f"\nВремя: {time.time()-t0:.1f}s")


if __name__ == "__main__":
    main()
