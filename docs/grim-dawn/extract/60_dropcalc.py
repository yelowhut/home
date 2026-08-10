# -*- coding: utf-8 -*-
"""Задание 60 — Калькулятор шанса дропа.

Отвечает на вопрос игрока: "сколько раз убить этого монстра/открыть этот сундук,
чтобы выбить этот предмет?" Задание 30 (`30_loot.py`) уже нашло СВЯЗКИ
(предмет, источник) и разложило путь по цепочке лут-таблиц в `variants[].path` +
`chain_kinds`, но НЕ свернуло их в вероятность — как только в цепочке появляется
`level`- или `difficulty`-хоп, `chance_hint` в drop_sources.jsonl становится `null`
(так устроено намеренно, см. REPORTS/30_loot.md, раздел "Честность про
вероятности"). Это 88% всех вариантов.

КЛЮЧЕВОЕ ОГРАНИЧЕНИЕ (из задания): drop_sources.jsonl хранит только ОДНУ пару
weight/weight_sum на вариант (последнего weighted-хопа), а не веса каждого звена.
Поэтому здесь цепочка проходится ЗАНОВО: для каждого хопа кода kind="weighted"
мы смотрим, из какого узла (LootMasterTable/LootItemTable_DynWeight —
`weighted_tables_raw`, "fixeditemloot" — `fixeditemloot_raw`, или собственный
слот монстра — `monsters[x].slots`) он взят, и там ищем вес конкретного ребёнка
и сумму весов ВСЕХ конкурентов в этом же списке. `loot_tables.json` (54 MB)
грузится в память целиком (~150-200 MB как python-объект, замерено) — это
безопасно, в отличие от полного разворота цепочек (тот блок памяти съедал
10 ГБ на задании 30). drop_sources.jsonl (170+ MB) читается потоково, по строке.

Формула (см. TASKS/60_dropcalc.md):
    P(вариант) = trigger_pct/100 (только для source_kind=monster, иначе 1.0)
                 x Пи по weighted-хопам (weight_i / weight_sum_i)
    P(предмет за убийство | сложность) = 1 - Пи по подходящим вариантам (1 - P(вариант))
    n(увер. X) = ln(1-X) / ln(1-p)

Честные допущения (подробно — в отчёте, коротко — в assumptions[] построчно):
  - level-хопы НЕ порождают множитель (это жёсткий гейт по уровню монстра/перса,
    не случайность) — но у 79% монстров minLevel/maxLevel = 1/250 (масштабируется
    под уровень персонажа), поэтому мы не можем определить, какая именно ветка
    LevelTable сработает на конкретном убийстве. Модель суммирует ВСЕ подходящие
    по сложности ветки через union-формулу выше (так же, как сама формула задания
    суммирует "по всем вариантам") — это ЗАВЫШАЕТ p для монстров с широким
    диапазоном уровня, если игрок фармит его на одном фиксированном уровне.
  - Обнаружен 4-й "индекс по игровому режиму" (метка "3", не Normal/Epic/Ultimate)
    ТОЛЬКО у сундуков (47592 вхождения) — судя по данным (общий table для
    Normal/Epic/Ultimate + отдельный "...a.dbr" на 4-м месте, ведущий в
    mt_monsterinfrequents_*), это похоже на отдельный бонус-ролл, а не 4-ю
    сложность. Не выдумываю смысл — такие варианты ИСКЛЮЧЕНЫ из расчёта
    Normal/Epic/Ultimate, посчитаны отдельно и обозначены как "не понято".
  - trigger_pct слота монстра берётся заново из loot_tables.json (per-variant,
    не из старого агрегированного поля строки, которое достоверно только для
    первого варианта после слияния в 30_loot.py).
  - Слоты одного монстра/сундука считаются независимыми (это ДОПУЩЕНИЕ, не факт).
  - Magic Find / число игроков / скрытые сложностные множители — НЕ в .dbr
    данных вообще, не моделируются (см. TASKS/60_dropcalc.md, "заведомо неизвестное").
"""
import json
import math
import random
from collections import Counter

from gdlib import open_sqlite, write_jsonl, out_path, norm

DIFF_LABELS = ["Normal", "Epic", "Ultimate"]
CONFIDENCES = (0.5, 0.9, 0.99)

