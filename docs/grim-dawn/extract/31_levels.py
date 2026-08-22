# -*- coding: utf-8 -*-
"""Задание 31 (СПАЙК): география мира -> data/grim-dawn/regions.json

Формат resources/Levels.arc -> world001.map НЕ реверсен (см. REPORTS/31_levels.md,
раздел про бинарный формат) - в PDF-руководстве по моддингу нет описания формата
и экспорта, у CLI-утилит игры (MapCompiler.exe, AssetManager.exe, ArchiveTool.exe)
нет документированной команды дампа содержимого уровня в читаемый вид.

Поэтому вся география здесь восстановлена из gd.sqlite, без парсинга .map:

  1. Записи Proxy / ProxyEndless / ProxyAmbush - спавнеры монстров. Поле poolN
     (poolEpicN/poolLegendaryN - тиры Endless Dungeon) ссылается на отдельную
     запись ProxyPool с полями nameK/nameChampionK (путь к Monster) и весами
     weightK/weightChampionK - это подтверждено дословным описанием в
     "Grim Dawn Modding Guide.pdf" (раздел "Spawning Monsters": Standard Proxy /
     Ambush Proxy / Spawn Pool) и проверено на 3+ записях (p_trollhalf_n.dbr,
     p_troll_t.dbr, p_yeti_t.dbr).
  2. Записи DungeonEntrance - двери/входы, поле description -> тэг с
     человекочитаемым названием. Для многих (особенно gdx1-3) это осмысленное
     имя локации ("Den of Carraxus", "Freyoll Valley", "Map Room of Rahn"), для
     старых записей (особенно base) - общий тип двери ("Cave Entrance").
  3. "Регион" в этом файле = буква зоны area[a-h] / area001 / areavoid, извлечённая
     регуляркой из ПУТИ записи (имя папки для Proxy: records/proxies/areae/...,
     или подстрока в имени файла для DungeonEntrance: ..._areae_...). Это не
     официальный термин игры, а замеченная закономерность:
       - records/proxies/area001/*  - весь мир базовой игры, монстры НЕ разнесены
         по буквам зон в путях (306 записей, src=base).
       - records/proxies/areae/*, areaf/*  - src=gdx1 (подтверждено на 90+53 записях).
       - records/proxies/areag/*            - src=gdx2 (162 записи).
       - records/proxies/areah/*            - src=gdx3 (146 записей).
       - records/proxies/areavoid/*          - src=gdx1, отдельный бонусный контент (31).
     Буквы b/c/d встречаются в путях квестов (quests/gdareab/...) и части
     DungeonEntrance/Proxy из категорий boss&quest/factionspawns, но НЕ как
     отдельная папка proxy для базовой игры - поэтому монстры базовой игры
     доступны только на уровне "весь мир area001", без разбивки на under-B/C/D.

  4. `records/ui/riftgatemap/riftgate_mastertable.dbr` (шаблон
     ingameui/worldmapwindow.tpl) - найден по подсказке из дампа
     `database/templates.arc` (field_schema.json/template_types.json) -
     АВТОРИТЕТНЫЙ список локаций мира с человеческими именами:
     `Region001ZoneList` (73 риftгейта, .dbr вида `riftgatemap1<буква>_<slug>`,
     имя резолвится через `ZoneNameTag`), `Region001ShrineList` (62 девоушен-
     святилища, имя лежит прямо в `FileDescription`, плюс пиксельные
     `WindowLocationX/Y`), `labelTagN`/`labelXN`/`labelYN` (118 подписей на
     текстуре карты с пиксельными координатами). Это НАДЁЖНЕЕ, чем
     DungeonEntrance.description (там много общих названий типа "Cave
     Entrance"), и это единственное место в БД, где вообще есть какие-то
     координаты (2D, пиксели UI-карты, не 3D-позиция в мире).
     ВАЖНО: буква "chapter" здесь (a,b,f,g,h,i,j,k) - это ДРУГОЙ, не
     пересекающийся с `region_code` (п.3, буквы b,c,d,e,f,g,h) внутренний
     индекс Crate. Они не сопоставляются 1:1 автоматически.

Не выдуманное: имена локаций и монстров - только резолв тэгов из tags_en.json.
Координат из .map (3D, игровых) нет и не будет - см. "Не делай" в задании;
единственные координаты в выходе - 2D пиксельные позиции подписей/иконок на
текстуре UI-карты мира из riftgate_mastertable.dbr (реальные числа из БД).

Запуск:  python 31_levels.py   (без аргументов, из папки extract)
Выход:   <GD_DATA>/regions.json
"""
import json
import re
from collections import Counter, defaultdict

