# -*- coding: utf-8 -*-
"""Задание 40: крафт — компоненты, аугменты, рецепты, фракции.

Предшественник: docs/grim-dawn/components.json (107 компонентов: только slots+resists),
собран старым docs/grim-dawn/tools/build_components.py. Формат НЕ ломаем — расширяем
(все старые ключи сохранены), пишем в новый путь data/grim-dawn/components.json.

Область (счётчики сверены `SELECT type, COUNT(*) FROM records GROUP BY type`):
  ItemRelic             107  -> компоненты (craftingMaterial=1)      -> components.json
  ItemEnchantment       386  -> аугменты                              -> augments.jsonl (kind=enchantment)
  ItemFactionBooster     30  -> бустеры репутации                     -> augments.jsonl (kind=faction_booster)
  ItemFactionWarrant     12  -> бустеры репутации (враждебные фракции) -> augments.jsonl (kind=faction_warrant)
  ItemArtifact          103  -> НЕ в этом задании — это gear-реликвии,
                                 уже покрыты заданием 10 (носимый слот "relic").
                                 Здесь встречаются только как output рецептов (resolve).
  ItemArtifactFormula   988  -> рецепты крафта                        -> recipes.jsonl
  ItemTransmuter         59  -> косметика (иллюзии), кратко в отчёте  -> recipes_summary.json
  ItemTransmuterSet      24  -> то же, сет-версия                     -> recipes_summary.json
  ItemAscensionFormula    9  -> Ascension (FG) reroll-формулы          -> recipes_summary.json
  ItemRerollFormula       3  -> reroll-формулы                         -> recipes_summary.json

Ключевые находки (см. отчёт REPORTS/40_crafting.md за подробностями и неуверенностями):
  - Имя компонента/аугмента/рецепта: поле "description" (не itemNameTag!) -> тэг.
    "itemText" -> тэг с описанием/лором (не имя).
  - Компонент собирается через ItemArtifactFormula, где artifactName == путь компонента
    (reagent1..6BaseName/Quantity + reagentBaseBaseName/Quantity — сырьё).
  - factionSource на ItemEnchantment (User0..User21) и boostedFaction на
    ItemFactionBooster/Warrant — id фракции. Имя фракции резолвится тэгом
    tagFactionUser<N>; несколько особых нечисловых id (Aetherials, Cthonians,
    Outlaws, Beasts, Survivors, Player) без тэга — читаемая метка добавлена вручную.
  - "Где падает/продаётся": на всю БД один раз строится reverse-index (какие записи
    ссылаются путём на нашу запись). Поле "marketStaticItems" в
    records/creatures/npcs/merchants/factiontables/<faction>_<tier>_01.dbr — это и есть
    "разблокировано на уровне репутации <tier>" (tier in friendly/respected/honored/revered).
  - Полный порядок из 8 уровней репутации (Rewards1..8) подтверждён авторитетно через
    data/grim-dawn/field_schema.json (распакованные редакторские шаблоны, см. дополнение
    к фундаменту): picklist поля "factionStanding" = "Nemesis;Hated;Despised;Tolerated;
    Friendly;Respected;Honored;Revered". Совпадает с наблюдаемым в БД (Rewards4=Tolerated
    везде "Empty"; Rewards5..8 совпадают с папками factiontables/<faction>_<tier>_01.dbr).
  - artifactCreationCost/rerollCost — поля типа "equation" (см. field_schema.json):
    значение бывает то числом, то строкой-числом, то реальной формулой ("parentLevel*1+5") —
    это нормально для этого типа поля, не ошибка парсинга.

Запуск:  python 40_crafting.py
Выход:   <GD_DATA>/components.json, augments.jsonl, recipes.jsonl, recipes_summary.json,
         factions.json
"""
import json
import re
import time
from collections import Counter, defaultdict

from gdlib import Tags, open_sqlite, write_json, write_jsonl, norm

# ---------------------------------------------------------------------------
# Слоты и резисты — те же поля/имена, что в старом tools/build_components.py,
# чтобы старые потребители (если такие появятся) узнавали значения.
ARMOR_SLOTS = ["head", "shoulders", "chest", "legs", "hands", "feet", "amulet", "ring", "medal", "waist"]
WEAPON_SLOTS = ["sword", "sword2h", "mace", "mace2h", "axe", "axe2h", "dagger", "scepter",
                "spear2h", "ranged1h", "ranged2h", "offhand", "shield"]
