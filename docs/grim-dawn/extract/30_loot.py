# -*- coding: utf-8 -*-
"""Задание 30 — Лут-таблицы и источники дропа.

Отвечает на вопрос "с кого фармить предмет X" и обратный "что падает с монстра Y".

Источники в БД (см. TASKS/30_loot.md и разведку в отчёте REPORTS/30_loot.md):

  LootMasterTable          lootNameN / lootWeightN  -> взвешенный список детей
  LootItemTable_DynWeight  lootNameN / lootWeightN  -> взвешенный список детей
                           (те же имена полей, что и у LootMasterTable — один
                           и тот же механизм "вес / сумма весов").
  LevelTable               levels[] / records[]     -> НЕ вероятность, а выбор
                           по диапазону уровня персонажа/монстра (i-я запись
                           действует для уровня [levels[i], levels[i+1]-1]).
  "fixeditemloot" записи   loot{N}Name{M}/loot{N}Weight{M}/loot{N}Chance[]
                           (нашёл только по шаблону полей — у них Class/type
                           пустой в БД) — несколько слотов, в каждом свой
                           взвешенный список + сырой массив chance (‰), смысл
                           индексов массива не расшифровывал (см. отчёт).
  Monster                  loot<Slot>ItemN / chanceToEquip<Slot>ItemN(/чистый
                           chanceToEquip<Slot>) — тот же паттерн "вес/сумма"
                           на верхнем уровне (какая из N таблиц слота
                           используется), плюс отдельный "триггер-шанс" слота.
  FixedItemContainer       lootTable (строка или список вариантов без веса —
                           trактую как варианты, не как случайный выбор).

Все 4 вида узлов сведены к одному рекурсивному resolve() с memoization и
защитой от циклов, который разворачивает цепочку до конечных предметов.

"chance_hint" считается ТОЛЬКО как произведение (weight/weight_sum) по хопам
вида "weighted" — то есть условная вероятность выбора предмета внутри уже
запущенного участка таблиц. Он НЕ включает: chanceToEquip<Slot> (шанс, что
слот вообще бросает предмет), уровневые ветки (это не случайность, а жёсткий
выбор по уровню) и "варианты" FixedItemContainer.lootTable (нет данных о их
весах). Подробности и качественные ограничения — в отчёте.
"""
import json
import re
from collections import Counter

from gdlib import Tags, open_sqlite, write_json, write_jsonl, norm

MAX_DEPTH = 20

# Многие "Misc"/"LeftHand" и т.п. слоты монстров (и часть слотов сундуков)
# ссылаются на ОБЩИЕ каталоги на сотни-тысячи записей (напр. mt_hu_miscall_a01
# -> 989 листьев, mt_hu_miscall_c01 -> 3167, mt_geararmorhead_c01 -> 217) --
# это переиспользуемые пулы крафт-компонентов/случайной брони, а не что-то,
# специфичное для конкретного монстра. Разворачивать их пословно для КАЖДОГО
# монстра, который на них ссылается (таких тысячи), даёт десятки миллионов
# строк и памяти на порядки больше разумного. Поэтому: если пул с конкретной
# ветки >GENERIC_POOL_CAP листьев, построчно в drop_sources.jsonl не
# разворачиваем (сама таблица всё равно целиком лежит в loot_tables.json) --
# КРОМЕ предметов, отмеченных как MI (их нужно найти всегда, вне зависимости
# от размера пула, это отдельное явное требование задания).
GENERIC_POOL_CAP = 60

# Типы записей, которые встречаются как "листья" лут-таблиц, но не являются
# снаряжением/предметом, который игрок реально "фармит" (материалы крафта,
# чертежи-формулы, квестовые предметы, разовые свитки/еда/грамоты фракций).
# Замечено эмпирически при разведке (см. отчёт): именно они дают основную
# массу строк на слотах Misc1/2/3 (~90% строк там -- ItemRelic, т.е. компонент
# крафта). Исключаем их из "общего" среза (не-MI), не теряя MI (MI ими не
# бывают по построению -- see MI_MODIFIER_RE) и не трогая loot_tables.json,
# где вся сырая таблица остаётся как есть.
NON_GEAR_ITEM_TYPES = {
    "ItemRelic", "ItemArtifactFormula", "QuestItem", "OneShot_Scroll",
    "ItemNote", "ItemFactionWarrant", "ItemDifficultyUnlock",
    "OneShot_SkillUnlock", "OneShot_Food",
}

