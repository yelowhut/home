#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
eso_deps.py — проверка и доустановка зависимостей аддонов The Elder Scrolls Online.

Что делает:
  1. читает манифесты установленных аддонов (<Имя>/<Имя>.txt или <Имя>/<Имя>.addon)
     и строит граф зависимостей из директив ## DependsOn, ## PCDependsOn,
     ## ConsoleDependsOn и ## OptionalDependsOn;
  2. показывает список аддонов с цветным индикатором состояния зависимостей;
  3. если всё на месте — предлагает завершить работу;
  4. если нет — резолвит недостающие библиотеки в каталоге ESOUI (api.mmoui.com),
     показывает план и спрашивает подтверждение;
  5. перед установкой делает zip-бэкап всей папки AddOns и печатает путь к нему;
  6. ставит библиотеки, пересчитывает граф до сходимости (у библиотек есть свои
     зависимости) и выводит итоговый статус.

Только стандартная библиотека Python 3.9+. Ничего не удаляет.
"""

from __future__ import annotations

import argparse
import hashlib
import io
import json
import os
import re
import sys
import time
import urllib.error
import urllib.request
import zipfile
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Iterable

DEFAULT_ADDONS_DIR = Path.home() / "Documents" / "Elder Scrolls Online" / "live" / "AddOns"
FILELIST_URL = "https://api.mmoui.com/v3/game/ESO/filelist.json"
FILEDETAILS_URL = "https://api.mmoui.com/v3/game/ESO/filedetails/{uid}.json"
USER_AGENT = "eso-addon-deps/1.0 (local dependency resolver)"
CACHE_TTL = 24 * 3600
MAX_ROUNDS = 6
MANIFEST_SUFFIXES = (".txt", ".addon")
DIRECTIVE_RE = re.compile(r"^\s*##\s*([A-Za-z0-9_.\-]+)\s*:\s*(.*)$")

# Обязательные зависимости объявляются тремя директивами: общей и двумя
# платформенными. Игнорировать платформенную — значит пропустить реальные
# требования (BeamMeUp просит LibZone/LibScrollableMenu только через PCDependsOn).
REQUIRED_KEYS = {
    "pc": ("dependson", "pcdependson"),
    "console": ("dependson", "consoledependson"),
}
OTHER_PLATFORM_KEY = {"pc": "consoledependson", "console": "pcdependson"}

# --------------------------------------------------------------------------- вывод


class C:
    """ANSI-цвета с автоотключением."""

    enabled = False
    RESET = BOLD = DIM = RED = GREEN = YELLOW = CYAN = GREY = ""

    @classmethod
    def setup(cls, want_color: bool) -> None:
        if not want_color or os.environ.get("NO_COLOR") or not sys.stdout.isatty():
            return
        if os.name == "nt":
            # включаем ENABLE_VIRTUAL_TERMINAL_PROCESSING, иначе PS 5.1 покажет мусор
            try:
                import ctypes

                k = ctypes.windll.kernel32
                mode = ctypes.c_uint32()
                handle = k.GetStdHandle(-11)
                if not k.GetConsoleMode(handle, ctypes.byref(mode)):
                    return
                k.SetConsoleMode(handle, mode.value | 0x0004)
            except Exception:
                return
        cls.enabled = True
        cls.RESET, cls.BOLD, cls.DIM = "\033[0m", "\033[1m", "\033[2m"
        cls.RED, cls.GREEN, cls.YELLOW = "\033[91m", "\033[92m", "\033[93m"
        cls.CYAN, cls.GREY = "\033[96m", "\033[90m"


def out(text: str = "") -> None:
    print(text)


def header(text: str) -> None:
    out(f"\n{C.BOLD}{text}{C.RESET}")
    out(C.DIM + "─" * max(len(text), 8) + C.RESET)


def ask(question: str, default: bool = True, assume_yes: bool = False) -> bool:
    suffix = "[Y/n]" if default else "[y/N]"
    if assume_yes:
        out(f"{question} {suffix} -> y (--yes)")
        return True
    if not sys.stdin or not sys.stdin.isatty():
        # запуск не из терминала (пайп, планировщик): не висим на вводе
        out(f"{question} {suffix} -> {'y' if default else 'n'} {C.DIM}(stdin не интерактивен){C.RESET}")
        return default
    while True:
        try:
            answer = input(f"{question} {suffix} ").strip().lower()
        except EOFError:
            return default
        if not answer:
            return default
        if answer in ("y", "yes", "д", "да"):
            return True
        if answer in ("n", "no", "н", "нет"):
            return False


# ------------------------------------------------------------------------ манифесты


@dataclass
class Addon:
    name: str
    path: Path
    manifest: Path
    depth: int
    version: int | None = None
    api: list[str] = field(default_factory=list)
    is_library: bool = False
    title: str = ""
    depends: list[tuple[str, int | None]] = field(default_factory=list)
    optional: list[tuple[str, int | None]] = field(default_factory=list)
    other_platform: list[tuple[str, int | None]] = field(default_factory=list)


def _split_dep(token: str) -> tuple[str, int | None]:
    """'LibFoo>=42' -> ('LibFoo', 42); 'LibFoo' -> ('LibFoo', None)."""
    if ">=" in token:
        name, _, raw = token.partition(">=")
        digits = re.sub(r"\D", "", raw)
        return name.strip(), int(digits) if digits else None
    return token.strip().rstrip("<>=!"), None


def _to_version(raw: str | None) -> int | None:
    if not raw:
        return None
    digits = re.sub(r"\D", "", raw)
    return int(digits) if digits else None


def parse_manifest(path: Path) -> dict[str, list[str]]:
    data = path.read_bytes().decode("utf-8-sig", errors="replace")
    fields: dict[str, list[str]] = {}
    for line in data.splitlines():
        m = DIRECTIVE_RE.match(line)
        if m:
            fields.setdefault(m.group(1).lower(), []).append(m.group(2).strip())
    return fields


def scan_addons(addons_dir: Path, platform: str = "pc") -> tuple[dict[str, Addon], list[Path]]:
    """Возвращает (аддоны по имени, папки без манифеста).

    Манифестом считается файл <Имя>.txt или <Имя>.addon внутри папки <Имя>.
    Игра грузит и вложенные аддоны, поэтому обход рекурсивный.
    """
    addons: dict[str, Addon] = {}
    with_manifest: set[Path] = set()

    for candidate in sorted(addons_dir.rglob("*")):
        if not candidate.is_file() or candidate.suffix.lower() not in MANIFEST_SUFFIXES:
            continue
        folder = candidate.parent
        if candidate.stem != folder.name:
            continue
        with_manifest.add(folder)
        fields = parse_manifest(candidate)
        first = lambda key: (fields.get(key) or [""])[0]  # noqa: E731
        def tokens(key: str) -> list[tuple[str, int | None]]:
            found: list[tuple[str, int | None]] = []
            for raw in fields.get(key, []):
                found += [_split_dep(t) for t in raw.split() if t]
            return found

        deps: list[tuple[str, int | None]] = []
        for key in REQUIRED_KEYS[platform]:
            deps += tokens(key)
        opts = tokens("optionaldependson")
        foreign = tokens(OTHER_PLATFORM_KEY[platform])
        addons[folder.name] = Addon(
            name=folder.name,
            path=folder,
            manifest=candidate,
            depth=len(folder.relative_to(addons_dir).parts),
            version=_to_version(first("addonversion")),
            api=first("apiversion").split(),
            is_library=first("islibrary").strip().lower() == "true",
            title=re.sub(r"\|c[0-9a-fA-F]{6}|\|r", "", first("title")).strip(),
            depends=deps,
            optional=opts,
            other_platform=foreign,
        )

    orphans = [
        d
        for d in sorted(addons_dir.iterdir())
        if d.is_dir() and not any(p == d or p in d.parents or d in p.parents for p in with_manifest)
    ]
    return addons, orphans


# --------------------------------------------------------------------------- статус


@dataclass
class Status:
    missing: list[tuple[str, int | None]] = field(default_factory=list)
    outdated: list[tuple[str, int, int]] = field(default_factory=list)  # name, have, need
    unverifiable: list[str] = field(default_factory=list)  # нет ## AddOnVersion
    missing_optional: list[str] = field(default_factory=list)

    @property
    def ok(self) -> bool:
        return not self.missing and not self.outdated

    @property
    def icon(self) -> str:
        if self.missing:
            return f"{C.RED}●{C.RESET}"
        if self.outdated:
            return f"{C.YELLOW}●{C.RESET}"
        return f"{C.GREEN}●{C.RESET}"


def evaluate(addons: dict[str, Addon]) -> dict[str, Status]:
    result: dict[str, Status] = {}
    for addon in addons.values():
        st = Status()
        for dep, minver in addon.depends:
            target = addons.get(dep)
            if target is None:
                st.missing.append((dep, minver))
            elif minver is not None and target.version is None:
                st.unverifiable.append(dep)
            elif minver is not None and target.version is not None and target.version < minver:
                st.outdated.append((dep, target.version, minver))
        st.missing_optional = [d for d, _ in addon.optional if d not in addons]
        result[addon.name] = st
    return result


def aggregate_missing(
    addons: dict[str, Addon], statuses: dict[str, Status], include_optional: bool = False
) -> dict[str, dict]:
    """Сводка недостающего: имя -> {minver, requesters, kind}."""
    need: dict[str, dict] = {}

    def add(name: str, minver: int | None, by: str, kind: str) -> None:
        slot = need.setdefault(name, {"minver": None, "requesters": [], "kind": kind})
        if minver is not None and (slot["minver"] is None or minver > slot["minver"]):
            slot["minver"] = minver
        if by not in slot["requesters"]:
            slot["requesters"].append(by)
        if kind == "required":
            slot["kind"] = "required"

    for name, st in statuses.items():
        for dep, minver in st.missing:
            add(dep, minver, name, "required")
        for dep, _have, needed in st.outdated:
            add(dep, needed, name, "required")
        if include_optional:
            for dep in st.missing_optional:
                add(dep, None, name, "optional")
    return need


def print_addon_table(addons: dict[str, Addon], statuses: dict[str, Status], orphans: list[Path]) -> None:
    header(f"Установленные аддоны: {len(addons)}")
    width = max((len(a.name) + a.depth * 2 for a in addons.values()), default=10)
    for name in sorted(addons, key=lambda n: (addons[n].depth, n.lower())):
        addon, st = addons[name], statuses[name]
        indent = "  " * (addon.depth - 1)
        label = f"{indent}{name}"
        notes: list[str] = []
        if st.missing:
            notes.append(f"{C.RED}нет: " + ", ".join(d for d, _ in st.missing) + C.RESET)
        if st.outdated:
            notes.append(
                f"{C.YELLOW}старая версия: "
                + ", ".join(f"{d} {have}<{need}" for d, have, need in st.outdated)
                + C.RESET
            )
        if not notes:
            total = len(addon.depends)
            notes.append(f"{C.DIM}{'зависимостей нет' if not total else f'все {total} на месте'}{C.RESET}")
        if st.unverifiable:
            notes.append(f"{C.DIM}версия не заявлена: {', '.join(st.unverifiable)}{C.RESET}")
        if st.missing_optional:
            notes.append(f"{C.GREY}+{len(st.missing_optional)} опц.{C.RESET}")
        if addon.other_platform:
            notes.append(f"{C.GREY}+{len(addon.other_platform)} для др. платформы{C.RESET}")
        out(f"  {st.icon} {label:<{width}}  {'; '.join(notes)}")

    out(
        f"\n  {C.GREEN}●{C.RESET} обязательные зависимости в порядке   "
        f"{C.YELLOW}●{C.RESET} версия ниже требуемой   "
        f"{C.RED}●{C.RESET} зависимости отсутствуют"
    )
    if orphans:
        out(f"\n{C.DIM}Папки без манифеста (игра их не грузит): "
            + ", ".join(p.name for p in orphans) + C.RESET)


# --------------------------------------------------------------------------- каталог


class Catalog:
    """Каталог ESOUI с локальным кэшем."""

    def __init__(self, cache_dir: Path, refresh: bool = False) -> None:
        self.cache_file = cache_dir / "filelist.json"
        self.records = self._load(refresh)
        self.by_dir: dict[str, list[dict]] = {}
        for rec in self.records:
            for folder in rec.get("UIDir") or []:
                self.by_dir.setdefault(folder, []).append(rec)

    def _load(self, refresh: bool) -> list[dict]:
        fresh = (
            self.cache_file.exists()
            and time.time() - self.cache_file.stat().st_mtime < CACHE_TTL
            and not refresh
        )
        if fresh:
            try:
                return json.loads(self.cache_file.read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError):
                pass
        out(f"{C.DIM}Загружаю каталог ESOUI...{C.RESET}")
        data = http_get(FILELIST_URL)
        self.cache_file.parent.mkdir(parents=True, exist_ok=True)
        self.cache_file.write_bytes(data)
        return json.loads(data.decode("utf-8"))

    @staticmethod
    def _score(rec: dict, name: str) -> float:
        dirs = rec.get("UIDir") or []
        score = 0.0
        if (rec.get("UIName") or "").strip() == name:
            score += 100
        if dirs and dirs[0] == name:
            score += 50
        if len(dirs) == 1:
            score += 25
        try:
            score += min(int(rec.get("UIDownloadTotal") or 0) / 1e6, 10)
        except ValueError:
            pass
        return score

    def resolve(self, name: str) -> tuple[dict | None, int]:
        """Ищем запись каталога, чей архив создаёт папку `name`."""
        candidates = self.by_dir.get(name) or []
        if not candidates:
            return None, 0
        ranked = sorted(candidates, key=lambda r: -self._score(r, name))
        return ranked[0], len(candidates)


def http_get(url: str, timeout: int = 120) -> bytes:
    request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(request, timeout=timeout) as response:
        return response.read()


def file_details(uid: str) -> dict:
    payload = json.loads(http_get(FILEDETAILS_URL.format(uid=uid)).decode("utf-8"))
    return payload[0] if isinstance(payload, list) else payload


# --------------------------------------------------------------------- бэкап/установка


def make_backup(addons_dir: Path) -> tuple[Path, list[tuple[Path, str]]]:
    """Пакует AddOns в zip. Возвращает (путь, список непрочитанных файлов).

    Заблокированные файлы (например TTC_Lock у запущенного клиента Tamriel Trade
    Centre) пропускаются, а не рушат бэкап, — но перечисляются вызывающему.
    """
    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    target = addons_dir.parent / f"AddOns-backup-{stamp}.zip"
    skipped: list[tuple[Path, str]] = []
    with zipfile.ZipFile(target, "w", zipfile.ZIP_DEFLATED, compresslevel=6) as zf:
        for path in addons_dir.rglob("*"):
            if not path.is_file():
                continue
            try:
                zf.write(path, path.relative_to(addons_dir.parent).as_posix())
            except OSError as exc:
                skipped.append((path.relative_to(addons_dir), exc.strerror or str(exc)))
    return target, skipped


def safe_extract(blob: bytes, addons_dir: Path) -> list[str]:
    """Распаковывает архив в AddOns, отбивая zip-slip. Возвращает папки верхнего уровня."""
    created: set[str] = set()
    root = addons_dir.resolve()
    with zipfile.ZipFile(io.BytesIO(blob)) as zf:
        members = [m for m in zf.infolist() if not m.is_dir()]
        for member in members:
            rel = member.filename.replace("\\", "/").lstrip("/")
            if not rel or ".." in rel.split("/") or re.match(r"^[A-Za-z]:", rel):
                raise ValueError(f"подозрительный путь в архиве: {member.filename!r}")
            target = (root / rel).resolve()
            if root not in target.parents:
                raise ValueError(f"путь вне AddOns: {member.filename!r}")
            created.add(rel.split("/")[0])
        for member in members:
            rel = member.filename.replace("\\", "/").lstrip("/")
            target = root / rel
            target.parent.mkdir(parents=True, exist_ok=True)
            with zf.open(member) as src, open(target, "wb") as dst:
                dst.write(src.read())
    return sorted(created)


def install(rec: dict, addons_dir: Path) -> list[str]:
    details = file_details(rec["UID"])
    url = details.get("UIDownload")
    if not url:
        raise ValueError("в filedetails нет ссылки UIDownload")
    blob = http_get(url)
    expected = (details.get("UIMD5") or "").strip().lower()
    if expected:
        actual = hashlib.md5(blob).hexdigest()
        if actual != expected:
            raise ValueError(f"MD5 не совпал: ожидался {expected}, получен {actual}")
    return safe_extract(blob, addons_dir)


# ------------------------------------------------------------------------------ план


def print_plan(plan: dict[str, dict], addons: dict[str, Addon]) -> tuple[list[str], list[str]]:
    resolvable = [n for n, info in plan.items() if info.get("record")]
    unresolved = [n for n, info in plan.items() if not info.get("record")]

    header(f"К установке: {len(resolvable)}")
    for name in sorted(resolvable, key=str.lower):
        info = plan[name]
        rec = info["record"]
        need = f">={info['minver']}" if info["minver"] else "любая"
        mark = "обновление" if name in addons else "новая"
        tag = "" if info["kind"] == "required" else f" {C.GREY}[опц.]{C.RESET}"
        out(
            f"  {C.CYAN}{name}{C.RESET}{tag}  {C.DIM}нужно {need}; "
            f"ESOUI #{rec['UID']} v{rec.get('UIVersion', '?')}; {mark}{C.RESET}"
        )
        out(f"      {C.DIM}для: {', '.join(sorted(info['requesters']))}{C.RESET}")
        if info["candidates"] > 1:
            out(f"      {C.YELLOW}в каталоге {info['candidates']} совпадений, выбран самый вероятный{C.RESET}")
        extra = [d for d in (rec.get("UIDir") or []) if d != name]
        if extra:
            out(f"      {C.DIM}архив также создаст: {', '.join(extra)}{C.RESET}")

    if unresolved:
        out(f"\n  {C.RED}Не найдено в каталоге ESOUI ({len(unresolved)}):{C.RESET}")
        for name in sorted(unresolved, key=str.lower):
            out(f"      {name}  {C.DIM}для: {', '.join(sorted(plan[name]['requesters']))}{C.RESET}")
        out(f"  {C.DIM}Такие зависимости ставятся вручную либо входят в состав другого аддона.{C.RESET}")
    return resolvable, unresolved


def build_plan(need: dict[str, dict], catalog: Catalog) -> dict[str, dict]:
    plan: dict[str, dict] = {}
    for name, info in need.items():
        rec, count = catalog.resolve(name)
        plan[name] = {**info, "record": rec, "candidates": count}
    return plan


# ------------------------------------------------------------------------------ main


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    p = argparse.ArgumentParser(
        description="Проверка и доустановка зависимостей аддонов ESO.",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    p.add_argument("--addons-dir", type=Path, default=DEFAULT_ADDONS_DIR, help="папка AddOns")
    p.add_argument(
        "--platform",
        choices=("pc", "console"),
        default="pc",
        help="какие платформенные зависимости считать обязательными (PCDependsOn / ConsoleDependsOn)",
    )
    p.add_argument("--optional", action="store_true", help="учитывать и OptionalDependsOn")
    p.add_argument("--only", default="", help="ставить только эти имена, через запятую")
    p.add_argument("--dry-run", action="store_true", help="показать план, ничего не менять")
    p.add_argument("--yes", action="store_true", help="не задавать вопросов")
    p.add_argument("--refresh", action="store_true", help="перекачать каталог ESOUI")
    p.add_argument("--no-color", action="store_true", help="без цвета")
    p.add_argument(
        "--cache-dir",
        type=Path,
        default=Path(os.environ.get("LOCALAPPDATA") or Path.home()) / "eso-addon-deps",
        help="папка кэша каталога",
    )
    return p.parse_args(argv)


def report_optional(addons: dict[str, Addon], statuses: dict[str, Status]) -> dict[str, list[str]]:
    grouped: dict[str, list[str]] = {}
    for name, st in statuses.items():
        for dep in st.missing_optional:
            grouped.setdefault(dep, []).append(name)
    return grouped


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    C.setup(not args.no_color)
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

    addons_dir: Path = args.addons_dir.expanduser()
    if not addons_dir.is_dir():
        out(f"{C.RED}Папка не найдена: {addons_dir}{C.RESET}")
        return 2

    out(f"{C.BOLD}ESO addon dependencies{C.RESET}  {C.DIM}{addons_dir}{C.RESET}")

    # ---- (1) обзор установленного
    addons, orphans = scan_addons(addons_dir, args.platform)
    if not addons:
        out(f"{C.RED}Манифестов аддонов не найдено.{C.RESET}")
        return 2
    statuses = evaluate(addons)
    print_addon_table(addons, statuses, orphans)

    only = {n.strip() for n in args.only.split(",") if n.strip()}
    include_optional = args.optional or bool(only)
    need = aggregate_missing(addons, statuses, include_optional)
    if only:
        need = {n: info for n, info in need.items() if n in only}
        unknown = only - set(need)
        if unknown:
            out(f"\n{C.YELLOW}--only: не встречаются в зависимостях: {', '.join(sorted(unknown))}{C.RESET}")

    broken = sum(1 for st in statuses.values() if not st.ok)
    optional_missing = report_optional(addons, statuses)

    # ---- всё в порядке: предложить закончить
    if not need:
        out(f"\n{C.GREEN}Все обязательные зависимости на месте.{C.RESET}")
        if optional_missing and not args.optional:
            out(f"{C.DIM}Не установлено опциональных: {len(optional_missing)} "
                f"(показать и поставить — запустите с --optional).{C.RESET}")
        if ask("Завершить работу?", default=True, assume_yes=args.yes):
            return 0
        if optional_missing:
            header(f"Опциональные, которых нет: {len(optional_missing)}")
            for dep in sorted(optional_missing, key=str.lower):
                out(f"  {dep}  {C.DIM}для: {', '.join(sorted(optional_missing[dep]))}{C.RESET}")
            out(f"\n{C.DIM}Поставить выбранное: --only Имя1,Имя2   Поставить все: --optional{C.RESET}")
        return 0

    # ---- (2) план и подтверждение
    out(f"\n{C.YELLOW}Аддонов с проблемами: {broken} из {len(addons)}.{C.RESET}")
    catalog = Catalog(args.cache_dir, args.refresh)
    plan = build_plan(need, catalog)
    resolvable, _ = print_plan(plan, addons)

    if not resolvable:
        out(f"\n{C.RED}Ставить нечего — ни одна зависимость не найдена в каталоге.{C.RESET}")
        return 1
    if args.dry_run:
        out(f"\n{C.DIM}--dry-run: ничего не менял.{C.RESET}")
        return 0
    if not ask(f"\nУстановить {len(resolvable)} шт.?", default=True, assume_yes=args.yes):
        out("Отменено, ничего не изменено.")
        return 0

    # ---- (3) бэкап
    header("Бэкап")
    try:
        backup_path, skipped = make_backup(addons_dir)
    except OSError as exc:
        out(f"{C.RED}Бэкап не удался: {exc}. Установка отменена.{C.RESET}")
        return 1
    size_mb = backup_path.stat().st_size / 1024 / 1024
    out(f"  {C.GREEN}Сохранено:{C.RESET} {backup_path}")
    out(f"  {C.DIM}{size_mb:.1f} МБ. Восстановление: распаковать этот архив в {addons_dir.parent}")
    out(f"  SavedVariables не затрагивались.{C.RESET}")
    if skipped:
        out(f"  {C.YELLOW}Не попали в бэкап ({len(skipped)}) — файлы заняты другим процессом:{C.RESET}")
        for rel, why in skipped:
            out(f"      {rel}  {C.DIM}({why}){C.RESET}")
        out(f"  {C.DIM}Обычно это lock-файлы запущенного клиента (ESO, TTC) — "
            f"на восстановление аддонов они не влияют.{C.RESET}")
        if not ask("  Бэкап неполный. Продолжать установку?", default=True, assume_yes=args.yes):
            out("Отменено. Бэкап оставлен: " + str(backup_path))
            return 0

    # ---- установка до сходимости: у библиотек есть свои зависимости
    installed_ok: list[str] = []
    failed: list[tuple[str, str]] = []
    unresolved_all: dict[str, list[str]] = {}

    for round_no in range(1, MAX_ROUNDS + 1):
        header(f"Установка, проход {round_no}")
        for name in sorted(resolvable, key=str.lower):
            rec = plan[name]["record"]
            try:
                folders = install(rec, addons_dir)
            except (urllib.error.URLError, ValueError, zipfile.BadZipFile, OSError) as exc:
                out(f"  {C.RED}✖{C.RESET} {name}: {exc}")
                failed.append((name, str(exc)))
                continue
            installed_ok.append(name)
            extra = [f for f in folders if f != name]
            suffix = f" {C.DIM}(+{', '.join(extra)}){C.RESET}" if extra else ""
            out(f"  {C.GREEN}✔{C.RESET} {name} {C.DIM}v{rec.get('UIVersion', '?')}{C.RESET}{suffix}")

        addons, orphans = scan_addons(addons_dir, args.platform)
        statuses = evaluate(addons)
        need = aggregate_missing(addons, statuses, include_optional)
        for name, _info in list(need.items()):
            if name in dict(failed):
                need.pop(name)
        plan = build_plan(need, catalog)
        resolvable = [n for n, info in plan.items() if info.get("record")]
        for name, info in plan.items():
            if not info.get("record"):
                unresolved_all[name] = sorted(info["requesters"])

        if not resolvable:
            break
        out(f"\n{C.DIM}Появились транзитивные зависимости ({len(resolvable)}): "
            f"{', '.join(sorted(resolvable, key=str.lower))}{C.RESET}")
        if not ask("Доставить их?", default=True, assume_yes=args.yes):
            break
    else:
        out(f"\n{C.YELLOW}Достигнут лимит проходов ({MAX_ROUNDS}) — запустите скрипт ещё раз.{C.RESET}")

    # ---- (4) итоговая проверка
    addons, orphans = scan_addons(addons_dir, args.platform)
    statuses = evaluate(addons)
    print_addon_table(addons, statuses, orphans)

    header("Итог")
    out(f"  Установлено: {len(installed_ok)}"
        + (f" ({', '.join(installed_ok)})" if installed_ok else ""))
    if failed:
        out(f"  {C.RED}Ошибки: {len(failed)}{C.RESET}")
        for name, why in failed:
            out(f"      {name}: {why}")
    if unresolved_all:
        out(f"  {C.YELLOW}Не найдено в каталоге: {len(unresolved_all)}{C.RESET}")
        for name, requesters in sorted(unresolved_all.items()):
            out(f"      {name}  {C.DIM}для: {', '.join(requesters)}{C.RESET}")
    still_broken = [n for n, st in statuses.items() if not st.ok]
    if still_broken:
        out(f"  {C.RED}Аддоны с незакрытыми зависимостями: {len(still_broken)} "
            f"({', '.join(sorted(still_broken))}){C.RESET}")
        out(f"  {C.DIM}Бэкап: {backup_path}{C.RESET}")
        return 1
    out(f"  {C.GREEN}Все обязательные зависимости закрыты.{C.RESET}")
    out(f"  {C.DIM}Бэкап: {backup_path}{C.RESET}")
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        out("\nПрервано.")
        sys.exit(130)
