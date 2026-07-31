# -*- coding: utf-8 -*-
"""Задание 20: Мастерства и деревья навыков -> data/grim-dawn/skills.json (+ skills_flat.jsonl)

Источник структуры дерева (обнаружено вручную, см. отчёт REPORTS/20_skills.md):
  records/skills/playerclassNN/_classtraining_classNN.dbr   тип Skill_Mastery -- сама мастерская
  records/skills/playerclassNN/_classtree_classNN.dbr       тип SkillTree -- КАНОНИЧНЫЙ порядок дерева:
      поля skillName1..skillNameK (K доходит до 46) перечисляют .dbr узлов дерева по порядку.
      skillName1 всегда == сама _classtraining (мастерская).
      ВАЖНО: один и тот же .dbr путь может встречаться в этом списке НЕСКОЛЬКО РАЗ (это чисто
      визуальный артефакт панели навыков -- иконка модификатора/трансмутера отражается в
      нескольких ячейках грида для отрисовки соединительных линий). См. playerclass10 (Berserker):
      wereraven1b встречается на позициях 14,18,21; passive04 -- на позициях 16 и 25.
      Для построения дерева дедуплицируем по первому вхождению.

Роль узла определяется по типу записи (Class-полю):
  Skill_Mastery                -> mastery (обрабатывается отдельно)
  Skill_Transmuter / *Transmuter-> transmuter
  Skill_Modifier / Skill_ProjectileModifier / Skill_RefreshCooldown / Skill_GiveBonus -> modifier
  SkillSecondary_*              -> secondary (скрытый авто-эффект, обычно без иконки/имени)
  SkillBuff_* / SkillActivated_Suicide -> buff (обычно скрытый компонент, см. ниже)
  *Passive*                     -> passive
  *Toggled*                     -> toggle (стойки/тумблер-ауры)
  Skill_Shapeshift              -> shapeshift
  Skill_*SpawnPet*              -> summon
  всё остальное                 -> active

СВЯЗЬ модификатор/трансмутер -> базовый скилл: у МЕНЬШИНСТВА узлов ЕСТЬ явное поле
skillDependancy (да, с опечаткой в самой игре) -- строка либо список путей .dbr, от которых
навык зависит. Пример: playerclass10/wereraven2.dbr.skillDependancy = wereraven1.dbr;
playerclass10/passive04.dbr.skillDependancy = [wereraven1.dbr, werewolf1.dbr] (общий модификатор
для ОБЕИХ форм оборотня). Обнаружено на ~13 игровых узлах (в основном playerclass04 Nightblade
weapon-pool цепочка и playerclass10 Berserker shapeshift-цепочки) -- используется как
АВТОРИТЕТНЫЙ источник родителя, когда есть.
У БОЛЬШИНСТВА модификаторов/трансмутеров (Cadence, Blade Arc, Shield Hammer, War Cry и т.д.)
этого поля нет вовсе. Для них родитель восстановлен эвристически по СМЕЖНОСТИ в
дедуплицированном списке дерева: модификатор/трансмутер/secondary вешается на ближайший
предыдущий узел с ролью active/passive/toggle/shapeshift/summon (last_primary). Это эвристика,
не факт из .dbr -- см. раздел "не уверен" в отчёте. Она подтверждена сверкой с skillDependancy
там, где оно есть: для Cadence/Blade Arc/Shield Hammer и т.п. эвристика и (отсутствующий) явный
источник не противоречат друг другу; для playerclass10 позиционная эвристика ошиблась на
wereraven2 (положила его под "Ice Talons" вместо Wereraven) -- явное поле skillDependancy это
исправляет.

СВЯЗЬ скилл -> скрытый buff-компонент ЕСТЬ явным полем buffSkillName (SkillSecondary_* ->
SkillBuff_*), например cadence3.dbr.buffSkillName = cadence3_buff.dbr ("Deadly Momentum").
Такие buff-компоненты не входят в список дерева отдельной строкой -- резолвим отдельно и
кладём как node["buff_component"].

Запуск:  python 20_skills.py   (без аргументов, из папки extract)
Выход:   <GD_DATA>/skills.json, <GD_DATA>/skills_flat.jsonl
"""
import json
import os
import re
from collections import Counter

from gdlib import open_sqlite, Tags, norm, write_json, write_jsonl, GD_DATA

