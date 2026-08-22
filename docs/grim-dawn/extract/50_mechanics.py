# -*- coding: utf-8 -*-
"""Задание 50 — Механики, константы, формулы.

Извлекает "правила игры" (не контент): игровые константы движка, формулы боя,
таблицу уровней/очков, и — самое главное — таблицу соответствия
"имя поля .dbr -> тип урона/сопротивление/модификатор", выведенную из
реального частотного списка полей всех 82132 записей БД (а не по памяти).

Вход:  D:/git/home/data/grim-dawn/gd.sqlite, tags_en.json (через gdlib)
Выход: D:/git/home/data/grim-dawn/mechanics.json
Идемпотентен, без аргументов: `python 50_mechanics.py`.
"""
import json
import re
from collections import Counter

import gdlib
from gdlib import GD_DATA, Tags, open_sqlite, write_json
import os

con = open_sqlite(readonly=True)
tags = Tags()

# Авторитетный словарь схемы полей .dbr, распакованный из редакторских
# шаблонов игры (database/templates.arc) скриптом 02_templates.py.
# Это НЕ моя работа — фундамент, добавленный координатором прямо во время
# этого задания. Используется как основной источник смысла полей; частотный
# анализ по данным (ниже) — как проверка покрытия/примеры.
_schema_path = os.path.join(GD_DATA, "field_schema.json")
with open(_schema_path, encoding="utf-8") as _f:
    FIELD_SCHEMA = json.load(_f)
print(f"field_schema.json загружен: {len(FIELD_SCHEMA)} полей .dbr")


def schema_of(fname):
    """Официальные type/class/groups/description поля из редакторских шаблонов."""
    e = FIELD_SCHEMA.get(fname)
    if not e:
        return None
    groups = [g for g in e.get("groups", []) if g != "All Groups"]
    return {
        "type": e.get("type"),
        "class": e.get("class"),
        "groups": groups,
        "description": e.get("description") or None,
        "default": e.get("default") or None,
    }


def rec(name):
    """Запись по точному нормализованному имени. None если нет."""
    row = con.execute(
        "SELECT fields FROM records WHERE name=?", (gdlib.norm(name),)
    ).fetchone()
    return json.loads(row[0]) if row else None


def pick(d, keys):
    """Оставить только непустые/ненулевые значения из allow-list ключей."""
    out = {}
    for k in keys:
        if k not in d:
            continue
        v = d[k]
        if v in (0, 0.0, "", None):
            continue
        if isinstance(v, list) and all(x in (0, 0.0) for x in v):
            continue
        out[k] = v
    return out


def resolve(v):
    if isinstance(v, str) and v.startswith("tag"):
        return tags(v)
    return v


# --------------------------------------------------------------------------
# 0. Один проход по ВСЕЙ базе: частотный список имён полей (для damage-type
#    таблицы) + первый попавшийся живой пример на каждое интересующее поле.
# --------------------------------------------------------------------------
print("Проход по всей базе для частотного списка полей...")
field_freq = Counter()
field_example = {}  # fieldname -> (record_name, record_type, value)
all_rows = con.execute("SELECT name, type, fields FROM records").fetchall()
for name, typ, fields_json in all_rows:
    f = json.loads(fields_json)
    for k, v in f.items():
        field_freq[k] += 1
        if k not in field_example:
            nonzero = v if not isinstance(v, list) else any(x not in (0, 0.0) for x in v)
            if v not in (0, 0.0, "", None) and nonzero:
                field_example[k] = (name, typ, v)
print(f"  всего записей: {len(all_rows)}, различных полей: {len(field_freq)}")

# --------------------------------------------------------------------------
# 1. Игровые константы движка (records/game/gameengine.dbr)
# --------------------------------------------------------------------------
engine = rec("records/game/gameengine.dbr")
ENGINE_KEYS = [
    "playerAttackSpeedCapMin", "playerAttackSpeedCapMax",
    "playerSpellCastSpeedCapMin", "playerSpellCastSpeedCapMax",
    "playerRunSpeedCapMin", "playerRunSpeedCapMax",
    "absoluteRunSpeedCapMin", "absoluteRunSpeedCapMax",
    "playerDefenseCap", "monsterDefenseCap",
    "playerReflectCap",
    "monsterAttackSpeedCapMin", "monsterAttackSpeedCapMax",
    "monsterSpellCastSpeedCapMin", "monsterSpellCastSpeedCapMax",
    "monsterRunSpeedCapMin", "monsterRunSpeedCapMax",
    "bossAttackSpeedCapMin", "bossAttackSpeedCapMax",
    "bossSpellCastSpeedCapMin", "bossSpellCastSpeedCapMax",
    "bossRunSpeedCapMax", "bossRunSpeedCapMin",
    "monsterLevelGapFixer", "monsterSleepAggressionFalloffRate",
    "skillMasteryTierLevel", "skillComboChargeTime", "skillComboChargeTimeRanged",
    "skillComboChargeMultipliers",
    "2hWeaponDamageFactor", "dwWeaponDamageFactor", "dwWeaponSpeedFactor",
    "armorDefensiveAbsorption",
    "pvpDamageMultiplier", "pvpCrowdControlDurationMultiplier",
    "absMaxDamageScaling",
    "absPhysicalMinScale", "absPhysicsMaxScale",
    "absFireMinScale", "absFireMaxScale",
    "absColdMinScale", "absColdMaxScale",
    "absLightningMinScale", "absLightningMaxScale",
    "absPoisonMinScale", "absPoisonMaxScale",
    "absAetherMinScale", "absAetherMaxScale",
    "absChaosMinScale", "absChaosMaxScale",
    "absLifeMinScale", "absLifeMaxScale",
    "autoCastEquation",
    "meleeRange", "shortRange", "moderateRange", "longRange", "maximumRange",
    "marketFactionDiscount", "potionStackLimit", "miniPetLimit",
]
engine_out = pick(engine, ENGINE_KEYS) if engine else {}

