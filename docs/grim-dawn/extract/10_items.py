# -*- coding: utf-8 -*-
"""Задание 10: полный каталог носимой экипировки (оружие/броня/украшения/щиты/оффхенды/реликвии).

ItemRelic vs ItemArtifact — ИСПРАВЛЕНО после проверки полей (см. отчёт,
раздел "Правки предыдущего захода"):
  - ItemRelic (records/items/materia/comp*.dbr) имеет флаг craftingMaterial=1,
    dropSound=...craftingpart..., это сырые крафтовые материалы для завершения
    реликвии/артефакта (комбинируются по Formula) — домен задания 40, НЕ включены.
  - ItemArtifact (records/items/gearrelic/*.dbr) — это готовые, надеваемые в
    отдельный слот "Relic" предметы (artifactClassification Lesser/Greater/Divine,
    itemClassification Rare/Epic/Legendary, реальные статы, itemSkillName и т.д.,
    БЕЗ craftingMaterial). Предыдущий заход ошибочно исключил и их тоже — здесь
    это исправлено, ItemArtifact включён со slot="relic".

Запуск:  python 10_items.py
Выход:   <GD_DATA>/items.jsonl, <GD_DATA>/items_summary.json
"""
import json
import re
import time
from collections import Counter, defaultdict

from gdlib import Tags, open_sqlite, write_json, write_jsonl, norm

# ---------------------------------------------------------------------------
# Область: типы записей и их слот экипировки.
# Список сверен реальным запросом SELECT type, COUNT(*) FROM records GROUP BY type
# (WeaponMelee_2H_* из брифа не существуют; реальные имена — *2h).
SLOT_BY_TYPE = {
    "WeaponMelee_Axe": "weapon1h",
    "WeaponMelee_Sword": "weapon1h",
    "WeaponMelee_Mace": "weapon1h",
    "WeaponMelee_Dagger": "weapon1h",
    "WeaponMelee_Scepter": "weapon1h",
    "WeaponMelee_Axe2h": "weapon2h",
    "WeaponMelee_Sword2h": "weapon2h",
    "WeaponMelee_Mace2h": "weapon2h",
    "WeaponMelee_Spear2h": "weapon2h",
    "WeaponHunting_Ranged1h": "weapon1h_ranged",
    "WeaponHunting_Ranged2h": "weapon2h_ranged",
    "WeaponArmor_Shield": "offhand_shield",
    "WeaponArmor_Offhand": "offhand",
    "ArmorProtective_Head": "head",
    "ArmorProtective_Chest": "chest",
    "ArmorProtective_Shoulders": "shoulders",
    "ArmorProtective_Hands": "hands",
    "ArmorProtective_Legs": "legs",
    "ArmorProtective_Feet": "feet",
    "ArmorProtective_Waist": "waist",
    "ArmorJewelry_Ring": "ring",       # игрок носит 2 таких слота одновременно
    "ArmorJewelry_Amulet": "amulet",
    "ArmorJewelry_Medal": "medal",
    "ItemArtifact": "relic",          # готовые Reliquary/Artifact-предметы, слот Relic (см. докстринг)
}
TYPES = tuple(SLOT_BY_TYPE)

# Слоты, у которых бывает собственный "урон оружия" (min/max) — только для них
# промотируем offensive<Type>* в секцию weapon_damage. На остальных слотах
# (украшения/броня/артефакт) те же поля означают "+X% урона" или "+X-Y урона"
# как обычный аффикс-стат, а не "оружие бьёт на X-Y" — там они остаются в stats.
WEAPON_SLOTS = {"weapon1h", "weapon2h", "weapon1h_ranged", "weapon2h_ranged", "offhand_shield"}

# Слоты, где у игрока физически 2 ячейки под один и тот же тип предмета.
DOUBLE_SLOTS = {"ring", "weapon1h", "weapon1h_ranged"}  # оружие 1h/пистолеты — при dual-wield

# Основные типы урона, у которых бывают offensive<T>Min/Max и offensiveBase<T>Min/Max —
# это "урон оружия" (промотируется в weapon_damage, не остаётся в общем stats).
DAMAGE_TYPES = ["Physical", "Pierce", "Fire", "Cold", "Lightning", "Poison", "Life", "Aether", "Chaos"]

