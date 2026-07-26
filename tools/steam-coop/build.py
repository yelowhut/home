#!/usr/bin/env python3
"""Собирает index.html + data.js в один переносимый файл dist/steam-coop.html.

Нужен, чтобы закинуть страницу на телефон одним файлом: внешних зависимостей нет,
интернет для открытия не требуется (ссылки на магазин, само собой, требуют).

Запуск:
  python3 tools/steam-coop/build.py

Данные не перекачивает — берёт готовый data.js. Обновить данные: fetch.py.
"""

import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
OUT = HERE / "dist" / "steam-coop.html"

# Порядок важен: логика страницы читает и данные, и список скрытых на старте.
# hidden.js может отсутствовать (свежий клон) — тогда вшиваем пустой список.
PAGES = [
    {
        "shell": "index.html",
        "out": "steam-coop.html",
        "scripts": [
            {"name": "data.js", "required": True},
            {"name": "hidden.js", "required": False,
             "fallback": "window.STEAM_COOP_HIDDEN = [];"},
            {"name": "page.js", "required": True},
        ],
    },
    {
        "shell": "store.html",
        "out": "steam-coop-store.html",
        "scripts": [
            {"name": "store_data.js", "required": True},
            {"name": "hidden_store.js", "required": False,
             "fallback": "window.STEAM_COOP_HIDDEN = [];"},
            {"name": "page.js", "required": True},
        ],
    },
]

CSS = "page.css"


def tag_re(name):
    return re.compile(r'[ \t]*<script src="%s"></script>\n?' % re.escape(name))


def css_re(name):
    return re.compile(r'[ \t]*<link rel="stylesheet" href="%s">\n?' % re.escape(name))


def escape_js(text):
    # Любая последовательность "</" внутри JS-строки закрыла бы <script> раньше времени
    # и страница молча умерла бы. В JS-литералах "<\/" эквивалентно "</".
    return text.replace("</", "<\\/").rstrip()


def build_page(page):
    shell_path = HERE / page["shell"]
    if not shell_path.exists():
        return None
    bundle = shell_path.read_text(encoding="utf-8")

    css_tag = css_re(CSS)
    if css_tag.search(bundle):
        css = (HERE / CSS).read_text(encoding="utf-8").rstrip()
        bundle = css_tag.sub(lambda _: "<style>\n" + css + "\n</style>\n", bundle, count=1)

    for spec in page["scripts"]:
        name = spec["name"]
        tag = tag_re(name)
        name = spec["name"]
        tag = tag_re(name)
        if not tag.search(bundle):
            raise SystemExit(f'В {page["shell"]} не найден <script src="{name}"></script>')

        path = HERE / name
        if path.exists():
            body = path.read_text(encoding="utf-8")
        elif spec["required"]:
            raise SystemExit(f"Нет {name} — сначала запустите fetch.py / fetch_store.py")
        else:
            body = spec["fallback"]
            print(f"  {name} отсутствует — вшит пустой список")

        bundle = tag.sub(
            lambda _, t=escape_js(body): "<script>\n" + t + "\n</script>\n",
            bundle, count=1,
        )

    out = HERE / "dist" / page["out"]
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(bundle, encoding="utf-8")

    # ${...} — шаблонные строки внутри вшитого JS, а не ссылки на файлы
    leftovers = [
        m for m in re.findall(r'(?:src|href)="(?!https?://|steam://|#)[^"]+"', bundle)
        if "${" not in m
    ]
    if leftovers:
        print("  ВНИМАНИЕ, остались локальные ссылки:", leftovers, file=sys.stderr)
    return out


def main():
    built = 0
    for page in PAGES:
        out = build_page(page)
        if out is None:
            print(f"{page['shell']} нет — пропущено")
            continue
        print(f"{out} — {out.stat().st_size/1024:.0f} КБ, внешних файлов нет")
        built += 1
    if not built:
        raise SystemExit("Нечего собирать")


if __name__ == "__main__":
    main()