# field_schema.json прямо документирует 18 полей gameengine.dbr как
# "Index by difficulty 0 to 2" — т.е. индекс массива = сложность
# (0=Normal, 1=Elite, 2=Ultimate). Это авторитетно снимает вопрос "что
# значат эти 3-элементные массивы" — переразмечаем их явными подписями
# вместо голого списка чисел.
DIFF_INDEX_LABELS = ["Normal", "Elite", "Ultimate"]
for k in list(engine_out):
    sch = FIELD_SCHEMA.get(k, {})
    if any("ndex by difficulty" in d for d in sch.get("description", [])):
        v = engine_out[k]
        if isinstance(v, list) and len(v) == 3:
            engine_out[k] = {
                "by_difficulty": dict(zip(DIFF_INDEX_LABELS, v)),
                "schema_description": sch["description"][0],
            }
        else:
            engine_out[k] = {"value": v, "schema_description": sch["description"][0]}

# --------------------------------------------------------------------------
# 2. Формулы боя (records/game/combatformulas.dbr) — берём всё, кроме FX/шаблонов
# --------------------------------------------------------------------------
combat = rec("records/game/combatformulas.dbr") or {}
combat_out = {
    k: v for k, v in combat.items()
    if k not in ("templateName",) and "FxPak" not in k
}
# табличка crit/PTH-модификаторов: threshold[i] -> damage multiplier[i]
pth_table = []
for i in range(1, 7):
    thr = combat.get(f"pthThreshold{i}")
    mod = combat.get(f"pthDamageModifier{i}")
    if thr is not None and mod is not None:
        pth_table.append({"pth_threshold": thr, "damage_multiplier": mod})

# --------------------------------------------------------------------------
# 3. Формулы опыта (records/game/experienceformulas.dbr)
# --------------------------------------------------------------------------
xp = rec("records/game/experienceformulas.dbr") or {}
xp_out = {k: v for k, v in xp.items() if k != "templateName"}

# --------------------------------------------------------------------------
# 4. Регенерация ресурсов и очки за уровень
# --------------------------------------------------------------------------
regen = rec("records/game/playerresourcebehavior.dbr") or {}
regen_out = {k: v for k, v in regen.items() if k != "templateName"}

score = rec("records/game/playerscore.dbr") or {}
score_out = {k: v for k, v in score.items() if k != "templateName"}

levels = rec("records/creatures/pc/playerlevels.dbr") or {}
max_level = int(levels.get("maxPlayerLevel", 0))
skill_pts_arr = levels.get("skillModifierPoints", [])
# индекс i массива соответствует уровню i+1 (стандартный порядок таблиц уровней в GD)
skill_pts_to_max_level = sum(skill_pts_arr[:max_level]) if skill_pts_arr else None
levels_out = {
    "record": "records/creatures/pc/playerlevels.dbr",
    "maxPlayerLevel": levels.get("maxPlayerLevel"),
    "maxDevotionPoints": levels.get("maxDevotionPoints"),
    "experienceLevelEquation": levels.get("experienceLevelEquation"),
    "characterModifierPoints_per_level": levels.get("characterModifierPoints"),
    "attribute_points_from_leveling_1_to_max": (
        levels.get("characterModifierPoints", 0) * max_level if max_level else None
    ),
    "skillModifierPoints_by_level_index": skill_pts_arr,
    "skill_points_from_leveling_1_to_max": skill_pts_to_max_level,
    "strengthIncrement": levels.get("strengthIncrement"),
    "dexterityIncrement": levels.get("dexterityIncrement"),
    "intelligenceIncrement": levels.get("intelligenceIncrement"),
    "lifeIncrement": levels.get("lifeIncrement"),
    "lifeIncrementDexterity": levels.get("lifeIncrementDexterity"),
    "lifeIncrementIntelligence": levels.get("lifeIncrementIntelligence"),
    "manaIncrement": levels.get("manaIncrement"),
    "initialSkillPoints": levels.get("initialSkillPoints"),
    "note": (
        "strengthIncrement/dexterityIncrement/intelligenceIncrement — сколько "
        "сырого очка Физики/Хитрости/Духа даёт ОДНО вложенное очко атрибута "
        "(характер: Str->Physique, Dex->Cunning, Int->Spirit в терминах игры). "
        "lifeIncrement — Life за очко Физики; lifeIncrementDexterity/"
        "lifeIncrementIntelligence — побочный прирост Life за очко Хитрости/Духа. "
        "Прямой формулы 'Life(уровень)' в БД нет — рост Life идёт только через "
        "вложение очков атрибутов, см. known_gaps."
    ),
}

# --------------------------------------------------------------------------
# 5. Базовые статы персонажа на 1 уровне (records/creatures/pc/*)
# --------------------------------------------------------------------------
base_char_keys = [
    "characterLife", "characterMana", "characterLifeRegen", "characterManaRegen",
    "characterStrength", "characterDexterity", "characterIntelligence",
    "characterOffensiveAbility", "characterDefensiveAbility",
    "characterAttackSpeed", "characterRunSpeed", "walkSpeed",
]
male = rec("records/creatures/pc/malepc01.dbr") or {}
female = rec("records/creatures/pc/femalepc01.dbr") or {}
base_char_out = {
    "record_male": "records/creatures/pc/malepc01.dbr",
    "record_female": "records/creatures/pc/femalepc01.dbr",
    "male": pick(male, base_char_keys),
    "female": pick(female, base_char_keys),
    "identical": pick(male, base_char_keys) == pick(female, base_char_keys),
}

# --------------------------------------------------------------------------
# 6. Штраф сопротивлений игрока по сложности (Normal/Elite/Ultimate)
#    records/game/balancingadjustment_mp+difficulty_players01.dbr
#    Массивы длины 12 = 3 сложности (Normal, Elite, Ultimate) x 4 размера
#    пати (1..4 игрока). Подтверждено тэгами tagRDifficultyTitle01..03
#    (Normal/Elite/Ultimate) — в GD только 3 прогресс-сложности, "Veteran"
#    это отдельный переключаемый режим Normal, а не 4-я сложность.
# --------------------------------------------------------------------------
DIFF_NAMES = ["Normal", "Elite", "Ultimate"]