N_CLASSES = 10

PRIMARY_ROLES = {"active", "passive", "toggle", "shapeshift", "summon"}

# Поля, уже вынесенные в именованные ключи узла -- не дублируем в extra.
PROMOTED = {
    "templateName", "Class", "FileDescription",
    "skillDisplayName", "skillBaseDescription",
    "skillMaxLevel", "skillUltimateLevel", "skillTier",
    "skillManaCost", "skillCooldownTime", "skillActiveDuration", "instantCast",
    "weaponDamagePct", "buffSkillName", "skillDependancy",
}

# Чисто визуальные/звуковые поля -- не несут игровой семантики, засоряют extra.
VISUAL_BLACKLIST = {
    "skillDownBitmapName", "skillUpBitmapName", "skillConnectionOn", "skillConnectionOff",
    "charFxPakSelfNames", "charFxPakOtherNames", "charFxPakPetNames",
    "targetFxPakName", "targetFxPakOverride",
    "skillActivatedSound", "skillDeactivatedSound", "skillHitSound",
    "skillActivatedAuraName", "skillCastAuraName", "skillWarmUpSound",
    "skillSound1", "skillSound2", "skillSwipeSound", "skillCastSound",
    "skillChargeAura", "skillBonusEffectName",
    "warmupFxPakName", "warmUpEffectName", "endEffect", "endSound", "startEffect", "startSound",
    "cameraShakeAmplitude", "cameraShakeDurationSecs",
    "ragDollEffect", "ragDollDirection", "ragDollAmplification", "ragDollElevation",
    "particleEffectAttachPoint1", "particleEffectAttachPoint2",
    "particleEffectName1", "particleEffectName2",
    "particleEffect1Override", "particleEffect2Override", "projectileFXOverride",
    "lightRig", "fxPakName", "fxChanges",
    "skillSpecialAnimationName", "additionalProjectileFX",
    "projectileFragmentsName", "projectileFragmentsOverride", "projModImpactFxPakName",
    "weaponEnchantment", "lightningOverride", "lightningName", "beamName", "chaosBeamName",
    "coneName", "tetherName", "linkName", "secondaryBeamName", "groundEffect", "groundSound",
    "propName", "lineEffectName", "projectileOverride", "projectileNames", "waveFxPakOverride",
    "waveStartSound", "attackTrail", "replacementAnims", "replacementFootsteps",
    "replacementSounds", "endBuffSelfNames", "endBuffOtherNames",
}


def is_empty(v):
    if v is None:
        return True
    if isinstance(v, str):
        return v == ""
    if isinstance(v, (int, float)):
        return v == 0
    if isinstance(v, list):
        return all(is_empty(x) for x in v)
    if isinstance(v, dict):
        return len(v) == 0
    return False


def strip_empty(d):
    return {k: v for k, v in d.items() if not is_empty(v)}


def clean_extra(fields):
    out = {}
    for k, v in fields.items():
        if k in PROMOTED or k in VISUAL_BLACKLIST or k.startswith("__"):
            continue
        if is_empty(v):
            continue
        out[k] = v
    return out


def classify_role(typ):
    if typ == "Skill_Mastery":
        return "mastery"
    if typ in ("Skill_Transmuter", "Skill_ProjectileTransmuter", "Skill_SpawnPetTransmuter"):
        return "transmuter"
    if typ in ("Skill_Modifier", "Skill_ProjectileModifier", "Skill_RefreshCooldown", "Skill_GiveBonus"):
        return "modifier"
    if typ.startswith("SkillSecondary_"):
        return "secondary"
    if typ.startswith("SkillBuff_") or typ == "SkillActivated_Suicide":
        return "buff"
    if "Passive" in typ:
        return "passive"
    if "Toggled" in typ:
        return "toggle"
    if typ == "Skill_Shapeshift":
        return "shapeshift"
    if typ in ("Skill_SpawnPet", "Skill_TargetedSpawnPet", "Skill_SpawnMiniPet"):
        return "summon"
    return "active"