# Подтверждено словарём полей (field_schema.json, поле сгенерировано из шаблонов
# редактора игры): loot<Slot>ItemN у Monster, loot{N}Name{M} у "fixeditemloot" и
# lootTable у FixedItemContainer помечены как class=array, description="Index by
# game mode" (для lootTable/levelOffset шаблона lootcontainer явно указано "Normal,
# Epic, Ultimate"). Это НЕ дополнительные взвешенные альтернативы, а детерминированный
# выбор по игровому режиму/сложности -- в chance_hint не входит.
DIFF_LABELS = ["Normal", "Epic", "Ultimate"]


def diff_label(i):
    return DIFF_LABELS[i] if i < len(DIFF_LABELS) else str(i)


def expand_diff(value):
    """str -> [(None, path)] (одно и то же на все сложности);
    list -> [(0, path0), (1, path1), ...] (index by game mode)."""
    if isinstance(value, list):
        return [(i, norm(v)) for i, v in enumerate(value) if isinstance(v, str) and v]
    if isinstance(value, str) and value:
        return [(None, norm(value))]
    return []

SLOTS = ["Head", "Shoulders", "Chest", "Hands", "Legs", "Feet",
         "LeftHand", "RightHand", "Finger1", "Finger2",
         "Misc1", "Misc2", "Misc3"]

WEIGHTED_TYPES = {"LootMasterTable", "LootItemTable_DynWeight"}

NAME_RE = re.compile(r"^lootName(\d+)$")
WEIGHT_RE = re.compile(r"^lootWeight(\d+)$")
FIXED_NAME_RE = re.compile(r"^loot(\d+)Name(\d+)$")
FIXED_WEIGHT_RE = re.compile(r"^loot(\d+)Weight(\d+)$")
FIXED_CHANCE_RE = re.compile(r"^loot(\d+)Chance$")
MI_MODIFIER_RE = re.compile(r"/skillmodifiers/(monsterinfrequents|mi)/")


def as_list(v):
    if v is None:
        return []
    return v if isinstance(v, list) else [v]


def to_float(v, default=0.0):
    try:
        return float(v)
    except (TypeError, ValueError):
        return default


def parse_weighted_list(f):
    """LootMasterTable / LootItemTable_DynWeight: lootNameN/lootWeightN -> [(child, weight)]."""
    names, weights = {}, {}
    for k, v in f.items():
        m = NAME_RE.match(k)
        if m:
            names[int(m.group(1))] = v
            continue
        m = WEIGHT_RE.match(k)
        if m:
            weights[int(m.group(1))] = to_float(v)
    out = []
    for idx, name in names.items():
        w = weights.get(idx, 0.0)
        if w <= 0:
            continue  # правило "нули не пиши"
        for nm in as_list(name):
            if isinstance(nm, str) and nm not in ("", "0"):
                out.append((norm(nm), w))
    return out


def parse_level_table(f):
    """LevelTable: levels[]/records[] -> [(lo, hi_or_None, child)], по возрастанию уровня."""
    levels = as_list(f.get("levels"))
    recs = as_list(f.get("records"))
    pairs = [(lv, rec) for lv, rec in zip(levels, recs) if isinstance(rec, str) and rec]
    pairs.sort(key=lambda p: p[0])
    out = []
    for i, (lo, rec) in enumerate(pairs):
        hi = pairs[i + 1][0] - 1 if i + 1 < len(pairs) else None
        out.append((lo, hi, norm(rec)))
    return out