def split_by_difficulty(arr):
    """Разбить 12-элементный [d0p1,d0p2,d0p3,d0p4, d1p1..,d2p1..] массив.
    Возвращает {Normal:.., Elite:.., Ultimate:..} если значение внутри
    каждой четвёрки одинаково (не зависит от размера пати), иначе None."""
    if not isinstance(arr, list) or len(arr) != 12:
        return None
    groups = [arr[0:4], arr[4:8], arr[8:12]]
    if all(len(set(g)) == 1 for g in groups):
        return {DIFF_NAMES[i]: groups[i][0] for i in range(3)}
    return None


players_pak = rec("records/game/balancingadjustment_mp+difficulty_players01.dbr") or {}
player_resist_penalty = {}
for k, v in players_pak.items():
    if k.startswith("defensive") and isinstance(v, list):
        split = split_by_difficulty(v)
        if split and any(split.values()):
            # имя типа = имя поля без "defensive"
            player_resist_penalty[k[len("defensive"):]] = {
                "by_difficulty": split,
                "field": k,
                "raw_12": v,
            }
players_pak_out = {
    "record": "records/game/balancingadjustment_mp+difficulty_players01.dbr",
    "resist_penalty_by_difficulty": player_resist_penalty,
    "note": (
        "Это ШТРАФ к текущему сопротивлению игрока на данной сложности "
        "(вычитается из итогового ресиста), а не жёсткий КЭП резиста. "
        "Одинаков для пати 1-4 игрока (все 4 значения в четвёрке равны). "
        "Полей вне списка выше (не-defensive*, либо defensive*-скаляр=0) "
        "на игрока сложность не влияет согласно этой записи."
    ),
}

# --------------------------------------------------------------------------
# 7. Баффы монстров по сложности (жизнь/OA/DA/урон/резисты монстров)
#    records/game/balancingadjustment_mp+difficulty_enemies01.dbr
# --------------------------------------------------------------------------
enemies_pak = rec("records/game/balancingadjustment_mp+difficulty_enemies01.dbr") or {}
ENEMY_KEYS_OF_INTEREST = [
    "characterLifeModifier", "characterLifeMultModifier", "characterLifeRegenModifier",
    "characterManaModifier", "characterManaRegenModifier",
    "characterOffensiveAbility", "characterOffensiveAbilityModifier",
    "characterDefensiveAbility", "characterDefensiveAbilityModifier",
    "characterAttackSpeedModifier", "characterSpellCastSpeedModifier",
    "characterRunSpeedModifier",
    "characterStrengthModifier", "characterDexterityModifier", "characterIntelligenceModifier",
    "defensiveAbsorptionModifier", "defensiveBlockModifier",
    "defensiveReflect", "defensiveReflectModifier",
    "defensiveAether", "defensiveChaos", "defensiveCold", "defensiveFire",
    "defensiveLife", "defensiveLightning", "defensivePierce", "defensivePhysical",
    "defensivePoison", "defensiveBleeding",
    "defensiveConfusion", "defensiveConvert", "defensiveDisruption", "defensiveFear",
    "defensiveFreeze", "defensivePetrify", "defensiveStun", "defensiveTrap",
    "defensiveManaBurnRatio", "defensivePercentCurrentLife", "defensivePercentReflectionResistance",
    "defensiveSlowLifeLeach",
    "offensiveTotalDamageModifier",
    "offensivePhysicalModifier", "offensivePierceModifier",
    "offensiveAetherModifier", "offensiveChaosModifier",
    "offensiveLifeModifier", "offensiveFreezeModifier", "offensivePetrifyModifier",
    "offensiveStunModifier", "offensiveTrapModifier",
    "offensiveSlowBleedingModifier", "offensiveSlowColdModifier", "offensiveSlowFireModifier",
    "offensiveSlowLifeModifier", "offensiveSlowLightningModifier", "offensiveSlowPhysicalModifier",
    "offensiveSlowPoisonModifier", "offensiveSlowLifeLeachModifier",
    "offensiveSlowDamageMultModifier",
]
enemy_scaling = {}
for k in ENEMY_KEYS_OF_INTEREST:
    v = enemies_pak.get(k)
    if v in (0, 0.0, None):
        continue
    if isinstance(v, list) and all(x in (0, 0.0) for x in v):
        continue
    split = split_by_difficulty(v) if isinstance(v, list) else None
    enemy_scaling[k] = {"by_difficulty": split, "raw": v} if split else {"raw": v}
enemies_pak_out = {
    "record": "records/game/balancingadjustment_mp+difficulty_enemies01.dbr",
    "monster_buffs_by_difficulty": enemy_scaling,
    "note": (
        "Прибавка к статам МОНСТРОВ (не игрока) на Normal/Elite/Ultimate. "
        "Где by_difficulty=None — значение зависит и от сложности, И от "
        "размера пати одновременно (raw — сырой 12-элементный массив "
        "[Normal x4 pati-size, Elite x4, Ultimate x4])."
    ),
}

# --------------------------------------------------------------------------
# 8. Таблица типов урона / статусов / полей .dbr — ГЛАВНАЯ ЧАСТЬ ЗАДАНИЯ.
#    Строится программно по реальным именам полей из БД (field_freq), не по
#    памяти. Семантика префиксов validated на конкретных записях (см. отчёт):
#      offensive<Type>            — мгновенный урон типа <Type> при попадании
#      offensiveSlow<Type>        — урон типа <Type> "по времени" (DoT)
#      defensive<Type>            — % сопротивления типу <Type> (флэт)
#      defensive<Type>MaxResist   — прибавка к КЭПУ сопротивления типа <Type>
#      defensive<Type>Duration    — % сокращения длительности эффекта/DoT типа <Type>
#      retaliation<Type>          — урон-возврат (retaliation) типа <Type>
#      <family><Type>Modifier     — % модификатор ("+X% <Type> damage/resist")
#      <family><Type>Chance       — шанс % (проков статуса, или шанс резиста CC)
#      <family><Type>Global/XOR   — служебные флаги ГСЧ для связывания роллов
#                                    между статами одной записи (генератор луты)
# --------------------------------------------------------------------------

