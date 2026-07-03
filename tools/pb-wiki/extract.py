# -*- coding: utf-8 -*-
"""
Phantom Brigade — extractor for the local equipment wiki.

Reads the game's YAML config + Russian/English text tables, resolves the
subsystem/preset inheritance trees and genSteps, classifies each player-mech
item (weapons / armor parts / backpacks) and internal module ("modification"),
extracts UI icons straight from the Unity assets, and writes a single
`data.js` (window.PB_DATA = {...}) that the offline index.html consumes.

Run:  python extract.py
"""
import os, sys, json, base64, io, re, collections

try:
    import yaml
except ImportError:
    sys.exit("PyYAML missing:  python -m pip install PyYAML")

GAME = r"C:/games/Steam/steamapps/common/Phantom Brigade"
CFG  = GAME + "/Configs"
EQ   = CFG + "/DataDecomposed/Equipment"
STATS_DIR = CFG + "/DataDecomposed/UnitStats"
QUAL_DIR  = CFG + "/DataDecomposed/Combat/QualityTables"
DATA_DATA = GAME + "/PhantomBrigade_Data"
OUT_DIR   = os.path.dirname(os.path.abspath(__file__))

# ---------------------------------------------------------------- YAML loader
# The configs use Unity custom tags (!AddHardpoints, !CheckPartRating, ...).
# Preserve them: return the mapping/sequence with a "__tag__" marker.
class PBLoader(yaml.SafeLoader):
    pass

def _tag_multi(loader, tag_suffix, node):
    if isinstance(node, yaml.MappingNode):
        d = loader.construct_mapping(node, deep=True)
        d["__tag__"] = tag_suffix
        return d
    if isinstance(node, yaml.SequenceNode):
        return loader.construct_sequence(node, deep=True)
    return loader.construct_scalar(node)

PBLoader.add_multi_constructor("!", _tag_multi)
# Unity floats sometimes serialize oddly; keep default scalar handling.

def load_yaml(path):
    with open(path, "r", encoding="utf-8-sig") as f:
        try:
            return yaml.load(f, Loader=PBLoader) or {}
        except Exception as e:
            print("  ! yaml error", os.path.basename(path), e, file=sys.stderr)
            return {}

def load_dir(path):
    """key(basename w/o .yaml) -> parsed dict, for every *.yaml in a flat dir."""
    out = {}
    if not os.path.isdir(path):
        return out
    for fn in os.listdir(path):
        if fn.endswith(".yaml"):
            out[fn[:-5]] = load_yaml(os.path.join(path, fn))
    return out

# ---------------------------------------------------------------- text tables
def load_text_sector(lang, sector):
    """Returns {entryKey: text} for a localization sector."""
    if lang == "en":
        p = f"{CFG}/TextLibrary/Sectors/{sector}.yaml"
    else:
        p = f"{CFG}/TextLocalizations/Russian/Sectors/{sector}.yaml"
    d = load_yaml(p)
    out = {}
    for k, v in (d.get("entries") or {}).items():
        if isinstance(v, dict):
            out[k] = v.get("text", "")
    return out

TXT = {}  # TXT[sector][lang][key]
def txt_sector(sector):
    if sector not in TXT:
        TXT[sector] = {"ru": load_text_sector("ru", sector),
                       "en": load_text_sector("en", sector)}
    return TXT[sector]

def text(sector, key, suffix):
    """Best available: RU then EN. suffix is '__name' or '__text'."""
    s = txt_sector(sector)
    k = key + suffix
    ru = s["ru"].get(k, "")
    en = s["en"].get(k, "")
    return ru or "", en or ""

print("Loading configs ...")
SUBS   = load_dir(EQ + "/Subsystems")
PRES   = load_dir(EQ + "/Part_Presets")
GROUPS = load_dir(EQ + "/Groups")
STATS  = load_dir(STATS_DIR)
QUAL   = load_dir(QUAL_DIR)
STATDIST = load_dir(EQ + "/Subsystem_StatDistributions")
print(f"  subsystems={len(SUBS)} presets={len(PRES)} groups={len(GROUPS)} stats={len(STATS)}")

