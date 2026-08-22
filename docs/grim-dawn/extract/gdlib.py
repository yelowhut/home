# -*- coding: utf-8 -*-
"""Общая библиотека доступа к данным Grim Dawn.

Три слоя:
  ARZ  — читает один .arz (LZ4-сжатая БД записей игры)
  DB   — сливает 4 .arz в один namespace (gdx3 > gdx2 > gdx1 > base)
  Tags — резолвит tagXxx -> человекочитаемая строка (из data/tags_en.json)

Пути берутся из окружения:
  GD_DIR   — установка игры (по умолчанию C:/games/Steam/steamapps/common/Grim Dawn)
  GD_DATA  — куда пишем извлечённое (по умолчанию <repo>/data/grim-dawn)
"""
import json
import os
import re
import struct
import sqlite3
import sys

# Консоль Windows по умолчанию cp1252 — любой print с кириллицей/юникодом падает.
# Чиним один раз здесь: все скрипты пайплайна импортируют gdlib.
for _s in (sys.stdout, sys.stderr):
    try:
        _s.reconfigure(encoding="utf-8", errors="replace")
    except (AttributeError, ValueError):
        pass

try:
    import lz4.block as _lz4
except ImportError:  # pragma: no cover
    _lz4 = None

GD_DIR = os.environ.get("GD_DIR", "C:/games/Steam/steamapps/common/Grim Dawn")
GD_DATA = os.environ.get(
    "GD_DATA",
    os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                  "..", "..", "..", "data", "grim-dawn")),
)

# Порядок важен: более поздние аддоны перекрывают записи с тем же именем.
ARZ_FILES = [
    ("base", "database/database.arz"),
    ("gdx1", "gdx1/database/GDX1.arz"),
    ("gdx2", "gdx2/database/GDX2.arz"),
    ("gdx3", "gdx3/database/GDX3.arz"),
]


def _lz4_block_decompress_py(src, dest_size):
    """Чистый Python на случай отсутствия пакета lz4. Медленно — только fallback."""
    out = bytearray()
    i, n = 0, len(src)
    while i < n:
        tok = src[i]; i += 1
        ll = tok >> 4
        if ll == 15:
            while True:
                b = src[i]; i += 1; ll += b
                if b != 255:
                    break
        out += src[i:i + ll]; i += ll
        if i >= n or len(out) >= dest_size:
            break
        off = src[i] | (src[i + 1] << 8); i += 2
        ml = tok & 0x0F
        if ml == 15:
            while True:
                b = src[i]; i += 1; ml += b
                if b != 255:
                    break
        ml += 4
        start = len(out) - off
        for j in range(ml):
            out.append(out[start + j])
    return bytes(out[:dest_size])


def _decompress(src, dest_size):
    if _lz4 is not None:
        return _lz4.decompress(src, uncompressed_size=dest_size)
    return _lz4_block_decompress_py(src, dest_size)


class ARZ:
    """Один .arz файл. Заголовок -> таблица строк -> заголовки записей -> тело."""

    def __init__(self, path):
        self.path = path
        self.d = open(path, "rb").read()
        (_unk, _ver, self.rt_start, self.rt_size, self.rt_entries,
         self.st_start, self.st_size) = struct.unpack_from("<hhiiiii", self.d, 0)
        self._read_string_table()
        self._read_record_headers()

    def _read_string_table(self):
        p = self.st_start
        cnt = struct.unpack_from("<i", self.d, p)[0]; p += 4
        st = []
        for _ in range(cnt):
            ln = struct.unpack_from("<i", self.d, p)[0]; p += 4
            st.append(self.d[p:p + ln].decode("latin-1")); p += ln
        self.st = st

    def _read_record_headers(self):
        p = self.rt_start
        hdrs = []
        for _ in range(self.rt_entries):
            fn = struct.unpack_from("<i", self.d, p)[0]; p += 4
            tl = struct.unpack_from("<i", self.d, p)[0]; p += 4
            typ = self.d[p:p + tl].decode("latin-1"); p += tl
            off, cs, ds, _u1, _u2 = struct.unpack_from("<iiiii", self.d, p); p += 20
            hdrs.append({"name": self.st[fn], "type": typ, "off": off, "cs": cs, "ds": ds})
        self.hdrs = hdrs

    def record(self, hdr):
        """Раскодировать запись в dict {fieldname: value|[values]}."""
        raw = self.d[hdr["off"] + 24: hdr["off"] + 24 + hdr["cs"]]
        dec = _decompress(raw, hdr["ds"])
        rec = {}
        p, n = 0, len(dec)
        while p + 8 <= n:
            typ, cnt = struct.unpack_from("<hh", dec, p); p += 4
            fnidx = struct.unpack_from("<i", dec, p)[0]; p += 4
            fname = self.st[fnidx]
            vals = []
            for _ in range(cnt):
                if typ == 1:
                    vals.append(struct.unpack_from("<f", dec, p)[0])
                elif typ == 2:
                    vals.append(self.st[struct.unpack_from("<i", dec, p)[0]])
                else:
                    vals.append(struct.unpack_from("<i", dec, p)[0])
                p += 4
            rec[fname] = vals[0] if cnt == 1 else vals
        return rec