# category: "damage" (учитывается ресистом из tagStatsResistance0X) или
# "status"/"cc" (crowd control, свой resist-chance, без числового ресиста) или
# "utility" (спецмеханики: конверт, ManaBurn, PercentCurrentLife, скорости)
DAMAGE_TYPES = [
    ("Physical",  "damage", "tagStatsResistance09", True),
    ("Pierce",    "damage", "tagStatsResistance05", True),
    ("Fire",      "damage", "tagStatsResistance01", True),
    ("Cold",      "damage", "tagStatsResistance03", True),
    ("Lightning", "damage", "tagStatsResistance02", True),
    ("Poison",    "damage", "tagStatsResistance04", True),   # Poison & Acid
    ("Life",      "damage", "tagStatsResistance07", True),   # Vitality
    ("Aether",    "damage", "tagStatsResistance08", True),
    ("Chaos",     "damage", "tagStatsResistance10", True),
    ("Bleeding",  "damage", "tagStatsResistance06", True),   # физический DoT
]
STATUS_TYPES = [
    ("Stun",       "cc"),
    ("Freeze",     "cc"),
    ("Petrify",    "cc"),
    ("Sleep",      "cc"),
    ("Trap",       "cc"),
    ("Taunt",      "cc"),
    ("Confusion",  "cc"),
    ("Fear",       "cc"),
    ("Convert",    "cc"),          # mind-control монстра
    ("Knockdown",  "cc"),
    ("Disruption", "cc"),          # прерывание каста
    ("Fumble",     "cc"),          # "осечка" атаки
    ("ProjectileFumble", "cc"),
    ("PercentCurrentLife", "utility"),  # урон % от текущего HP
    ("ManaBurn",   "utility"),
    ("SlowLifeLeach", "utility"),  # похищение жизни (DoT-леч)
    ("SlowManaLeach", "utility"),
    ("DefensiveAbility", "debuff"),  # "Slow"-снижение DA цели (Weakened)
    ("OffensiveAbility", "debuff"),  # "Slow"-снижение OA цели
    ("DefensiveReduction", "debuff"),  # % снижения DA цели
    ("OffensiveReduction", "debuff"),  # % снижения OA цели
    ("AttackSpeed", "debuff"),
    ("RunSpeed", "debuff"),
    ("TotalSpeed", "debuff"),
    ("DamageMult", "debuff"),       # "Vulnerability" — увеличение получаемого урона целью
]

OFFENSIVE_SUFFIXES = {
    "instant_min": "Min", "instant_max": "Max", "instant_chance": "Chance",
    "modifier_pct": "Modifier", "modifier_chance": "ModifierChance",
    "rng_global": "Global", "rng_xor": "XOR",
}
# offensiveBase<Type> — group "Item Base Damage" по field_schema.json: врождённый
# базовый урон оружия/скилла ДО % бонусов с предметов (отдельная строка от
# offensive<Type>, которая складывается сверху).
OFFENSIVE_BASE_SUFFIXES = {
    "weapon_base_min": "Min", "weapon_base_max": "Max",
    "rng_global": "Global", "rng_xor": "XOR",
}
OFFENSIVE_SLOW_SUFFIXES = {
    "dot_min": "Min", "dot_max": "Max",
    "dot_duration_min": "DurationMin", "dot_duration_max": "DurationMax",
    "dot_chance": "Chance", "dot_modifier_pct": "Modifier",
    "dot_modifier_chance": "ModifierChance",
    "dot_duration_modifier_pct": "DurationModifier",
    "rng_global": "Global", "rng_xor": "XOR",
}
DEFENSIVE_SUFFIXES = {
    "resist_flat": "", "resist_chance": "Chance",
    "resist_duration_reduction_pct": "Duration",
    "resist_duration_reduction_chance": "DurationChance",
    "resist_duration_modifier_pct": "DurationModifier",
    "resist_duration_modifier_chance": "DurationModifierChance",
    "resist_modifier_pct": "Modifier", "resist_modifier_chance": "ModifierChance",
    "resist_cap_bonus": "MaxResist",
}
RETALIATION_SUFFIXES = {
    "retal_min": "Min", "retal_max": "Max", "retal_chance": "Chance",
    "retal_modifier_pct": "Modifier", "retal_modifier_chance": "ModifierChance",
    "rng_global": "Global", "rng_xor": "XOR",
}
# retaliationSlow<Type> — DoT/дебафф-версия retaliation (например, retaliation
# наносит ещё и статус типа Bleeding/Cold/DefensiveAbility-debuff вдобавок к
# мгновенному retaliation-урону). Зеркало OFFENSIVE_SLOW_SUFFIXES.
RETALIATION_SLOW_SUFFIXES = {
    "retal_dot_min": "Min", "retal_dot_max": "Max",
    "retal_dot_duration_min": "DurationMin", "retal_dot_duration_max": "DurationMax",
    "retal_dot_chance": "Chance", "retal_dot_modifier_pct": "Modifier",
    "retal_dot_modifier_chance": "ModifierChance",
    "retal_dot_duration_modifier_pct": "DurationModifier",
    "retal_dot_duration_modifier_chance": "DurationModifierChance",
    "rng_global": "Global", "rng_xor": "XOR",
}


SEEN_SCHEMA_FIELDS = set()  # для сверки покрытия схема<->данные ниже


