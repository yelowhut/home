# -*- coding: utf-8 -*-
"""Задание 92: кросс-валидация выходов всех 8 экстракторов пайплайна.

Роль — скептик: ищем расхождения между независимо написанными экстракторами,
а не подтверждаем, что "все сошлось". Каждая проверка пишет
{"check", "status": "ok|mismatch|error", "counts": {...}, "examples": [...], "note": "..."}
в data/grim-dawn/crossval.json.

ВАЖНО ПРО ПАМЯТЬ:
  - drop_sources.jsonl (174 MB, 117871 строк) читается ТОЛЬКО построчно (for line in f),
    никогда не собирается в список. Копим только counters/sets/до-10-примеров.
  - loot_tables.json (53 MB) — один JSON-объект (не JSONL, несмотря на предупреждение
    в задании — построчно его прочитать нельзя, он в одну строку). Загружается ОДИН
    раз целиком (json.load), из него сразу вынимается нужное (meta, mi_items — это
    ключи 1625 MI-предметов), после чего объект удаляется (del + gc.collect()) —
    держать 53 MB распарсенного JSON одновременно с остальными файлами не нужно.
  - items.jsonl (~9 MB), affixes.jsonl (~16 MB), regions.json (~17 MB),
    field_schema.json (~5 MB) — загружаются целиком, это безопасно по объёму.

Запуск:  python 92_crossval.py
Выход:   <GD_DATA>/crossval.json
"""
import gc
import json
import re
import time
from collections import Counter, defaultdict

from gdlib import GD_DATA, Tags, open_sqlite, out_path, write_json, norm

TAG_RE = re.compile(r"^tag[A-Z]")

checks = []


def add_check(check, status, counts=None, examples=None, note=""):
    checks.append({
        "check": check,
        "status": status,
        "counts": counts or {},
        "examples": (examples or [])[:10],
        "note": note,
    })
    print(f"[{status.upper():8}] {check} :: {counts}")


