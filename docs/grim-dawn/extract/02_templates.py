# -*- coding: utf-8 -*-
"""Шаг 2: распаковать templates.arc → словарь схемы полей .dbr.

Зачем: `.arz` хранит только имена полей и значения, без смысла. А `database/templates.arc`
— это редакторские шаблоны DBR, где для каждого поля указаны тип, класс, описание,
значение по умолчанию и группа (человекочитаемая категория). Это авторитетный ответ
на вопрос «что значит поле X», вместо угадывания по данным.

Формат .tpl — фигурные скобки:
    Group
    {
        name = "Defensive Fire"
        type = "list"
        Variable
        {
            name = "defensiveFire"     <- реальное имя поля .dbr
            class = "array"
            type  = "real"
            description = "..."
            defaultValue = ""
        }
    }

Запуск:  python 02_templates.py
Выход:   <GD_DATA>/field_schema.json      поле .dbr -> {тип, класс, описание, группы, шаблоны}
         <GD_DATA>/template_types.json    шаблон -> список его полей
"""
import os
import re
import subprocess
import sys
from collections import defaultdict

from gdlib import GD_DIR, GD_DATA, out_path, write_json

ARC_SOURCES = [
    ("base", "database/templates.arc"),
    ("gdx1", "gdx1/database/templates.arc"),
    ("gdx2", "gdx2/database/templates.arc"),
    ("gdx3", "gdx3/database/templates.arc"),
]

KV = re.compile(r'^\s*(\w+)\s*=\s*"?(.*?)"?\s*$')


def extract_arc(arc_rel, dest):
    tool = os.path.join(GD_DIR, "ArchiveTool.exe")
    arc = os.path.join(GD_DIR, arc_rel)
    if not os.path.exists(arc):
        return False
    os.makedirs(dest, exist_ok=True)
    subprocess.run([tool, arc, "-extract", dest], cwd=GD_DIR,
                   capture_output=True, text=True)
    return True


def parse_tpl(text):
    """Разбирает .tpl в дерево. Возвращает список блоков верхнего уровня.

    Блок = {"__kind": "Group"|"Variable", <ключи>, "__children": [...]}.
    Формат простой и регулярный, поэтому хватает построчного разбора со стеком.
    """
    root = {"__kind": "root", "__children": []}
    stack = [root]
    pending = None  # имя блока, увиденное перед '{'
    for line in text.splitlines():
        s = line.strip()
        if not s:
            continue
        if s == "{":
            node = {"__kind": pending or "Block", "__children": []}
            stack[-1]["__children"].append(node)
            stack.append(node)
            pending = None
            continue
        if s == "}":
            if len(stack) > 1:
                stack.pop()
            continue
        m = KV.match(s)
        if m:
            k, v = m.group(1), m.group(2)
            # 'name'/'type' встречаются и как ключ блока — не затираем детей
            stack[-1][k] = v
            pending = None
        else:
            pending = s.split()[0] if s.split() else None
    return root["__children"]


def walk(nodes, group_path, out_fields, tpl_name):
    for n in nodes:
        kind = n.get("__kind")
        if kind == "Variable":
            fname = n.get("name")
            if not fname:
                continue
            e = out_fields[fname]
            if n.get("type"):
                e["types"].add(n["type"])
            if n.get("class"):
                e["classes"].add(n["class"])
            d = (n.get("description") or "").strip()
            if d:
                e["descriptions"].add(d)
            dv = (n.get("defaultValue") or "").strip()
            if dv:
                e["defaults"].add(dv)
            for g in group_path:
                if g:
                    e["groups"].add(g)
            e["templates"].add(tpl_name)
        children = n.get("__children") or []
        if children:
            gp = group_path
            if kind == "Group" and n.get("name"):
                gp = group_path + [n["name"]]
            walk(children, gp, out_fields, tpl_name)


def main():
    raw_root = os.path.join(GD_DATA, "raw", "templates")
    got = []
    for src, rel in ARC_SOURCES:
        dest = os.path.join(raw_root, src)
        if extract_arc(rel, dest):
            got.append((src, dest))
            print(f"[{src}] {rel} распакован")
        else:
            print(f"[{src}] {rel} — нет файла, пропуск")

    fields = defaultdict(lambda: {"types": set(), "classes": set(), "descriptions": set(),
                                  "defaults": set(), "groups": set(), "templates": set()})
    tpl_fields = defaultdict(set)
    n_tpl = 0
    for _src, root in got:
        for dirpath, _dirs, files in os.walk(root):
            for fn in files:
                if not fn.lower().endswith(".tpl"):
                    continue
                path = os.path.join(dirpath, fn)
                # 'copy of copy of X.tpl' — редакторский мусор, дублирует оригинал
                if fn.lower().startswith("copy "):
                    continue
                for enc in ("utf-8-sig", "utf-8", "cp1252", "latin-1"):
                    try:
                        text = open(path, encoding=enc).read()
                        break
                    except UnicodeDecodeError:
                        continue
                else:
                    print(f"  ! не декодировал {path}", file=sys.stderr)
                    continue
                tpl_name = os.path.splitext(fn)[0]
                n_tpl += 1
                before = set(fields)
                walk(parse_tpl(text), [], fields, tpl_name)
                tpl_fields[tpl_name] |= (set(fields) - before)

    # Второй проход: точный состав полей каждого шаблона (не только новых).
    tpl_fields = defaultdict(set)
    for fname, e in fields.items():
        for t in e["templates"]:
            tpl_fields[t].add(fname)

    schema = {}
    for fname, e in sorted(fields.items()):
        schema[fname] = {
            "type": sorted(e["types"]),
            "class": sorted(e["classes"]),
            "description": sorted(e["descriptions"]),
            "default": sorted(e["defaults"]),
            "groups": sorted(e["groups"]),
            "templates": sorted(e["templates"]),
        }
    p1, s1 = write_json("field_schema.json", schema, indent=1)
    p2, s2 = write_json("template_types.json",
                        {k: sorted(v) for k, v in sorted(tpl_fields.items())}, indent=1)

    print(f"\nШаблонов разобрано: {n_tpl}")
    print(f"Уникальных полей .dbr: {len(schema)}")
    print(f"  с непустым описанием: {sum(1 for v in schema.values() if v['description'])}")
    print(f"{p1} ({s1/1024:.0f} KB)")
    print(f"{p2} ({s2/1024:.0f} KB)")

    for probe in ("defensiveFire", "offensivePhysicalMin", "itemSkillName",
                  "prefixTableName1", "maxDevotionPoints", "conversionInType"):
        v = schema.get(probe)
        if v:
            print(f"  проба {probe}: type={v['type']} class={v['class']} "
                  f"groups={v['groups'][:2]} desc={v['description'][:1]}")
        else:
            print(f"  проба {probe}: НЕТ в шаблонах")


if __name__ == "__main__":
    main()