def build_family(type_name, prefix, suffix_map):
    out = {}
    for label, suf in suffix_map.items():
        fname = f"{prefix}{type_name}{suf}"
        in_data = fname in field_freq
        in_schema = fname in FIELD_SCHEMA
        if not in_data and not in_schema:
            continue
        if in_schema:
            SEEN_SCHEMA_FIELDS.add(fname)
        ex = field_example.get(fname)
        out[label] = {
            "field": fname,
            "schema": schema_of(fname),
            "records_using": field_freq.get(fname, 0),
            "in_editor_schema_but_unused_in_data": in_schema and not in_data,
            "example": None if not ex else {
                "record": ex[0], "type": ex[1], "value": ex[2],
            },
        }
    return out


damage_type_table = []
for type_name, category, resist_tag, is_dot in DAMAGE_TYPES:
    entry = {
        "type": type_name,
        "category": category,
        "resist_name": tags(resist_tag),
        "resist_desc": tags(resist_tag + "Desc"),
        "offensive_base_weapon_damage": build_family(type_name, "offensiveBase", OFFENSIVE_BASE_SUFFIXES),
        "offensive_instant": build_family(type_name, "offensive", OFFENSIVE_SUFFIXES),
        "offensive_dot": build_family(type_name, "offensiveSlow", OFFENSIVE_SLOW_SUFFIXES),
        "defensive_resist": build_family(type_name, "defensive", DEFENSIVE_SUFFIXES),
        "retaliation": build_family(type_name, "retaliation", RETALIATION_SUFFIXES),
        "retaliation_dot": build_family(type_name, "retaliationSlow", RETALIATION_SLOW_SUFFIXES),
    }
    damage_type_table.append(entry)

status_type_table = []
for type_name, category in STATUS_TYPES:
    entry = {
        "type": type_name,
        "category": category,
        "offensive_instant": build_family(type_name, "offensive", OFFENSIVE_SUFFIXES),
        "offensive_dot": build_family(type_name, "offensiveSlow", OFFENSIVE_SLOW_SUFFIXES),
        "defensive_resist": build_family(type_name, "defensive", DEFENSIVE_SUFFIXES),
        "retaliation": build_family(type_name, "retaliation", RETALIATION_SUFFIXES),
        "retaliation_dot": build_family(type_name, "retaliationSlow", RETALIATION_SLOW_SUFFIXES),
    }
    # чистим пустые ветки
    entry = {k: v for k, v in entry.items() if not isinstance(v, dict) or v or k in ("type", "category")}
    status_type_table.append(entry)