SLOT_FLAGS = ARMOR_SLOTS + WEAPON_SLOTS

RES = {
    "defensiveFire": "fire", "defensiveCold": "cold", "defensiveLightning": "lightning",
    "defensivePoison": "poison", "defensivePierce": "pierce", "defensiveBleeding": "bleed",
    "defensiveLife": "vitality", "defensiveAether": "aether", "defensiveChaos": "chaos",
    "defensivePhysical": "physical", "defensiveElementalResistance": "elemental_all",
    "defensiveDisruption": "disruption", "defensiveStun": "stun",
}

# Косметика/движок — никогда не несёт игровой семантики, выбрасываем из "stats" всегда.
META_FIELDS = {
    "templateName", "Class", "actorHeight", "actorRadius", "allowTransparency", "castsShadows",
    "cannotPickUp", "cannotPickUpMultiple", "maxTransparency", "outlineThickness",
    "physicsFriction", "physicsMass", "physicsRestitution", "scale", "shadowBias",
    "unloadedBoundingBoxExtents", "quest", "mesh", "bitmap", "bitmapFemale",
    "relicBitmap", "shardBitmap", "relicCompleteSound", "relicToItemSound", "relicToRelicSound",
    "artifactBitmap", "artifactFormulaBitmapName", "emptyBitmap", "fullBitmap",
    "dropSound", "dropSound3D", "dropSoundWater", "useSound", "longFX", "roundFX",
    "attachPointName", "characterBaseAttackSpeedTag", "dlcRequirement",
}

PROMOTED = {
    "FileDescription", "description", "itemText", "itemNameTag",
    "itemLevel", "levelRequirement", "itemCost", "itemClassification",
    "soulbound", "untradeable", "factionSource",
    "strengthRequirement", "dexterityRequirement", "intelligenceRequirement",
    "itemSkillName", "itemSkillLevelEq", "itemSkillAutoController", "itemSkillLevel",
    "craftingMaterial", "completedRelicLevel", "bonusTableName",
    "boostedFaction", "boostedMultiplier",
    "artifactName", "artifactCreateQuantity", "artifactCreationCost",
    "forcedRandomArtifactName", "forcedRelicCompletion",
    "reagentBaseBaseName", "reagentBaseQuantity",
}
for _i in range(1, 7):
    PROMOTED.add(f"reagent{_i}BaseName")
    PROMOTED.add(f"reagent{_i}Quantity")
PROMOTED |= set(SLOT_FLAGS) | set(RES)

DEBUG_PATH_RE = re.compile(r"sandbox|test|debug|_dev", re.IGNORECASE)


def num(v):
    try:
        f = float(v)
        return int(f) if f == int(f) else round(f, 2)
    except (TypeError, ValueError):
        return v


def is_zero(v):
    if v is None:
        return True
    if isinstance(v, str):
        return v == ""
    if isinstance(v, (int, float)):
        return v == 0
    if isinstance(v, list):
        return all(is_zero(x) for x in v)
    return False


def nonzero(f, exclude):
    out = {}
    for k, v in f.items():
        if k in exclude or is_zero(v):
            continue
        out[k] = num(v) if not isinstance(v, list) else [num(x) for x in v]
    return out


class Resolver:
    """Резолв путь-записи -> {record, name} с кэшем. Работает для любого типа записи
    (предмет/скилл/лут-таблица) — имя ищем по универсальным полям name-тэгов."""

    NAME_FIELDS = ("description", "itemNameTag", "skillDisplayName", "setName")

    def __init__(self, con, tags):
        self.con = con
        self.tags = tags
        self.cache = {}

    def _fields(self, key):
        row = self.con.execute("SELECT fields, type FROM records WHERE name=?", (key,)).fetchone()
        if not row:
            return None, None
        return json.loads(row[0]), row[1]

    def name_of(self, key):
        if key in self.cache:
            return self.cache[key]
        f, typ = self._fields(key)
        name = None
        if f:
            for nf in self.NAME_FIELDS:
                v = f.get(nf)
                if isinstance(v, str) and v in self.tags:
                    name = self.tags(v)
                    break
            if not name:
                name = f.get("FileDescription")
        self.cache[key] = name
        return name

    def ref(self, path):
        """path (records/.../x.dbr) -> {"record":..., "name":...} или None."""
        if not path:
            return None
        key = norm(path)
        return {"record": path, "name": self.name_of(key)}