def load_jsonl(name):
    path = out_path(name)
    rows = []
    with open(path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                rows.append(json.loads(line))
    return rows


def load_json(name):
    with open(out_path(name), encoding="utf-8") as f:
        return json.load(f)


t0 = time.time()
print("=== 92_crossval: загрузка средних файлов ===")
items = load_jsonl("items.jsonl")
affixes = load_jsonl("affixes.jsonl")
skills_flat = load_jsonl("skills_flat.jsonl")
augments = load_jsonl("augments.jsonl")
recipes = load_jsonl("recipes.jsonl")
components = load_json("components.json")
factions = load_json("factions.json")
field_schema = load_json("field_schema.json")
mechanics = load_json("mechanics.json")
devotions = load_json("devotions.json")
items_summary = load_json("items_summary.json")
regions = load_json("regions.json")
print(f"загружено за {time.time()-t0:.1f}s")

item_records = set(r["record"].lower() for r in items)
skill_records = set(r["record"].lower() for r in skills_flat)

con = open_sqlite(readonly=True)


def db_exists(path):
    row = con.execute("SELECT 1 FROM records WHERE name=?", (norm(path),)).fetchone()
    return row is not None


def db_type(path):
    row = con.execute("SELECT type FROM records WHERE name=?", (norm(path),)).fetchone()
    return row[0] if row else None


# ---------------------------------------------------------------------------
# 1. Гранты скиллов с предметов: itemSkill / augments[].skill / skill_modifiers[].modifies
#    resolve в skills_flat.jsonl. mastery_augments[].mastery и skill_modifiers[].modifier
#    ссылаются на другие сущности (маркер требования мастерства / безымянный
#    Skill_Modifier-узел) — не скиллы верхнего уровня, отдельно измеряем как "expected".
# ---------------------------------------------------------------------------
resolvable_total = 0
resolvable_missing = []
expected_nonskill_mastery = 0
expected_nonskill_modifier = 0
missing_by_kind = Counter()

for r in items:
    rec = r["record"]
    refs = []
    isk = r.get("itemSkill")
    if isk and isk.get("skill"):
        refs.append(("itemSkill", isk["skill"], isk.get("skill_name")))
    for a in (r.get("augments") or []):
        if a.get("skill"):
            refs.append(("augments[].skill", a["skill"], a.get("skill_name")))
    for sm in (r.get("skill_modifiers") or []):
        if sm.get("modifies"):
            refs.append(("skill_modifiers[].modifies", sm["modifies"], sm.get("modifies_name")))
    for kind, ref, name in refs:
        resolvable_total += 1
        if ref.lower() not in skill_records:
            missing_by_kind[kind] += 1
            resolvable_missing.append({
                "item": rec, "field": kind, "skill_ref": ref, "skill_name": name,
                "exists_in_db": db_exists(ref), "db_type": db_type(ref),
            })
    for ma in (r.get("mastery_augments") or []):
        if ma.get("mastery"):
            expected_nonskill_mastery += 1
    for sm in (r.get("skill_modifiers") or []):
        if sm.get("modifier") and sm["modifier"].lower() not in skill_records:
            expected_nonskill_modifier += 1

# ns/gdx prefix breakdown of the misses (hypothesis: extension item-skill namespaces
# missing wholesale from skills_flat.jsonl)
miss_prefixes = Counter()
for m in resolvable_missing:
    parts = m["skill_ref"].lower().split("/")
    miss_prefixes["/".join(parts[:3])] += 1

status = "ok" if not resolvable_missing else "mismatch"
add_check(
    "item_skill_grants_resolve",
    status,
    counts={
        "total_refs_checked": resolvable_total,
        "missing": len(resolvable_missing),
        "missing_by_field": dict(missing_by_kind),
        "missing_by_ref_prefix": dict(miss_prefixes.most_common(10)),
        "expected_nonskill_mastery_augment_refs": expected_nonskill_mastery,
        "expected_nonskill_skill_modifier_modifier_refs": expected_nonskill_modifier,
    },
    examples=resolvable_missing,
    note=("Все непогасившиеся ссылки — из поля itemSkill (не augments/skill_modifiers.modifies, "
          "они резолвятся 100%). Все промахи указывают на записи под "
          "records/skills/itemskillsgdx1|gdx2|gdx3/legendary/*.dbr — это активные скиллы-проки "
          "легендарных предметов дополнений. skills_flat.jsonl (задание 20) индексирует только "
          "records/skills/itemskills/ (789 базовых item-скиллов) и 10 мастерских деревьев — "
          "expansion-неймспейсы itemskillsgdx{1,2,3} и nonplayerskillsgdx2 не сканировались "
          "вообще (проверено: ни один record из них не встречается в skills_flat.jsonl). "
          "Это БАГ/пробел покрытия задания 20, не особенность данных — сами скилл-записи "
          "существуют в БД (db_type подтверждает Skill_* типы) и имеют настоящие имена "
          "('Flame Patch', \"Executioner's Edge\" и т.п.). mastery_augments[].mastery и "
          "skill_modifiers[].modifier осознанно не считаются 'непогасившимися' — это ссылки "
          "на _classtraining_* (маркер требования мастерства) и безымянные MI-мод-узлы "
          "соответственно, задокументировано в отчёте задания 10."),
)


# ---------------------------------------------------------------------------
# 2. Проки аффиксов (поле proc, 496 записей) -> skills_flat.jsonl
# ---------------------------------------------------------------------------
proc_total = 0
proc_missing = []
for r in affixes:
    proc = r.get("proc")
    if proc and proc.get("skill"):
        proc_total += 1
        ref = proc["skill"].lower()
        if ref not in skill_records:
            proc_missing.append({
                "affix": r["record"], "skill_ref": proc["skill"], "skill_name": proc.get("skill_name"),
                "exists_in_db": db_exists(proc["skill"]),
            })

status = "ok" if not proc_missing else "mismatch"
add_check(
    "affix_proc_resolve",
    status,
    counts={"total_procs": proc_total, "missing": len(proc_missing)},
    examples=proc_missing,
    note=("494/496 (99.6%) проков резолвятся. 2 промаха — records/skills/itemskills/"
          "componentskills/compb_diamond_{arcanerage,primalrage}.dbr — эти пути НЕ существуют "
          "нигде в gd.sqlite (exists_in_db=False), т.е. это не пробел экстрактора skills, а "
          "мёртвая/legacy-ссылка в самих данных игры (соседняя compb_diamond_prismaticrage.dbr "
          "существует и реальна) — особенность данных, не баг."),
)


# ---------------------------------------------------------------------------
# 5. Компоненты (107, ItemRelic) vs items.jsonl
# ---------------------------------------------------------------------------
comp_missing = []
for cid, c in components.items():
    rec = c["record"].lower()
    if rec not in item_records:
        comp_missing.append({"component": cid, "record": c["record"], "name": c.get("name")})

comp_type_counts = Counter()
for cid, c in components.items():
    comp_type_counts[db_type(c["record"])] += 1

items_summary_types = set(items_summary["counts"]["by_type"].keys())

add_check(
    "components_in_items",
    "mismatch",
    counts={
        "components_total": len(components),
        "missing_from_items_jsonl": len(comp_missing),
        "component_db_types": dict(comp_type_counts),
        "items_jsonl_scope_types_count": len(items_summary_types),
        "itemrelic_in_items_jsonl_scope": "ItemRelic" in items_summary_types,
    },
    examples=comp_missing,
    note=("ВСЕ 107 из 107 компонентов отсутствуют в items.jsonl — но это ожидаемо, а не "
          "провал резолва: сам бриф задания 92 и здравая проверка по коду расходятся с тем, "
          "что реально сделали задания 10 и 40. items.jsonl (задание 10) охватывает СТРОГО 24 "
          "типа надеваемой брони/оружия (см. items_summary.json.counts.by_type) — 'ItemRelic' "
          "туда никогда не входил. Заголовок 40_crafting.py прямым текстом документирует: "
          "'ItemArtifact 103 -> НЕ в этом задании — это gear-реликвии, уже покрыты заданием 10 "
          "(слот relic)', а про ItemRelic (107) явно говорит, что это отдельный домен, целиком "
          "покрытый components.json. Т.е. задание 92 ошиблось в посылке проверки #5 (спутало "
          "'ItemRelic' DB-тип, 107 крафтовых компонентов типа Dread Skull/Amber, с 'ItemArtifact' "
          "— настоящими надеваемыми в слот Relic предметами, 91 шт., которые ДЕЙСТВИТЕЛЬНО есть "
          "в items.jsonl). Компоненты и артефакты — два разных типа в БД с почти одинаковыми "
          "именами не просто случайно: это не баг экстракторов, оба сделали ровно то, что "
          "заявили в своих отчётах. Слоты/статы компонентов сверить с items.jsonl невозможно "
          "в принципе (там таких записей нет) — components.json остаётся единственным источником."),
)


# ---------------------------------------------------------------------------
# 6. Фракции аугментов vs factions.json
# ---------------------------------------------------------------------------
faction_ids = set(factions["factions"].keys())
aug_faction_missing = []
aug_faction_seen = set()
for r in augments:
    fac = r.get("faction")
    if fac:
        aug_faction_seen.add(fac.get("id"))
        if fac.get("id") not in faction_ids:
            aug_faction_missing.append({"augment": r["record"], "faction": fac})

add_check(
    "augment_factions_in_factions_json",
    "ok" if not aug_faction_missing else "mismatch",
    counts={
        "distinct_faction_ids_in_augments": len(aug_faction_seen),
        "missing": len(aug_faction_missing),
        "factions_json_ids_total": len(faction_ids),
    },
    examples=aug_faction_missing,
    note="Полное совпадение — 0 промахов. Оба извлечены из одного и того же picklist-поля myFaction/factionSource, расхождению неоткуда взяться.",
)


# ---------------------------------------------------------------------------
# 7. Сеты: items_summary.json.sets vs записи records/items/lootsets/*.dbr (+ проверка
#    брифа задания 10/30 "7 из 207 потеряно").
# ---------------------------------------------------------------------------
cur = con.execute("SELECT name, type FROM records WHERE name LIKE 'records/items/lootsets/%'")
lootset_names = set()
lootset_types = Counter()
for name, typ in cur.fetchall():
    lootset_names.add(name)
    lootset_types[typ or "(empty)"] += 1

sets = items_summary["sets"]
set_keys = set(k.lower() for k in sets.keys())

matched = lootset_names & set_keys
raw_excluded = sorted(lootset_names - set_keys)
extra_found = sorted(set_keys - lootset_names)

petbonus_excluded = [x for x in raw_excluded if "_petbonus" in x]
placeholder_excluded = [x for x in raw_excluded if x not in petbonus_excluded]

extra_examples = []
for k in extra_found[:10]:
    orig_key = next(kk for kk in sets if kk.lower() == k)
    extra_examples.append({"set": k, "name": sets[orig_key].get("name"), "members": sets[orig_key].get("members")})

add_check(
    "item_sets_vs_lootsets_records",
    "mismatch",
    counts={
        "raw_lootsets_dbr_records": len(lootset_names),
        "items_summary_sets_count": len(sets),
        "matched_under_lootsets_prefix": len(matched),
        "raw_lootsets_excluded": len(raw_excluded),
        "raw_lootsets_excluded_petbonus_variant": len(petbonus_excluded),
        "raw_lootsets_excluded_placeholder": len(placeholder_excluded),
        "extra_sets_found_outside_lootsets_prefix": len(extra_found),
    },
    examples=[{"kind": "raw_excluded_placeholder", "record": x} for x in placeholder_excluded] +
             [{"kind": "raw_excluded_petbonus", "record": x} for x in petbonus_excluded[:3]] +
             extra_examples[:6],
    note=(f"Уточнение брифа заданий 10/30 ('7 из 207 сетов потеряно'): реальная картина точнее и "
          f"МЕНЕЕ тревожная. 207 сырых records/items/lootsets/*.dbr (все type=''), items_summary "
          f"даёт 200. Но это НЕ '207 минус 7 потерянных' — это {len(matched)} прямых совпадений "
          f"под префиксом lootsets/ + {len(extra_found)} сетов, найденных экстрактором СВЕРХ "
          f"lootsets/ (в других путях: records/items/awakened/lootsets/* — 8 сетов дополнения, "
          f"и 1 совершенно отдельный records/storyelements/signs/signset.dbr = 'Lokarr's Spoils', "
          f"настоящий квестовый сет-бонус за собирание знаков). Из {len(raw_excluded)} сырых "
          f"lootsets-записей, которые НЕ попали в items_summary, {len(petbonus_excluded)} — это "
          f"'_petbonus'-варианты (вспомогательные пет-бонусные копии сета, не самостоятельные "
          f"сеты) и {len(placeholder_excluded)} — placeholder-записи (_itemset_blank.dbr, "
          f"_itemset_c000.dbr, _itemset_d000.dbr, ведущее подчёркивание — тот же паттерн "
          f"заглушек, что и в items.jsonl). Все 16 исключений выглядят НАМЕРЕННЫМИ и корректными "
          f"— ни один настоящий игровой сет, похоже, реально не потерян; отчёт заданий 10/30 "
          f"был неточен в формулировке 'потеряно', хотя итоговое число 200 и вывод "
          f"'расхождение есть' верны."),
)


# ---------------------------------------------------------------------------
# 8. Поля статов items.jsonl + affixes.jsonl -> field_schema.json + mechanics.json
# ---------------------------------------------------------------------------
stat_fields = set()
for r in items:
    stat_fields.update((r.get("stats") or {}).keys())
for r in affixes:
    stat_fields.update((r.get("stats") or {}).keys())

missing_schema = sorted(s for s in stat_fields if s not in field_schema)
mech_text = json.dumps(mechanics, ensure_ascii=False)
missing_mech = sorted(s for s in stat_fields if s not in mech_text)

add_check(
    "stat_fields_covered_by_schema_and_mechanics",
    "mismatch" if missing_mech else "ok",
    counts={
        "distinct_stat_fields_items_and_affixes": len(stat_fields),
        "missing_from_field_schema_json": len(missing_schema),
        "not_mentioned_anywhere_in_mechanics_json": len(missing_mech),
    },
    examples=[{"field": f, "in_field_schema": f in field_schema} for f in missing_mech],
    note=("field_schema.json покрывает 328/328 (100%) полей статов, встречающихся в items.jsonl "
          "и affixes.jsonl — как и ожидалось, это авторитетный словарь редактора, почти полный. "
          f"Но mechanics.json НЕ классифицирует {len(missing_mech)}/328 (17%) этих полей ни в "
          "одной из своих таблиц. Это ожидаемое поведение, не баг: mechanics.json сам явно "
          "документирует (schema_coverage_check.note) узкий охват — только 35 вручную отобранных "
          "типов урона/статусов в Offensive/Defensive/Retaliation/Conversion группах, а не "
          "исчерпывающий словарь всех полей (эта роль уже выполняется affixes.jsonl.stat_groups/"
          "categories через прямое обращение к field_schema.json). Пропущенные поля — по "
          "большей части не боевые статы, а служебные (itemCost*, itemStyleTag, dlcRequirement, "
          "hidePrefixName и т.п.), которые mechanics.json и не планировал покрывать."),
)


# ---------------------------------------------------------------------------
# 9. Нерезолвленные имена (name == raw tag / empty) по всем файлам
# ---------------------------------------------------------------------------
def unresolved_name_stats(rows, label, name_field="name", tag_field="name_tag"):
    total = len(rows)
    bad = []
    real_failures = 0
    for r in rows:
        n = r.get(name_field)
        is_bad = n is None or n == "" or (isinstance(n, str) and TAG_RE.match(n))
        if is_bad:
            tag = r.get(tag_field)
            # "реальный провал" = было ЧТО резолвить (тег указан), но не получилось
            # (тег не нашёлся в tags_en.json или сам вернул пустую строку), а не
            # случай "тега не было вовсе" (осознанно безымянная сущность).
            is_real_failure = bool(tag)
            if is_real_failure:
                real_failures += 1
            bad.append({
                "record": r.get("record"), "name": n, "name_tag": tag,
                "real_failure": is_real_failure,
            })
    return total, bad, real_failures


unresolved_examples = []
unresolved_counts = {}
for rows, label in [
    (items, "items.jsonl"), (affixes, "affixes.jsonl"), (skills_flat, "skills_flat.jsonl"),
    (augments, "augments.jsonl"), (recipes, "recipes.jsonl"),
]:
    total, bad, real = unresolved_name_stats(rows, label)
    unresolved_counts[label] = {"total": total, "empty_or_tag_or_null": len(bad), "real_resolve_failures": real}
    for b in bad:
        if b["real_failure"]:
            b2 = dict(b)
            b2["source_file"] = label
            unresolved_examples.append(b2)

total_real_failures = sum(v["real_resolve_failures"] for v in unresolved_counts.values())
add_check(
    "unresolved_or_empty_names",
    "mismatch" if total_real_failures else "ok",
    counts=unresolved_counts,
    examples=unresolved_examples,
    note=("Разделяю 'пусто/None/сырой тег в name' на два разных случая: (1) у сущности "
          "вообще нет name_tag — это осознанно безымянные записи (completion-аффиксы, "
          "MI-мод-скиллы, сырьевые рецепты без витрины) — их большинство (например 1788/7984 "
          "у affixes.jsonl, 161/1135 у skills_flat.jsonl), это НЕ баг; и (2) name_tag "
          f"присутствует, но резолв всё равно не удался — таких {total_real_failures} штук "
          "по всем файлам, это настоящие находки. items.jsonl: 1 (enemygear-запись NPC, "
          "tagTorsoB004 существует в tags_en.json, но резолвится в буквально пустую строку — "
          "минорный краевой случай, вещь не для игрока). augments.jsonl: 5 (records/items/"
          "enchants/*_blank/*000a*.dbr, tag-и вроде tagEnchantB066A нигде не встречаются даже "
          "в tags_en.json — судя по путям ('_blank', паддинг нулями) это неиспользуемые "
          "dev-заглушки, а не пробел резолвера тэгов)."),
)


del items_summary  # больше не нужен

print("=== освобождаем regions/mechanics/field_schema, переходим к loot_tables.json (53 MB) ===")


# ---------------------------------------------------------------------------
# 4. is_mi (items.jsonl) vs mi_items (loot_tables.json, задание 30) — измеряем
#    расхождение эвристики, оно ОЖИДАЕМО (см. задание).
# ---------------------------------------------------------------------------
items_mi = set(r["record"].lower() for r in items if r.get("is_mi"))

t1 = time.time()
loot_tables_raw = load_json("loot_tables.json")
print(f"loot_tables.json загружен за {time.time()-t1:.1f}s")
mi_loot = set(k.lower() for k in loot_tables_raw["mi_items"].keys())
loot_meta = dict(loot_tables_raw["meta"])
del loot_tables_raw
gc.collect()

both = items_mi & mi_loot
only_items = items_mi - mi_loot
only_loot = mi_loot - items_mi

mi_examples = []
for x in sorted(only_loot):
    mi_examples.append({"record": x, "kind": "only_in_loot_tables_mi_items",
                         "in_items_jsonl": x in item_records})
for x in sorted(only_items)[:8]:
    mi_examples.append({"record": x, "kind": "only_in_items_jsonl_is_mi"})

add_check(
    "is_mi_heuristic_vs_task30_mi_items",
    "mismatch",
    counts={
        "items_jsonl_is_mi_true": len(items_mi),
        "loot_tables_mi_items_task30": len(mi_loot),
        "intersection": len(both),
        "only_in_items_jsonl_is_mi": len(only_items),
        "only_in_loot_tables_mi_items": len(only_loot),
    },
    examples=mi_examples,
    note=("Расхождение ожидаемо и предсказано обоими отчётами (10 и 30) — это две РАЗНЫЕ "
          "эвристики. items.jsonl.is_mi: itemClassification=='Rare' + путь не quest/story + "
          "есть валидное имя (широкая эвристика по 'редкости', даёт 2727). loot_tables.json."
          "mi_items (задание 30): узкая структурная эвристика — есть modifierSkillName*, "
          "указывающий на .../skillmodifiers/monsterinfrequents/ или .../skillmodifiers/mi/ "
          f"(даёт 1625, официальное игровое понятие 'Monster Infrequent'). {len(both)}/"
          f"{len(mi_loot)} строгого множества task30 подтверждены и в items.jsonl.is_mi "
          f"(99.9%). Ровно 1 расхождение в обратную сторону — records/items/enemygear/"
          "restlessdeadlooter_sword2h.dbr (itemClassification=Common, визуальное оружие NPC "
          "'wight', ложное срабатывание пути в task30, само задание 30 уже это признало). "
          f"{len(only_items)} записей — это Rare-предметы, помеченные is_mi эвристикой "
          "задания 10, но НЕ являющиеся настоящими MI по структурному определению (просто "
          "рандомные Rare-аффиксные вещи или фракционные редкости) — это ожидаемый шум "
          "широкой эвристики, не баг, но означает, что 'is_mi' в items.jsonl категорически "
          "нельзя использовать как точный список настоящих Monster Infrequent для билд-калькулятора."),
)
del loot_meta
gc.collect()


# ---------------------------------------------------------------------------
# 3. Предметы в дропе: drop_sources.jsonl (174 MB, СТРОГО построчно) -> items.jsonl
# ---------------------------------------------------------------------------
print("=== 92_crossval: потоковый проход drop_sources.jsonl (174 MB) ===")
t2 = time.time()
drop_total = 0
orphans_by_cat = defaultdict(list)
orphan_cat_totals = Counter()
orphan_count = 0
orphan_distinct = set()
with open(out_path("drop_sources.jsonl"), encoding="utf-8") as f:
    for line in f:
        line = line.strip()
        if not line:
            continue
        drop_total += 1
        r = json.loads(line)
        item = (r.get("item") or "").lower()
        if item and item not in item_records:
            orphan_count += 1
            orphan_distinct.add(item)
            parts = item.split("/")
            cat = parts[2] if len(parts) >= 3 else "<short>"
            orphan_cat_totals[cat] += 1
            if len(orphans_by_cat[cat]) < 5:
                orphans_by_cat[cat].append({
                    "item": r.get("item"), "item_name": r.get("item_name"),
                    "source_name": r.get("source_name"), "source_kind": r.get("source_kind"),
                    "exists_in_db": db_exists(item),
                })
print(f"drop_sources.jsonl обработан за {time.time()-t2:.1f}s, строк: {drop_total}")

orphan_examples = []
for cat, exs in orphans_by_cat.items():
    for e in exs:
        e2 = dict(e)
        e2["category"] = cat
        orphan_examples.append(e2)

add_check(
    "drop_sources_items_in_items_jsonl",
    "mismatch" if orphan_count else "ok",
    counts={
        "drop_sources_total_lines": drop_total,
        "orphan_lines": orphan_count,
        "orphan_lines_pct": round(100 * orphan_count / drop_total, 3) if drop_total else 0,
        "orphan_distinct_items": len(orphan_distinct),
        "orphan_category_counts": dict(orphan_cat_totals),
    },
    examples=orphan_examples,
    note=("137/117871 (0.12%) строк drop_sources.jsonl ссылаются на 'item', которого нет в "
          "items.jsonl — очень небольшая доля, но не ноль, и причины РАЗНЫЕ, не одна: "
          "(1) 'records/item/loottables/...' и 'records/xpack/item/loottables/...' — "
          "мёртвые пути к мастер-таблицам, которых нет в БД вообще (db_exists=False) — легаси-"
          "ссылки в самих .dbr игры, задание 30 уже фиксировало 255-256 таких нерезолвленных "
          "путей в целом, но не упомянуло, что часть из них всё же просачивается в "
          "drop_sources.jsonl как 'item' с item_name=null, а не отбрасывается молча, как "
          "утверждает отчёт 30 ('дают пустой список') — маленькое расхождение с собственным "
          "отчётом задания 30; (2) records/items/loreobjects/*, records/items/questitems/* — "
          "лорные книги и квестовые предметы, вне заявленного домена items.jsonl (не "
          "экипировка) — ожидаемо; (3) records/items/crafting/consumables/*, records/"
          "endlessdungeon/items/* (OneShot_EndlessDungeon) — расходники/спецпредметы, тоже вне "
          "24 типов items.jsonl — ожидаемо; (4) records/sandbox/jakub/test_sword.dbr — dev-"
          "заглушка (тэг tagWeaponSwordA000='Shiv'), корректно исключённая из items.jsonl "
          "(203 debug_sandbox), но при этом РЕАЛЬНО подключенная в живую лут-таблицу монстра "
          "в drop_sources.jsonl — т.е. drop_sources.jsonl вскрыл, что боевая лут-таблица "
          "действительно ссылается на sandbox-мусор (баг/недосмотр разработчиков игры, не "
          "экстрактора); (5) records/items/gearaccessories/medals/b3000_medal.dbr — "
          "'BASE BLANK MEDAL' (FileDescription), корректно отфильтрован items.jsonl как "
          "placeholder, но у него есть настоящее имя через тэг ('Mark of Nerf') и реальный "
          "источник в drop_sources.jsonl — похоже на медаль, которую разработчики 'занулили' "
          "(нерфнули), не убрав из лут-таблиц — данные игры, не баг экстрактора."),
)


# ---------------------------------------------------------------------------
# 10. Очки девоушена: 55 (devotions.json/mechanics.json) vs 62 святилища (regions.json)
# ---------------------------------------------------------------------------
max_points = devotions["meta"]["max_devotion_points"]
shrines = regions["world_map"]["shrines"]
riftgates_n = regions["world_map"].get("riftgates")
n_shrines = len(shrines)
ruined = sum(1 for s in shrines if s.get("ruined"))
corrupted = sum(1 for s in shrines if s.get("corrupted"))
no_flag = [s for s in shrines if not s.get("ruined") and not s.get("corrupted")]
quest_named = [s for s in shrines if "quest" in (s.get("name") or "").lower()]
no_chapter = [s for s in shrines if "chapter" not in s]

add_check(
    "devotion_points_arithmetic",
    "mismatch",
    counts={
        "max_devotion_points": max_points,
        "world_map_shrines_total": n_shrines,
        "shrines_flag_ruined": ruined,
        "shrines_flag_corrupted": corrupted,
        "shrines_no_ruined_or_corrupted_flag": len(no_flag),
        "shrines_named_quest_shrine": len(quest_named),
        "shrines_missing_chapter_field": len(no_chapter),
        "arithmetic_gap_shrines_minus_max_points": n_shrines - max_points,
    },
    examples=[{"record": s["record"], "name": s.get("name"), "flags":
               {k: s[k] for k in ("ruined", "corrupted") if k in s}} for s in quest_named + no_chapter + no_flag[:5]],
    note=("Арифметика НЕ бьётся, и оба задания (21_devotions, 31_levels) сами честно писали, "
          "что не смогли восстановить разбивку 'святилище vs квест' из статических .dbr — "
          "подтверждаю это тем же выводом, но добавляю конкретику. Разрыв: "
          f"{n_shrines} записей world_map.shrines vs {max_points} максимум очков девоушена — "
          f"разница {n_shrines - max_points}. Если бы каждое святилище давало ровно 1 очко "
          "(так работает в игре), 62 святилища дали бы больше очков, чем максимум персонажа "
          "— значит либо не все 62 записи являются 'обычными' исследуемыми святилищами на "
          "карте, либо часть очков перекрывается/не аддитивна. Нашёл косвенное "
          "подтверждение первой гипотезы: 1 запись прямо называется 'Quest Shrine - Rover "
          "Legacy' (records/ui/riftgatemap/devotionshrines/riftgatemapmogdrogen_shrine.dbr) — "
          "т.е. это НЕ точка на карте, а квестовая награда, ошибочно попавшая в тот же "
          "список 'shrines', что и обычные исследуемые святилища (и у неё же отсутствует поле "
          "'chapter', которое есть у всех 61 остальных — тоже сигнал, что она структурно "
          "другая). Флаги ruined/corrupted оказались бесполезны для гипотезы 'дубликаты одного "
          "физического святilища до/после квеста реставрации' — они стоят почти на всех "
          "61 обычных записях (24 ruined + 37 corrupted), это, похоже, просто лорный "
          "визуальный статус, а не признак дублирования. Итог: подтверждаю находку "
          "('арифметика не сходится'), уточняю на один конкретный артефакт данных (Quest "
          "Shrine затесался в shrines), но полную формулу 'сколько от святилищ, сколько от "
          "квестов' восстановить из статических данных пайплайна невозможно — это требует "
          ".qst-файлов квестов, которые ни один из 8 экстракторов не парсит (прямым текстом "
          "написано в отчёте 50_mechanics.md, п.3)."),
)


# ---------------------------------------------------------------------------
# Итог
# ---------------------------------------------------------------------------
n_ok = sum(1 for c in checks if c["status"] == "ok")
n_mismatch = sum(1 for c in checks if c["status"] == "mismatch")
n_error = sum(1 for c in checks if c["status"] == "error")
print(f"\n=== ИТОГО: {len(checks)} проверок, ok={n_ok}, mismatch={n_mismatch}, error={n_error} ===")

path, size = write_json("crossval.json", {
    "meta": {
        "generated_by": "docs/grim-dawn/extract/92_crossval.py",
        "checks_total": len(checks), "ok": n_ok, "mismatch": n_mismatch, "error": n_error,
    },
    "checks": checks,
}, indent=1)
print(f"Записано: {path} ({size} байт)")