# ---------------------------------------------------------------- helpers
def as_list(v):
    if v is None or v == "":
        return []
    return v if isinstance(v, list) else [v]

def tag_keys(v):
    """tags can be a list (subsystems) or a dict {tag: true} (group filters)."""
    if isinstance(v, dict):
        return [k for k, on in v.items() if on and k != "__tag__"]
    return [t for t in as_list(v) if t]

# ---------------------------------------------------------------- subsystem resolution
_sub_cache = {}
def resolve_sub(key, seen=None):
    """Merge a subsystem with its parent chain. Returns dict(stats, tags, rating, hardpoints, ...)."""
    if key in _sub_cache:
        return _sub_cache[key]
    seen = seen or set()
    raw = SUBS.get(key)
    if raw is None or key in seen:
        return {"stats": {}, "tags": [], "rating": 1, "hardpoints": [],
                "statDistribution": "", "hidden": True, "missing": True}
    seen = seen | {key}
    parent = raw.get("parent") or ""
    base = resolve_sub(parent, seen) if parent else {
        "stats": {}, "tags": [], "rating": 1, "hardpoints": [], "statDistribution": ""}
    stats = dict(base["stats"])
    for sk, sv in (raw.get("stats") or {}).items():
        if isinstance(sv, dict) and "value" in sv:
            stats[sk] = sv.get("value")
    tags = list(dict.fromkeys(base["tags"] + tag_keys(raw.get("tags"))))
    res = {
        "stats": stats,
        "tags": tags,
        "rating": raw.get("rating", base.get("rating", 1)),
        "hardpoints": tag_keys(raw.get("hardpoints")) or base.get("hardpoints", []),
        "statDistribution": raw.get("statDistribution") or base.get("statDistribution", ""),
        "hidden": raw.get("hidden", False),
        "visuals": tag_keys(raw.get("visuals")),
        "parent": parent,
    }
    _sub_cache[key] = res
    return res

def sub_text(key):
    return text("equipment_subsystems", key, "__name") + text("equipment_subsystems", key, "__text")

def sub_name_resolved(key):
    """Climb the parent chain until a localized name is found (tier variants inherit it)."""
    k = key
    seen = set()
    while k and k not in seen:
        seen.add(k)
        ru, en = text("equipment_subsystems", k, "__name")
        if ru or en:
            rd, ed = text("equipment_subsystems", k, "__text")
            return ru, en, rd, ed
        raw = SUBS.get(k) or {}
        k = raw.get("parent") or ""
    return "", "", "", ""

TIER_RE = re.compile(r"_(r[123]|[0-9]{1,2})$")
def module_family(key):
    """Strip trailing tier suffix to group tier variants together."""
    m = TIER_RE.search(key)
    return key[:m.start()] if m else key
def module_tier(key):
    m = TIER_RE.search(key)
    return m.group(1) if m else ""

# ---------------------------------------------------------------- preset resolution
def resolve_preset(key, seen=None):
    """Merge preset parents (multi-inheritance). Accumulate tags, sockets, genSteps, chain keys."""
    seen = seen or set()
    raw = PRES.get(key)
    if raw is None or key in seen:
        return {"tags": [], "sockets": [], "genSteps": [], "chain": [], "hidden": True}
    seen = seen | {key}
    tags, sockets, gensteps, chain = [], [], [], []
    for p in as_list(raw.get("parents")):
        pk = p.get("key") if isinstance(p, dict) else p
        if pk:
            base = resolve_preset(pk, seen)
            tags += base["tags"]; sockets += base["sockets"]
            gensteps += base["genSteps"]; chain += base["chain"] + [pk]
    tags += tag_keys(raw.get("tags"))
    sockets += tag_keys(raw.get("sockets"))
    gensteps += as_list(raw.get("genSteps"))
    return {
        "tags": list(dict.fromkeys(tags)),
        "sockets": list(dict.fromkeys(sockets)),
        "genSteps": gensteps,
        "chain": list(dict.fromkeys(chain)),
        "hidden": raw.get("hidden", False),
        "raw": raw,
    }