# ---------------------------------------------------------------------------
# Фракции: id (Player/Survivors/Aetherials/.../User0..User22) -> читаемое имя.
# UserN резолвится тэгом tagFactionUser<N> (см. tags_en.json). Нечисловые id тэга не
# имеют (это внутренние "трекеры репутации" для враждебных монстров) — метки ниже
# подобраны вручную по контексту (см. отчёт, раздел "неуверенности").
FACTION_LABELS_NO_TAG = {
    "Player": "Player (собственная репутация)",
    "Survivors": "Survivors / Devil's Crossing",
    "NeutralNPC": "Neutral NPC",
    "Aetherials": "Aetherials (враждебная фракция)",
    "Cthonians": "Chthonians (враждебная фракция)",
    "Outlaws": "Outlaws (враждебная фракция)",
    "Beasts": "Beasts (враждебная фракция)",
}


def faction_name(fid, tags):
    if not fid:
        return None
    if fid.startswith("User"):
        tag = f"tagFactionUser{fid[4:]}"
        if tag in tags:
            return tags(tag)
    return FACTION_LABELS_NO_TAG.get(fid, fid)


# Порядок вендор-тиров, подтверждённый наличием папок factiontables/<faction>_<tier>_01.dbr
VENDOR_TIERS = ["friendly", "respected", "honored", "revered"]
FACTIONTABLE_RE = re.compile(r"factiontables/([a-z]+)_(friendly|respected|honored|revered)_\d+\.dbr$")


def build_reverse_index(con, targets):
    """Один проход по ВСЕЙ БД: для каждого пути из targets собираем список записей,
    которые на него ссылаются (поле, тип, имя ссылающейся записи). targets — set
    норм.путей. Это единственный практичный способ ответить на "где падает/продаётся"
    без пересборки полного дерева лут-таблиц (домен задания 30)."""
    refs = defaultdict(list)
    rows = con.execute("SELECT name, type, fields FROM records").fetchall()
    for name, typ, fields in rows:
        if ".dbr" not in fields:
            continue
        f = json.loads(fields)
        for k, v in f.items():
            vals = v if isinstance(v, list) else [v]
            for item in vals:
                if isinstance(item, str) and item.endswith(".dbr"):
                    nk = norm(item)
                    if nk in targets:
                        refs[nk].append((name, typ or "", k))
    return refs


def categorize_refs(refs_for_key):
    """refs_for_key: список (name, type, field) -> сгруппированный словарь источников."""
    out = {"vendor": [], "monster": [], "loot_table": [], "used_as_reagent_in": [], "other": []}
    for name, typ, field in refs_for_key:
        if field == "marketStaticItems":
            m = FACTIONTABLE_RE.search(name)
            if m:
                out["vendor"].append({"faction_slug": m.group(1), "tier": m.group(2), "table": name})
            else:
                out["vendor"].append({"table": name})
        elif typ == "Monster" and field.startswith("loot"):
            out["monster"].append({"monster": name, "field": field})
        elif typ.startswith("Loot"):
            out["loot_table"].append({"table": name, "type": typ, "field": field})
        elif typ == "ItemArtifactFormula" and field.startswith("reagent"):
            out["used_as_reagent_in"].append({"formula": name})
        else:
            out["other"].append({"record": name, "type": typ, "field": field})
    # обрезаем длинные списки, но сохраняем счётчик
    result = {}
    for k, v in out.items():
        if not v:
            continue
        result[k] = {"count": len(v), "examples": v[:8]}
    return result