# Поля брони/блока — промотируются в отдельные секции armor/block.
# Список сверен реальным SELECT DISTINCT полей по всем записям (см. отчёт):
# defensiveProtectionModifierChance и characterDefensiveBlockRecoveryReduction
# в исходном заходе отсутствовали и утекали в общий stats.
ARMOR_FIELDS = ["defensiveProtection", "defensiveProtectionChance", "defensiveProtectionModifier",
                "defensiveProtectionModifierChance", "defensiveBonusProtection"]
BLOCK_FIELDS = ["blockAbsorption", "blockRecoveryTime", "defensiveBlock", "defensiveBlockChance",
                "defensiveBlockAmountModifier", "defensiveBlockModifier",
                "characterDefensiveBlockRecoveryReduction"]

# Требования атрибутов: реальные имена полей .dbr — strength/dexterity/intelligence
# (наследие Titan Quest), в игре показываются как Physique/Cunning/Spirit.
ATTR_MAP = [
    ("strengthRequirement", "physiqueRequirement"),
    ("dexterityRequirement", "cunningRequirement"),
    ("intelligenceRequirement", "spiritRequirement"),
]

# Чисто косметические/редакторские поля — не несут игровой семантики, выбрасываем всегда.
META_FIELDS = {
    "Class", "templateName", "actorHeight", "actorRadius", "allowTransparency", "alternateMesh",
    "armorFemaleBaseTexture", "armorFemaleBumpTexture", "armorFemaleMesh",
    "armorMaleBaseTexture", "armorMaleBumpTexture", "armorMaleMesh",
    "armorNativeBumpTexture", "armorNativeMesh", "attackEffect", "baseTexture", "baseTextures",
    "basicProjectileName", "bitmap", "bitmapFemale", "blockSound", "bumpTexture", "bumpTextures",
    "castsShadows", "dropSound", "dropSound3D", "dropSoundWater", "editorTransparency",
    "glowTexture", "glowTextures", "headFemaleBaseTexture", "headFemaleBumpTexture", "headFemaleMesh",
    "headMaleBaseTexture", "headMaleBumpTexture", "headMaleMesh", "hitSound", "maxTransparency",
    "mesh", "outlineThickness", "physicsFriction", "physicsMass", "physicsRestitution",
    "shadowBias", "specTexture", "swipeSound", "weaponTrail", "shader",
    "replacementAnimsFemale", "replacementAnimsMale", "areaOffsetX", "areaOffsetY",
    "areaRotate", "areaRotation", "markerRange", "useBoundingBoxesForDynamicObstacles",
    "taskUID1", "taskUID2", "taskUID3", "taskUID4", "taskUID5",
    "taskUID6", "taskUID7", "taskUID8", "taskUID9", "taskUID10",
}

# Поля, которые промотируются в именованные атрибуты верхнего уровня — исключаются из stats,
# чтобы не дублировать.
PROMOTED_EXTRA = {
    "FileDescription", "itemNameTag", "itemClassification", "itemLevel", "levelRequirement",
    "strengthRequirement", "dexterityRequirement", "intelligenceRequirement",
    "itemSkillName", "itemSkillLevelEq", "itemSkillAutoController", "itemSkillLevel",
    "augmentAllLevel", "itemSetName",
}
for _i in range(1, 6):
    PROMOTED_EXTRA.add(f"augmentSkillName{_i}")
    PROMOTED_EXTRA.add(f"augmentSkillLevel{_i}")
for _i in range(1, 4):
    PROMOTED_EXTRA.add(f"augmentMasteryName{_i}")
    PROMOTED_EXTRA.add(f"augmentMasteryLevel{_i}")
for _i in range(1, 7):
    PROMOTED_EXTRA.add(f"modifiedSkillName{_i}")
    PROMOTED_EXTRA.add(f"modifierSkillName{_i}")

PLACEHOLDER_RE = re.compile(r"\bblank\b|\btemplate\b", re.IGNORECASE)
DEBUG_PATH_RE = re.compile(r"test|debug|_dev|sandbox", re.IGNORECASE)


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


def nonzero_items(f, exclude):
    return {k: v for k, v in f.items() if k not in exclude and not is_zero(v)}