class DB:
    """Слитый namespace всех .arz. Имена записей нормализованы: lowercase, '/'."""

    def __init__(self, gd_dir=None, lazy=True):
        self.gd_dir = gd_dir or GD_DIR
        self.arz = {}
        self.index = {}   # norm_name -> (src, hdr)
        self._cache = {}
        for src, rel in ARZ_FILES:
            path = os.path.join(self.gd_dir, rel)
            if not os.path.exists(path):
                continue
            az = ARZ(path)
            self.arz[src] = az
            for hdr in az.hdrs:
                self.index[norm(hdr["name"])] = (src, hdr)

    def __len__(self):
        return len(self.index)

    def get(self, name):
        """Запись по имени (регистр/слэши неважны). None если нет."""
        key = norm(name)
        if key in self._cache:
            return self._cache[key]
        ent = self.index.get(key)
        if ent is None:
            return None
        src, hdr = ent
        rec = self.arz[src].record(hdr)
        rec["__name"] = hdr["name"]
        rec["__type"] = hdr["type"]
        rec["__src"] = src
        self._cache[key] = rec
        return rec

    def type_of(self, name):
        ent = self.index.get(norm(name))
        return ent[1]["type"] if ent else None

    def names_by_type(self, *types):
        want = set(types)
        return [hdr["name"] for _src, hdr in self.index.values() if hdr["type"] in want]

    def names_matching(self, substr):
        s = substr.lower()
        return [hdr["name"] for k, (_src, hdr) in self.index.items() if s in k]

    def iter_records(self, types=None, prefix=None):
        """Итерирует (name, record). types — фильтр по типу, prefix — по пути."""
        want = set(types) if types else None
        pre = norm(prefix) if prefix else None
        for key, (src, hdr) in self.index.items():
            if want and hdr["type"] not in want:
                continue
            if pre and not key.startswith(pre):
                continue
            yield hdr["name"], self.get(hdr["name"])

    def type_counts(self):
        from collections import Counter
        return Counter(hdr["type"] for _src, hdr in self.index.values())


def norm(name):
    return name.replace("\\", "/").lower()


# Тэги игры содержат управляющие коды форматирования вида ^k, ^N (2283 тэга из 20245):
# '^kDread Skull'. Это разметка для игрового UI, в данных она не нужна никому —
# снимаем централизованно, иначе каждый экстрактор чистит их сам и кто-нибудь забудет.
_FMT_CODES = re.compile(r"\^[a-zA-Z]")


def strip_codes(s):
    return _FMT_CODES.sub("", s) if isinstance(s, str) else s


class Tags:
    """tagXxx -> строка. Источник: data/tags_en.json (см. 00_text.py).

    Коды форматирования снимаются по умолчанию; raw=True отдаёт строку как в игре.
    """

    def __init__(self, path=None, raw=False):
        path = path or os.path.join(GD_DATA, "tags_en.json")
        self.raw = raw
        with open(path, encoding="utf-8") as f:
            self.t = json.load(f)
        if not raw:
            self.t = {k: strip_codes(v) for k, v in self.t.items()}

    def __contains__(self, k):
        return k in self.t

    def get(self, key, default=None):
        if not key:
            return default
        return self.t.get(key, default)

    def __call__(self, key, default=None):
        """Резолв с fallback на сам тэг — чтобы в выводе было видно недостающее."""
        if not key:
            return default
        return self.t.get(key, default if default is not None else key)

    def item_name(self, rec):
        """Имя предмета из записи (itemNameTag, иначе description/FileDescription)."""
        if not rec:
            return None
        for f in ("itemNameTag", "description", "skillDisplayName", "petDisplayName"):
            v = rec.get(f)
            if isinstance(v, str) and v:
                r = self.t.get(v)
                if r:
                    return r
        return rec.get("FileDescription") or rec.get("__name")


def open_sqlite(path=None, readonly=False):
    """Открыть gd.sqlite (полный дамп записей, см. 01_dump.py)."""
    path = path or os.path.join(GD_DATA, "gd.sqlite")
    if readonly:
        con = sqlite3.connect(f"file:{path}?mode=ro", uri=True)
    else:
        con = sqlite3.connect(path)
    con.row_factory = sqlite3.Row
    return con


def out_path(*parts):
    """Путь внутри GD_DATA, создаёт директории."""
    p = os.path.join(GD_DATA, *parts)
    os.makedirs(os.path.dirname(p), exist_ok=True)
    return p


def write_json(rel, obj, indent=None):
    p = out_path(rel)
    with open(p, "w", encoding="utf-8") as f:
        json.dump(obj, f, ensure_ascii=False, indent=indent)
    return p, os.path.getsize(p)


def write_jsonl(rel, rows):
    p = out_path(rel)
    with open(p, "w", encoding="utf-8") as f:
        for r in rows:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")
    return p, os.path.getsize(p)


if __name__ == "__main__":
    db = DB()
    print("GD_DIR :", GD_DIR)
    print("GD_DATA:", GD_DATA)
    print("merged records:", len(db))
    for src, az in db.arz.items():
        print(f"  {src}: {len(az.hdrs)} records")
    tc = db.type_counts()
    print("types:", len(tc))
    for t, n in tc.most_common(15):
        print(f"   {t or '(empty)'}: {n}")
