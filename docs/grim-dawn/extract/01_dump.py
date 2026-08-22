# -*- coding: utf-8 -*-
"""Шаг 1: полный дамп всех записей БД игры в gd.sqlite.

Это фундамент для всех экстракторов: дальше никто не парсит .arz заново,
все работают SQL-ом по одной таблице.

Схема:
  records(name PK, orig_name, type, src, fields)   fields = JSON {поле: значение}
  tags(tag PK, text)                               из tags_en.json
  meta(key PK, value)                              счётчики/версия

Запуск:  python 01_dump.py
Выход:   <GD_DATA>/gd.sqlite
"""
import json
import os
import time

from gdlib import DB, GD_DATA, ARZ_FILES, norm, out_path

DDL = """
PRAGMA journal_mode=OFF;
PRAGMA synchronous=OFF;
DROP TABLE IF EXISTS records;
DROP TABLE IF EXISTS tags;
DROP TABLE IF EXISTS meta;
CREATE TABLE records (
    name      TEXT PRIMARY KEY,   -- нормализованное: lowercase, прямые слэши
    orig_name TEXT NOT NULL,      -- как в .arz
    type      TEXT NOT NULL,      -- Class-подобный тип записи (может быть '')
    src       TEXT NOT NULL,      -- base | gdx1 | gdx2 | gdx3 (кто победил при слиянии)
    fields    TEXT NOT NULL       -- JSON объект полей .dbr
);
CREATE INDEX idx_records_type ON records(type);
CREATE INDEX idx_records_src  ON records(src);
CREATE TABLE tags (tag TEXT PRIMARY KEY, text TEXT NOT NULL);
CREATE TABLE meta (key TEXT PRIMARY KEY, value TEXT NOT NULL);
"""


def main():
    t0 = time.time()
    db = DB()
    print(f"слито записей: {len(db)} из {len(db.arz)} .arz")

    path = out_path("gd.sqlite")
    if os.path.exists(path):
        os.remove(path)
    import sqlite3
    con = sqlite3.connect(path)
    con.executescript(DDL)

    rows = []
    n = 0
    for key, (src, hdr) in db.index.items():
        rec = db.arz[src].record(hdr)
        rows.append((key, hdr["name"], hdr["type"], src,
                     json.dumps(rec, ensure_ascii=False)))
        n += 1
        if len(rows) >= 2000:
            con.executemany("INSERT INTO records VALUES (?,?,?,?,?)", rows)
            rows.clear()
            if n % 20000 == 0:
                print(f"  {n} ... {time.time()-t0:.0f}s")
    if rows:
        con.executemany("INSERT INTO records VALUES (?,?,?,?,?)", rows)

    tags_path = os.path.join(GD_DATA, "tags_en.json")
    if os.path.exists(tags_path):
        with open(tags_path, encoding="utf-8") as f:
            tags = json.load(f)
        con.executemany("INSERT INTO tags VALUES (?,?)", list(tags.items()))
        print(f"тэгов: {len(tags)}")

    con.executemany("INSERT INTO meta VALUES (?,?)", [
        ("records", str(n)),
        ("arz_files", json.dumps([r for _s, r in ARZ_FILES])),
        ("built_seconds", f"{time.time()-t0:.1f}"),
    ])
    con.commit()
    con.execute("VACUUM")
    con.close()

    size = os.path.getsize(path)
    print(f"\nЗаписано {n} записей -> {path} ({size/1024/1024:.0f} MB) за {time.time()-t0:.0f}s")

    # Санити-чек
    con = sqlite3.connect(path)
    for probe in ("records/items/materia/compa_frozenheart.dbr",
                  "records/skills/soldier/cadence.dbr"):
        r = con.execute("SELECT type, src FROM records WHERE name=?", (norm(probe),)).fetchone()
        print(f"  проба {probe} -> {r}")
    print("  топ типов:")
    for t, c in con.execute(
            "SELECT type, COUNT(*) c FROM records GROUP BY type ORDER BY c DESC LIMIT 10"):
        print(f"    {t or '(пусто)'}: {c}")
    con.close()


if __name__ == "__main__":
    main()