from gdlib import open_sqlite, Tags, norm, write_json

# area001 / areavoid - отдельные "буквы", не A..H по регексу ниже.
SPECIAL_AREA_FOLDERS = {"area001", "areavoid"}
AREA_LETTER_RE = re.compile(r'(?:^|[^a-z])area([a-h])(?:[^a-z]|$)')
POOL_FIELD_RE = re.compile(r'^pool([A-Za-z]*)(\d+)$')
NAME_FIELD_RE = re.compile(r'^name(Champion)?(\d+)$')


def area_code(path):
    """Регион записи по пути: 'area001' | 'areavoid' | 'area_<a..h>' | None."""
    p = path.lower()
    if "/proxies/area001/" in p:
        return "area001"
    if "/proxies/areavoid/" in p:
        return "areavoid"
    m = AREA_LETTER_RE.search(p)
    if m:
        return f"area_{m.group(1)}"
    return None


def compact(d):
    """Убрать None/0/''/[] значения - см. правило 4 общего брифа."""
    out = {}
    for k, v in d.items():
        if v is None:
            continue
        if isinstance(v, str) and v == "":
            continue
        if isinstance(v, (int, float)) and v == 0:
            continue
        if isinstance(v, list) and not v:
            continue
        out[k] = v
    return out


def main():
    con = open_sqlite(readonly=True)
    tags = Tags()

    pool_cache = {}
    monster_cache = {}
    counters = Counter()

    def get_record(path):
        key = norm(path)
        row = con.execute(
            "SELECT name, type, src, fields FROM records WHERE name=?", (key,)
        ).fetchone()
        if not row:
            return None
        return {"name": row[0], "type": row[1], "src": row[2], "fields": json.loads(row[3])}

    def monster_display(rec_path):
        key = norm(rec_path)
        if key in monster_cache:
            return monster_cache[key]
        rec = get_record(key)
        if rec is None:
            counters["monster_ref_unresolved"] += 1
            res = {"record": rec_path, "name": None, "name_tag": None, "resolved": False}
        else:
            f = rec["fields"]
            desc_tag = f.get("description")
            disp = tags(desc_tag) if desc_tag else None
            if not disp:
                disp = f.get("FileDescription")
            res = compact({
                "record": rec["name"],
                "monster_type": rec["type"],
                "name": disp,
                "name_tag": desc_tag,
                "resolved": True,
            })
        monster_cache[key] = res
        return res

    def resolve_pool(pool_path, tier):
        key = norm(pool_path)
        cache_key = (key, tier)
        if cache_key in pool_cache:
            return pool_cache[cache_key]
        rec = get_record(key)
        if rec is None:
            counters["pool_ref_unresolved"] += 1
            pool_cache[cache_key] = None
            return None
        f = rec["fields"]
        monsters = []
        for k, v in f.items():
            m = NAME_FIELD_RE.match(k)
            if not m:
                continue
            champion = bool(m.group(1))
            idx = m.group(2)
            wkey = f"weight{'Champion' if champion else ''}{idx}"
            weight = f.get(wkey)
            paths = v if isinstance(v, list) else [v]
            for p in paths:
                if not p:
                    continue
                entry = {"champion": champion, "weight": weight}
                entry.update(monster_display(p))
                monsters.append(entry)
        monsters.sort(key=lambda m: (-(m.get("weight") or 0)))
        result = compact({
            "pool_record": rec["name"],
            "tier": tier,
            "spawn_min": f.get("spawnMin"),
            "spawn_max": f.get("spawnMax"),
            "champion_min": f.get("championMin"),
            "champion_max": f.get("championMax"),
            "champion_chance_pct": f.get("championChance"),
            "monsters": monsters,
        })
        pool_cache[cache_key] = result
        return result

    # ------------------------------------------------------------------
    # Proxy / ProxyEndless / ProxyAmbush -> спавнеры монстров
    # ------------------------------------------------------------------
    regions = defaultdict(lambda: {
        "proxies": [], "dungeon_entrances": [], "src_counts": Counter(),
    })
    non_geo_proxies = defaultdict(list)
    non_geo_proxy_srcs = defaultdict(Counter)

    proxy_rows = con.execute(
        "SELECT name, type, src, fields FROM records "
        "WHERE type IN ('Proxy','ProxyEndless','ProxyAmbush')"
    ).fetchall()
    counters["proxies_total"] = len(proxy_rows)

    for name, typ, src, fields_json in proxy_rows:
        f = json.loads(fields_json)
        pools_out = []
        for k, v in f.items():
            m = POOL_FIELD_RE.match(k)
            if not m:
                continue
            tier = m.group(1) or "normal"
            res = resolve_pool(v, tier)
            if res:
                pools_out.append(res)

        entry = compact({
            "record": name,
            "type": typ,
            "src": src,
            "chance_to_run_pct": f.get("chanceToRun"),
            "placement_extents": f.get("placementExtents"),
            "alert_area": f.get("alertArea"),
            "min_group_size": f.get("minGroupSize"),
            "max_group_size": f.get("maxGroupSize"),
            "pools": pools_out,
        })

        code = area_code(name)
        if code:
            regions[code]["proxies"].append(entry)
            regions[code]["src_counts"][src] += 1
            counters["proxies_geo"] += 1
        else:
            parts = name.split("/")
            if len(parts) > 2 and parts[1] == "proxies":
                cat = parts[2]
            elif "endlessdungeon" in name:
                cat = "endlessdungeon"
            else:
                cat = "/".join(parts[:3])
            non_geo_proxies[cat].append(entry)
            non_geo_proxy_srcs[cat][src] += 1
            counters["proxies_non_geo"] += 1

    # ------------------------------------------------------------------
    # DungeonEntrance -> названия локаций (из тэга description)
    # ------------------------------------------------------------------
    entrance_rows = con.execute(
        "SELECT name, src, fields FROM records WHERE type='DungeonEntrance'"
    ).fetchall()
    counters["entrances_total"] = len(entrance_rows)
    non_geo_entrances = []

    for name, src, fields_json in entrance_rows:
        f = json.loads(fields_json)
        desc_tag = f.get("description")
        disp = tags(desc_tag) if desc_tag else None
        entry = compact({
            "record": name,
            "src": src,
            "name": disp,
            "name_tag": desc_tag,
            "locked": bool(f.get("locked")) if f.get("locked") else None,
            "on_add_to_world": f.get("onAddToWorld"),
        })
        code = area_code(name)
        if code:
            regions[code]["dungeon_entrances"].append(entry)
            regions[code]["src_counts"][src] += 1
            counters["entrances_geo"] += 1
        else:
            non_geo_entrances.append(entry)
            counters["entrances_non_geo"] += 1

    # ------------------------------------------------------------------
    # Мировая карта (авторитетный список локаций с человеческими именами).
    # Найдено благодаря дампу database/templates.arc (field_schema.json /
    # template_types.json), который подсказал шаблоны zone.tpl / shrineicon.tpl /
    # ingameui/worldmapwindow.tpl - по ним нашлась таблица
    # records/ui/riftgatemap/riftgate_mastertable.dbr (интерфейс "карта рифтов"/
    # быстрого перемещения - см. PDF, раздел про Riftgates). Это ГОРАЗДО более
    # надёжный источник человеческих названий локаций, чем DungeonEntrance:
    #   - Region001ZoneList (73 записи) - каждая точка риftгейта, .dbr-имя вида
    #     riftgatemap1<буква>_<slug>.dbr, поле ZoneNameTag/TeleportNameTag -> тэг.
    #   - Region001ShrineList (62 записи) - девоушен-святилища на карте, ИМЕНА
    #     ЛЕЖАТ ПРЯМО В FileDescription (не тэг), + пиксельные WindowLocationX/Y.
    #   - labelTagN/labelXN/labelYN (118 записей) - подписи прямо на картинке
    #     карты мира с пиксельными координатами X/Y (это НЕ 3D-координаты игрока,
    #     а 2D-позиция подписи на UI-текстуре карты - но это реальные, а не
    #     придуманные числа из БД, поэтому включены).
    # "Буква главы" (chapter) здесь - ДРУГАЯ система, чем region_code выше:
    # riftgatemap использует буквы a,b,f,g,h,i,j,k (нет c/d/e!), тогда как
    # area_code из путей Proxy/quest использует b,c,d,e,f,g,h (нет a!). Это два
    # независимых внутренних индекса Crate, они НЕ соответствуют друг другу
    # напрямую - см. REPORTS/31_levels.md.
    # ------------------------------------------------------------------
    world_map = {"riftgates": [], "shrines": [], "map_labels": [], "chapters": []}
    mt_row = con.execute(
        "SELECT fields FROM records WHERE name='records/ui/riftgatemap/riftgate_mastertable.dbr'"
    ).fetchone()
    if mt_row is None:
        counters["world_map_missing"] = 1
    else:
        mtf = json.loads(mt_row[0])
        zone_re = re.compile(r'riftgatemap\d([a-z])_(?:(\d+)_)?(.+)\.dbr$')
        riftgate_slugs = []
        for zpath in mtf.get("Region001ZoneList", []):
            zrow = con.execute("SELECT fields FROM records WHERE name=?", (norm(zpath),)).fetchone()
            zf = json.loads(zrow[0]) if zrow else {}
            name_tag = zf.get("ZoneNameTag") or zf.get("TeleportNameTag")
            name = tags(name_tag) if name_tag else None
            m = zone_re.search(norm(zpath))
            chapter, order, slug = (m.group(1), m.group(2), m.group(3)) if m else (None, None, None)
            loc = compact({
                "record": zpath, "chapter": chapter,
                "order_in_chapter": int(order) if order else None,
                "slug": slug, "name": name, "name_tag": name_tag,
            })
            world_map["riftgates"].append(loc)
            if slug:
                riftgate_slugs.append((slug, loc))

        shrine_re = re.compile(r'riftgatemap([a-z])(\d+)_shrine\.dbr$')
        for spath in mtf.get("Region001ShrineList", []):
            srow = con.execute("SELECT fields FROM records WHERE name=?", (norm(spath),)).fetchone()
            sf = json.loads(srow[0]) if srow else {}
            m = shrine_re.search(norm(spath))
            chapter, order = (m.group(1), m.group(2)) if m else (None, None)
            world_map["shrines"].append(compact({
                "record": spath, "chapter": chapter,
                "order_in_chapter": int(order) if order else None,
                "name": sf.get("FileDescription"),
                "position": {"x": sf.get("WindowLocationX"), "y": sf.get("WindowLocationY")},
                "ruined": bool(sf.get("ruinedShrine")) if sf.get("ruinedShrine") else None,
                "corrupted": bool(sf.get("corruptedShrine")) if sf.get("corruptedShrine") else None,
            }))

        i = 0
        while f"labelTag{i}" in mtf:
            tag = mtf.get(f"labelTag{i}")
            entry = compact({
                "name": tags(tag) if tag else None, "name_tag": tag,
                "position": {"x": mtf.get(f"labelX{i}"), "y": mtf.get(f"labelY{i}")},
            })
            entry["index"] = i  # индекс важен (связывает с labelX/Y) - не давать compact() съесть 0
            world_map["map_labels"].append(entry)
            i += 1

        chapter_counter = Counter(l["chapter"] for l in world_map["riftgates"] if l.get("chapter"))
        world_map["chapters"] = [
            {
                "chapter": c,
                "riftgate_count": n,
                "riftgate_names": sorted(
                    l["name"] for l in world_map["riftgates"]
                    if l.get("chapter") == c and l.get("name")
                ),
            }
            for c, n in sorted(chapter_counter.items())
        ]

        # Эвристическая (best-effort, НЕ авторитетная) привязка: точное вхождение
        # "slug" риftгейт-локации в путь любого Proxy/ProxyEndless/ProxyAmbush/
        # DungeonEntrance (без ограничения на area_code). Recall низкий (см.
        # отчёт: 21/73 = 29%), но ни одного ложного совпадения не найдено при
        # ручной проверке выборки - оставляю как подсказку, не как факт.
        all_spawnish_names = [
            n for (n,) in con.execute(
                "SELECT name FROM records WHERE type IN "
                "('Proxy','ProxyEndless','ProxyAmbush','DungeonEntrance')"
            ).fetchall()
        ]
        for slug, loc in riftgate_slugs:
            matches = [n for n in all_spawnish_names if slug in n]
            if matches:
                loc["possible_spawn_records_best_effort"] = matches

    # ------------------------------------------------------------------
    # Сборка финального regions.json
    # ------------------------------------------------------------------
    region_list = []
    for code, data in regions.items():
        entrance_names = Counter(
            e["name"] for e in data["dungeon_entrances"] if e.get("name")
        )
        distinct_monsters = set()
        for p in data["proxies"]:
            for pool in p.get("pools", []):
                for mon in pool.get("monsters", []):
                    if mon.get("name"):
                        distinct_monsters.add(mon["name"])
        region_list.append({
            "region_code": code,
            "src_counts": dict(data["src_counts"]),
            "proxy_count": len(data["proxies"]),
            "dungeon_entrance_count": len(data["dungeon_entrances"]),
            "distinct_monsters_seen": len(distinct_monsters),
            "distinct_location_names": sorted(
                n for n, c in entrance_names.items()
            ),
            "dungeon_entrances": data["dungeon_entrances"],
            "proxies": data["proxies"],
        })

    region_order = {"area001": 0, "area_a": 1, "area_b": 2, "area_c": 3, "area_d": 4,
                    "area_e": 5, "area_f": 6, "areavoid": 7, "area_g": 8, "area_h": 9}
    region_list.sort(key=lambda r: region_order.get(r["region_code"], 99))

    out = {
        "meta": {
            "note": (
                "Формат world001.map не реверсен (см. отчёт REPORTS/31_levels.md). "
                "География восстановлена из gd.sqlite двумя независимыми путями: "
                "(1) world_map - авторитетный список локаций с человеческими "
                "именами из records/ui/riftgatemap/riftgate_mastertable.dbr "
                "(риftгейты/святилища/подписи карты, найдено по шаблонам из "
                "database/templates.arc); (2) regions - Proxy/ProxyEndless/"
                "ProxyAmbush (спавнеры монстров) + DungeonEntrance, сгруппированные "
                "по замеченной букве зоны в пути (region_code). Буквы в (1) и (2) "
                "используют РАЗНЫЕ несовпадающие внутренние индексы Crate - "
                "не путать. 3D-координат игрока нет нигде; в world_map есть только "
                "2D пиксельные позиции подписей/иконок на текстуре карты (реальные "
                "числа из БД, не придуманные)."
            ),
            "world_map_riftgates": len(world_map["riftgates"]),
            "world_map_shrines": len(world_map["shrines"]),
            "world_map_labels": len(world_map["map_labels"]),
            "world_map_chapters": len(world_map["chapters"]),
            "proxies_total": counters["proxies_total"],
            "proxies_assigned_to_region": counters["proxies_geo"],
            "proxies_unclassified": counters["proxies_non_geo"],
            "entrances_total": counters["entrances_total"],
            "entrances_assigned_to_region": counters["entrances_geo"],
            "entrances_unclassified": counters["entrances_non_geo"],
            "monster_refs_unresolved": counters["monster_ref_unresolved"],
            "pool_refs_unresolved": counters["pool_ref_unresolved"],
            "regions_found": len(region_list),
        },
        "world_map": world_map,
        "regions": region_list,
        "unclassified": {
            "note": (
                "Спавнеры/входы без определимого region_code - в основном служебные "
                "категории (боссы/квесты/фракции/девоушены/эндлесс данжен), которые "
                "не привязаны к одной точке мира, либо путь не содержит букву зоны. "
                "Ничего не выброшено - см. proxies_by_category и dungeon_entrances."
            ),
            "proxies_by_category": {
                cat: {
                    "count": len(items),
                    "src_counts": dict(non_geo_proxy_srcs[cat]),
                }
                for cat, items in sorted(non_geo_proxies.items(), key=lambda x: -len(x[1]))
            },
            "proxies": dict(non_geo_proxies),
            "dungeon_entrances": non_geo_entrances,
        },
    }

    path, size = write_json("regions.json", out, indent=1)

    # --- покрытие ---
    print("=== Мировая карта (riftgate_mastertable) ===")
    print(f"  риftгейтов: {len(world_map['riftgates'])}, "
          f"святилищ: {len(world_map['shrines'])}, "
          f"подписей на карте: {len(world_map['map_labels'])}, "
          f"глав (chapter): {len(world_map['chapters'])}")
    for ch in world_map["chapters"]:
        print(f"    chapter {ch['chapter']}: {ch['riftgate_count']} локаций -> "
              f"{', '.join(ch['riftgate_names'][:4])}...")
    linked = sum(1 for l in world_map["riftgates"] if l.get("possible_spawn_records_best_effort"))
    print(f"  риftгейтов с best-effort привязкой к Proxy/DungeonEntrance: "
          f"{linked}/{len(world_map['riftgates'])}")
    print()
    print("=== Регионы (по area_code) ===")
    for r in region_list:
        print(f"  {r['region_code']}: proxies={r['proxy_count']} "
              f"entrances={r['dungeon_entrance_count']} "
              f"distinct_monsters={r['distinct_monsters_seen']} "
              f"src={r['src_counts']}")
    print()
    print(f"Proxy-подобных записей всего: {counters['proxies_total']}")
    print(f"  -> привязано к региону: {counters['proxies_geo']}")
    print(f"  -> не привязано (служебные категории): {counters['proxies_non_geo']}")
    print(f"DungeonEntrance всего: {counters['entrances_total']}")
    print(f"  -> привязано к региону: {counters['entrances_geo']}")
    print(f"  -> не привязано: {counters['entrances_non_geo']}")
    print(f"Ссылок на монстров, не найденных в БД: {counters['monster_ref_unresolved']}")
    print(f"Ссылок на пулы, не найденных в БД: {counters['pool_ref_unresolved']}")
    print(f"Выход: {path} ({size} байт)")


if __name__ == "__main__":
    main()