def preset_text(key, chain):
    """PB joins names/descs across the whole inheritance chain."""
    ru_names, en_names, ru_desc, en_desc = [], [], [], []
    for k in chain + [key]:
        rn, en = text("equipment_part_presets", k, "__name")
        if rn: ru_names.append(rn)
        if en: en_names.append(en)
        rd, ed = text("equipment_part_presets", k, "__text")
        if rd: ru_desc.append(rd)
        if ed: en_desc.append(ed)
    return (" ".join(ru_names), " ".join(en_names),
            " ".join(dict.fromkeys(ru_desc)), " ".join(dict.fromkeys(en_desc)))

# ---------------------------------------------------------------- gen steps
def parse_gensteps(gensteps):
    """Return list of installed subsystems w/ target hardpoint + rarity gate, and empty gated slots."""
    installed = []   # {subsystem, hardpoint, ratingMin, ratingMax}
    for step in gensteps:
        if not isinstance(step, dict):
            continue
        tag = step.get("__tag__", "")
        hps = tag_keys(step.get("hardpointsTargeted"))
        rmin, rmax = 1, 99
        for chk in as_list(step.get("checks")):
            if isinstance(chk, dict) and chk.get("__tag__") == "CheckPartRating":
                if chk.get("ratingMin") is not None: rmin = chk["ratingMin"]
                if chk.get("ratingMax") is not None: rmax = chk["ratingMax"]
        subs = tag_keys(step.get("subsystemsInitial"))
        if tag == "AddHardpoints":
            if subs:
                for s in subs:
                    for hp in (hps or [""]):
                        installed.append({"subsystem": s, "hardpoint": hp,
                                          "ratingMin": rmin, "ratingMax": rmax, "empty": False})
            else:
                for hp in hps:
                    installed.append({"subsystem": None, "hardpoint": hp,
                                      "ratingMin": rmin, "ratingMax": rmax, "empty": True})
        elif tag == "SetHardpointState":
            for hp in hps:
                installed.append({"subsystem": None, "hardpoint": hp,
                                  "ratingMin": rmin, "ratingMax": rmax, "empty": True,
                                  "setState": True})
    return installed

# ---------------------------------------------------------------- classification
SET_FAMILIES = {
    "arrow": "Стрела", "asgard": "Асгард", "bein": "Бейн", "blackbird": "Ворон",
    "elbrus": "Эльбрус", "hakobu": "Хакобу", "helge": "Хельге", "knox": "Нокс",
    "tsubasa": "Тсубаса", "vidar": "Видар",
}
WEIGHT = {"light": "Лёгкий", "medium": "Средний", "heavy": "Тяжёлый"}
WEIGHT_SFX = {"_l": "light", "_m": "medium", "_h": "heavy"}

def classify_item(key, pr):
    tags, sockets, chain = pr["tags"], pr["sockets"], pr["chain"]
    slot = None
    if "back" in tags or "back" in sockets:
        slot = "back"
    elif "part_top" in tags or "body_top" in chain:
        slot = "torso"
    elif "part_bottom" in tags or "body_bottom" in chain:
        slot = "legs"
    elif "part_arm" in tags or "body_arm" in chain:
        slot = "arm"
    elif "wpn_secondary" in tags or "wpn_root_secondary" in chain or "secondary" in sockets:
        slot = "secondary_weapon"
    elif "wpn_primary" in tags or "wpn_root_primary" in chain:
        slot = "main_weapon"
    # set family + weight (armor)
    fam = famname = weight = None
    for f in SET_FAMILIES:
        if f in key:
            fam, famname = f, SET_FAMILIES[f]
            break
    for sfx, w in [("_light", "light"), ("_medium", "medium"), ("_heavy", "heavy")]:
        if sfx in key:
            weight = w; break
    return slot, fam, famname, weight

def manufacturer_of(tags):
    for t in tags:
        m = re.match(r"^mnf_(\d+)$", t)
        if m:
            ru, en = text("equipment_groups", f"part_mnf_{m.group(1)}", "__name")
            return {"key": t, "name": ru or en or t.upper()}
    return None

# player-mech only: drop vehicles / tanks / turrets / sentries / frigates
EXCLUDE = re.compile(r"vhc_|tank_|turret|sentry|frigate|_v01|walker_leg")
def is_player_gear(key, pr):
    if EXCLUDE.search(key):
        return False
    return classify_item(key, pr)[0] is not None