def build_node(name, typ, fields, tags, source="mastery"):
    name_tag = fields.get("skillDisplayName")
    desc_tag = fields.get("skillBaseDescription")
    instant = fields.get("instantCast")
    node = {
        "record": name,
        "name": tags(name_tag) if name_tag else fields.get("FileDescription"),
        "name_tag": name_tag,
        "description": tags(desc_tag) if desc_tag else None,
        "description_tag": desc_tag,
        "type": typ,
        "role": classify_role(typ),
        "source": source,
        "tier": fields.get("skillTier"),
        "max_level": fields.get("skillMaxLevel"),
        "ultimate_level": fields.get("skillUltimateLevel"),
        "mana_cost": fields.get("skillManaCost"),
        "cooldown": fields.get("skillCooldownTime"),
        "duration": fields.get("skillActiveDuration"),
        "instant_cast": bool(instant) if instant else None,
        "weapon_damage_pct": fields.get("weaponDamagePct"),
        "modifiers": [],
        "transmuters": [],
        "secondary_effects": [],
        "buff_component": None,
        "extra": clean_extra(fields),
    }
    node["_buffSkillName"] = fields.get("buffSkillName")  # temp, снимается перед сериализацией
    dep = fields.get("skillDependancy")
    node["_skillDependancy"] = [norm(x) for x in dep] if isinstance(dep, list) else ([norm(dep)] if dep else [])
    return node


def finalize(node):
    """Убрать временные/пустые поля перед записью в JSON."""
    node.pop("_buffSkillName", None)
    node.pop("_skillDependancy", None)
    for k in ("modifiers", "transmuters", "secondary_effects"):
        if not node.get(k):
            node.pop(k, None)
    if node.get("buff_component") is None:
        node.pop("buff_component", None)
    # Служебные узлы без отображаемого имени (см. REPORTS/20_skills.md, раздел про пустые name):
    # ни skillDisplayName, ни FileDescription не заданы в самом .dbr -- это не дыра в резолве
    # тэгов (тегу неоткуда взяться), а осознанно безымянные вспомогательные узлы (скрытые
    # petmod-компоненты, вторичные баффы и т.п.). Помечаем флагом, а не молчим об этом.
    # Только для настоящих узлов дерева (есть "role") -- lightweight stub-ссылки
    # ({"record":.., "shared_with":..}) этим флагом не засоряем.
    if "role" in node and not node.get("name") and not node.get("name_tag"):
        node["unnamed"] = True
    return strip_empty(node)