# доп. глобальные ("Total"/"All") поля — не привязаны к одному типу
GLOBAL_FIELDS = [
    "offensiveTotalDamageModifier", "offensiveTotalDamageGlobal",
    "offensiveTotalDamageReductionAbsoluteGlobal", "offensiveTotalDamageReductionPercentGlobal",
    "offensiveTotalResistanceReductionAbsoluteMin", "offensiveTotalResistanceReductionAbsoluteMax",
    "offensiveTotalResistanceReductionAbsoluteDurationMin", "offensiveTotalResistanceReductionAbsoluteChance",
    "offensiveTotalResistanceReductionPercentMin", "offensiveTotalResistanceReductionPercentMax",
    "offensiveTotalResistanceReductionPercentDurationMin", "offensiveTotalResistanceReductionPercentChance",
    "offensivePhysicalResistanceReductionAbsoluteMin", "offensivePhysicalResistanceReductionAbsoluteDurationMin",
    "offensivePhysicalResistanceReductionPercentMin", "offensivePhysicalResistanceReductionPercentDurationMin",
    "offensiveElementalResistanceReductionAbsoluteMin", "offensiveElementalResistanceReductionAbsoluteDurationMin",
    "offensiveElementalResistanceReductionPercentMin", "offensiveElementalResistanceReductionPercentDurationMin",
    "offensiveElementalReductionPercentMin", "offensiveElementalReductionPercentGlobal",
    "offensivePhysicalReductionPercentMin", "offensivePhysicalReductionPercentGlobal",
    "defensiveAllResistance", "defensiveAllResistanceChance", "defensiveAllMaxResist",
    "defensiveCrowdControl", "defensiveCrowdControlChance", "defensiveCrowdControlMaxResist",
    "defensiveElementalResistance", "defensiveElementalResistanceChance", "defensiveElementalModifier",
    "offensivePierceRatioMin", "offensivePierceRatioMax", "offensivePierceRatioChance",
    "defensiveTotalSpeedResistance",
    # Броня: Protection (флэт "Armor"), Absorption (% поглощения урона <= Armor),
    # BonusProtection — три величины, напрямую фигурирующие в
    # combatformulas.dbr#physicalDamageDefenseEquationDGP/DLEP (sumProtectionDV,
    # sumAbsorptionDV).
    "defensiveProtection", "defensiveProtectionChance",
    "defensiveProtectionModifier", "defensiveProtectionModifierChance",
    "defensiveBonusProtection",
    "defensiveAbsorption", "defensiveAbsorptionChance",
    "defensiveAbsorptionModifier", "defensiveAbsorptionModifierChance",
    # "Elemental" — псевдо-тип (Fire+Cold+Lightning вместе), отдельная группа
    # в схеме от Total (все типы) и от конкретных элементов по одному.
    "offensiveElementalMin", "offensiveElementalMax", "offensiveElementalChance",
    "offensiveElementalModifier", "offensiveElementalModifierChance",
    "offensiveElementalGlobal", "offensiveElementalXOR",
    "retaliationElementalMin", "retaliationElementalMax", "retaliationElementalChance",
    "retaliationElementalModifier", "retaliationElementalModifierChance",
    "retaliationElementalGlobal", "retaliationElementalXOR",
    "offensiveTotalDamageModifierChance", "offensiveTotalDamageReductionPercentMin",
    "offensiveTotalDamageReductionPercentChance", "offensiveTotalDamageReductionAbsoluteMin",
    "offensiveTotalResistanceReductionAbsoluteGlobal", "offensiveTotalResistanceReductionPercentGlobal",
    "offensiveGlobalChance", "retaliationGlobalChance",
    # Pierce Ratio — полное семейство (не только Min/Max/Chance)
    "offensivePierceRatioModifier", "offensivePierceRatioModifierChance",
    "offensivePierceRatioGlobal", "offensivePierceRatioXOR",
    "retaliationPierceRatioMin", "retaliationPierceRatioMax", "retaliationPierceRatioChance",
    "retaliationPierceRatioModifier", "retaliationPierceRatioModifierChance",
    # Разное: крит, лайфлич (мгновенный, не DoT), манабёрн, "бонусный" физ.урон
    "offensiveCritDamageModifier",
    "offensiveLifeLeechMin", "offensiveLifeLeechMax", "offensiveLifeLeechChance",
    "offensiveManaBurnDrainMin", "offensiveManaBurnDamageRatio",
    "offensiveBonusPhysicalMin", "offensiveBonusPhysicalMax", "offensiveBonusPhysicalChance",
    "retaliationTotalDamageModifier", "retaliationTotalDamageModifierChance",
    "retaliationTotalDamageGlobal", "retaliationTotalDamageXOR",
    # "SlowLifeLeach"/"SlowManaLeach" — само слово Slow уже часть имени типа
    # (не общий DoT-префикс), поэтому Duration-варианты не попадают в
    # стандартную offensive_dot схему выше — довешиваем явно.
    "offensiveSlowLifeLeachDurationMin", "offensiveSlowLifeLeachDurationMax",
    "offensiveSlowLifeLeachDurationModifier",
    "offensiveSlowManaLeachDurationMin", "offensiveSlowManaLeachDurationMax",
    "offensiveSlowManaLeachDurationModifier",
    "retaliationSlowLifeLeachDurationMin", "retaliationSlowLifeLeachDurationMax",
    "retaliationSlowLifeLeachDurationModifier", "retaliationSlowLifeLeachDurationModifierChance",
    "retaliationSlowManaLeachDurationMin", "retaliationSlowManaLeachDurationMax",
    "retaliationSlowManaLeachDurationModifier", "retaliationSlowManaLeachDurationModifierChance",
    # Остаточные служебные RNG-флаги (Global/XOR) на редких полях
    "offensiveBonusPhysicalGlobal", "offensiveBonusPhysicalXOR",
    "offensiveLifeLeechGlobal", "offensiveLifeLeechXOR",
    "offensiveTotalDamageXOR", "offensiveTotalDamageReductionAbsoluteXOR",
    "offensiveTotalDamageReductionPercentXOR", "offensiveTotalDamageReductionPercentDurationMin",
    "offensiveTotalResistanceReductionAbsoluteXOR", "offensiveTotalResistanceReductionAbsoluteDurationMax",
    "offensiveTotalResistanceReductionPercentXOR",
    "offensiveElementalReductionPercentDurationMin", "offensiveElementalReductionPercentDurationMax",
    "offensiveElementalReductionPercentXOR",
    "offensivePhysicalReductionPercentDurationMin", "offensivePhysicalReductionPercentXOR",
    "offensiveFumbleDurationMin", "offensiveProjectileFumbleDurationMin",
    "retaliationPercentcurrentLifeGlobal", "retaliationPierceRatioGlobal", "retaliationPierceRatioXOR",
    "defensivePhysicalDurationChanceModifier",
]
rr_table = {}
for fname in GLOBAL_FIELDS:
    in_data = fname in field_freq
    in_schema = fname in FIELD_SCHEMA
    if not in_data and not in_schema:
        continue
    if in_schema:
        SEEN_SCHEMA_FIELDS.add(fname)
    ex = field_example.get(fname)
    rr_table[fname] = {
        "schema": schema_of(fname),
        "records_using": field_freq.get(fname, 0),
        "example": None if not ex else {"record": ex[0], "type": ex[1], "value": ex[2]},
    }

# --------------------------------------------------------------------------
# 8b. Сверка покрытия: field_schema.json (авторитетный, из редакторских
#     шаблонов игры) как основной источник против того, что я реально
#     разложил по damage_type_table/status_effect_table/rr_table выше.
#     Ищем поля, которые (а) реально встречаются в данных (field_freq),
#     (б) относятся по groups-меткам схемы к Offensive/Defensive/
#     Retaliation/Conversion семействам, но (в) не попали ни в одну из
#     построенных выше таблиц — потенциальные пропуски.
# --------------------------------------------------------------------------
INTERESTING_GROUP_PREFIXES = (
    "Offensive", "Defensive", "Retaliation", "Conversion",
)
EXCLUDED_GROUPS = {
    # общие контейнеры без предметной привязки — не считаем "пропуском"
    "Offensive Parameters", "Defensive Parameters", "Conversion Parameters",
    "Retaliation Parameters",
    # UI-категории char sheet (текстовые лейблы вкладок, не геймплейные поля)
    "Offensive", "Defensive", "Retaliation",
}
schema_relevant_fields = {
    fname for fname, e in FIELD_SCHEMA.items()
    if "charstatstab3" not in e.get("templates", [])
    and any(
        g.startswith(INTERESTING_GROUP_PREFIXES) and g not in EXCLUDED_GROUPS
        for g in e.get("groups", [])
    )
}
used_in_data = {f for f in schema_relevant_fields if field_freq.get(f)}
missed_fields = sorted(used_in_data - SEEN_SCHEMA_FIELDS)
coverage_check = {
    "note": (
        "field_schema.json (редакторские шаблоны игры) взят как основной "
        "источник смысла полей, частотный анализ по данным — как проверка "
        "покрытия. Ниже — поля из групп Offensive/Defensive/Retaliation/"
        "Conversion, которые реально встречаются в живых данных, но НЕ "
        "попали ни в damage_type_table, ни в status_effect_table, ни в "
        "resistance_reduction_and_global_modifiers этого файла (не по "
        "лени — просто вне 35 типов/статусов, отобранных вручную для "
        "главной таблицы; полный список полей и так есть в field_schema.json)."
    ),
    "schema_fields_in_offensive_defensive_retaliation_conversion_groups": len(schema_relevant_fields),
    "of_those_actually_used_in_live_data": len(used_in_data),
    "captured_in_this_output": len(SEEN_SCHEMA_FIELDS & used_in_data),
    "missed_count": len(missed_fields),
    "missed_fields_sample": missed_fields[:80],
}

