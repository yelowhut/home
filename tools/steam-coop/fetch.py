#!/usr/bin/env python3
"""Собирает игры для локального co-op (на одном устройстве) из двух библиотек Steam.

Источники:
  * IPlayerService/GetOwnedGames  — списки игр (нужен STEAM_API_KEY, профили публичные)
  * IStoreBrowseService/GetItems  — категории, дата релиза, отзывы, Steam Deck (без ключа,
                                    до 200 appid за запрос)

Запуск:
  STEAM_API_KEY=... python3 tools/steam-coop/fetch.py

Пишет data.js рядом со скриптом. Ответы GetItems кешируются в cache.json,
поэтому повторная генерация страницы не дёргает Steam заново (--refresh сбрасывает кеш).
"""

import json
import os
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

HERE = Path(__file__).resolve().parent
CACHE = HERE / "cache.json"
OUT = HERE / "data.js"

ACCOUNTS = [
    {"key": "yelowhut", "steamid": "76561198297641574", "label": "yelowhut"},
    {"key": "cutlet", "steamid": "76561197999293155", "label": "cutlet"},
]

# id категорий Steam (supported_player_categoryids)
CAT_SINGLE = 2
CAT_MULTI = 1
CAT_COOP = 9
CAT_SPLIT = 24          # Shared/Split Screen — «зонтик», сам по себе может быть только PvP
CAT_SPLIT_PVP = 37      # Shared/Split Screen PvP — это НЕ кооп
CAT_SPLIT_COOP = 39     # Shared/Split Screen Co-op — точное попадание
CAT_ONLINE_COOP = 38
CAT_LAN_COOP = 48
CAT_RPT = 44            # Remote Play Together — живёт в feature_categoryids, два устройства

BATCH = 200
STORE_URL = "https://api.steampowered.com/IStoreBrowseService/GetItems/v1/"