# ---------------------------------------------------------------- stat metadata
def stat_meta():
    meta = {}
    for k, d in STATS.items():
        if not isinstance(d, dict):
            continue
        col = d.get("uiColor") or {}
        ipl = d.get("increasePerLevel")
        per_level = None
        if isinstance(ipl, dict) and ipl.get("f") is not None:
            per_level = ipl["f"]
        ru, en = text("unit_stats", k, "__name")
        flags = d.get("flags") or {}
        meta[k] = {
            "key": k,
            "name": ru or en or k,
            "nameEn": en,
            "icon": d.get("uiIcon") or "",
            "color": [round(col.get("r", 1), 3), round(col.get("g", 1), 3), round(col.get("b", 1), 3)]
                      if col else [1, 1, 1],
            "priority": d.get("uiPriority", 0),
            "percentage": bool(d.get("uiPercentage")),
            "multiplier": d.get("uiMultiplier", 1),
            "rounded": bool(d.get("rounded")),
            "perLevel": per_level,
            "isDamage": bool(flags.get("isDamage")),
            "exposedPerSubsystem": bool(d.get("exposedPerSubsystem")),
            "showAsOutput": bool(d.get("showAsOutput")),
        }
    return meta

# ---------------------------------------------------------------- quality (rarity)
def quality_tables():
    out = {}
    for name in ("default_r0_training", "default_r1_common",
                 "default_r2_uncommon", "default_r3_rare"):
        d = QUAL.get(name) or {}
        col = d.get("uiColor") or {}
        idx = None
        for w in as_list(d.get("weightsInternal")):
            if isinstance(w, dict):
                idx = w.get("qualityIndex")
        out[name] = {
            "color": [round(col.get("r", 1), 3), round(col.get("g", 1), 3), round(col.get("b", 1), 3)],
            "qualityIndex": idx,
            "liveryGrade": d.get("liveryGrade"),
        }
    return out

# ---------------------------------------------------------------- groups (filters + icons)
def build_groups():
    out = []
    for k, d in GROUPS.items():
        if not isinstance(d, dict):
            continue
        ru, en = text("equipment_groups", "part_" + k, "__name")
        if not (ru or en):
            ru, en = text("equipment_groups", k, "__name")
        out.append({
            "key": k,
            "name": ru or en or k,
            "type": d.get("type"),
            "icon": d.get("icon") or "",
            "iconSmall": d.get("iconSmall") or "",
            "visibleInFilters": bool(d.get("visibleInFilters")),
            "visibleInName": bool(d.get("visibleInName")),
            "tagsPreset": tag_keys(d.get("tagsPartPreset")),
            "tagsSub": tag_keys(d.get("tagsSubsystem")),
            "parts": bool(d.get("parts")),
            "subsystems": bool(d.get("subsystems")),
        })
    return out

print("This module defines the extractor; run build() below.")


# ============================================================ ICON EXTRACTION
def extract_icons(wanted):
    """wanted: set of texture names. Returns {name: 'data:image/png;base64,...'}."""
    try:
        import UnityPy
    except ImportError:
        print("  ! UnityPy missing — icons skipped")
        return {}
    icons = {}
    files = ["resources.assets", "sharedassets0.assets", "globalgamemanagers.assets"]
    for fn in files:
        path = os.path.join(DATA_DATA, fn)
        if not os.path.exists(path):
            continue
        try:
            env = UnityPy.load(path)
        except Exception as e:
            print("  ! load", fn, e); continue
        for obj in env.objects:
            if obj.type.name != "Texture2D":
                continue
            try:
                data = obj.read()
                nm = data.m_Name
            except Exception:
                continue
            if nm in wanted and nm not in icons:
                try:
                    img = data.image
                    if img is None:
                        continue
                    buf = io.BytesIO()
                    img.save(buf, format="PNG")
                    icons[nm] = "data:image/png;base64," + base64.b64encode(buf.getvalue()).decode()
                except Exception as e:
                    print("  ! decode", nm, e)
    return icons