def parse_fixed_loot(f):
    """"fixeditemloot"-подобная запись -> {slot_id: {"chance_permille": [...], "children": [(child,weight)]}}."""
    slots = {}
    chances = {}
    for k, v in f.items():
        m = FIXED_CHANCE_RE.match(k)
        if m:
            chances[int(m.group(1))] = as_list(v)
    names = {}   # slot -> {idx: name}
    weights = {}  # slot -> {idx: weight}
    for k, v in f.items():
        m = FIXED_NAME_RE.match(k)
        if m:
            s, i = int(m.group(1)), int(m.group(2))
            names.setdefault(s, {})[i] = v
            continue
        m = FIXED_WEIGHT_RE.match(k)
        if m:
            s, i = int(m.group(1)), int(m.group(2))
            weights.setdefault(s, {})[i] = to_float(v)
    for s, idx_names in names.items():
        w_map = weights.get(s, {})
        children = []
        for idx, name in idx_names.items():
            w = w_map.get(idx, 0.0)
            if w <= 0:
                continue
            # name может быть строкой ИЛИ списком (class=array, "Index by game
            # mode" -- см. field_schema.json loot1Name1). Сохраняем сырьём,
            # weight относится к ЦЕЛОМУ индексу idx, а не к каждому элементу
            # массива -- разворачивание по сложности делает resolve().
            children.append({"value": name, "weight": w})
        if children:
            slots[f"loot{s}"] = {"chance_permille": chances.get(s, []), "children": children}
    return slots