def get_json(url, timeout=60):
    req = urllib.request.Request(url, headers={"Accept-Encoding": "identity"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.load(r)


def fetch_owned(key, steamid):
    url = (
        "https://api.steampowered.com/IPlayerService/GetOwnedGames/v1/?"
        + urllib.parse.urlencode(
            {
                "key": key,
                "steamid": steamid,
                "include_appinfo": 1,
                "include_played_free_games": 1,
                "format": "json",
            }
        )
    )
    resp = get_json(url).get("response", {})
    games = resp.get("games")
    if games is None:
        raise SystemExit(
            f"Библиотека {steamid} недоступна: профиль скрыл 'Игровые данные' "
            "или ключ невалиден."
        )
    return games


def fetch_items(appids, batch=BATCH):
    """Тянет store-данные пачками. Возвращает {appid: item}."""
    out = {}
    batches = [appids[i : i + batch] for i in range(0, len(appids), batch)]
    for n, chunk in enumerate(batches, 1):
        req = {
            "ids": [{"appid": a} for a in chunk],
            "context": {"language": "english", "country_code": "US"},
            "data_request": {
                "include_basic_info": True,
                "include_release": True,
                "include_platforms": True,
                "include_reviews": True,
            },
        }
        url = STORE_URL + "?input_json=" + urllib.parse.quote(json.dumps(req))
        for attempt in range(4):
            try:
                items = get_json(url).get("response", {}).get("store_items", [])
                for it in items:
                    if it.get("appid"):
                        out[it["appid"]] = it
                break
            except (urllib.error.URLError, urllib.error.HTTPError, TimeoutError) as e:
                wait = 5 * (attempt + 1)
                print(f"  пачка {n}: {e} — повтор через {wait}s", file=sys.stderr)
                time.sleep(wait)
        else:
            print(f"  пачка {n}: не удалась, {len(chunk)} игр без данных", file=sys.stderr)
        print(f"  store: пачка {n}/{len(batches)} -> {len(out)} записей")
        time.sleep(1)
    return out


def deck_rank(cat):
    """Явный порядок: Verified > Playable > Unsupported > Не проверено (всегда последним)."""
    return {3: 3, 2: 2, 1: 1}.get(cat, 0)


def main():
    api_key = os.environ.get("STEAM_API_KEY", "").strip()
    if not api_key:
        raise SystemExit("Нужна переменная окружения STEAM_API_KEY")
    refresh = "--refresh" in sys.argv

    owners = {}   # appid -> [account key]
    names = {}
    playtime = {}
    lib_sizes = {}
    for acc in ACCOUNTS:
        games = fetch_owned(api_key, acc["steamid"])
        lib_sizes[acc["key"]] = len(games)
        print(f"{acc['label']}: {len(games)} игр")
        for g in games:
            appid = g["appid"]
            owners.setdefault(appid, []).append(acc["key"])
            if g.get("name"):
                names[appid] = g["name"]
            playtime[appid] = max(
                playtime.get(appid, 0), int(g.get("playtime_forever") or 0)
            )

    union = sorted(owners)
    print(f"union: {len(union)} уникальных appid")

    cache = {}
    if CACHE.exists() and not refresh:
        cache = {int(k): v for k, v in json.loads(CACHE.read_text()).items()}
    missing = [a for a in union if a not in cache]
    print(f"кеш: {len(cache)} записей, нужно дотянуть {len(missing)}")

    if missing:
        cache.update(fetch_items(missing))
        # повторная попытка для не ответивших — часть отказов транзиентная
        still = [a for a in missing if a not in cache or cache[a].get("success") != 1]
        if still:
            print(f"повтор для {len(still)} игр мелкими пачками")
            cache.update(fetch_items(still, batch=25))
        CACHE.write_text(json.dumps({str(k): v for k, v in cache.items()}))

    # распределение type/item_type — чтобы отсечь DLC/саундтреки осознанно
    dist = {}
    for a in union:
        it = cache.get(a) or {}
        dist[(it.get("type"), it.get("item_type"))] = (
            dist.get((it.get("type"), it.get("item_type")), 0) + 1
        )
    print("распределение (type,item_type):", sorted(dist.items(), key=lambda x: -x[1])[:10])

    unresolved = [a for a in union if (cache.get(a) or {}).get("success") != 1]
    print(f"без store-данных: {len(unresolved)} игр (категории неизвестны)")

    games = []
    for appid in union:
        it = cache.get(appid) or {}
        if it.get("success") != 1:
            continue
        cats = it.get("categories") or {}
        spc = cats.get("supported_player_categoryids") or []
        feat = cats.get("feature_categoryids") or []

        # В файл идёт всё про совместную игру, включая онлайн-кооп.
        # Какие режимы показывать — решают переключатели на странице.
        modes = [c for c in (CAT_SPLIT_COOP, CAT_SPLIT, CAT_SPLIT_PVP,
                             CAT_ONLINE_COOP, CAT_LAN_COOP) if c in spc]
        if not modes:
            continue
        split_coop = CAT_SPLIT_COOP in spc
        umbrella_coop = CAT_SPLIT in spc and CAT_COOP in spc
        same_device = split_coop or umbrella_coop
        split_pvp_only = (not same_device) and CAT_SPLIT_PVP in spc
        if it.get("type") not in (None, 0):
            continue

        rel = it.get("release") or {}
        ts = rel.get("steam_release_date") or rel.get("original_steam_release_date")
        rv = (it.get("reviews") or {}).get("summary_filtered") or {}
        plat = it.get("platforms") or {}
        deck = plat.get("steam_deck_compat_category", 0)

        games.append(
            {
                "appid": appid,
                "name": names.get(appid) or it.get("name") or f"App {appid}",
                "owners": owners[appid],
                "playtime": playtime.get(appid, 0),
                "spc": spc,          # сырые категории: фильтры собираются из них
                "sameDevice": same_device,
                "splitCoop": split_coop,
                "splitPvpOnly": split_pvp_only,
                "coop": CAT_COOP in spc,
                "onlineCoop": CAT_ONLINE_COOP in spc,
                "lanCoop": CAT_LAN_COOP in spc,
                "remotePlayTogether": CAT_RPT in feat,
                "releaseTs": ts,
                "reviewPercent": rv.get("percent_positive"),
                "reviewCount": rv.get("review_count"),
                "reviewScore": rv.get("review_score"),
                "reviewLabel": rv.get("review_score_label"),
                "deck": deck,
                "deckRank": deck_rank(deck),
                "storePath": it.get("store_url_path") or f"app/{appid}",
            }
        )

    same = sum(1 for g in games if g["sameDevice"])
    online = sum(1 for g in games if CAT_ONLINE_COOP in g["spc"])
    print(f"итог: {len(games)} игр про совместную игру; "
          f"локальный co-op {same}, онлайн-кооп {online}")

    payload = {
        "mode": "owned",
        "accounts": [
            {**a, "size": lib_sizes[a["key"]]} for a in ACCOUNTS
        ],
        "stats": {
            "union": len(union),
            "unresolved": len(unresolved),
            "sameDevice": same,
            "online": online,
            "total": len(games),
            "libraries": lib_sizes,
        },
        "games": sorted(games, key=lambda g: g["name"].lower()),
    }
    OUT.write_text(
        "// Сгенерировано tools/steam-coop/fetch.py — не редактировать вручную\n"
        "window.STEAM_COOP_DATA = "
        + json.dumps(payload, ensure_ascii=False, separators=(",", ":"))
        + ";\n",
        encoding="utf-8",
    )
    print(f"записано {OUT}")


if __name__ == "__main__":
    main()