# ============================================================ BUILD
def build():
    smeta = stat_meta()
    quals = quality_tables()
    groups = build_groups()

    # category/spec resolution via group tag-filters (subset match, most specific wins)
    cat_groups  = [g for g in groups if g["type"] == "category"]
    spec_groups = [g for g in groups if g["type"] == "spec"]
    ARMOR_RU = {"light": "Броня (лёгкая)", "medium": "Броня (средняя)", "heavy": "Броня (тяжёлая)"}
    def match_group(item_tags, glist):
        best, best_n = None, -1
        tagset = set(item_tags)
        for g in glist:
            req = g["tagsPreset"] + g["tagsSub"]
            if req and all(t in tagset for t in req):
                if len(req) > best_n:
                    best, best_n = g, len(req)
        return best
    def resolve_category(item_tags, weight):
        g = match_group(item_tags, cat_groups)
        if g:
            return g["name"], g["icon"]
        for t in item_tags:
            if t.startswith("category_armor"):
                return ARMOR_RU.get(weight, "Броня"), "s_icon_l32_part_arch_all"
        return None, None
    def resolve_specs(item_tags):
        out = []
        for t in item_tags:
            if not t.startswith("spec_"):
                continue
            g = next((g for g in spec_groups if t in (g["tagsPreset"] + g["tagsSub"])
                      or g["key"] == "part_" + t), None)
            if not g:
                ru, en = text("equipment_groups", "part_" + t, "__name")
                nm = ru or en or t.replace("spec_", "")
            else:
                nm = g["name"]
            out.append({"key": t, "name": nm})
        return out

    items = []
    modules = []

    # ---- items (part presets, player gear only) ----
    for key, raw in PRES.items():
        pr = resolve_preset(key)
        if pr.get("hidden"):
            continue
        if not is_player_gear(key, pr):
            continue
        slot, fam, famname, weight = classify_item(key, pr)
        rn, en, rd, ed = preset_text(key, pr["chain"])
        installed = parse_gensteps(pr["genSteps"])

        # resolve installed subsystems, gather stats + manufacturer + specs
        sublist = []          # real installed parts (weapon core / armor plates)
        module_slots = []     # internal_aux_* slots, w/ rarity gate (the "modification" slots)
        agg = collections.defaultdict(float)
        all_tags = list(pr["tags"])
        for inst in installed:
            sk = inst["subsystem"]
            hp = inst["hardpoint"]
            gate = {"hardpoint": hp, "ratingMin": inst["ratingMin"], "ratingMax": inst["ratingMax"]}
            # module slot? (accepts a modification chip)
            if hp.startswith("internal_aux_"):
                slot_entry = dict(gate)
                if sk:
                    rs = resolve_sub(sk)
                    srn, sen, srd, sed = sub_name_resolved(sk)
                    slot_entry["default"] = {"key": sk, "name": srn or sen or sk}
                    if inst["ratingMin"] <= 1:
                        for st, val in rs["stats"].items():
                            if isinstance(val, (int, float)): agg[st] += val
                    all_tags += rs["tags"]
                module_slots.append(slot_entry)
                continue
            # meta hardpoints (rarity/perk) — skip from display
            if not (hp.startswith("external_") or hp.startswith("internal_main")):
                continue
            if not sk:
                continue
            rs = resolve_sub(sk)
            srn, sen, srd, sed = sub_name_resolved(sk)
            entry = dict(gate)
            entry.update({"key": sk, "name": srn or sen or sk,
                          "stats": rs["stats"], "tags": rs["tags"],
                          "rating": rs["rating"], "statDistribution": rs["statDistribution"]})
            all_tags += rs["tags"]
            if inst["ratingMin"] <= 1:
                for st, val in rs["stats"].items():
                    if isinstance(val, (int, float)): agg[st] += val
            sublist.append(entry)

        # collapse module slots to one entry per hardpoint (min unlock rarity, keep default)
        by_hp = {}
        for s in module_slots:
            hp = s["hardpoint"]
            cur = by_hp.get(hp)
            if cur is None:
                by_hp[hp] = dict(s)
            else:
                cur["ratingMin"] = min(cur["ratingMin"], s["ratingMin"])
                if "default" not in cur and "default" in s:
                    cur["default"] = s["default"]
        module_slots = sorted(by_hp.values(), key=lambda s: (s["ratingMin"], s["hardpoint"]))

        all_tags = list(dict.fromkeys(all_tags))
        manu = manufacturer_of(all_tags)
        specs = resolve_specs(all_tags)
        category = next((t for t in all_tags if t.startswith("category_")), None)
        cat_name, cat_icon = resolve_category(all_tags, weight)

        items.append({
            "key": key, "slot": slot,
            "set": fam, "setName": famname, "weight": weight,
            "name": rn or en or key, "nameEn": en,
            "desc": rd, "descEn": ed,
            "manufacturer": manu,
            "category": category, "catName": cat_name, "catIcon": cat_icon,
            "specs": specs,
            "tags": all_tags,
            "subsystems": sublist,
            "moduleSlots": module_slots,
            "stats": {k: round(v, 4) for k, v in agg.items()},
            "chain": pr["chain"], "sockets": pr["sockets"],
        })

    # ---- modules (internal_aux subsystems = modifications) ----
    MODULE_HP = ("internal_aux_offense", "internal_aux_defense", "internal_aux_mobility",
                 "internal_aux_pilot", "internal_aux_weapon", "internal_aux_top_thrusters",
                 "internal_aux_top_core")
    for key, raw in SUBS.items():
        if not key.startswith("internal_aux"):
            continue
        if EXCLUDE.search(key) or raw.get("hidden"):
            continue
        rs = resolve_sub(key)
        hps = rs["hardpoints"]
        if not any(h in MODULE_HP for h in hps):
            continue
        if not rs["stats"]:
            continue
        srn, sen, srd, sed = sub_name_resolved(key)
        manu = manufacturer_of(rs["tags"])
        # comp2/comp3/scrap are internal bookkeeping, not meaningful module effects
        eff = {k: v for k, v in rs["stats"].items()
               if isinstance(v, (int, float)) and k not in
               ("comp2_value", "comp3_value", "scrap_value")}
        modules.append({
            "key": key, "kind": "module",
            "family": module_family(key), "tier": module_tier(key),
            "name": srn or sen or key, "nameEn": sen,
            "desc": srd, "descEn": sed,
            "slots": [h for h in hps if h in MODULE_HP],
            "rating": rs["rating"],
            "stats": eff,
            "tags": rs["tags"],
            "manufacturer": manu,
        })

    # ---- icons ----
    wanted = set()
    for m in smeta.values():
        if m["icon"]:
            wanted.add(m["icon"])
    for g in groups:
        if g["icon"]: wanted.add(g["icon"])
        if g["iconSmall"]: wanted.add(g["iconSmall"])
    print(f"Extracting {len(wanted)} icons from Unity assets ...")
    icons = extract_icons(wanted)
    print(f"  got {len(icons)} icons")

    data = {
        "generated": "extract.py",
        "sets": SET_FAMILIES,
        "weights": WEIGHT,
        "slots": {
            "main_weapon": "Основное оружие", "secondary_weapon": "Доп. оружие",
            "torso": "Торс", "legs": "Ноги", "arm": "Рука", "back": "Ранец",
        },
        "statMeta": smeta,
        "quality": quals,
        "groups": groups,
        "items": items,
        "modules": modules,
        "icons": icons,
        "levelScaling": {"increase": 0.25, "limit": 99, "upgradeLimit": 3,
                         "stats": [k for k, m in smeta.items() if m["perLevel"]]},
    }

    out_path = os.path.join(OUT_DIR, "data.js")
    with open(out_path, "w", encoding="utf-8") as f:
        f.write("window.PB_DATA = ")
        json.dump(data, f, ensure_ascii=False, separators=(",", ":"))
        f.write(";")
    size = os.path.getsize(out_path)
    print(f"\nWrote {out_path}  ({size/1024:.0f} KB)")
    print(f"  items={len(items)}  modules={len(modules)}  groups={len(groups)}  icons={len(icons)}")
    # quick slot breakdown
    bd = collections.Counter(i["slot"] for i in items)
    print("  slots:", dict(bd))
    return data


if __name__ == "__main__":
    build()
