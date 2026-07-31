# -*- coding: utf-8 -*-
"""Шаг 0: распаковать Text_EN.arc (+ аддоны) и собрать tags_en.json.

Тэги живут в нескольких .arc: базовый resources/Text_EN.arc и по одному
на каждый аддон (gdx1/2/3/resources/Text_EN.arc). Порядок слияния —
как у .arz: аддоны перекрывают базу.

Запуск:  python 00_text.py
Выход:   <GD_DATA>/tags_en.json  +  <GD_DATA>/raw/text_en/ (сырые .txt)
"""
import os
import subprocess
import sys

from gdlib import GD_DIR, GD_DATA, out_path, write_json

ARC_SOURCES = [
    ("base", "resources/Text_EN.arc"),
    ("gdx1", "gdx1/resources/Text_EN.arc"),
    ("gdx2", "gdx2/resources/Text_EN.arc"),
    ("gdx3", "gdx3/resources/Text_EN.arc"),
]


def extract_arc(arc_rel, dest):
    """ArchiveTool.exe <arc> -extract <dir>. Кладёт файлы в <dir>/<имя арки>/."""
    tool = os.path.join(GD_DIR, "ArchiveTool.exe")
    arc = os.path.join(GD_DIR, arc_rel)
    if not os.path.exists(arc):
        return None
    os.makedirs(dest, exist_ok=True)
    r = subprocess.run([tool, arc, "-extract", dest],
                       cwd=GD_DIR, capture_output=True, text=True)
    if r.returncode != 0:
        print(f"  ! ArchiveTool rc={r.returncode} на {arc_rel}: {r.stderr[:200]}",
              file=sys.stderr)
    return dest


def parse_tag_files(root):
    """Разобрать все tags_*.txt: строки вида key=value, # — комментарий."""
    tags = {}
    for dirpath, _dirs, files in os.walk(root):
        for fn in files:
            if not fn.lower().startswith("tags") or not fn.lower().endswith(".txt"):
                continue
            path = os.path.join(dirpath, fn)
            # Файлы игры — UTF-8 (иногда с BOM), редко cp1252.
            for enc in ("utf-8-sig", "utf-8", "cp1252"):
                try:
                    with open(path, encoding=enc) as f:
                        lines = f.read().splitlines()
                    break
                except UnicodeDecodeError:
                    continue
            else:
                print(f"  ! не смог декодировать {path}", file=sys.stderr)
                continue
            for line in lines:
                line = line.strip()
                if not line or line.startswith("#") or "=" not in line:
                    continue
                k, v = line.split("=", 1)
                tags[k.strip()] = v.strip()
    return tags


def main():
    raw_root = out_path("raw", "text_en", ".keep").rsplit(os.sep, 1)[0]
    all_tags = {}
    for src, rel in ARC_SOURCES:
        dest = os.path.join(raw_root, src)
        print(f"[{src}] {rel} -> {dest}")
        if extract_arc(rel, dest) is None:
            print(f"  (нет файла, пропуск)")
            continue
        t = parse_tag_files(dest)
        print(f"  тэгов: {len(t)}")
        all_tags.update(t)  # аддоны перекрывают базу

    path, size = write_json("tags_en.json", all_tags)
    print(f"\nИТОГО тэгов: {len(all_tags)}")
    print(f"Записано: {path} ({size/1024:.0f} KB)")

    # Санити-чек: тэги, которые обязаны существовать.
    probes = ["tagWeaponSwordA000", "tagSkillClassName01", "tagRelicE001"]
    for p in probes:
        print(f"  проба {p} = {all_tags.get(p, '!!! НЕТ')}")


if __name__ == "__main__":
    main()