def main():
    t0 = time.time()
    con = open_sqlite(readonly=True)
    tags = Tags()
    res = Resolver(con, tags)

    # ------------------------------------------------------------------
    # 1) Компоненты (ItemRelic, craftingMaterial=1)
    # ------------------------------------------------------------------
    relic_rows = con.execute("SELECT name, fields FROM records WHERE type='ItemRelic'").fetchall()
    components = {}
    comp_skipped = []
    for name, fields_json in relic_rows:
        f = json.loads(fields_json)
        if not f.get("craftingMaterial"):
            comp_skipped.append(name)
            continue
        key = name.split("/")[-1].replace(".dbr", "")
        slots = [s for s in SLOT_FLAGS if f.get(s) == 1]
        resists = {nm: num(f[fld]) for fld, nm in RES.items() if not is_zero(f.get(fld))}

        name_tag = f.get("description")
        entry = {
            "record": name,
            "desc": f.get("FileDescription", ""),
            "name": tags(name_tag) if name_tag else f.get("FileDescription"),
            "name_tag": name_tag,
            "slots": slots,
            "resists": resists,
        }
        if f.get("characterArmor"):
            entry["armor"] = num(f["characterArmor"])
        if f.get("characterArmorModifier"):
            entry["armor_pct"] = num(f["characterArmorModifier"])
        if f.get("characterLife"):
            entry["health"] = num(f["characterLife"])
        if f.get("characterLifeModifier"):
            entry["health_pct"] = num(f["characterLifeModifier"])
        if f.get("defensiveAbsorptionModifier"):
            entry["armor_absorb_pct"] = num(f["defensiveAbsorptionModifier"])

        item_skill = f.get("itemSkillName")
        entry["grants_skill"] = bool(item_skill)
        if item_skill:
            entry["skill"] = {
                "record": item_skill,
                "name": res.name_of(norm(item_skill)),
                "levelEq": f.get("itemSkillLevelEq"),
            }

        for fld, dst in (("itemLevel", "itemLevel"), ("levelRequirement", "levelRequirement"),
                         ("itemCost", "itemCost"), ("itemClassification", "itemClassification"),
                         ("completedRelicLevel", "completedRelicLevel")):
            if not is_zero(f.get(fld)):
                entry[dst] = f[fld]

        stats = nonzero(f, META_FIELDS | PROMOTED)
        if stats:
            entry["stats"] = stats

        components[key] = entry

    # рецепт компонента: ItemArtifactFormula, где artifactName указывает на эту запись
    formula_rows = con.execute("SELECT name, fields FROM records WHERE type='ItemArtifactFormula'").fetchall()
    formulas_by_output = defaultdict(list)
    all_formulas = []
    for fname, fields_json in formula_rows:
        f = json.loads(fields_json)
        all_formulas.append((fname, f))
        out_ref = f.get("artifactName")
        if out_ref:
            formulas_by_output[norm(out_ref)].append((fname, f))

    def build_reagents(f):
        reagents = []
        for i in range(1, 7):
            bn = f.get(f"reagent{i}BaseName")
            if bn:
                reagents.append({"record": bn, "name": res.name_of(norm(bn)),
                                  "quantity": f.get(f"reagent{i}Quantity")})
        base = f.get("reagentBaseBaseName")
        if base:
            bases = base if isinstance(base, list) else [base]
            for b in bases:
                reagents.append({"record": b, "name": res.name_of(norm(b)),
                                  "quantity": f.get("reagentBaseQuantity")})
        return reagents

    comp_with_recipe = 0
    for key, entry in components.items():
        cands = formulas_by_output.get(norm(entry["record"]))
        if cands:
            comp_with_recipe += 1
            fname, ff = cands[0]
            entry["recipe"] = {
                "record": fname,
                "reagents": build_reagents(ff),
                "creation_cost": ff.get("artifactCreationCost"),
                "blueprint_itemLevel": ff.get("itemLevel"),
                "blueprint_levelRequirement": ff.get("levelRequirement"),
            }
            if len(cands) > 1:
                entry["recipe"]["alt_formulas"] = [n for n, _ in cands[1:]]

    # ------------------------------------------------------------------
    # 2) Аугменты: ItemEnchantment + ItemFactionBooster + ItemFactionWarrant
    # ------------------------------------------------------------------
    augments = []
    ench_rows = con.execute("SELECT name, fields FROM records WHERE type='ItemEnchantment'").fetchall()
    for name, fields_json in ench_rows:
        f = json.loads(fields_json)
        name_tag = f.get("description")
        slots = [s for s in SLOT_FLAGS if f.get(s) == 1]
        entry = {
            "record": name,
            "kind": "enchantment",
            "name": tags(name_tag) if name_tag else f.get("FileDescription"),
            "name_tag": name_tag,
            "slots": slots,
            "itemLevel": f.get("itemLevel"),
            "levelRequirement": f.get("levelRequirement"),
            "itemCost": f.get("itemCost"),
            "itemClassification": f.get("itemClassification"),
            "soulbound": bool(f.get("soulbound")),
        }
        fs = f.get("factionSource")
        if fs:
            entry["faction"] = {"id": fs, "name": faction_name(fs, tags)}
        stats = nonzero(f, META_FIELDS | PROMOTED | set(SLOT_FLAGS))
        if stats:
            entry["stats"] = stats
        augments.append(entry)

    for typ, kind in (("ItemFactionBooster", "faction_booster"), ("ItemFactionWarrant", "faction_warrant")):
        rows = con.execute("SELECT name, fields FROM records WHERE type=?", (typ,)).fetchall()
        for name, fields_json in rows:
            f = json.loads(fields_json)
            name_tag = f.get("description")
            bf = f.get("boostedFaction")
            entry = {
                "record": name,
                "kind": kind,
                "name": tags(name_tag) if name_tag else f.get("FileDescription"),
                "name_tag": name_tag,
                "itemLevel": f.get("itemLevel"),
                "itemCost": f.get("itemCost"),
                "itemClassification": f.get("itemClassification"),
                "soulbound": bool(f.get("soulbound")),
                "untradeable": bool(f.get("untradeable")),
                "boosted_faction": {"id": bf, "name": faction_name(bf, tags)} if bf else None,
                "boosted_multiplier": f.get("boostedMultiplier"),
            }
            augments.append(entry)

    # ------------------------------------------------------------------
    # 3) Рецепты: ItemArtifactFormula
    # ------------------------------------------------------------------
    recipes = []
    for fname, f in all_formulas:
        name_tag = f.get("description")
        entry = {
            "record": fname,
            "name": tags(name_tag) if name_tag else f.get("FileDescription"),
            "name_tag": name_tag,
            "itemLevel": f.get("itemLevel"),
            "levelRequirement": f.get("levelRequirement"),
            "itemClassification": f.get("itemClassification"),
            "blueprint_cost": f.get("itemCost"),
            "creation_cost": f.get("artifactCreationCost"),
            "soulbound": bool(f.get("soulbound")),
        }
        out_ref = f.get("artifactName")
        if out_ref:
            entry["output"] = {"record": out_ref, "name": res.name_of(norm(out_ref)),
                                "quantity": f.get("artifactCreateQuantity")}
        rand_ref = f.get("forcedRandomArtifactName")
        if rand_ref:
            entry["forced_random_output"] = {"record": rand_ref, "name": res.name_of(norm(rand_ref))}
        if f.get("forcedRelicCompletion"):
            entry["forced_relic_completion"] = True
        entry["reagents"] = build_reagents(f)
        recipes.append(entry)

    # ------------------------------------------------------------------
    # 4) Reverse-index "где падает/продаётся" — один проход по всей БД
    # ------------------------------------------------------------------
    targets = set()
    targets.update(norm(c["record"]) for c in components.values())
    targets.update(norm(a["record"]) for a in augments)
    targets.update(norm(r["record"]) for r in recipes)
    print(f"Строю reverse-index ссылок для {len(targets)} целевых записей "
          f"(полный проход по {con.execute('SELECT COUNT(*) FROM records').fetchone()[0]} записям БД)...")
    t_idx = time.time()
    refs = build_reverse_index(con, targets)
    print(f"  reverse-index построен за {time.time()-t_idx:.1f}s, "
          f"найдены ссылки на {len(refs)}/{len(targets)} целей")

    def attach_drop_sources(record_path, entry):
        r = refs.get(norm(record_path))
        if r:
            cat = categorize_refs(r)
            if cat:
                entry["drop_sources"] = cat

    for c in components.values():
        attach_drop_sources(c["record"], c)
    for a in augments:
        attach_drop_sources(a["record"], a)
        # для enchantment дополнительно вытащим вендорный тир, если нашли
        ds = a.get("drop_sources", {}).get("vendor")
        if ds:
            tiers = {ex.get("tier") for ex in ds["examples"] if ex.get("tier")}
            if tiers:
                a["vendor_tiers"] = sorted(tiers)
    for r in recipes:
        attach_drop_sources(r["record"], r)

    # ------------------------------------------------------------------
    # 5) Фракции: контроллеры records/controllers/factions/*.dbr + тэги + вендор-тиры
    # ------------------------------------------------------------------
    ctrl_rows = con.execute(
        "SELECT name, fields FROM records WHERE name LIKE 'records/controllers/factions/%'"
    ).fetchall()
    faction_ids = []
    for cname, fields_json in ctrl_rows:
        f = json.loads(fields_json)
        fid = f.get("myFaction")
        if fid:
            faction_ids.append(fid)

    # слаги вендор-таблиц -> faction id, определяем автоматически по факту пересечения
    # (у любого предмета из marketStaticItems этого слага смотрим его factionSource/
    # boostedFaction — что найдём первым, то и id фракции для слага).
    fac_table_rows = con.execute(
        "SELECT name, fields FROM records WHERE name LIKE 'records/creatures/npcs/merchants/factiontables/%'"
    ).fetchall()
    slug_items = defaultdict(list)  # slug -> [(tier, [item paths])]
    for tname, fields_json in fac_table_rows:
        m = FACTIONTABLE_RE.search(tname)
        if not m:
            continue
        slug, tier = m.group(1), m.group(2)
        f = json.loads(fields_json)
        items = f.get("marketStaticItems") or []
        if isinstance(items, str):
            items = [items]
        slug_items[slug].append((tier, items))

    slug_to_fid = {}
    for slug, tier_items in slug_items.items():
        found = None
        for _tier, items in tier_items:
            for it in items:
                row = con.execute("SELECT fields FROM records WHERE name=?", (norm(it),)).fetchone()
                if not row:
                    continue
                itf = json.loads(row[0])
                fs = itf.get("factionSource") or itf.get("boostedFaction")
                if fs:
                    found = fs
                    break
            if found:
                break
        slug_to_fid[slug] = found

    fid_to_slug = {v: k for k, v in slug_to_fid.items() if v}

    factions = {}
    for fid in sorted(set(faction_ids)):
        entry = {"id": fid, "name": faction_name(fid, tags)}
        if fid.startswith("User"):
            n = fid[4:]
            info_tag = f"tagFactionUser{n}Info"
            if info_tag in tags:
                info = tags(info_tag)
                if info and info != "N/A":
                    entry["info"] = info
            reward_tiers = []
            for i in range(1, 9):
                rtag = f"tagFactionUser{n}Rewards{i}"
                if rtag in tags:
                    txt = tags(rtag)
                    reward_tiers.append({"index": i, "text": txt})
            if reward_tiers:
                entry["reward_tiers"] = reward_tiers
        slug = fid_to_slug.get(fid)
        if slug:
            entry["vendor_slug"] = slug
            vendor_unlocks = {}
            for tier, items in slug_items[slug]:
                resolved = [{"record": it, "name": res.name_of(norm(it))} for it in items]
                vendor_unlocks[tier] = resolved
            entry["vendor_unlocks"] = vendor_unlocks
        factions[fid] = entry

    factions_out = {
        "factions": factions,
        "reward_tier_order": {
            "note": ("Индекс Rewards1..8 на тэгах tagFactionUser<N>Rewards<i> = порядок уровней "
                     "репутации от худшего к лучшему. Источник — авторитетный словарь схемы полей "
                     "data/grim-dawn/field_schema.json (распакован из database/templates.arc), "
                     "picklist поля 'factionStanding'/'commonMonsterGainReductionStart' "
                     "(template factionpack/proxy/dungeonentrance): "
                     "'Nemesis;Hated;Despised;Tolerated;Friendly;Respected;Honored;Revered'. "
                     "Совпадает с наблюдаемым: Rewards4 (Tolerated) везде 'Empty' — нейтральная "
                     "стартовая позиция; Rewards5..8 (Friendly/Respected/Honored/Revered) совпадают "
                     "с папками factiontables/<faction>_<tier>_01.dbr."),
            "order": ["Nemesis", "Hated", "Despised", "Tolerated", "Friendly", "Respected", "Honored", "Revered"],
        },
    }

    # ------------------------------------------------------------------
    # 6) Прочее: ItemTransmuter/Set, ItemAscensionFormula, ItemRerollFormula — кратко
    # ------------------------------------------------------------------
    misc_types = {
        "ItemTransmuter": "Косметический предмет ('иллюзия'): меняет ТОЛЬКО внешний вид "
                           "надетого предмета на transmuteDbr, статы не затрагивает.",
        "ItemTransmuterSet": "То же, что ItemTransmuter, но на несколько слотов сразу "
                              "(transmuteDbrs — список).",
        "ItemAscensionFormula": "Формула переброса (reroll) аффиксов для Ascended-предметов "
                                 "(FG): задаёт таблицы аффиксов/мастерства по слоту оружия/брони "
                                 "и стоимость reagent-ов.",
        "ItemRerollFormula": "Формула переброса аффиксов обычного предмета за soulgreater/"
                              "awakeningashes; reagent1Quantity и rerollCost — параллельные "
                              "массивы (цена растёт с попытками).",
    }
    misc_summary = {}
    for typ, desc in misc_types.items():
        rows = con.execute("SELECT name, fields FROM records WHERE type=?", (typ,)).fetchall()
        examples = []
        for name, fields_json in rows[:3]:
            f = json.loads(fields_json)
            examples.append({"record": name, "nonzero_fields": nonzero(f, META_FIELDS)})
        misc_summary[typ] = {"count": len(rows), "description": desc, "examples": examples}

    # ------------------------------------------------------------------
    # Запись
    # ------------------------------------------------------------------
    cpath, csize = write_json("components.json", components, indent=1)
    apath, asize = write_jsonl("augments.jsonl", augments)
    rpath, rsize = write_jsonl("recipes.jsonl", recipes)
    rspath, rssize = write_json("recipes_summary.json", {
        "artifact_formula_count": len(recipes),
        "misc_crafting_types": misc_summary,
    }, indent=1)
    fpath, fsize = write_json("factions.json", factions_out, indent=1)

    # ------------------------------------------------------------------
    # Покрытие
    # ------------------------------------------------------------------
    print(f"\n=== Покрытие (за {time.time()-t0:.1f}s) ===")
    print(f"ItemRelic всего: {len(relic_rows)}, craftingMaterial=1 (компоненты): {len(components)}, "
          f"пропущено (craftingMaterial=0): {len(comp_skipped)}")
    print(f"  из них с найденным рецептом (ItemArtifactFormula по artifactName): {comp_with_recipe}")
    print(f"ItemEnchantment: {len(ench_rows)}")
    print(f"ItemFactionBooster+Warrant: {len(augments) - len(ench_rows)}")
    print(f"Итого augments.jsonl: {len(augments)}")
    print(f"ItemArtifactFormula (recipes.jsonl): {len(recipes)}")
    for typ, s in misc_summary.items():
        print(f"  {typ}: {s['count']} (описано кратко в recipes_summary.json)")
    print(f"Фракций (controllers/factions/*): {len(faction_ids)} id, {len(factions)} уникальных")
    print(f"  из них с вендор-слагом (нашли marketStaticItems -> factionSource): {len(fid_to_slug)}")
    unresolved_slugs = [s for s, v in slug_to_fid.items() if not v]
    if unresolved_slugs:
        print(f"  ВНИМАНИЕ: слаги без резолва faction id: {unresolved_slugs}")
    print(f"\nФайлы:")
    print(f"  {cpath} ({csize/1024:.0f} KB)")
    print(f"  {apath} ({asize/1024:.0f} KB)")
    print(f"  {rpath} ({rsize/1024:.0f} KB)")
    print(f"  {rspath} ({rssize/1024:.0f} KB)")
    print(f"  {fpath} ({fsize/1024:.0f} KB)")


if __name__ == "__main__":
    main()