def main():
    con = open_sqlite(readonly=True)
    tags = Tags()

    # ---- индекс имя->тип (дёшево: без fields) ----
    type_of = {}
    for name, typ in con.execute("SELECT name, type FROM records"):
        type_of[name] = typ

    # ---- графы таблиц ----
    weighted_graph = {}   # path -> [(child, weight)]
    level_graph = {}      # path -> [(lo, hi, child)]
    fixed_graph = {}      # path -> {slot: {...}}
    fixed_node_names = set()

    table_types_seen = Counter()
    unresolved_children = Counter()  # child path -> сколько раз встретился, но не найден в БД

    for typ in ("LootMasterTable", "LootItemTable_DynWeight"):
        for name, fields in con.execute("SELECT name, fields FROM records WHERE type=?", (typ,)):
            f = json.loads(fields)
            children = parse_weighted_list(f)
            weighted_graph[name] = children
            table_types_seen[typ] += 1
            for child, _w in children:
                if child not in type_of:
                    unresolved_children[child] += 1

    for name, fields in con.execute("SELECT name, fields FROM records WHERE type=?", ("LevelTable",)):
        f = json.loads(fields)
        brackets = parse_level_table(f)
        level_graph[name] = brackets
        table_types_seen["LevelTable"] += 1
        for _lo, _hi, child in brackets:
            if child not in type_of:
                unresolved_children[child] += 1

    # "fixeditemloot"-подобные записи: Class/type у них пустой, ищем по паттерну полей.
    for name, fields in con.execute("SELECT name, fields FROM records"):
        if not re.search(r"loot\dName\d", fields):
            continue
        f = json.loads(fields)
        if not any(FIXED_NAME_RE.match(k) for k in f):
            continue
        slots = parse_fixed_loot(f)
        if slots:
            fixed_graph[name] = slots
            fixed_node_names.add(name)
            table_types_seen["fixeditemloot(no Class)"] += 1
            for slot in slots.values():
                for entry in slot["children"]:
                    for _diff_idx, child in expand_diff(entry["value"]):
                        if child not in type_of:
                            unresolved_children[child] += 1

    def node_kind(path):
        t = type_of.get(path)
        if t in WEIGHTED_TYPES:
            return "weighted"
        if t == "LevelTable":
            return "level"
        if path in fixed_node_names:
            return "fixed"
        return "leaf"

    # ---- рекурсивный резолвер с memo + защитой от циклов ----
    memo = {}
    in_progress = set()
    stats = Counter()

    def resolve(path, depth=0):
        if path in memo:
            return memo[path]
        if path in in_progress:
            stats["cycles"] += 1
            return []
        if depth > MAX_DEPTH:
            stats["depth_exceeded"] += 1
            return []
        kind = node_kind(path)
        if kind == "leaf":
            return [{"item": path, "hops": []}]

        in_progress.add(path)
        out = []

        if kind == "weighted":
            children = weighted_graph.get(path, [])
            total = sum(w for _c, w in children)
            for child, w in children:
                hop = {"table": path, "kind": "weighted", "weight": w, "weight_sum": total}
                for sub in resolve(child, depth + 1):
                    out.append({"item": sub["item"], "hops": [hop] + sub["hops"]})

        elif kind == "level":
            for lo, hi, child in level_graph.get(path, []):
                hop = {"table": path, "kind": "level", "level_bracket": [lo, hi]}
                for sub in resolve(child, depth + 1):
                    out.append({"item": sub["item"], "hops": [hop] + sub["hops"]})

        elif kind == "fixed":
            for slot_id, slot in fixed_graph.get(path, {}).items():
                entries = slot["children"]
                total = sum(e["weight"] for e in entries)
                for e in entries:
                    w = e["weight"]
                    base_hop = {"table": path, "kind": "weighted", "slot": slot_id,
                                "weight": w, "weight_sum": total,
                                "chance_permille_raw": slot["chance_permille"]}
                    for diff_idx, child in expand_diff(e["value"]):
                        hops = [base_hop]
                        if diff_idx is not None:
                            hops.append({"table": path, "kind": "difficulty", "slot": slot_id,
                                         "difficulty_index": diff_idx,
                                         "difficulty_label": diff_label(diff_idx)})
                        for sub in resolve(child, depth + 1):
                            out.append({"item": sub["item"], "hops": hops + sub["hops"]})

        in_progress.discard(path)
        memo[path] = out
        return out

    def chain_summary(hops):
        chain = [h["table"] for h in hops]
        kinds = [h["kind"] for h in hops]
        level_bracket = None
        difficulty = None
        for h in hops:
            if h["kind"] == "level":
                level_bracket = h["level_bracket"]
            if h["kind"] == "difficulty":
                difficulty = h["difficulty_label"]
        if hops and all(h["kind"] == "weighted" for h in hops):
            prod = 1.0
            ok = True
            for h in hops:
                if h["weight_sum"] <= 0:
                    ok = False
                    break
                prod *= h["weight"] / h["weight_sum"]
            chance_hint = prod if ok else None
        else:
            chance_hint = None
        last_weighted = next((h for h in reversed(hops) if h["kind"] == "weighted"), None)
        weight = last_weighted["weight"] if last_weighted else None
        weight_sum = last_weighted["weight_sum"] if last_weighted else None
        return chain, kinds, level_bracket, difficulty, chance_hint, weight, weight_sum

    # ---- предметы: имя, itemClassification, признак MI ----
    item_cache = {}

    def get_item_info(path):
        if path in item_cache:
            return item_cache[path]
        row = con.execute("SELECT type, fields FROM records WHERE name=?", (path,)).fetchone()
        if row is None:
            info = {"name": None, "type": None, "classification": None, "is_mi": False}
            item_cache[path] = info
            return info
        typ, fields = row
        f = json.loads(fields)
        is_mi = False
        for k, v in f.items():
            if not k.startswith("modifierSkillName"):
                continue
            for val in as_list(v):
                if isinstance(val, str) and MI_MODIFIER_RE.search(norm(val)):
                    is_mi = True
        name = tags.item_name(f)
        info = {
            "name": name,
            "name_tag": f.get("itemNameTag"),
            "type": typ,
            "classification": f.get("itemClassification"),
            "item_level": f.get("itemLevel"),
            "is_mi": is_mi,
        }
        item_cache[path] = info
        return info

    # Огромные общие пулы (mt_hu_miscall_* и т.п., сотни-тысячи листьев)
    # переиспользуются тысячами монстров. Раз таблица одна и та же для всех
    # вызывающих, достаточно один раз найти в ней MI-листья и закэшировать --
    # иначе пришлось бы пере-сканировать тысячи записей на каждого монстра.
    mi_subset_cache = {}

    def mi_subset(table_path):
        cached = mi_subset_cache.get(table_path)
        if cached is None:
            cached = [res for res in resolve(table_path) if get_item_info(res["item"])["is_mi"]]
            mi_subset_cache[table_path] = cached
        return cached

    # ================= MONSTERS =================
    monsters_out = {}
    monster_rows = list(con.execute(
        "SELECT name, fields FROM records WHERE type='Monster'"))
    print(f"Monster records: {len(monster_rows)}")

    drop_rows = []
    mi_sources = {}  # item_path -> list of source dicts (monster or chest)

    n_mon_processed = 0
    n_mon_no_loot = 0
    unknown_classification = Counter()

    for name, fields in monster_rows:
        f = json.loads(fields)
        n_mon_processed += 1

        classification_raw = f.get("monsterClassification")
        cls_parts = set()
        if isinstance(classification_raw, str):
            cls_parts = {p for p in classification_raw.split(";") if p}
        is_hero = "Hero" in cls_parts
        is_champion = "Champion" in cls_parts
        is_boss = "Boss" in cls_parts
        is_superboss = "SuperBoss" in cls_parts
        is_quest = "Quest" in cls_parts
        is_common = "Common" in cls_parts
        if not cls_parts:
            unknown_classification[classification_raw] += 1

        is_nemesis = "/nemesis/" in name
        is_sandbox = name.startswith("records/sandbox/")

        faction_path = f.get("factions")
        faction_name = None
        if isinstance(faction_path, str):
            frow = con.execute("SELECT fields FROM records WHERE name=?", (norm(faction_path),)).fetchone()
            if frow:
                try:
                    faction_name = json.loads(frow[0]).get("myFaction")
                except (TypeError, ValueError, json.JSONDecodeError):
                    faction_name = None

        mon_name = tags.item_name(f) or tags(f.get("description")) if f.get("description") else None
        mon_name = tags(f.get("description")) if f.get("description") else f.get("FileDescription")

        monster_slots = {}
        for slot in SLOTS:
            pct = f.get(f"chanceToEquip{slot}")
            candidates = []
            for i in range(1, 8):
                nm = f.get(f"loot{slot}Item{i}")
                w = f.get(f"chanceToEquip{slot}Item{i}")
                if nm and w:
                    w = to_float(w)
                    if w > 0:
                        # nm может быть строкой ИЛИ списком (class=array, "Index
                        # by game mode", подтверждено field_schema.json) --
                        # сохраняем сырьём, вес относится к целому индексу i,
                        # разворот по сложности делает expand_diff() ниже.
                        candidates.append({"value": nm, "weight": w})
            if candidates:
                monster_slots[slot] = {"trigger_pct": pct, "candidates": candidates}

        if not monster_slots:
            n_mon_no_loot += 1

        monsters_out[name] = {
            "record": name,
            "name": mon_name,
            "description_tag": f.get("description"),
            "level_min": f.get("minLevel"),
            "level_max": f.get("maxLevel"),
            "char_level_formula": f.get("charLevel"),
            "monster_classification": classification_raw,
            "is_hero": is_hero, "is_champion": is_champion, "is_boss": is_boss,
            "is_superboss": is_superboss, "is_quest": is_quest, "is_common": is_common,
            "is_nemesis": is_nemesis, "is_sandbox": is_sandbox,
            "faction": faction_name,
            "gold_generator": f.get("goldGenerator"),
            "slots": {s: {"trigger_pct": d["trigger_pct"],
                          "candidates": [{"value": c["value"], "weight": c["weight"]} for c in d["candidates"]]}
                      for s, d in monster_slots.items()},
        }

        include_generic = not is_common  # общие "Common" мобы не разворачиваем построчно (см. отчёт)

        for slot, data in monster_slots.items():
            total = sum(c["weight"] for c in data["candidates"])
            for cand in data["candidates"]:
                w = cand["weight"]
                base_hop = {"table": name, "kind": "weighted", "slot": slot, "weight": w, "weight_sum": total}
                for diff_idx, table in expand_diff(cand["value"]):
                    top_hops = [base_hop]
                    if diff_idx is not None:
                        top_hops.append({"table": name, "kind": "difficulty", "slot": slot,
                                          "difficulty_index": diff_idx, "difficulty_label": diff_label(diff_idx)})
                    res_list = resolve(table)
                    allow_generic = include_generic and len(res_list) <= GENERIC_POOL_CAP
                    # Большой общий пул и монстр не MI-фильтруется целиком -- не
                    # проходим по тысячам листьев, а берём только предвычисленный
                    # MI-срез (см. mi_subset выше).
                    iterate_list = res_list if allow_generic else mi_subset(table)
                    for res in iterate_list:
                        hops = top_hops + res["hops"]
                        item = res["item"]
                        info = get_item_info(item)
                        if info["is_mi"]:
                            pass
                        elif not allow_generic or info["type"] in NON_GEAR_ITEM_TYPES:
                            continue
                        chain, kinds, level_bracket, difficulty, chance_hint, weight, weight_sum = chain_summary(hops)
                        row = {
                            "item": item, "item_name": info["name"], "item_is_mi": info["is_mi"],
                            "source": name, "source_name": mon_name, "source_kind": "monster",
                            "slot": slot,
                            "path": chain, "chain_kinds": kinds,
                            "weight": weight, "weight_sum": weight_sum,
                            "chance_hint": chance_hint, "level_bracket": level_bracket,
                            "difficulty": difficulty,
                            "slot_trigger_pct": data["trigger_pct"],
                            "monster_level_min": f.get("minLevel"), "monster_level_max": f.get("maxLevel"),
                            "monster_classification": classification_raw,
                            "is_hero": is_hero, "is_champion": is_champion, "is_boss": is_boss,
                            "is_superboss": is_superboss, "is_nemesis": is_nemesis,
                            "faction": faction_name,
                        }
                        drop_rows.append(row)
                        if info["is_mi"]:
                            mi_sources.setdefault(item, []).append({
                                "source": name, "source_name": mon_name, "source_kind": "monster",
                                "slot": slot, "difficulty": difficulty, "chance_hint": chance_hint,
                            })

    print(f"Monsters processed: {n_mon_processed}, without any loot slot: {n_mon_no_loot}")
    print("Classification breakdown (raw field values w/o recognized keyword):", dict(unknown_classification))

    # ================= FIXED ITEM CONTAINERS (chests) =================
    chest_rows = list(con.execute(
        "SELECT name, fields FROM records WHERE type='FixedItemContainer'"))
    print(f"FixedItemContainer records: {len(chest_rows)}")

    chests_out = {}
    n_chest_no_loot = 0
    # 644 записи FixedItemContainer резолвятся всего в 130 РАЗНЫХ комбинаций
    # lootTable-вариантов -- одна и та же таблица лута расставлена по десяткам
    # похожих сундуков в разных зонах. Полное разворачивание по всем 644 дало бы
    # ~330k однотипных строк; группируем по сигнатуре вариантов и считаем один раз,
    # а все имена-дубликаты сохраняем в source_group_members (полный список
    # каждого отдельного контейнера остаётся в chests_out, не теряется).
    variant_groups = {}

    for name, fields in chest_rows:
        f = json.loads(fields)
        chest_name = tags(f.get("description")) if f.get("description") else f.get("FileDescription")
        loot_table = f.get("lootTable")
        variants = [norm(v) for v in as_list(loot_table) if isinstance(v, str) and v]

        chests_out[name] = {
            "record": name,
            "name": chest_name,
            "description_tag": f.get("description"),
            "loot_classification": f.get("lootClassification"),
            "level_min": f.get("minLevel"), "level_max": f.get("maxLevel"),
            "level_offset": f.get("levelOffset"),
            "gold_generator": f.get("goldGenerator"),
            "fixed_item": f.get("perPartyMemberDropItemName"),
            "loot_table_variants": variants,
        }

        if not variants and not f.get("perPartyMemberDropItemName"):
            n_chest_no_loot += 1

        if variants:
            grp = variant_groups.setdefault(tuple(variants), {"members": [], "rep_name": None, "rep_f": None})
            grp["members"].append(name)
            if grp["rep_name"] is None:
                grp["rep_name"] = name
                grp["rep_f"] = f

        # гарантированный фиксированный предмет (не рандом, отдельная механика,
        # как правило уникальна для конкретного контейнера/лора -- НЕ группируем)
        fixed_item = f.get("perPartyMemberDropItemName")
        if isinstance(fixed_item, str) and fixed_item:
            item = norm(fixed_item)
            info = get_item_info(item)
            row = {
                "item": item, "item_name": info["name"], "item_is_mi": info["is_mi"],
                "source": name, "source_name": chest_name, "source_kind": "chest",
                "slot": "perPartyMemberDropItemName",
                "path": [name], "chain_kinds": ["fixed_guaranteed"],
                "weight": None, "weight_sum": None,
                "chance_hint": 1.0, "level_bracket": None,
                "chest_classification": f.get("lootClassification"),
                "chest_level_min": f.get("minLevel"), "chest_level_max": f.get("maxLevel"),
                "chest_level_offset": f.get("levelOffset"),
            }
            drop_rows.append(row)

    print(f"Chests processed: {len(chest_rows)}, without any loot table/fixed item: {n_chest_no_loot}")
    print(f"Distinct chest lootTable-сигнатур: {len(variant_groups)}")

    # lootTable -- class=array "Index by game mode" (см. levelOffset того же
    # шаблона lootcontainer: "Normal, Epic, Ultimate"). Это НЕ взвешенные
    # альтернативы -- каждый элемент действует в своей сложности.
    for variants, grp in variant_groups.items():
        name = grp["rep_name"]
        f = grp["rep_f"]
        members = grp["members"]
        chest_name = tags(f.get("description")) if f.get("description") else f.get("FileDescription")
        for vi, table in enumerate(variants):
            top_hop = {"table": name, "kind": "difficulty", "difficulty_index": vi,
                       "difficulty_label": diff_label(vi)}
            res_list = resolve(table)
            allow_generic = len(res_list) <= GENERIC_POOL_CAP
            iterate_list = res_list if allow_generic else mi_subset(table)
            for res in iterate_list:
                hops = [top_hop] + res["hops"]
                item = res["item"]
                info = get_item_info(item)
                if info["is_mi"]:
                    pass
                elif not allow_generic or info["type"] in NON_GEAR_ITEM_TYPES:
                    continue
                chain, kinds, level_bracket, difficulty, chance_hint, weight, weight_sum = chain_summary(hops)
                row = {
                    "item": item, "item_name": info["name"], "item_is_mi": info["is_mi"],
                    "source": name, "source_name": chest_name, "source_kind": "chest",
                    "source_group_size": len(members),
                    "slot": f"lootTable[{vi}]",
                    "path": chain, "chain_kinds": kinds,
                    "weight": weight, "weight_sum": weight_sum,
                    "chance_hint": chance_hint, "level_bracket": level_bracket,
                    "difficulty": difficulty,
                    "chest_classification": f.get("lootClassification"),
                    "chest_level_min": f.get("minLevel"), "chest_level_max": f.get("maxLevel"),
                    "chest_level_offset": f.get("levelOffset"),
                }
                drop_rows.append(row)
                if info["is_mi"]:
                    mi_sources.setdefault(item, []).append({
                        "source": name, "source_name": chest_name, "source_kind": "chest",
                        "source_group_size": len(members),
                        "slot": f"lootTable[{vi}]", "difficulty": difficulty, "chance_hint": chance_hint,
                    })

    # Полный список контейнеров на каждую сигнатуру -- отдельно, чтобы не
    # дублировать список из десятков имён в КАЖДОЙ строке drop_sources.jsonl.
    chest_signature_groups = [
        {"representative": grp["rep_name"], "variants": list(variants), "members": grp["members"]}
        for variants, grp in variant_groups.items()
    ]

    # ================= MI items summary (mi_items) =================
    mi_all = {}
    for path, info in item_cache.items():
        if info["is_mi"]:
            mi_all[path] = info

    def dedupe_sources(sources):
        # тот же предмет иногда достижим несколькими путями из ОДНОГО и того же
        # источника (два разных под-раздела общего пула и т.п.) -- это одна и та
        # же практическая находка "падает с X", схлопываем по (source, slot).
        seen = {}
        for s in sources:
            key = (s["source"], s.get("slot"), s.get("difficulty"))
            if key not in seen:
                seen[key] = s
        return list(seen.values())

    mi_items_out = {}
    for item, info in mi_all.items():
        mi_items_out[item] = {
            "record": item,
            "name": info["name"],
            "name_tag": info["name_tag"],
            "item_type": info["type"],
            "item_level": info["item_level"],
            "sources": dedupe_sources(mi_sources.get(item, [])),
        }
    mi_no_source = sum(1 for v in mi_items_out.values() if not v["sources"])

    print(f"MI items found (by modifierSkillName path signature): {len(mi_items_out)}")
    print(f"MI items with NO resolved drop source in our graph: {mi_no_source}")

    # ---- финальное слияние строк drop_sources: один и тот же (item, source)
    # часто достижим несколькими путями -- через разные слоты монстра, разные
    # сложности (Normal/Epic/Ultimate), разные ветки LevelTable. Отдельная
    # строка на каждый такой путь распухает файл (в разы) без новой сути:
    # ответ на "выпадает ли X с Y" один и тот же. Схлопываем в одну строку на
    # (item, source), а все конкретные пути (слот/сложность/вес/chance_hint)
    # складываем в список "variants".
    VARIANT_FIELDS = ("slot", "path", "chain_kinds", "weight", "weight_sum",
                       "chance_hint", "level_bracket", "difficulty")

    def merge_rows(rows):
        groups = {}
        order = []
        for row in rows:
            key = (row["item"], row["source"])
            variant = {k: row.get(k) for k in VARIANT_FIELDS}
            if key not in groups:
                base = {k: v for k, v in row.items() if k not in VARIANT_FIELDS}
                base["variants"] = [variant]
                groups[key] = base
                order.append(key)
            else:
                groups[key]["variants"].append(variant)
        for key in order:
            groups[key]["variant_count"] = len(groups[key]["variants"])
        return [groups[k] for k in order]

    n_before_merge = len(drop_rows)
    drop_rows = merge_rows(drop_rows)
    print(f"Слияние drop_sources: {n_before_merge} -> {len(drop_rows)} строк "
          f"(по одной на пару item+source, пути внутри variants)")

    # ================= write outputs =================
    loot_tables_doc = {
        "meta": {
            "weighted_tables": table_types_seen.get("LootMasterTable", 0)
                               + table_types_seen.get("LootItemTable_DynWeight", 0),
            "loot_master_table": table_types_seen.get("LootMasterTable", 0),
            "loot_item_table_dynweight": table_types_seen.get("LootItemTable_DynWeight", 0),
            "level_table": table_types_seen.get("LevelTable", 0),
            "fixeditemloot_nodes": table_types_seen.get("fixeditemloot(no Class)", 0),
            "monsters": len(monsters_out),
            "chests": len(chests_out),
            "mi_items": len(mi_items_out),
            "unresolved_child_refs_distinct": len(unresolved_children),
            "cycles_detected": stats.get("cycles", 0),
            "depth_exceeded": stats.get("depth_exceeded", 0),
        },
        "weighted_tables_raw": {
            name: [{"child": c, "weight": w} for c, w in children]
            for name, children in weighted_graph.items()
        },
        "level_tables_raw": {
            name: [{"level_min": lo, "level_max": hi, "child": c} for lo, hi, c in brackets]
            for name, brackets in level_graph.items()
        },
        "fixeditemloot_raw": fixed_graph,
        "monsters": monsters_out,
        "chests": chests_out,
        "chest_signature_groups": chest_signature_groups,
        "mi_items": mi_items_out,
    }

    p1, sz1 = write_json("loot_tables.json", loot_tables_doc)
    p2, sz2 = write_jsonl("drop_sources.jsonl", drop_rows)

    print()
    print("=== ИТОГ ===")
    print(f"{p1}  {sz1/1e6:.1f} MB")
    print(f"{p2}  {sz2/1e6:.1f} MB, строк: {len(drop_rows)}")
    print(f"Уникальных нерезолвленных ссылок на дочерние таблицы/предметы: {len(unresolved_children)}")
    if unresolved_children:
        for child, cnt in unresolved_children.most_common(10):
            print(f"    {child}  (x{cnt})")
    print(f"Циклов обнаружено и обрублено: {stats.get('cycles', 0)}")
    print(f"Обрублено по превышению глубины ({MAX_DEPTH}): {stats.get('depth_exceeded', 0)}")


if __name__ == "__main__":
    main()