# Многие Skill_* записи (например playerclass03/bloodofdreeg1.dbr) сами не несут
# skillDisplayName — имя лежит в связанной "buff"/"pet"-записи, на которую они
# ссылаются одним из этих полей. Проверено на bloodofdreeg1 (-> ..._buff.dbr,
# skillDisplayName=tagClass03SkillName04A) и на нескольких *_petmodifier.dbr
# (-> petSkillName). Без этого шага ~17% augment-записей теряли имя скилла.
SKILL_INDIRECTION_FIELDS = ("buffSkillName", "petSkillName", "alternatePetModifierSkillName")


def resolve_skill(path, tags, name_cache, con, _depth=0):
    """path (records/.../x.dbr) -> человекочитаемое имя скилла, None если пусто/не найдено.

    Если у самой записи нет имени, пробуем один-два шага косвенности через
    buffSkillName/petSkillName (см. SKILL_INDIRECTION_FIELDS) — так называемые
    "тонкие" Skill_* записи типично ссылаются на настоящую именованную запись.
    """
    if not path:
        return None
    key = norm(path)
    if key in name_cache:
        return name_cache[key]
    name_cache[key] = None  # guard против циклических ссылок при рекурсии
    row = con.execute("SELECT fields FROM records WHERE name=?", (key,)).fetchone()
    name = None
    if row:
        f = json.loads(row[0])
        for tagfield in ("skillDisplayName", "description", "itemNameTag"):
            tv = f.get(tagfield)
            if isinstance(tv, str) and tv in tags:
                name = tags(tv)
                break
        if not name and _depth < 3:
            for indirect in SKILL_INDIRECTION_FIELDS:
                nxt = f.get(indirect)
                if nxt:
                    name = resolve_skill(nxt, tags, name_cache, con, _depth + 1)
                    if name:
                        break
        if not name:
            name = f.get("FileDescription")
    name_cache[key] = name
    return name


def is_mi(item_classification, path, file_description, typ=None):
    """Эвристика Monster Infrequent: см. отчёт REPORTS/10_items.md, раздел 'Неуверенности'."""
    if typ == "ItemArtifact":
        # Готовые реликвии/артефакты baseline-тира тоже itemClassification=Rare,
        # но это не "монстро-инфрequent" дропы, а базовый крафтовый тир — не MI.
        return False
    if item_classification != "Rare":
        return False
    if "storyelements" in path or "/quest" in path:
        return False  # квестовые награды — тоже Rare+именные, но не MI
    if not file_description:
        return False
    fd = file_description.strip().lower()
    if not fd or "blank" in fd or "template" in fd or fd == "none":
        return False
    return True


def build_weapon_damage(f):
    wd = {}
    for t in DAMAGE_TYPES:
        sub = {}
        for suffix in ("Min", "Max"):
            k = f"offensiveBase{t}{suffix}"
            if not is_zero(f.get(k)):
                sub[k] = f[k]
        for suffix in ("Min", "Max", "Modifier", "Chance"):
            k = f"offensive{t}{suffix}"
            if not is_zero(f.get(k)):
                sub[k] = f[k]
        if sub:
            wd[t] = sub
    return wd


def build_augments(f, tags, name_cache, con):
    augments = []
    for i in range(1, 6):
        sn = f.get(f"augmentSkillName{i}")
        if sn:
            augments.append({
                "skill": sn,
                "skill_name": resolve_skill(sn, tags, name_cache, con),
                "level": f.get(f"augmentSkillLevel{i}"),
            })
    mastery = []
    for i in range(1, 4):
        mn = f.get(f"augmentMasteryName{i}")
        if mn:
            mastery.append({
                "mastery": mn,
                "mastery_name": resolve_skill(mn, tags, name_cache, con),
                "level": f.get(f"augmentMasteryLevel{i}"),
            })
    modifiers = []
    for i in range(1, 7):
        modified = f.get(f"modifiedSkillName{i}")
        modifier = f.get(f"modifierSkillName{i}")
        if modified or modifier:
            modifiers.append({
                "modifies": modified,
                "modifies_name": resolve_skill(modified, tags, name_cache, con),
                "modifier": modifier,
                "modifier_name": resolve_skill(modifier, tags, name_cache, con),
            })
    return augments, mastery, modifiers


