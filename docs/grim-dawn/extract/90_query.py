# -*- coding: utf-8 -*-
"""CLI-поиск по извлечённой базе Grim Dawn.

Смысл: данные лежат в 19 файлах общим весом ~294 MB, руками там не походишь.
Этот инструмент отвечает на вопросы, которые реально возникают при сборке билда.

Примеры:
    python 90_query.py item "Sunherald"                 предметы по имени
    python 90_query.py item --stat defensiveChaos --slot Ring --min 15
    python 90_query.py skill "Cadence"                  навыки
    python 90_query.py devotion "Widow"                 созвездия
    python 90_query.py affix --stat offensiveFire --top 15
    python 90_query.py drop "Bloodlord"                 кто дропает предмет
    python 90_query.py monster "Fabius"                 что дропает монстр
    python 90_query.py kills "Kyzogg's Skull"            сколько убийств до предмета
    python 90_query.py component "Frozen Heart"         компоненты
    python 90_query.py augment --faction Homestead      аугменты фракции
    python 90_query.py recipe "Blademaster"             рецепты
    python 90_query.py field defensiveFire              что значит поле .dbr
    python 90_query.py show records/items/.../x.dbr     сырая запись из gd.sqlite
    python 90_query.py stats                            что вообще есть в базе

Флаг --json у любой подкоманды выдаёт сырой JSON вместо текста.
"""
import argparse
import json
import os
import re
import sys

from gdlib import GD_DATA, open_sqlite, norm

# Имена в тэгах игры содержат управляющие коды цвета вида ^k / ^N (2283 тэга из 20245).
# Большинство экстракторов их снимает, но не все — чистим при выводе, чтобы поиск
# и отображение не зависели от того, кто из них аккуратнее.
_CODES = re.compile(r"\^[a-zA-Z]")


def clean(s):
    return _CODES.sub("", s) if isinstance(s, str) else s


def as_name(v):
    """Поле может быть строкой или объектом {name: ...} — приводим к строке."""
    if isinstance(v, dict):
        v = v.get("name") or v.get("id") or v.get("record") or ""
    return clean(v) if isinstance(v, str) else ""

# ---------- загрузка (ленивая: файлы большие, грузим только нужное) ----------

_cache = {}