# --------------------------------------------------------------------------
# 9. Конверсия урона (conversionInType / conversionOutType / conversionPercentage)
# --------------------------------------------------------------------------
conv_examples = []
cur = con.execute(
    "SELECT name, type, fields FROM records WHERE fields LIKE '%conversionInType%' LIMIT 4000"
)
seen_pairs = set()
for name, typ, fields_json in cur:
    f = json.loads(fields_json)
    cin, cout, pct = f.get("conversionInType"), f.get("conversionOutType"), f.get("conversionPercentage")
    if cin and cout and pct:
        key = (cin, cout)
        if key not in seen_pairs:
            seen_pairs.add(key)
            conv_examples.append({
                "record": name, "type": typ,
                "conversionInType": cin, "conversionOutType": cout,
                "conversionPercentage": pct,
            })
_conv_schema = schema_of("conversionInType") or {}
_conv_default = (_conv_schema.get("default") or [""])[0]
conversion_authoritative_types = _conv_default.split(";") if _conv_default else []
conversion_out = {
    "fields": {
        "conversionInType": "исходный тип урона (picklist, см. authoritative_types ниже)",
        "conversionOutType": "тип, в который конвертируется (тот же picklist)",
        "conversionPercentage": "% от урона типа In, конвертируемый в Out (0-100)",
        "conversionInType2/conversionOutType2/conversionPercentage2": "вторая независимая пара конверсии на той же записи",
    },
    "authoritative_types_source": "field_schema.json#conversionInType.default (picklist из редакторского шаблона parameters_conversion.tpl)",
    "authoritative_types": conversion_authoritative_types,
    "distinct_in_out_pairs_found_in_data": len(seen_pairs),
    "examples": conv_examples[:15],
}

# --------------------------------------------------------------------------
# 10. Формулы стоимости предметов (для полноты — из records/game/itemcostformulas*.dbr)
# --------------------------------------------------------------------------
itemcost = rec("records/game/itemcostformulas_medium.dbr") or {}
itemcost_out = {k: v for k, v in itemcost.items() if k != "templateName"}

# --------------------------------------------------------------------------
# 11. Спот-чек (обязательный раздел брифа)
# --------------------------------------------------------------------------
spot_check = {
    "max_character_level": {
        "value": levels.get("maxPlayerLevel"),
        "source": "records/creatures/pc/playerlevels.dbr#maxPlayerLevel",
    },
    "resist_cap_on_ultimate": {
        "found_in_db": False,
        "explanation": (
            "В БД нет поля вида 'resistanceCap'/'ultimateResistCap'. Найден только "
            "ШТРАФ к текущему сопротивлению игрока по сложности (см. "
            "from_db.difficulty_player_resist_penalty), например для Fire/Cold/"
            "Lightning/Pierce/Poison: Normal 0%, Elite -25%, Ultimate -50% "
            "(records/game/balancingadjustment_mp+difficulty_players01.dbr). "
            "Базовый КЭП сопротивления (в игре общеизвестен как 80%, повышаемый "
            "конкретными предметами через defensive<Type>MaxResist, см. "
            "damage_type_table) как константа НЕ найден в .arz — вероятно "
            "зашит в Game.dll. См. known_gaps."
        ),
    },
    "oa_per_1_point_dexterity": {
        "value": 0.5,
        "source": "records/game/combatformulas.dbr#offensiveAbilityEquation",
        "formula": combat.get("offensiveAbilityEquation"),
        "explanation": (
            "OA = (offensiveAbilityDV + characterLevelDV*12 + "
            "(dexterityDV+bonusDV)*0.5) * (1+modifier/100) + 53 — коэффициент "
            "при dexterityDV равен 0.5, т.е. 1 очко Хитрости(Dexterity) даёт "
            "0.5 OA до умножения на % модификаторы. ВНИМАНИЕ: контрольная "
            "запись игрока (malepc01.dbr) на уровне 1 имеет "
            "characterDexterity=50, characterOffensiveAbility=65, что не "
            "сходится арифметически с формулой встык (12+25+53=90≠65) — "
            "видимо dexterityDV/characterLevelDV в реальном движке считаются "
            "не как сырые видимые статы, а как отдельно нормализованные "
            "величины (DV = 'derived value'), недоступные напрямую из .dbr. "
            "Коэффициент 0.5 в формуле достоверен, но абсолютная сходимость "
            "с итоговым OA на экране персонажа не проверяема данными из БД "
            "— см. known_gaps."
        ),
    },
}