def main():
    t0 = time.time()
    con = open_sqlite(readonly=True)
    tags = Tags()
    name_cache = {}
    set_cache = {}  # norm(itemSetName) -> summary dict (для items_summary.json)

    q = ",".join("?" * len(TYPES))
    rows = con.execute(
        f"SELECT name, type, src, fields FROM records WHERE type IN ({q})", TYPES
    ).fetchall()
    print(f"записей в области заданий (по типам): {len(rows)}")

    items = []
    skipped_debug = []
    skipped_placeholder = []
    by_type = Counter()
    by_slot = Counter()
    by_classification = Counter()
    mi_count = 0
    unknown_stat_keys = Counter()

    for name, typ, src, fields_json in rows:
        f = json.loads(fields_json)
        file_desc = f.get("FileDescription")

        if DEBUG_PATH_RE.search(name):
            skipped_debug.append(name)
            continue
        if file_desc and PLACEHOLDER_RE.search(file_desc):
            skipped_placeholder.append((name, file_desc))
            continue

        # --- имя ---
        # itemNameTag отсутствует у ItemArtifact (records/items/gearrelic/*) —
        # там имя лежит в поле description (тот же тэг-паттерн, см. gdlib.Tags.
        # item_name(), которая пробует itemNameTag, затем description). Без
        # этого шага все 91 реликвия/артефакт получали имя из FileDescription —
        # для b016_relic.dbr это, например, редакторская пометка
        # "Quest Reward - Lost Elder" вместо настоящего "Sacred Talisman".
        name_tag = f.get("itemNameTag") or f.get("description")
        if name_tag and name_tag in tags:
            item_name = tags(name_tag)
            name_source = "tag"
        elif file_desc:
            item_name = file_desc
            name_source = "file_description"
        else:
            item_name = name
            name_source = "record_name"

        item_classification = f.get("itemClassification")
        slot = SLOT_BY_TYPE.get(typ)
        mi_flag = is_mi(item_classification, name, file_desc, typ)
        if mi_flag:
            mi_count += 1

        entity = {
            "record": name,
            "name": item_name,
            "name_tag": name_tag,
            "name_source": name_source,
            "type": typ,
            "src": src,
            "slot": slot,
            "itemClassification": item_classification,
            "is_mi": mi_flag,
        }

        for src_field, dst_field in (("itemLevel", "itemLevel"), ("levelRequirement", "levelRequirement")):
            v = f.get(src_field)
            if not is_zero(v):
                entity[dst_field] = v
        for src_field, dst_field in ATTR_MAP:
            v = f.get(src_field)
            if not is_zero(v):
                entity[dst_field] = v

        # --- базовые статы ---
        # offensive<Type>Min/Max/Modifier/Chance значит "урон оружия" только на
        # оружейных слотах (WEAPON_SLOTS). На украшениях/броне/артефакте те же
        # поля — это аффикс "+X% урона типа T" или "+X-Y урона типа T", а не урон
        # оружия предмета (у кольца нет "оружейного урона") — там они остаются
        # в общем stats под сырым именем, без промоушена в weapon_damage.
        is_weapon_slot = slot in WEAPON_SLOTS
        wd = build_weapon_damage(f) if is_weapon_slot else {}
        if wd:
            entity["weapon_damage"] = wd
        armor = {k: f[k] for k in ARMOR_FIELDS if not is_zero(f.get(k))}
        if armor:
            entity["armor"] = armor
        block = {k: f[k] for k in BLOCK_FIELDS if not is_zero(f.get(k))}
        if block:
            entity["block"] = block

        # --- гранта скилла предметом ---
        item_skill = f.get("itemSkillName")
        if item_skill:
            entity["itemSkill"] = {
                "skill": item_skill,
                "skill_name": resolve_skill(item_skill, tags, name_cache, con),
                "levelEq": f.get("itemSkillLevelEq"),
                "autoController": f.get("itemSkillAutoController"),
            }

        # --- аугменты (мастерство/скиллы, встроенные в предмет) ---
        augments, mastery_augments, skill_modifiers = build_augments(f, tags, name_cache, con)
        if augments:
            entity["augments"] = augments
        if mastery_augments:
            entity["mastery_augments"] = mastery_augments
        if skill_modifiers:
            entity["skill_modifiers"] = skill_modifiers
        if not is_zero(f.get("augmentAllLevel")):
            entity["augmentAllLevel"] = f["augmentAllLevel"]

        # --- сет ---
        set_ref = f.get("itemSetName")
        if set_ref:
            key = norm(set_ref)
            entity["set"] = {"record": set_ref}
            if key not in set_cache:
                srow = con.execute("SELECT fields FROM records WHERE name=?", (key,)).fetchone()
                if srow:
                    sf = json.loads(srow[0])
                    set_name_tag = sf.get("setName")
                    set_name = tags(set_name_tag) if set_name_tag else sf.get("FileDescription")
                    bonuses = nonzero_items(sf, {
                        "setMembers", "setName", "setDescription", "FileDescription",
                        "templateName", "Class", "characterBaseAttackSpeedTag",
                    } | META_FIELDS)
                    # Пути к скиллам внутри bonuses_by_pieces (itemSkillName,
                    # augmentSkillNameN, augmentMasteryNameN) резолвим так же,
                    # как и для обычных предметов — храним и путь, и имя.
                    for bk in list(bonuses):
                        if bk == "itemSkillName" or re.match(
                                r"^(augmentSkillName|augmentMasteryName|"
                                r"modifiedSkillName|modifierSkillName)\d*$", bk):
                            bonuses[f"{bk}_resolved"] = resolve_skill(
                                bonuses[bk], tags, name_cache, con)
                    set_cache[key] = {
                        "record": set_ref,
                        "name": set_name,
                        "members": sf.get("setMembers", []),
                        "bonuses_by_pieces": bonuses,  # индекс i в массиве = бонус при (i+1) надетых предметах сета
                    }
                else:
                    set_cache[key] = {"record": set_ref, "name": None, "members": [], "bonuses_by_pieces": {}}

        # --- всё остальное ненулевое -> stats (сырые имена полей .dbr) ---
        exclude = META_FIELDS | PROMOTED_EXTRA
        if is_weapon_slot:
            # Уже промотировано в weapon_damage выше — не дублируем в stats.
            # На НЕ-оружейных слотах эти же поля осознанно остаются в stats
            # (это "+% урона типа T", а не урон оружия — см. комментарий выше).
            exclude |= {k for t in DAMAGE_TYPES for k in
                        (f"offensiveBase{t}Min", f"offensiveBase{t}Max",
                         f"offensive{t}Min", f"offensive{t}Max", f"offensive{t}Modifier", f"offensive{t}Chance")}
        exclude |= set(ARMOR_FIELDS) | set(BLOCK_FIELDS)
        stats = nonzero_items(f, exclude)
        if stats:
            entity["stats"] = stats
            unknown_stat_keys.update(stats.keys())

        items.append(entity)
        by_type[typ] += 1
        by_slot[slot] += 1
        by_classification[str(item_classification)] += 1

    path, size = write_jsonl("items.jsonl", items)
    print(f"\nЗаписано {len(items)} предметов -> {path} ({size/1024:.0f} KB) за {time.time()-t0:.1f}s")

    summary = {
        "generated_from": "gd.sqlite",
        "counts": {
            "total_in_scope_types": len(rows),
            "written": len(items),
            "skipped_debug_sandbox": len(skipped_debug),
            "skipped_placeholder": len(skipped_placeholder),
            "by_type": dict(by_type.most_common()),
            "by_slot": dict(by_slot.most_common()),
            "by_itemClassification": dict(by_classification.most_common()),
            "is_mi_count": mi_count,
        },
        "excluded_examples": {
            "debug_sandbox": skipped_debug[:20],
            "placeholder": [n for n, _d in skipped_placeholder[:20]],
        },
        "sets": set_cache,
        "top_stat_fields": dict(unknown_stat_keys.most_common(60)),
    }
    spath, ssize = write_json("items_summary.json", summary, indent=1)
    print(f"Записана сводка -> {spath} ({ssize/1024:.0f} KB)")

    # --- покрытие ---
    print("\n=== Покрытие ===")
    print(f"Всего записей в областных типах: {len(rows)}")
    print(f"Записано в items.jsonl: {len(items)}")
    print(f"Пропущено (test/debug/_dev/sandbox путь): {len(skipped_debug)}")
    print(f"Пропущено (BASE BLANK / TEMPLATE заглушка): {len(skipped_placeholder)}")
    print(f"Помечено is_mi=true: {mi_count}")
    print(f"Наборов (sets) найдено: {len(set_cache)}")
    print(f"Уникальных raw-полей в stats (после промоушена): {len(unknown_stat_keys)}")
    print("По слотам:", dict(by_slot.most_common()))
    print("По itemClassification:", dict(by_classification.most_common()))


if __name__ == "__main__":
    main()