GLOBAL_ASSUMPTIONS = [
    "slots_independent: слоты монстра/сундука роллятся независимо друг от друга (не проверено в данных)",
    "no_magic_find: '% Item Rarity' игрока не моделируется (нет в .dbr)",
    "no_difficulty_multiplier: множители дропа по сложности сверх выбора таблицы не моделируются (нет в .dbr)",
    "no_player_count: влияние числа игроков в отряде не моделируется",
    "level_gate_summed: level-хопы суммируются как альтернативные варианты (см. REPORTS/60_dropcalc.md) — "
    "завышает p для монстров с широким диапазоном уровня, если по факту фармится на одном уровне",
]


def load_loot_tables():
    path = out_path("loot_tables.json")
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def diff_bucket_for(label):
    """None -> применимо ко всем 3 сложностям; известная метка -> [метка];
    неизвестная (4-й индекс) -> None (не включаем никуда, честно теряем)."""
    if label is None:
        return list(DIFF_LABELS)
    if label in DIFF_LABELS:
        return [label]
    return None


def kills_for(p, conf):
    if p is None or p <= 0:
        return None
    if p >= 1:
        return 1
    return math.ceil(math.log(1 - conf) / math.log(1 - p))


class ChainResolver:
    """Пересчитывает вес каждого weighted-хопа цепочки заново по loot_tables.json,
    а не по единственной агрегированной паре weight/weight_sum из drop_sources.jsonl."""

    def __init__(self, doc):
        self.weighted_raw = doc["weighted_tables_raw"]
        self.fixed_raw = doc["fixeditemloot_raw"]
        self.monsters = doc["monsters"]
        self.chests = doc["chests"]
        self._weighted_dict_cache = {}

    def _weighted_dict(self, table):
        cached = self._weighted_dict_cache.get(table)
        if cached is not None:
            return cached
        entries = self.weighted_raw.get(table, [])
        d = {}
        total = 0.0
        for e in entries:
            d[e["child"]] = d.get(e["child"], 0.0) + e["weight"]
            total += e["weight"]
        cached = (d, total)
        self._weighted_dict_cache[table] = cached
        return cached

    def find_weight(self, table, true_child, i, source, source_kind, slot_top):
        """Вес и сумма весов для хопа table->true_child. None,None если не нашли
        (unresolved_child_refs/циклы задания 30 — не выдумываем число)."""
        if i == 0 and source_kind == "monster" and table == source:
            cands = self.monsters.get(source, {}).get("slots", {}).get(slot_top, {}).get("candidates", [])
            total = sum(c.get("weight") or 0.0 for c in cands)
            for c in cands:
                val = c.get("value")
                if isinstance(val, str):
                    if val == true_child:
                        return c["weight"], total
                elif isinstance(val, list):
                    if true_child in val:
                        return c["weight"], total
            return None, None

        if table in self.weighted_raw:
            d, total = self._weighted_dict(table)
            w = d.get(true_child)
            if w is not None:
                return w, total
            return None, None

        if table in self.fixed_raw:
            for slot_id, sd in self.fixed_raw[table].items():
                children = sd.get("children", [])
                total = sum(c.get("weight") or 0.0 for c in children)
                for c in children:
                    val = c.get("value")
                    if isinstance(val, str):
                        if val == true_child:
                            return c["weight"], total
                    elif isinstance(val, list):
                        if true_child in val:
                            return c["weight"], total
            return None, None

        return None, None

    def trigger_pct(self, source, slot):
        return self.monsters.get(source, {}).get("slots", {}).get(slot, {}).get("trigger_pct")

    def variant_probability(self, item, source, source_kind, variant):
        """Возвращает (p, resolved, assumptions_used) для одного variant-а строки
        drop_sources.jsonl. resolved=False если хоп не нашёлся (не выдумываем)."""
        chain_kinds = variant.get("chain_kinds") or []
        path = variant.get("path") or []
        slot = variant.get("slot")
        assumptions = set()

        if chain_kinds == ["fixed_guaranteed"]:
            return 1.0, True, assumptions

        prod = 1.0
        n = len(chain_kinds)
        for i, kind in enumerate(chain_kinds):
            if kind != "weighted":
                continue
            next_kind = chain_kinds[i + 1] if i + 1 < n else None
            if next_kind == "difficulty":
                true_child = path[i + 2] if i + 2 < len(path) else item
            else:
                true_child = path[i + 1] if i + 1 < len(path) else item
            w, wsum = self.find_weight(path[i], true_child, i, source, source_kind, slot)
            if w is None or wsum is None or wsum <= 0:
                return None, False, assumptions
            prod *= w / wsum

        p = prod
        if source_kind == "monster":
            trig = self.trigger_pct(source, slot)
            if trig is None:
                assumptions.add("trigger_pct_missing_assumed_100")
            else:
                if trig > 100.0:
                    # Один известный случай во всей игре: bandit_oldwounds.dbr/LeftHand
                    # = 1000 (все остальные trigger_pct в данных <=100). Явный выброс
                    # авторства/движка — не выдумываем смысл "1000%", клэмпим к 100%.
                    trig = 100.0
                    assumptions.add("trigger_pct_clamped_100")
                p *= trig / 100.0
        else:
            assumptions.add("chest_trigger_assumed_100")

        if any(k == "level" for k in chain_kinds):
            assumptions.add("level_gate_summed")

        return p, True, assumptions