# --------------------------------------------------------------------------
# 12. known_gaps — то, что нужно, но в базе не нашлось
# --------------------------------------------------------------------------
known_gaps = [
    "Базовый КЭП сопротивлений (широко известное значение 80%) как явочная "
    "константа в .arz не найден — вероятно в Game.dll. В БД есть только "
    "бонусы к кэпу (defensive<Type>MaxResist на конкретных предметах/скиллах) "
    "и штраф к текущему ресисту по сложности, но не базовое число, от "
    "которого штраф/бонус отсчитывается.",

    "Уклонение (dodge) КАК ИГРОВОЙ СТАТ ПЕРСОНАЖА в БД не найдено — "
    "уточнено через field_schema.json: поле 'characterDodgePercent' "
    "существует (группа 'Character Ability'), но в живых данных встречается "
    "только на записях типа Monster/ControllerMonster/ControllerGraeae "
    "(пример: records/creatures/anomalies/anomaly_a01.dbr, 25%; боссовский "
    "controller_boss_witchgodguardian_dreegeye.dbr, DodgeChance=80) — то "
    "есть это AI-механика уклонения МОНСТРОВ/боссов (когда и как далеко "
    "отскочить), а не итемизируемый защитный стат игрока. Ни одного предмета/"
    "скилла/девоушена с ненулевым 'characterDodgePercent' на стороне игрока "
    "не найдено — похоже, в этой версии GD у игрока в принципе нет "
    "статистического 'уклонения' как отдельного механизма (защита игрока — "
    "через DA/резисты/блок/абсорб). Явного числового кэпа для "
    "'characterDodgePercent' тоже не найдено.",

    "Кэп блока: найдены meleeBlockEquation/projectileBlockEquation "
    "(= blockChanceDV + blockChanceModifierDV) в combatformulas.dbr, но "
    "явного числового кэпа % шанса блока в БД нет.",

    "Точная механика 'defensive<Type>Duration' (сокращение длительности "
    "эффекта/DoT типа Type) — по field_schema.json не имеет собственного "
    "'description', только групповую метку 'Defensive Absolute'/'Defensive "
    "<Type>' наравне с самим ресистом; текста тултипа, прямо поясняющего "
    "смысл, не нашлось. Разница offensive<Type>ReductionPercent vs "
    "offensive<Type>ResistanceReductionPercent теперь ПОДТВЕРЖДЕНА "
    "официальными group-метками схемы (не только по именам "
    "скиллов-источников): 'Elemental Damage Reduction Percent' (ослабляет "
    "урон, наносимый целью) — это отдельная от 'Elemental Resistance "
    "Reduction Percent' (RR, снижает сопротивление цели) категория в самой "
    "игре. Задание просило найти 3 типа RR (flat/% reduced/% reduction) — "
    "в данных и в схеме нашлось ровно 2 официальных RR-варианта на семейство "
    "(Absolute и Percent, для Total/Physical/Elemental), третий вариант "
    "не идентифицирован как отдельная механика ни в данных, ни в схеме.",

    "Итоговая сумма очков навыков/атрибутов, которую видит игрок на "
    "максимальном уровне, ВКЛЮЧАЕТ бонусы от квестов (поля 'bonusSkillPoints'/"
    "'bonusAttributePoints' встретились только на сундуках/дверях со значением "
    "0 — фактические квестовые награды хранятся в .qst файлах вне .arz базы, "
    "которую покрывает этот пайплайн). from_db даёт только базовые 238 очков "
    "навыков и 100 очков атрибутов от левелинга 1-100 (без квестовых бонусов).",

    "Crucible / Shattered Realm / Nemesis-механика: явных отдельных .dbr с "
    "формулами их скейлинга в records/game/ не найдено (кроме "
    "challengeAreas/* — ChallengeArea/AttributePak записи для Crucible ним, "
    "не расшифрованы подробно в этом задании — вне заявленного фокуса "
    "'механики, не контент'; при необходимости можно добавить отдельным "
    "проходом по records/game/challengeareas/*).",

    "Множитель урона монстров/HP по слоям Shattered Realm/Crucible волн не "
    "найден — возможно генерируется процедурно кодом, а не таблицей .dbr.",

    "'characterModifierPoints'=1 (очко атрибута за уровень) — скаляр, а не "
    "массив по уровням, в отличие от skillModifierPoints. Не удалось "
    "перепроверить по независимому источнику (например, сравнить с суммой "
    "очков на живом персонаже макс. уровня), т.к. в этой сессии нет доступа "
    "к сохранениям — считать подтверждённым только на уровне 'так написано "
    "в этой записи'.",
]

# --------------------------------------------------------------------------
# Сборка и запись
# --------------------------------------------------------------------------
out = {
    "meta": {
        "source_db": "D:/git/home/data/grim-dawn/gd.sqlite",
        "source_field_schema": "D:/git/home/data/grim-dawn/field_schema.json",
        "total_records_scanned": len(all_rows),
        "distinct_field_names_seen": len(field_freq),
        "distinct_field_names_in_editor_schema": len(FIELD_SCHEMA),
        "generated_by": "docs/grim-dawn/extract/50_mechanics.py",
    },
    "from_db": {
        "engine_constants": {
            "record": "records/game/gameengine.dbr",
            "fields": engine_out,
        },
        "combat_formulas": {
            "record": "records/game/combatformulas.dbr",
            "fields": combat_out,
            "crit_pth_table": pth_table,
        },
        "experience_formulas": {
            "record": "records/game/experienceformulas.dbr",
            "fields": xp_out,
        },
        "resource_regen": {
            "record": "records/game/playerresourcebehavior.dbr",
            "fields": regen_out,
        },
        "player_score_formula": {
            "record": "records/game/playerscore.dbr",
            "fields": score_out,
        },
        "level_system": levels_out,
        "base_character_stats_lvl1": base_char_out,
        "difficulty_player_resist_penalty": players_pak_out,
        "difficulty_monster_scaling": enemies_pak_out,
        "damage_type_table": damage_type_table,
        "status_effect_table": status_type_table,
        "resistance_reduction_and_global_modifiers": rr_table,
        "schema_coverage_check": coverage_check,
        "damage_conversion": conversion_out,
        "item_cost_formulas": {
            "record": "records/game/itemcostformulas_medium.dbr",
            "fields": itemcost_out,
        },
    },
    "known_gaps": known_gaps,
    "spot_check": spot_check,
}

path, size = write_json("mechanics.json", out, indent=1)
print(f"Записано: {path} ({size} байт)")
print(f"damage_type_table: {len(damage_type_table)} типов урона")
print(f"status_effect_table: {len(status_type_table)} статусов/CC")
print(f"resistance_reduction/global fields: {len(rr_table)}")
print(f"conversion пар найдено: {len(seen_pairs)}")
print(f"known_gaps: {len(known_gaps)} пунктов")
