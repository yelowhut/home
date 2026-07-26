#!/usr/bin/env python3
"""Собирает игры для локального co-op из магазина Steam, КОТОРЫХ НЕТ на аккаунтах.

Список «что можно купить». Владение вычитается, поэтому пересекается с data.js по нулю.

Источники:
  * store/search/results  — перебор категорий 39 и 24 (обе нужны: 24 не надмножество 39,
                            встречаются игры с 39 без 24 — Jackbox 3, UNO, CoD WWII)
  * IPlayerService/GetOwnedGames — что уже есть, чтобы вычесть (нужен STEAM_API_KEY)
  * IStoreBrowseService/GetItems — категории, дата, отзывы, Deck, цена

Запуск:
  STEAM_API_KEY=... python3 tools/steam-coop/fetch_store.py [--min-reviews N] [--refresh]

Пишет store_data.js. Кеши: store_ids.json (выдача поиска), cache_store.json (данные магазина).
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
IDS_CACHE = HERE / "store_ids.json"
ITEM_CACHE = HERE / "cache_store.json"
OUT = HERE / "store_data.js"

ACCOUNTS = [
    {"key": "yelowhut", "steamid": "76561198297641574"},
    {"key": "cutlet", "steamid": "76561197999293155"},
]

# Перебираем все режимы, которые потом переключаются фильтрами на странице.
# Ни одна категория не надмножество другой: встречаются 39 без 24, 37 без 24 и т.п.
SWEEP_CATEGORIES = [39, 24, 37, 38, 48]
CAT_COOP, CAT_SPLIT, CAT_SPLIT_PVP, CAT_SPLIT_COOP = 9, 24, 37, 39
CAT_ONLINE_COOP, CAT_LAN_COOP, CAT_RPT = 38, 48, 44

PAGE = 100
BATCH = 200
STORE_URL = "https://api.steampowered.com/IStoreBrowseService/GetItems/v1/"
NOW = int(time.time())


def get_json(url, timeout=60):
    req = urllib.request.Request(url, headers={"Accept-Encoding": "identity"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.load(r)


def retrying(url, what, tries=6):
    """Поиск магазина щедро отдаёт 429, поэтому ждём с растущей паузой."""
    for attempt in range(tries):
        try:
            return get_json(url)
        except (urllib.error.URLError, urllib.error.HTTPError, TimeoutError) as e:
            code = getattr(e, "code", None)
            wait = (15 if code == 429 else 4) * (attempt + 1)
            print(f"  {what}: {e} — повтор через {wait}s", file=sys.stderr)
            time.sleep(wait)
    print(f"  {what}: НЕ УДАЛОСЬ", file=sys.stderr)
    return None


def sweep_category(cat):
    """Перебирает всю выдачу поиска по одной категории, возвращает набор appid."""
    import re

    found = set()
    failed = []
    start, total = 0, None
    while True:
        url = (
            "https://store.steampowered.com/search/results/?"
            + urllib.parse.urlencode(
                {
                    "query": "",
                    "start": start,
                    "count": PAGE,
                    "dynamic_data": "",
                    "category2": cat,
                    "json": 1,
                    "cc": "us",
                    "l": "english",
                    "infinite": 1,
                }
            )
        )
        d = retrying(url, f"поиск cat={cat} start={start}")
        if d is None:
            # НЕ обрываем перебор: одна упавшая страница — это дырка в данных,
            # а не конец списка. Пропускаем и идём дальше, потери считаем.
            failed.append(start)
            start += PAGE
            if total and start >= total:
                break
            time.sleep(3)
            continue
        if total is None:
            total = d.get("total_count") or 0
            print(f"  категория {cat}: всего {total}")
        html = d.get("results_html") or ""
        # у бандлов в data-ds-appid лежит список appid через запятую
        page_ids = set()
        for m in re.findall(r'data-ds-appid="([\d,]+)"', html):
            page_ids.update(int(x) for x in m.split(",") if x)
        if not page_ids:
            break
        found |= page_ids
        start += PAGE
        if total and start >= total:
            break
        time.sleep(1.5)
    if failed:
        print(f"  категория {cat}: ПОТЕРЯНО {len(failed)} страниц "
              f"(~{len(failed)*PAGE} игр), смещения: {failed[:10]}", file=sys.stderr)
    print(f"  категория {cat}: собрано {len(found)} appid из {total}")
    return found, failed


def fetch_owned(api_key):
    owned = set()
    for acc in ACCOUNTS:
        url = (
            "https://api.steampowered.com/IPlayerService/GetOwnedGames/v1/?"
            + urllib.parse.urlencode(
                {"key": api_key, "steamid": acc["steamid"], "include_played_free_games": 1,
                 "format": "json"}
            )
        )
        resp = (get_json(url) or {}).get("response", {})
        games = resp.get("games")
        if games is None:
            raise SystemExit(f"Библиотека {acc['steamid']} недоступна (профиль или ключ)")
        owned |= {g["appid"] for g in games}
        print(f"  {acc['key']}: {len(games)}")
    return owned


def fetch_items(appids, batch=BATCH):
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
                "include_all_purchase_options": True,
            },
        }
        url = STORE_URL + "?input_json=" + urllib.parse.quote(json.dumps(req))
        d = retrying(url, f"store пачка {n}")
        if d:
            for it in d.get("response", {}).get("store_items", []):
                if it.get("appid"):
                    out[it["appid"]] = it
        if n % 10 == 0 or n == len(batches):
            print(f"  store: пачка {n}/{len(batches)} -> {len(out)}")
        time.sleep(0.7)
    return out


def deck_rank(cat):
    return {3: 3, 2: 2, 1: 1}.get(cat, 0)


def price_of(it):
    """(центы, текст, бесплатна ли). У бесплатных best_purchase_option отсутствует."""
    if it.get("is_free") or (it.get("basic_info") or {}).get("is_free"):
        return None, "бесплатно", True
    opt = it.get("best_purchase_option") or {}
    cents = opt.get("final_price_in_cents")
    try:
        cents = int(cents) if cents is not None else None
    except (TypeError, ValueError):
        cents = None
    return cents, opt.get("formatted_final_price") or "", False


def main():
    api_key = os.environ.get("STEAM_API_KEY", "").strip()
    if not api_key:
        raise SystemExit("Нужна переменная окружения STEAM_API_KEY")
    refresh = "--refresh" in sys.argv
    min_reviews = 0
    if "--min-reviews" in sys.argv:
        min_reviews = int(sys.argv[sys.argv.index("--min-reviews") + 1])

    print("Владение:")
    owned = fetch_owned(api_key)
    print(f"  всего уникальных на аккаунтах: {len(owned)}")

    if IDS_CACHE.exists() and not refresh:
        swept = set(json.loads(IDS_CACHE.read_text()))
        print(f"выдача поиска из кеша: {len(swept)} appid")
    else:
        print("Перебор магазина (долго):")
        swept = set()
        lost_pages = 0
        for cat in SWEEP_CATEGORIES:
            ids, failed = sweep_category(cat)
            swept |= ids
            lost_pages += len(failed)
        IDS_CACHE.write_text(json.dumps(sorted(swept)))
        print(f"  объединение категорий: {len(swept)} appid")
        if lost_pages:
            print(f"  ВНИМАНИЕ: потеряно {lost_pages} страниц выдачи — список неполный. "
                  f"Повторите с --refresh, чтобы добрать.", file=sys.stderr)

    candidates = sorted(swept - owned)
    print(f"кандидаты (магазин минус владение): {len(candidates)}")

    cache = {}
    if ITEM_CACHE.exists() and not refresh:
        cache = {int(k): v for k, v in json.loads(ITEM_CACHE.read_text()).items()}
    missing = [a for a in candidates if a not in cache]
    print(f"кеш магазина: {len(cache)}, дотянуть {len(missing)}")
    if missing:
        cache.update(fetch_items(missing))
        still = [a for a in missing if (cache.get(a) or {}).get("success") != 1]
        if still:
            print(f"повтор для {len(still)} мелкими пачками")
            cache.update(fetch_items(still, batch=25))
        ITEM_CACHE.write_text(json.dumps({str(k): v for k, v in cache.items()}))

    unresolved = [a for a in candidates if (cache.get(a) or {}).get("success") != 1]
    print(f"без данных магазина: {len(unresolved)}")

    rows, coming = [], 0
    for appid in candidates:
        it = cache.get(appid) or {}
        if it.get("success") != 1 or it.get("type") not in (None, 0):
            continue
        if it.get("visible") is False:
            continue
        cats = it.get("categories") or {}
        spc = cats.get("supported_player_categoryids") or []
        feat = cats.get("feature_categoryids") or []

        # В файл идёт всё, что вообще про совместную игру — режимы разбираются
        # переключателями на странице, а не здесь.
        modes = [c for c in (CAT_SPLIT_COOP, CAT_SPLIT, CAT_SPLIT_PVP,
                             CAT_ONLINE_COOP, CAT_LAN_COOP) if c in spc]
        if not modes:
            continue
        split_coop = CAT_SPLIT_COOP in spc
        umbrella = CAT_SPLIT in spc and CAT_COOP in spc
        same_device = split_coop or umbrella
        split_pvp_only = (not same_device) and CAT_SPLIT_PVP in spc

        rel = it.get("release") or {}
        ts = rel.get("steam_release_date") or rel.get("original_steam_release_date") or None
        soon = bool(ts and ts > NOW)
        if soon:
            coming += 1
        rv = (it.get("reviews") or {}).get("summary_filtered") or {}
        plat = it.get("platforms") or {}
        deck = plat.get("steam_deck_compat_category", 0)
        cents, ptext, free = price_of(it)

        rows.append(
            {
                "appid": appid,
                "name": it.get("name") or f"App {appid}",
                "owners": [],
                "spc": spc,          # сырые категории: фильтры собираются из них
                "sameDevice": same_device,
                "splitCoop": split_coop,
                "splitPvpOnly": split_pvp_only,
                "coop": CAT_COOP in spc,
                "onlineCoop": CAT_ONLINE_COOP in spc,
                "lanCoop": CAT_LAN_COOP in spc,
                "remotePlayTogether": CAT_RPT in feat,
                "releaseTs": ts,
                "comingSoon": soon,
                "reviewPercent": rv.get("percent_positive"),
                "reviewCount": rv.get("review_count"),
                "reviewScore": rv.get("review_score"),
                "reviewLabel": rv.get("review_score_label"),
                "deck": deck,
                "deckRank": deck_rank(deck),
                "priceCents": cents,
                "priceText": ptext,
                "isFree": free,
                "storePath": it.get("store_url_path") or f"app/{appid}",
            }
        )

    # гистограмма отзывов — по ней выбирается порог, а не наугад
    print(f"\nпрошли предикат: {len(rows)} (из них не вышли: {coming})")
    print("распределение по числу отзывов (сколько останется при пороге):")
    for cut in (0, 10, 25, 50, 100, 250, 500, 1000, 5000):
        n = sum(1 for r in rows if (r["reviewCount"] or 0) >= cut)
        print(f"  >= {cut:5d} отзывов: {n:6d}")

    # У ещё не вышедших игр отзывов нет по определению, порог вырезал бы их все
    # и фильтр «показать не вышедшие» стал бы мёртвым. Порог — только для вышедших.
    kept = [r for r in rows if r["comingSoon"] or (r["reviewCount"] or 0) >= min_reviews]
    dropped = len(rows) - len(kept)
    same = sum(1 for r in kept if r["sameDevice"])
    print(f"\nпорог {min_reviews} отзывов -> оставлено {len(kept)}, отброшено {dropped}")
    # разбивка по режимам: суммы пересекаются, одна игра бывает и локальной, и онлайновой
    for cid, cname in ((CAT_SPLIT_COOP, "39 split-screen co-op"),
                       (CAT_SPLIT, "24 общий экран"),
                       (CAT_SPLIT_PVP, "37 split-screen PvP"),
                       (CAT_ONLINE_COOP, "38 онлайн-кооп"),
                       (CAT_LAN_COOP, "48 LAN-кооп")):
        print(f"  {cname}: {sum(1 for r in kept if cid in r['spc'])}")

    payload = {
        "mode": "store",
        "accounts": [],
        "stats": {
            "swept": len(swept),
            "owned": len(owned),
            "candidates": len(candidates),
            "unresolved": len(unresolved),
            "matched": len(rows),
            "dropped": dropped,
            "minReviews": min_reviews,
            "comingSoon": coming,
            "sameDevice": same,
        },
        "games": sorted(kept, key=lambda r: r["name"].lower()),
    }
    OUT.write_text(
        "// Сгенерировано tools/steam-coop/fetch_store.py — не редактировать вручную\n"
        "window.STEAM_COOP_DATA = "
        + json.dumps(payload, ensure_ascii=False, separators=(",", ":"))
        + ";\n",
        encoding="utf-8",
    )
    print(f"записано {OUT} ({OUT.stat().st_size/1024:.0f} КБ)")


if __name__ == "__main__":
    main()