def main():
    doc = load_loot_tables()
    resolver = ChainResolver(doc)

    src_path = out_path("drop_sources.jsonl")

    out_rows = []
    n_rows = 0
    n_variants = 0
    n_unresolved = 0
    n_excluded_4th = 0
    n_guaranteed = 0
    monotonicity_violations = []
    max_p_variant_seen = 0.0

    # для валидации 4 (известные MI) — запоминаем строки по ходу стрима
    watch_items = {"Kyzogg's Skull": None, "Bloodlord's Vengeance": None, "Ragrathar's Horn": None}

    with open(src_path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            row = json.loads(line)
            n_rows += 1
            item = row["item"]
            item_name = row.get("item_name")
            source = row["source"]
            source_name = row.get("source_name")
            source_kind = row.get("source_kind")

            buckets = {d: [] for d in DIFF_LABELS}
            row_assumptions = set()

            for variant in row.get("variants", []):
                n_variants += 1
                p, resolved, assum = resolver.variant_probability(item, source, source_kind, variant)
                if not resolved:
                    n_unresolved += 1
                    continue
                if variant.get("chain_kinds") == ["fixed_guaranteed"]:
                    n_guaranteed += 1
                row_assumptions |= assum

                targets = diff_bucket_for(variant.get("difficulty"))
                if targets is None:
                    n_excluded_4th += 1
                    row_assumptions.add("excluded_unknown_difficulty_index")
                    continue

                # монотонность: p варианта не должен превышать его собственный
                # trigger_pct/100 (для монстров) — проверяем ДО group-объединения.
                if source_kind == "monster":
                    trig = resolver.trigger_pct(source, variant.get("slot"))
                    trig = min(trig, 100.0) if trig is not None else 100.0
                    cap = trig / 100.0
                    if p > cap + 1e-9:
                        monotonicity_violations.append((item, source, variant.get("slot"), p, cap))
                max_p_variant_seen = max(max_p_variant_seen, p)

                for d in targets:
                    buckets[d].append(p)

            if len(row_assumptions) > 1 or (row_assumptions and "excluded_unknown_difficulty_index" not in row_assumptions):
                pass  # assumptions per-row written below regardless

            for d in DIFF_LABELS:
                ps = buckets[d]
                if not ps:
                    continue
                p_per_kill = 1.0
                for p in ps:
                    p_per_kill *= (1.0 - p)
                p_per_kill = 1.0 - p_per_kill

                out_row = {
                    "item": item, "item_name": item_name,
                    "source": source, "source_name": source_name,
                    "source_kind": source_kind,
                    "difficulty": d,
                    "monster_level_min": row.get("monster_level_min"),
                    "monster_level_max": row.get("monster_level_max"),
                    "p_per_kill": round(p_per_kill, 8),
                    "kills_50": kills_for(p_per_kill, 0.5),
                    "kills_90": kills_for(p_per_kill, 0.9),
                    "kills_99": kills_for(p_per_kill, 0.99),
                    "variants_used": len(ps),
                    "assumptions": sorted(row_assumptions),
                }
                out_rows.append(out_row)

                if item_name in watch_items and watch_items[item_name] is None:
                    watch_items[item_name] = []
                if item_name in watch_items:
                    watch_items[item_name].append(dict(out_row))

            if n_rows % 20000 == 0:
                print(f"... {n_rows} строк drop_sources обработано, "
                      f"{len(out_rows)} строк drop_rates накоплено")

    p2, sz2 = write_jsonl("drop_rates.jsonl", out_rows)

    print()
    print("=== ИТОГ ===")
    print(f"drop_sources.jsonl строк обработано: {n_rows}")
    print(f"вариантов обработано: {n_variants}, unresolved (не нашли вес — не выдумали): {n_unresolved}")
    print(f"вариантов с fixed_guaranteed: {n_guaranteed}")
    print(f"вариантов исключено (4-й неизвестный индекс сложности, метка '3' и т.п.): {n_excluded_4th}")
    print(f"{p2}  {sz2/1e6:.1f} MB, строк: {len(out_rows)}")
    print(f"максимальный p одного варианта за весь прогон: {max_p_variant_seen:.6f}")
    print(f"нарушений монотонности (p варианта > его trigger_pct/100): {len(monotonicity_violations)}")
    for v in monotonicity_violations[:10]:
        print("   ", v)

    # ================= ВАЛИДАЦИЯ 1: гарантированные дропы =================
    print()
    print("=== ВАЛИДАЦИЯ 1: гарантированные дропы (p должен быть 1.0) ===")
    guaranteed_rows = [r for r in out_rows if r["p_per_kill"] >= 0.999999]
    print(f"строк drop_rates.jsonl с p_per_kill ~= 1.0: {len(guaranteed_rows)}")
    callagadra = [r for r in out_rows
                  if r["item"] == "records/items/gearhead/d220_head.dbr"
                  and "sandscion" in r["source"]]
    print("Callagadra -> Callagadra's Visage:")
    for r in callagadra:
        print("   ", {k: r[k] for k in ("difficulty", "p_per_kill", "kills_50", "kills_90", "kills_99")})

    # ================= ВАЛИДАЦИЯ 2: сумма весов 10 случайных таблиц =================
    print()
    print("=== ВАЛИДАЦИЯ 2: сумма долей 10 случайных weighted-таблиц (должна быть ~1.0) ===")
    print("Сверяем НЕ с самим loot_tables.json (это было бы тавтологией), а заново")
    print("с сырыми полями lootNameN/lootWeightN в gd.sqlite.")
    con = open_sqlite(readonly=True)
    random.seed(42)
    sample_tables = random.sample(list(doc["weighted_tables_raw"].keys()), 10)
    for t in sample_tables:
        row = con.execute("SELECT fields FROM records WHERE name=?", (t,)).fetchone()
        if row is None:
            print(f"   {t}: НЕ НАЙДЕНА в gd.sqlite (не должно случаться)")
            continue
        raw = json.loads(row[0])
        import re
        name_re = re.compile(r"^lootName(\d+)$")
        weight_re = re.compile(r"^lootWeight(\d+)$")
        names, weights = {}, {}
        for k, v in raw.items():
            m = name_re.match(k)
            if m:
                names[int(m.group(1))] = v
                continue
            m = weight_re.match(k)
            if m:
                weights[int(m.group(1))] = v
        raw_sum = sum(float(weights.get(i, 0) or 0) for i in names
                      if float(weights.get(i, 0) or 0) > 0)
        stored_children = doc["weighted_tables_raw"][t]
        stored_sum = sum(c["weight"] for c in stored_children)
        ratio = stored_sum / raw_sum if raw_sum else float("nan")
        print(f"   {t}: raw(gd.sqlite) sum={raw_sum:g}, loot_tables.json sum={stored_sum:g}, "
              f"ratio={ratio:.4f}, доли внутри таблицы суммируются в "
              f"{sum(c['weight'] for c in stored_children)/stored_sum if stored_sum else 0:.4f}")

    # ================= ВАЛИДАЦИЯ 3: монотонность =================
    print()
    print("=== ВАЛИДАЦИЯ 3: монотонность (p варианта <= slot_trigger_pct/100) ===")
    print(f"нарушений: {len(monotonicity_violations)} из {n_variants} вариантов")

    # ================= ВАЛИДАЦИЯ 4: здравый смысл на известных MI =================
    print()
    print("=== ВАЛИДАЦИЯ 4: здравый смысл (3 известных MI) ===")
    for name, rows in watch_items.items():
        print(f"--- {name} ---")
        if not rows:
            print("   НЕ НАЙДЕН в выходе (искали по item_name)")
            continue
        for r in rows[:6]:
            print(f"   source={r['source_name']}  difficulty={r['difficulty']}  "
                  f"p_per_kill={r['p_per_kill']:.5f}  kills_50={r['kills_50']} "
                  f"kills_90={r['kills_90']} kills_99={r['kills_99']}  "
                  f"assumptions={r['assumptions']}")


if __name__ == "__main__":
    main()