def load(name):
    if name in _cache:
        return _cache[name]
    path = os.path.join(GD_DATA, name)
    if not os.path.exists(path):
        sys.exit(f"Нет файла {path}. Запусти соответствующий экстрактор.")
    if name.endswith(".jsonl"):
        rows = []
        with open(path, encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line:
                    rows.append(json.loads(line))
        obj = rows
    else:
        with open(path, encoding="utf-8") as f:
            obj = json.load(f)
    _cache[name] = obj
    return obj


def stream(name):
    """Потоковое чтение — для drop_sources.jsonl (174 MB), его в память не тянем."""
    path = os.path.join(GD_DATA, name)
    if not os.path.exists(path):
        sys.exit(f"Нет файла {path}.")
    with open(path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                yield json.loads(line)


# ---------- утилиты ----------

def matches(text, needle):
    if isinstance(text, dict):
        text = as_name(text)
    if not isinstance(text, str):
        text = "" if text is None else str(text)
    return needle.lower() in clean(text).lower()


def stat_value(stats, field):
    """Достаёт число из stats, каким бы ни было представление значения."""
    if not isinstance(stats, dict):
        return None
    v = stats.get(field)
    if v is None:
        return None
    if isinstance(v, (int, float)):
        return float(v)
    if isinstance(v, list) and v:
        nums = [x for x in v if isinstance(x, (int, float))]
        return float(max(nums)) if nums else None
    if isinstance(v, dict):
        for k in ("max", "value", "min"):
            if isinstance(v.get(k), (int, float)):
                return float(v[k])
    return None


def out(rows, args, fmt):
    if args.json:
        print(json.dumps(rows, ensure_ascii=False, indent=1))
        return
    if not rows:
        print("Ничего не найдено.")
        return
    for r in rows:
        print(fmt(r))
    print(f"\n— найдено: {len(rows)}")


def trunc(s, n):
    s = str(s)
    return s if len(s) <= n else s[: n - 1] + "…"


# ---------- подкоманды ----------

def cmd_item(args):
    rows = load("items.jsonl")
    res = []
    for it in rows:
        if args.query and not matches(it.get("name"), args.query):
            continue
        if args.slot and not matches(it.get("slot"), args.slot):
            continue
        if args.rarity and not matches(it.get("itemClassification"), args.rarity):
            continue
        if args.mi and not it.get("is_mi"):
            continue
        if args.maxlevel is not None and (it.get("levelRequirement") or 0) > args.maxlevel:
            continue
        if args.stat:
            v = stat_value(it.get("stats"), args.stat)
            if v is None or (args.min is not None and v < args.min):
                continue
            it = dict(it, _sort=v)
        res.append(it)
    if args.stat:
        res.sort(key=lambda r: r.get("_sort", 0), reverse=True)
    else:
        res.sort(key=lambda r: (r.get("levelRequirement") or 0))
    res = res[: args.top]

    def fmt(r):
        head = (f"{r.get('name')}  [{r.get('slot')}/{r.get('itemClassification')}"
                f"{'/MI' if r.get('is_mi') else ''}]  ур.{r.get('levelRequirement') or 0}")
        extra = f"   {args.stat} = {r['_sort']:g}" if args.stat else ""
        return f"{head}{extra}\n   {r.get('record')}"
    out(res, args, fmt)


def cmd_skill(args):
    rows = load("skills_flat.jsonl")
    res = [s for s in rows
           if (not args.query or matches(s.get("name"), args.query))
           and (not args.mastery or matches(s.get("mastery_name"), args.mastery))]
    res = res[: args.top]

    def fmt(r):
        m = r.get("mastery_name") or r.get("source") or "-"
        return (f"{r.get('name')}  [{m} / {r.get('role')}]  max {r.get('max_level')}"
                f"{'+' + str(r['ultimate_level']) if r.get('ultimate_level') else ''}\n"
                f"   {trunc(r.get('description') or '', 100)}\n   {r.get('record')}")
    out(res, args, fmt)


def cmd_devotion(args):
    d = load("devotions.json")
    cons = d.get("constellations")
    cons = list(cons.values()) if isinstance(cons, dict) else (cons or [])
    res = []
    for c in cons:
        blob = json.dumps(c, ensure_ascii=False)
        if args.query and not matches(blob, args.query):
            continue
        res.append(c)
    res = res[: args.top]

    def fmt(r):
        nodes = r.get("nodes") or []
        powers = [n for n in nodes if isinstance(n, dict)
                  and (n.get("is_power") or n.get("trigger") or n.get("celestial_power"))]
        head = (f"{clean(r.get('name'))}  [тир {r.get('tier')}]  "
                f"узлов {len(nodes)}, очков {r.get('points_cost')}")
        pw = ""
        if powers:
            names = [as_name(p.get("name") or p) for p in powers]
            pw = f"\n   силы: {', '.join(n for n in names if n)}"
        return (f"{head}\n"
                f"   нужно: {r.get('affinity_required') or {}}\n"
                f"   даёт:  {r.get('affinity_given') or {}}{pw}\n"
                f"   {r.get('record')}")
    out(res, args, fmt)


def cmd_affix(args):
    rows = load("affixes.jsonl")
    res = []
    for a in rows:
        if args.query and not matches(a.get("name"), args.query):
            continue
        if args.kind and (a.get("kind") or "") != args.kind:
            continue
        if args.stat:
            v = stat_value(a.get("stats"), args.stat)
            if v is None or (args.min is not None and v < args.min):
                continue
            a = dict(a, _sort=v)
        res.append(a)
    if args.stat:
        res.sort(key=lambda r: r.get("_sort", 0), reverse=True)
    res = res[: args.top]

    def fmt(r):
        extra = f"   {args.stat} = {r['_sort']:g}" if args.stat else ""
        cats = ", ".join((r.get("categories") or [])[:4])
        return (f"{r.get('name')}  [{r.get('kind')}]{extra}\n"
                f"   даёт: {trunc(cats, 100)}\n   {r.get('record')}")
    out(res, args, fmt)


def _lvl_range(r):
    lo, hi = r.get("monster_level_min"), r.get("monster_level_max")
    if lo is None and hi is None:
        return ""
    return f", ур.{lo}" + (f"-{hi}" if hi is not None and hi != lo else "")


def _fmt_drop(r):
    """Общий формат строки дропа. Полей `weight`/`monster_level` в данных нет —
    задание 30 отдаёт классификацию монстра, диапазон уровней и число вариантов."""
    marks = "".join(m for m, k in (("BOSS", "is_boss"), ("SUPER", "is_superboss"),
                                   ("HERO", "is_hero"), ("NEM", "is_nemesis"))
                    if r.get(k))
    cls = r.get("monster_classification") or r.get("source_kind") or "?"
    tag = f"{cls}/{marks}" if marks else cls
    mi = "  [MI]" if r.get("item_is_mi") else ""
    item = clean(r.get("item_name")) or r.get("item")
    src = clean(r.get("source_name")) or r.get("source")

    bits = []
    # Вес и доля лежат в variants[] — берём лучший вариант как ориентир.
    variants = [v for v in (r.get("variants") or []) if isinstance(v, dict)]
    best = max(variants, key=lambda v: v.get("chance_hint") or 0, default=None)
    if best:
        ch, w, ws = best.get("chance_hint"), best.get("weight"), best.get("weight_sum")
        if ch is not None:
            bits.append(f"доля в таблице {ch*100:.1f}%"
                        + (f" ({w:g}/{ws:g})" if w and ws else ""))
        if best.get("slot"):
            bits.append(f"слот {best['slot']}")
    if r.get("slot_trigger_pct") is not None:
        bits.append(f"слот роллится {r['slot_trigger_pct']}%")
    if (r.get("variant_count") or 0) > 1:
        bits.append(f"вариантов {r['variant_count']}")
    detail = ("\n   " + ", ".join(bits)) if bits else ""

    return f"{item}{mi}  ←  {src}\n   [{tag}{_lvl_range(r)}]{detail}"


def cmd_drop(args):
    """Кто дропает предмет. Стрим, потому что файл 174 MB."""
    res, seen = [], set()
    for row in stream("drop_sources.jsonl"):
        if not matches(row.get("item_name"), args.query):
            continue
        key = (row.get("item"), row.get("source"))
        if key in seen:
            continue
        seen.add(key)
        res.append(row)
        if len(res) >= args.top:
            break

    out(res, args, _fmt_drop)


def cmd_monster(args):
    """Что дропает монстр."""
    res, seen = [], set()
    for row in stream("drop_sources.jsonl"):
        if not matches(row.get("source_name"), args.query):
            continue
        k = row.get("item")
        if k in seen:
            continue
        seen.add(k)
        res.append(row)
        if len(res) >= args.top:
            break

    def fmt(r):
        mi = "  [MI]" if r.get("item_is_mi") else ""
        return f"{clean(r.get('source_name'))}  →  {clean(r.get('item_name'))}{mi}"
    out(res, args, fmt)


_DIFF_ORDER = {"Normal": 0, "Epic": 1, "Ultimate": 2}


def cmd_kills(args):
    """Сколько раз убить/открыть источник, чтобы выбить предмет — задание 60.
    Читает drop_rates.jsonl (по строке на item x source x difficulty, p_per_kill
    уже свёрнут по всей цепочке лут-таблиц, см. REPORTS/60_dropcalc.md)."""
    rows = [r for r in stream("drop_rates.jsonl") if matches(r.get("item_name"), args.query)]

    # Один предмет даёт сотни строк: тиры предмета x источники x сложности. Без свёртки
    # в выдачу первыми попадают случайные сундуки с мизерным шансом, а нужный герой-источник
    # теряется — это активно вводит в заблуждение. Сворачиваем до лучшего шанса
    # на пару (источник, сложность) и сортируем по убыванию вероятности.
    best = {}
    for r in rows:
        key = (clean(r.get("source_name")) or r.get("source"), r.get("difficulty"))
        cur = best.get(key)
        if cur is None or (r.get("p_per_kill") or 0) > (cur.get("p_per_kill") or 0):
            best[key] = r
    res = sorted(best.values(),
                 key=lambda r: (-(r.get("p_per_kill") or 0.0),
                                _DIFF_ORDER.get(r.get("difficulty"), 9)))
    if args.best:
        # Только лучший источник, по одной строке на сложность.
        top_src = res[0].get("source_name") if res else None
        res = [r for r in res if r.get("source_name") == top_src]
    total_sources = len({k[0] for k in best})
    res = res[: args.top]
    if res and not args.json:
        print(f"(источников: {total_sources}; показаны лучшие по шансу)\n")

    def fmt(r):
        assum = r.get("assumptions") or []
        note = f"\n   допущения: {', '.join(assum)}" if assum else ""
        p = r.get("p_per_kill") or 0.0
        return (f"{clean(r.get('item_name'))}  <-  {clean(r.get('source_name'))}  [{r.get('difficulty')}]\n"
                f"   p за убийство/открытие = {p*100:.3g}%   "
                f"убийств: 50%={r.get('kills_50')}  90%={r.get('kills_90')}  99%={r.get('kills_99')}"
                f"   (вариантов учтено: {r.get('variants_used')}){note}")
    out(res, args, fmt)


def cmd_component(args):
    d = load("components.json")
    items = list(d.values()) if isinstance(d, dict) else d
    # По умолчанию ищем по имени. Поиск по всему объекту находит и те компоненты,
    # где запрос упомянут в рецепте или источнике дропа — это отдельный режим (--deep).
    res = [c for c in items if not args.query or matches(
        json.dumps(c, ensure_ascii=False) if args.deep else c.get("name"), args.query)]
    if args.slot:
        res = [c for c in res
               if any(matches(s, args.slot) for s in (c.get("slots") or []))]
    res = res[: args.top]

    def fmt(r):
        sk = r.get("skill")  # grants_skill — булев флаг, сам скилл лежит в skill
        return (f"{clean(r.get('name'))}\n"
                f"   слоты: {', '.join(r.get('slots') or []) or '-'}\n"
                f"   резисты: {r.get('resists') or {}}\n"
                f"   скилл: {as_name(sk) or '-'}")
    out(res, args, fmt)


def cmd_augment(args):
    rows = load("augments.jsonl")
    res = [a for a in rows
           if (not args.query or matches(a.get("name"), args.query))
           and (not args.faction or matches(a.get("faction"), args.faction))]
    res = res[: args.top]

    def fmt(r):
        return (f"{clean(r.get('name'))}  [{as_name(r.get('faction')) or '-'}"
                f" / {', '.join(r.get('vendor_tiers') or []) or '-'}]"
                f"  ур.{r.get('levelRequirement') or 0}\n"
                f"   слоты: {', '.join(r.get('slots') or []) or '-'}")
    out(res, args, fmt)


def cmd_recipe(args):
    rows = load("recipes.jsonl")
    # --deep ищет и по реагентам/выходу рецепта, а не только по его имени.
    res = [r for r in rows if not args.query or matches(
        json.dumps(r, ensure_ascii=False) if args.deep else r.get("name"),
        args.query)][: args.top]

    def fmt(r):
        o = r.get("output") or {}
        oname = o.get("name") if isinstance(o, dict) else o
        reag = r.get("reagents") or []
        names = [x.get("name") if isinstance(x, dict) else str(x) for x in reag]
        return (f"{r.get('name')}  →  {oname}\n"
                f"   реагенты: {trunc(', '.join(n for n in names if n), 110)}")
    out(res, args, fmt)


def cmd_field(args):
    schema = load("field_schema.json")
    hits = {k: v for k, v in schema.items() if matches(k, args.query)}
    if not hits:
        print("Поле не найдено в схеме.")
        return
    if args.json:
        print(json.dumps(hits, ensure_ascii=False, indent=1))
        return
    for k, v in list(hits.items())[: args.top]:
        print(f"{k}")
        print(f"   тип: {', '.join(v.get('type') or [])}  класс: {', '.join(v.get('class') or [])}")
        print(f"   категории: {', '.join(v.get('groups') or [])}")
        if v.get("description"):
            print(f"   описание: {'; '.join(v['description'])}")
    print(f"\n— найдено: {len(hits)}")


def cmd_show(args):
    con = open_sqlite(readonly=True)
    r = con.execute("SELECT orig_name, type, src, fields FROM records WHERE name=?",
                    (norm(args.query),)).fetchone()
    if not r:
        like = con.execute(
            "SELECT orig_name FROM records WHERE name LIKE ? LIMIT 15",
            (f"%{norm(args.query)}%",)).fetchall()
        print("Точного совпадения нет." + (" Похожие:" if like else ""))
        for x in like:
            print("  ", x[0])
        return
    fields = json.loads(r["fields"])
    if args.json:
        print(json.dumps(fields, ensure_ascii=False, indent=1))
        return
    print(f"{r['orig_name']}   type={r['type']}  src={r['src']}")
    for k in sorted(fields):
        if k.startswith("__"):
            continue
        print(f"   {k} = {fields[k]}")


def cmd_stats(args):
    print("Содержимое базы знаний:\n")
    for fn, label in [
        ("items.jsonl", "предметы"), ("affixes.jsonl", "аффиксы"),
        ("skills_flat.jsonl", "навыки"), ("augments.jsonl", "аугменты"),
        ("recipes.jsonl", "рецепты"), ("drop_sources.jsonl", "связок дроп→предмет"),
    ]:
        p = os.path.join(GD_DATA, fn)
        if not os.path.exists(p):
            print(f"  {label:28} — НЕТ ФАЙЛА")
            continue
        n = sum(1 for _ in open(p, encoding="utf-8"))
        print(f"  {label:28} {n:>8}   ({os.path.getsize(p)/1024/1024:.1f} MB)")
    for fn, label, key in [
        ("devotions.json", "созвездия", "constellations"),
        ("components.json", "компоненты", None),
        ("factions.json", "фракции", "factions"),
        ("field_schema.json", "полей .dbr в схеме", None),
    ]:
        p = os.path.join(GD_DATA, fn)
        if not os.path.exists(p):
            print(f"  {label:28} — НЕТ ФАЙЛА")
            continue
        d = json.load(open(p, encoding="utf-8"))
        c = d.get(key) if key else d
        print(f"  {label:28} {len(c):>8}   ({os.path.getsize(p)/1024/1024:.1f} MB)")


def main():
    ap = argparse.ArgumentParser(
        description="Поиск по извлечённой базе Grim Dawn",
        formatter_class=argparse.RawDescriptionHelpFormatter, epilog=__doc__)
    sub = ap.add_subparsers(dest="cmd", required=True)

    def add(name, fn, q_required=False, **extra):
        p = sub.add_parser(name)
        p.add_argument("query", nargs="?" if not q_required else None, default="")
        p.add_argument("--top", type=int, default=20)
        p.add_argument("--json", action="store_true")
        for flag, kw in extra.items():
            p.add_argument("--" + flag, **kw)
        p.set_defaults(func=fn)
        return p

    add("item", cmd_item, slot={}, rarity={}, stat={},
        min={"type": float}, maxlevel={"type": int}, mi={"action": "store_true"})
    add("skill", cmd_skill, mastery={})
    add("devotion", cmd_devotion)
    add("affix", cmd_affix, kind={}, stat={}, min={"type": float})
    add("drop", cmd_drop, q_required=True)
    add("monster", cmd_monster, q_required=True)
    add("kills", cmd_kills, q_required=True,
        best={"action": "store_true", "help": "только лучший источник, по строке на сложность"})
    add("component", cmd_component, slot={},
        deep={"action": "store_true", "help": "искать и в рецептах/дропе, не только в имени"})
    add("augment", cmd_augment, faction={})
    add("recipe", cmd_recipe,
        deep={"action": "store_true", "help": "искать и по реагентам/выходу"})
    add("field", cmd_field, q_required=True)
    add("show", cmd_show, q_required=True)

    p = sub.add_parser("stats")
    p.add_argument("--json", action="store_true")
    p.set_defaults(func=cmd_stats)

    args = ap.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