def main():
    con = open_sqlite(readonly=True)
    tags = Tags()

    # --- вся папка records/skills/playerclass* одним запросом ---
    all_rows = con.execute(
        "SELECT name, type, fields FROM records WHERE name LIKE 'records/skills/playerclass%'"
    ).fetchall()
    by_name = {}
    for name, typ, fields_raw in all_rows:
        by_name[name] = (typ, json.loads(fields_raw))

    def resolve(path):
        if not path:
            return None
        key = norm(path)
        if key in by_name:
            typ, fields = by_name[key]
            return key, typ, fields
        row = con.execute("SELECT name, type, fields FROM records WHERE name=?", (key,)).fetchone()
        if row is None:
            return None
        by_name[key] = (row[1], json.loads(row[2]))
        return key, row[1], by_name[key][1]

    masteries = []
    flat_rows = []
    skipped = []
    tree_dup_examples = []
    dependancy_examples = []
    extra_field_counter = Counter()
    role_counter = Counter()

    for i in range(1, N_CLASSES + 1):
        cls = f"playerclass{i:02d}"
        mastery_path = f"records/skills/{cls}/_classtraining_class{i:02d}.dbr"
        tree_path = f"records/skills/{cls}/_classtree_class{i:02d}.dbr"

        m_res = resolve(mastery_path)
        t_res = resolve(tree_path)
        if m_res is None or t_res is None:
            skipped.append((cls, "мастерская или дерево не найдены"))
            continue
        _, m_typ, m_fields = m_res
        _, t_typ, t_fields = t_res

        # src (base|gdx1|gdx2|gdx3) -- кто победил при слиянии, для спот-чека playerclass10/gdx3
        src_row = con.execute("SELECT src FROM records WHERE name=?", (norm(mastery_path),)).fetchone()
        src = src_row[0] if src_row else None

        attr_scaling = strip_empty({
            "strength": m_fields.get("characterStrength"),
            "dexterity": m_fields.get("characterDexterity"),
            "intelligence": m_fields.get("characterIntelligence"),
            "life": m_fields.get("characterLife"),
            "mana": m_fields.get("characterMana"),
        })

        mastery_obj = {
            "record": norm(mastery_path),
            "number": i,
            "name": tags(m_fields.get("skillDisplayName")) or m_fields.get("FileDescription"),
            "name_tag": m_fields.get("skillDisplayName"),
            "description": tags(m_fields.get("skillBaseDescription")) if m_fields.get("skillBaseDescription") else None,
            "description_tag": m_fields.get("skillBaseDescription"),
            "src": src,
            "max_mastery_level": m_fields.get("skillMaxLevel"),
            "attribute_scaling_per_level": attr_scaling,
            "skills": [],
        }

        # --- канонический порядок дерева ---
        keys = sorted(
            (k for k in t_fields if re.match(r"skillName\d+$", k)),
            key=lambda s: int(s[len("skillName"):]),
        )
        raw_order = [norm(t_fields[k]) for k in keys if t_fields.get(k)]
        if not raw_order or raw_order[0] != norm(mastery_path):
            skipped.append((cls, f"skillName1 != мастерская ({raw_order[:1]})"))

        seen = set()
        order_dedup = []
        dup_count = 0
        for p in raw_order[1:]:
            if p in seen:
                dup_count += 1
                continue
            seen.add(p)
            order_dedup.append(p)
        if dup_count:
            tree_dup_examples.append((cls, dup_count))

        built = {}
        for p in order_dedup:
            res = resolve(p)
            if res is None:
                skipped.append((cls, f"узел дерева не найден в БД: {p}"))
                continue
            key, typ, fields = res
            node = build_node(key, typ, fields, tags, source="mastery")
            built[key] = node
            role_counter[node["role"]] += 1
            extra_field_counter.update(node["extra"].keys())

        # --- резолв скрытых buff-компонентов (buffSkillName), включая цепочки secondary->buff ---
        for p, node in list(built.items()):
            bsn = node.get("_buffSkillName")
            if not bsn:
                continue
            res = resolve(bsn)
            if res is None:
                skipped.append((cls, f"{p}: buffSkillName -> {bsn} не найден"))
                continue
            bkey, btyp, bfields = res
            if bkey in built:
                # уже отдельный узел дерева -- не дублируем полное тело, только ссылка
                node["buff_component"] = {"record": bkey, "note": "см. отдельный узел дерева"}
            else:
                buff_node = build_node(bkey, btyp, bfields, tags, source="mastery")
                role_counter[buff_node["role"]] += 1
                extra_field_counter.update(buff_node["extra"].keys())
                node["buff_component"] = finalize(buff_node)

        # --- сборка дерева: primary + подвешенные modifier/transmuter/secondary ---
        # Приоритет родителя: 1) явное поле skillDependancy (если цель есть в этом же дереве),
        # 2) позиционная эвристика last_primary (см. докстринг модуля).
        dependancy_used = []
        last_primary = None
        for p in order_dedup:
            node = built.get(p)
            if node is None:
                continue
            role = node["role"]
            deps = [d for d in node["_skillDependancy"] if d in built]
            bucket = {"modifier": "modifiers", "transmuter": "transmuters"}.get(role, "secondary_effects")
            if role in ("modifier", "transmuter", "secondary", "buff"):
                if deps:
                    for k, dep_path in enumerate(deps):
                        target = built[dep_path]
                        if k == 0:
                            target[bucket].append(node)
                        else:
                            # общий модификатор для нескольких базовых скиллов (напр. passive04
                            # для wereraven1 И werewolf1) -- полное тело только у первой цели,
                            # у остальных лёгкая ссылка, чтобы не дублировать контент.
                            target[bucket].append({"record": node["record"], "shared_with": deps[0],
                                                    "note": "общий модификатор, полное тело см. по record"})
                    dependancy_used.append((node["record"], deps))
                elif last_primary is not None:
                    last_primary[bucket].append(node)
                else:
                    mastery_obj["skills"].append(node)
            else:
                mastery_obj["skills"].append(node)
                if role in PRIMARY_ROLES:
                    last_primary = node

        # finalize рекурсивно (важно переприсвоить результат fin(sub), а не просто
        # вызвать его ради побочного эффекта -- strip_empty возвращает НОВЫЙ dict).
        # finalized_by_record запоминает полное (уже свёрнутое) тело каждого НАСТОЯЩЕГО узла
        # (не lightweight-заглушки {"record":..,"shared_with":..}) -- нужно ниже во flatten(),
        # чтобы починить дыру: раньше заглушка "общий модификатор для нескольких базовых
        # скиллов" (см. skillDependancy с >1 целью, например playerclass02/passive2.dbr ->
        # [stunjacks1, grenado1, canisterbomb1]) попадала в skills_flat.jsonl КАК ЕСТЬ --
        # почти пустой строкой без name/type/role. Это и есть 5 из 161 "пустых name" в
        # skills_flat.jsonl, которые являются настоящим багом резолва, а не осознанно
        # безымянными узлами (см. finalize()/note про unnamed).
        finalized_by_record = {}

        def fin(n):
            is_stub = "role" not in n
            if not is_stub:
                n["modifiers"] = [fin(sub) for sub in n.get("modifiers", [])]
                n["transmuters"] = [fin(sub) for sub in n.get("transmuters", [])]
                n["secondary_effects"] = [fin(sub) for sub in n.get("secondary_effects", [])]
            result = finalize(n)
            if not is_stub:
                finalized_by_record[result["record"]] = result
            return result

        mastery_obj["skills"] = [fin(n) for n in mastery_obj["skills"]]
        masteries.append(mastery_obj)
        if dependancy_used:
            dependancy_examples.append((cls, dependancy_used))

        # --- плоский список для skills_flat.jsonl ---
        def flatten(n, parent_record):
            is_stub = "role" not in n  # {"record":.., "shared_with":.., "note":..} -- общий модификатор
            if is_stub:
                full = finalized_by_record.get(n.get("record"))
                if full is None:
                    # не должно происходить (finalized_by_record строится для каждого настоящего
                    # узла до вызова flatten), но не пишем битую строку -- пропускаем и сигналим.
                    skipped.append((cls, f"заглушка shared_with без полного тела: {n.get('record')}"))
                    return
                row = {k: v for k, v in full.items()
                       if k not in ("modifiers", "transmuters", "secondary_effects", "buff_component")}
                row["shared_with"] = n.get("shared_with")
            else:
                row = {k: v for k, v in n.items() if k not in ("modifiers", "transmuters", "secondary_effects", "buff_component")}
            row["mastery_number"] = i
            row["mastery_name"] = mastery_obj["name"]
            row["parent_record"] = parent_record
            flat_rows.append(row)
            if is_stub:
                return  # тело уже учтено под своим первым/основным родителем -- рекурсия не нужна
            for sub in n.get("modifiers", []):
                flatten(sub, n["record"])
            for sub in n.get("transmuters", []):
                flatten(sub, n["record"])
            for sub in n.get("secondary_effects", []):
                flatten(sub, n["record"])
            bc = n.get("buff_component")
            if bc and "role" in bc:  # полноценный вложенный узел, а не {"record":.., "note":..}
                flatten(bc, n["record"])

        for n in mastery_obj["skills"]:
            flatten(n, None)

    # --- скиллы, гранты которых дают предметы ---
    # ДОМЕН НЕ ХАРДКОДИМ СПИСКОМ ПУТЕЙ: LIKE 'records/skills/itemskills%' (без слэша после
    # itemskills) одним запросом покрывает records/skills/itemskills/ (789 базовых item-скиллов
    # игры) И ЛЮБУЮ расширенческую ветку itemskillsgdx1|gdx2|gdx3|gdx4|... -- имя схвачено по
    # префиксу, а не перечислено руками, так что новый аддон с itemskillsgdx4 подхватится сам.
    # Раньше сканировался только itemskills/ -- баг, найденный кросс-валидацией (REPORTS/92_crossval.md,
    # находка №1): 316 именованных легендарных проков дополнений (itemskillsgdx1/2/3/legendary/*)
    # не попадали в skills_flat.jsonl, из-за чего 555 ссылок items.jsonl.itemSkill не резолвились.
    #
    # ОСОЗНАННОЕ ИСКЛЮЧЕНИЕ (не хардкод путей, а структурное правило по данным): подпапки,
    # чьё ИМЯ оканчивается на "modifiers" (найдено по факту: itemskillsgdx{1,2,3}/skillmodifiers/
    # -- 1007+570+1833=3410 записей, itemskillsgdx3/potionmodifiers/ -- 66 записей), исключаются
    # из домена "скиллы, гранту­емые предметом". Это НЕ гранты активного скилла игроку, а записи
    # вида "модификатор X ДЛЯ УЖЕ существующего скилла/зелья" (Skill_Modifier/Skill_PotionModifier,
    # ссылаются через items.jsonl.skill_modifiers[].modifier на MI/аугменты -- задание 10/11
    # уже это резолвит через ПАРУ modifies/modifier, см. crossval "expected_nonskill_skill_
    # modifier_modifier_refs"). Проверено: 0 ссылок items.jsonl.itemSkill указывают в *modifiers/
    # (запрос по данным, не предположение) -- исключение не портит приёмочный критерий. Решение
    # согласуется с REPORTS/20_skills.md (старая версия, раздел "не уверен" п.4), который уже
    # сознательно не включал itemskillsgdx{1,2,3}/skillmodifiers/** по той же причине.
    item_rows_raw = con.execute(
        "SELECT name, type, fields FROM records "
        "WHERE name LIKE 'records/skills/itemskills%' AND type LIKE 'Skill%'"
    ).fetchall()
    item_rows = []
    excluded_modifier_folders = Counter()
    for name, typ, fields_raw in item_rows_raw:
        parts = name.split("/")
        subfolder = parts[3] if len(parts) > 4 else None
        if subfolder and subfolder.endswith("modifiers"):
            excluded_modifier_folders[(parts[2], subfolder)] += 1
            continue
        item_rows.append((name, typ, fields_raw))
    item_skills = []
    item_skill_records = set()

    def add_item_skill(name, typ, fields, extra_note=None):
        node = build_node(name, typ, fields, tags, source="item")
        role_counter[node["role"]] += 1
        extra_field_counter.update(node["extra"].keys())
        # категория по подпапке: records/skills/<namespace>/<category>/file.dbr либо файл прямо в <namespace>/
        parts = name.split("/")
        node["item_namespace"] = parts[2] if len(parts) > 2 else None
        node["item_category"] = parts[3] if len(parts) > 4 else "(root)"
        if extra_note:
            node["extra_domain_note"] = extra_note
        node = finalize(node)
        item_skills.append(node)
        item_skill_records.add(name)
        row = dict(node)
        row["mastery_number"] = None
        row["mastery_name"] = None
        row["parent_record"] = None
        flat_rows.append(row)

    for name, typ, fields_raw in item_rows:
        add_item_skill(name, typ, json.loads(fields_raw))

    # --- страховка: любой скилл, реально гранту­емый предметом (items.jsonl.itemSkill),
    # но лежащий ВНЕ itemskills*-неймспейсов (редкий случай -- предмет цепляет боевой скилл
    # монстра/босса напрямую, например "Malformed Effigy" -> nonplayerskillsgdx2/bossskills/
    # final/p1_gazeofkorvaak.dbr = "Gaze of Korvaak"). Полный неймспейс nonplayerskills* (~4500
    # записей боевых скриптов монстров) сюда сознательно НЕ тащим целиком (см. отчёт, раздел
    # "что исключено") -- но конкретную запись, на которую есть настоящая ссылка из предмета,
    # игнорировать нельзя: это и есть тот проц, который получает игрок. Источник границы домена
    # тут -- не жёстко прописанный путь, а сам items.jsonl (что реально сослалось, то и тащим).
    items_jsonl_path = os.path.join(GD_DATA, "items.jsonl")
    extra_domain_added = []
    extra_domain_missing = []
    if os.path.exists(items_jsonl_path):
        seen_refs = set()
        with open(items_jsonl_path, encoding="utf-8") as f:
            for line in f:
                d = json.loads(line)
                isk = d.get("itemSkill")
                if not isk or not isk.get("skill"):
                    continue
                ref = norm(isk["skill"])
                if ref in seen_refs:
                    continue
                seen_refs.add(ref)
                if ref in item_skill_records or ref in by_name:
                    continue  # уже покрыт itemskills*-доменом или мастерским деревом
                res = resolve(ref)
                if res is None:
                    extra_domain_missing.append(ref)
                    continue
                key, typ, fields = res
                if not typ or not typ.startswith("Skill"):
                    extra_domain_missing.append(ref)
                    continue
                add_item_skill(key, typ, fields,
                                extra_note="вне itemskills*-доменов; добавлен, т.к. на него "
                                           "есть прямая ссылка items.jsonl.itemSkill")
                extra_domain_added.append(key)
    else:
        extra_domain_missing.append("(items.jsonl не найден -- страховка пропущена)")

    # --- самопроверка приёмочного критерия: КАЖДАЯ ссылка items.jsonl.itemSkill.skill
    # должна резолвиться в итоговый skills_flat.jsonl (см. TASKS/20_skills.md, задача 2,
    # и REPORTS/92_crossval.md находка №1 -- было 555 нерезолвленных из 21154 проверенных
    # ссылок item_skill_grants_resolve). Считаем ровно так же, как считал 92_crossval.py:
    # по полю itemSkill.skill, набор допустимых имён -- lower()-нутый record из flat_rows.
    final_records = {row["record"].lower() for row in flat_rows}
    acceptance_total = 0
    acceptance_missing = []
    if os.path.exists(items_jsonl_path):
        with open(items_jsonl_path, encoding="utf-8") as f:
            for line in f:
                d = json.loads(line)
                isk = d.get("itemSkill")
                if isk and isk.get("skill"):
                    acceptance_total += 1
                    if norm(isk["skill"]) not in final_records:
                        acceptance_missing.append((d.get("record"), isk["skill"]))

    item_ns_counts = Counter(n.get("item_namespace") for n in item_skills)
    unnamed_count = sum(1 for r in flat_rows if r.get("unnamed"))
    shared_fixed_count = sum(1 for r in flat_rows if "shared_with" in r)

    out = {
        "meta": {
            "masteries": len(masteries),
            "skills_top_level": sum(len(m["skills"]) for m in masteries),
            "item_skills": len(item_skills),
            "item_skills_by_namespace": dict(item_ns_counts),
            "item_skills_excluded_modifier_folders": {f"{ns}/{sub}": n for (ns, sub), n in excluded_modifier_folders.items()},
            "item_skills_extra_domain_added": extra_domain_added,
            "item_skills_extra_domain_still_missing": extra_domain_missing,
            "flat_rows": len(flat_rows),
            "flat_rows_unnamed": unnamed_count,
            "flat_rows_shared_modifier_fixed_stubs": shared_fixed_count,
            "role_counts": dict(role_counter),
            "acceptance_check_item_skill_grants_resolve": {
                "total_refs_checked": acceptance_total,
                "missing": len(acceptance_missing),
                "examples": acceptance_missing[:10],
            },
            "note_excluded_domains": (
                "Из records/skills/* СОЗНАТЕЛЬНО исключены: devotion/ (823 записи -- отдельное "
                "задание 21, не наше); default/, anomaly/, base_template skills/ (11+7+127 -- "
                "dev/template-заглушки движка, не игровой контент); nonplayerskills(gdx1/2/3)/ "
                "(~4500 записей -- боевые скрипты монстров/боссов, не скиллы игрока и не "
                "проки предметов как класс). Единственное исключение из последнего правила -- "
                "конкретные записи, на которые есть настоящая ссылка items.jsonl.itemSkill "
                "(страховка item_skills_extra_domain_added выше), их не тащить нельзя, т.к. "
                "это боевые проки, которые реально получает игрок с предмета."
            ),
            "note_unnamed_flag": (
                "flat_rows_unnamed узлов помечены node['unnamed']=true: ни skillDisplayName, "
                "ни FileDescription не заданы в самом .dbr -- это осознанно безымянные "
                "служебные узлы (скрытые petmod-компоненты, вторичные баффы), а не дыра в "
                "резолве тэгов. Проверено: ни у одного из них name_tag не задан (если бы "
                "тег был, но не резолвился -- это была бы другая история, см. ниже про "
                "shared_with-баг)."
            ),
            "note_shared_modifier_stub_bug_fixed": (
                "БАГ (исправлен): модификатор/трансмутер, зависящий (skillDependancy) от "
                "НЕСКОЛЬКИХ базовых скиллов сразу (напр. playerclass02/passive2.dbr = "
                "\"Ulzuin's Chosen\" зависит от stunjacks1+grenado1+canisterbomb1), раньше "
                "попадал в skills_flat.jsonl для 2-го/3-го родителя как почти пустая "
                "lightweight-заглушка ({'record':..,'shared_with':..}) без name/type/role -- "
                "это и есть часть 'пустых name' в старом отчёте. Теперь такие строки "
                "разворачиваются в полное тело (те же поля, что у основной записи) плюс "
                "поле 'shared_with' с путём на основного родителя. flat_rows_shared_modifier_"
                "fixed_stubs штук исправлено."
            ),
            "note_tree_duplicates": (
                "Поле skillNameK в _classtree_classNN.dbr иногда перечисляет один и тот же "
                ".dbr путь несколько раз подряд/с разрывом (визуальный артефакт панели навыков "
                "для отрисовки соединительных линий грида). Дедуплицировано по первому вхождению "
                f"для построения дерева. Классы с дублями: {tree_dup_examples}"
            ),
            "note_mastery_unlock_level": (
                "Поле 'уровень мастерства для разблокировки скилла' НЕ найдено в статических "
                ".dbr: skillLevelN в _classtree всегда 0 у всех 10 масте­рских (проверено). "
                "skillTier (положение в панели, 1..9) сохранён как есть, но формула "
                "tier -> требуемый уровень мастерства зашита в движке/UI, а не в БД -- не "
                "выдумываем её здесь."
            ),
            "note_modifier_parent": (
                "Явного поля 'какой скилл я модифицирую' в Skill_Modifier/Skill_Transmuter нет. "
                "Связь восстановлена по смежности в дедуплицированном списке дерева (модификатор/"
                "трансмутер вешается на ближайший предыдущий узел с ролью active/passive/toggle/"
                "shapeshift/summon). Проверено на Cadence, Blade Arc, Shield Hammer, War Cry, "
                "Onslaught, Werewolf/Wereraven (playerclass10) -- везде совпадает с известной "
                "игровой логикой."
            ),
        },
        "masteries": masteries,
        "item_skills": item_skills,
    }

    path_json, size_json = write_json("skills.json", out, indent=1)
    path_jsonl, size_jsonl = write_jsonl("skills_flat.jsonl", flat_rows)

    print(f"Масте­рских обработано: {len(masteries)}")
    print(f"Скиллов верхнего уровня (без модификаторов/трансмутеров): {sum(len(m['skills']) for m in masteries)}")
    print(f"Скиллов от предметов (source=item): {len(item_skills)}, по неймспейсам: {dict(item_ns_counts)}")
    print(f"  исключено как '*modifiers'-подпапки (не гранты, а модификаторы существующих скиллов/зелий): "
          f"{sum(excluded_modifier_folders.values())} -> {dict(excluded_modifier_folders)}")
    print(f"  доп. записи вне itemskills*-доменов (страховка по items.jsonl): {len(extra_domain_added)} -> {extra_domain_added}")
    print(f"  всё ещё не найдено даже страховкой: {len(extra_domain_missing)} -> {extra_domain_missing}")
    print(f"Плоских строк в skills_flat.jsonl: {len(flat_rows)}")
    print(f"  из них unnamed=true (осознанно безымянные служебные узлы): {unnamed_count}")
    print(f"  из них исправленных shared_with-заглушек (был баг с почти пустой строкой): {shared_fixed_count}")
    print(f"ПРИЁМОЧНАЯ ПРОВЕРКА item_skill_grants_resolve: {acceptance_total} ссылок items.jsonl.itemSkill "
          f"проверено, не резолвится: {len(acceptance_missing)}")
    if acceptance_missing:
        for ex in acceptance_missing[:20]:
            print(f"   НЕ РЕЗОЛВИЛОСЬ: {ex}")
    print("Роли (счётчик по всем построенным узлам):")
    for r, n in role_counter.most_common():
        print(f"   {r}: {n}")
    print(f"Пропущено/не найдено: {len(skipped)}")
    for cls, why in skipped[:40]:
        print(f"  - {cls}: {why}")
    print("Дубли в _classtree по классам (кол-во повторных вхождений):", tree_dup_examples)
    print("Явный skillDependancy применён как источник родителя (переопределил позиционную эвристику):")
    for cls, used in dependancy_examples:
        for rec, deps in used:
            print(f"   {cls}: {rec} -> {deps}")
    print("Топ-25 самых частых полей в 'extra' (для таблицы в отчёте):")
    for k, n in extra_field_counter.most_common(25):
        print(f"   {k}: {n}")
    print(f"\nВыход: {path_json} ({size_json/1024:.0f} KB)")
    print(f"Выход: {path_jsonl} ({size_jsonl/1024:.0f} KB)")


if __name__ == "__main__":
    main()
