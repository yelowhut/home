# -*- coding: utf-8 -*-
"""Задание 21: Девоушены (созвездия) -> data/grim-dawn/devotions.json

Цепочка резолва (обнаружена вручную, см. отчёт REPORTS/21_devotions.md):
  records/ui/skills/devotion/constellations/constellationNN.dbr   (тип '', НЕ Skill_*)
      .devotionButtonK  -> records/ui/skills/devotion/tierT_NNx.dbr   (UI-кнопка, тип '')
          .skillName    -> records/skills/devotion/tierT_NNx[_skill].dbr  (сам узел)
              type == 'Skill_Passive'  -> узел-стат (сопротивления/статы)
              иначе                     -> узел-небесная сила (celestial power)

Порядок узлов = порядковый номер K в devotionButtonK.
Связь узла с деревом (для веток типа Ulzuin's Torch) — поле devotionLinksK на самом
созвездии: devotionLinksK = J означает "узел K соединён с узлом J" (J меньше K).
У узла 1 такого поля нет (корень).

Триггер небесной силы: поле templateAutoCast на узле -> отдельная запись-контроллер
records/controllers/itemskills/cast_@....dbr с полями chanceToRun/triggerType/targetType/
autoTargetRadius — это авторитетный источник (не парсим имя файла).

Запуск:  python 21_devotions.py   (без аргументов, из папки extract)
Выход:   <GD_DATA>/devotions.json
"""
import json
import re
import sys

from gdlib import open_sqlite, Tags, norm, write_json

# Поля-метаданные/визуал, которые не несут игровой семантики - не тащим в stats/effect.
META_BLACKLIST = {
    "templateName", "Class", "FileDescription",
    "skillDisplayName", "skillBaseDescription",
    "skillDownBitmapName", "skillUpBitmapName",
    "skillActivatedSound", "skillHitSound", "charFxPakSelfNames",
    "skillExperienceLevels",  # общая XP-кривая шаблона скилла, не относится к девоушенам
    "skillUltimateLevel", "skillMaxLevel",
    "skillTemplates",  # список ~45 базовых шаблонов скиллов, к которым можно цеплять
                        # почти любую силу - не несёт различающей информации (см. отчёт)
    "cameraShakeAmplitude", "templateAutoCast", "skillBlackList",
    "skillMasteryLevelRequired", "isPetDisplayable", "exclusiveSkill",
    "dualWieldOnly", "dualRangedOnly", "unarmedOnly",
    "characterBaseAttackSpeedTag",
    "skillCooldownTime", "skillActiveDuration", "instantCast",
    # флаги "годится ли для оружия X" - у девоушенов всегда 0
    "Axe", "Axe2h", "Mace", "Mace2h", "Magical", "Offhand", "Ranged1h",
    "Ranged2h", "Shield", "Spear", "Staff", "Sword", "Sword2h",
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
    return False


def clean(fields, extra_blacklist=()):
    bl = META_BLACKLIST | set(extra_blacklist)
    out = {}
    for k, v in fields.items():
        if k in bl or k.startswith("__"):
            continue
        if is_empty(v):
            continue
        out[k] = v
    return out


def main():
    con = open_sqlite(readonly=True)
    tags = Tags()

    # --- предзагрузка нужных префиксов ---
    buttons = {}
    for name, fields in con.execute(
        "SELECT name, fields FROM records WHERE name LIKE 'records/ui/skills/devotion/tier%'"
    ):
        buttons[norm(name)] = json.loads(fields)

    nodes = {}
    for name, typ, fields in con.execute(
        "SELECT name, type, fields FROM records WHERE name LIKE 'records/skills/devotion/tier%'"
    ):
        nodes[norm(name)] = (typ, json.loads(fields))

    controllers = {}
    for name, fields in con.execute(
        "SELECT name, fields FROM records WHERE name LIKE 'records/controllers/itemskills/%'"
    ):
        controllers[norm(name)] = json.loads(fields)

    # petBonusName ссылается на отдельную запись *_petbonus.dbr - это шаблон
    # petbonus.tpl с ~350 полями, у которых почти все 0 и ровно 1-2 ненулевых -
    # бонус, который получает АКТИВНЫЙ ПИТОМЕЦ игрока (не сам игрок), пока у игрока
    # есть этот узел девоушена. Проверено на 3+ записях (tier1_27b_petbonus.dbr ->
    # только offensiveCritDamageModifier=5.0, и т.д.) - раньше в выходе был просто
    # путь-строка, теперь резолвим в реальные цифры.
    # Один файл в самой игре назван с опечаткой (tier1_31d_perbonus.dbr вместо
    # petbonus) - ссылка на него (petBonusName) в других записях указывает именно
    # на это опечатанное имя, так что ловим оба варианта написания.
    pet_bonuses = {}
    for name, fields in con.execute(
        "SELECT name, fields FROM records WHERE name LIKE '%petbonus.dbr' OR name LIKE '%perbonus.dbr'"
    ):
        pet_bonuses[norm(name)] = json.loads(fields)

    def resolve_pet_bonus(fdict):
        """Если в fdict есть petBonusName - заменить путь-строку на резолв."""
        pb_path = fdict.get("petBonusName")
        if not pb_path:
            return
        pb_fields = pet_bonuses.get(norm(pb_path))
        if pb_fields is None:
            return
        fdict["petBonusName"] = {
            "record": pb_fields.get("__name", pb_path),
            "stats": clean(pb_fields, extra_blacklist={"templateName"}),
        }

    const_rows = con.execute(
        "SELECT name, fields FROM records "
        "WHERE name LIKE 'records/ui/skills/devotion/constellations/constellation%.dbr' "
        "AND name NOT LIKE '%background%'"
    ).fetchall()

    # --- справочник аффинити (1..5), из records/ui/skills/devotion/affinity_0Xnumber.dbr
    # + records/ui/styles/text/style_nooutline_devotionaffinity0X_sizel.dbr (цвет) ---
    affinities = []
    for i in range(1, 6):
        style_name = f"records/ui/styles/text/style_nooutline_devotionaffinity{i:02d}_sizel.dbr"
        row = con.execute("SELECT fields FROM records WHERE name=?", (style_name,)).fetchone()
        color = None
        if row:
            sf = json.loads(row[0])
            color = {
                "r": sf.get("fontColorRed"),
                "g": sf.get("fontColorGreen"),
                "b": sf.get("fontColorBlue"),
            }
        name_tag = f"tagDevotionAffinity{i:02d}"
        desc_tag = name_tag + "Info"
        affinities.append({
            "num": i,
            "name": tags(name_tag),
            "name_tag": name_tag,
            "desc": tags(desc_tag),
            "desc_tag": desc_tag,
            "color_rgb": color,
        })

    skipped = []
    node_type_counts = {}
    trigger_type_counts = {}
    unresolved_field_samples = set()

    constellations = []
    for cname, cfields_raw in const_rows:
        f = json.loads(cfields_raw)
        btn_keys = sorted(
            (k for k in f if re.match(r"devotionButton\d+$", k)),
            key=lambda s: int(s[len("devotionButton"):]),
        )
        if not btn_keys:
            # constellation87 = "Crossroads - Bitmap", чисто декоративный коннектор на карте,
            # не настоящее созвездие - пропускаем.
            skipped.append((cname, "no devotionButton* fields (декоративный коннектор)"))
            continue

        m = re.search(r"constellation(\d+)\.dbr$", cname)
        number = int(m.group(1)) if m else None

        affinity_required = {}
        affinity_given = {}
        for i in (1, 2, 3):
            rn, ra = f.get(f"affinityRequiredName{i}"), f.get(f"affinityRequired{i}", 0)
            if rn and ra:
                affinity_required[rn] = ra
            gn, ga = f.get(f"affinityGivenName{i}"), f.get(f"affinityGiven{i}", 0)
            if gn and ga:
                affinity_given[gn] = ga

        disp_tag = f.get("constellationDisplayTag")
        info_tag = f.get("constellationInfoTag")

        node_list = []
        tiers_seen = set()
        for bk in btn_keys:
            idx = int(bk[len("devotionButton"):])
            btn_path = f[bk]
            btn_fields = buttons.get(norm(btn_path))
            if btn_fields is None:
                skipped.append((cname, f"{bk}: кнопка {btn_path} не найдена"))
                continue
            skill_path = btn_fields.get("skillName")
            node_entry = nodes.get(norm(skill_path)) if skill_path else None
            if node_entry is None:
                skipped.append((cname, f"{bk}: узел {skill_path} не найден"))
                continue
            ntype, nf = node_entry

            tm = re.search(r"/tier(\d)_", norm(skill_path))
            if tm:
                tiers_seen.add(int(tm.group(1)))

            parent_key = f"devotionLinks{idx}"
            parent_index = f.get(parent_key) if parent_key in f else None

            node_type_counts[ntype] = node_type_counts.get(ntype, 0) + 1

            record_path = nf.get("__name", skill_path)

            if ntype == "Skill_Passive":
                stats = clean(nf)
                resolve_pet_bonus(stats)
                node_list.append({
                    "index": idx,
                    "parent_index": parent_index,
                    "record": record_path,
                    "kind": "stat",
                    "stats": stats,
                })
                continue

            # --- небесная сила ---
            name_tag = nf.get("skillDisplayName")
            desc_tag = nf.get("skillBaseDescription")

            trigger = None
            tac = nf.get("templateAutoCast")
            if tac:
                ctrl = controllers.get(norm(tac))
                if ctrl:
                    trigger = {
                        "record": tac,
                        "trigger_type": ctrl.get("triggerType"),
                        "target_type": ctrl.get("targetType"),
                        "chance_pct": ctrl.get("chanceToRun"),
                        "radius": ctrl.get("autoTargetRadius"),
                    }
                    trigger_type_counts[ctrl.get("triggerType")] = (
                        trigger_type_counts.get(ctrl.get("triggerType"), 0) + 1
                    )
                else:
                    unresolved_field_samples.add(f"templateAutoCast -> {tac} не найден")

            effect = clean(nf)
            resolve_pet_bonus(effect)
            power = {
                "name": tags(name_tag) if name_tag else nf.get("FileDescription"),
                "name_tag": name_tag,
                "desc": tags(desc_tag) if desc_tag else None,
                "desc_tag": desc_tag,
                "skill_class": nf.get("Class", ntype),
                "cooldown": nf.get("skillCooldownTime"),
                "duration": nf.get("skillActiveDuration"),
                "instant_cast": bool(nf.get("instantCast")) if nf.get("instantCast") else None,
                "trigger": trigger,
                # Скиллы, к которым эту силу НЕЛЬЗЯ привязать (движковый чёрный список,
                # обычно телепорт/рывок-руны) - т.е. по умолчанию сила навешивается на
                # любой активный скилл, КРОМЕ перечисленных здесь.
                "attach_blacklist": nf.get("skillBlackList") or [],
                # Небесные силы без "trigger" (templateAutoCast) не проки, а всегда
                # активные ауры/бафы (Skill_BuffRadius) или постоянные модификаторы
                # атаки (Skill_AttackBuff) - см. отчёт, раздел "неуверенности".
                "effect": effect,
            }
            node_list.append({
                "index": idx,
                "parent_index": parent_index,
                "record": record_path,
                "kind": "power",
                "power": power,
            })

        tier = tiers_seen.pop() if len(tiers_seen) == 1 else None
        if tier is None:
            unresolved_field_samples.add(f"{cname}: не удалось однозначно определить tier ({tiers_seen})")

        constellations.append({
            "record": cname,
            "number": number,
            "name": tags(disp_tag) if disp_tag else f.get("FileDescription"),
            "name_tag": disp_tag,
            "desc": tags(info_tag) if info_tag else None,
            "desc_tag": info_tag,
            "tier": tier,
            "points_cost": len(node_list),
            "affinity_required": affinity_required,
            "affinity_given": affinity_given,
            "nodes": sorted(node_list, key=lambda n: n["index"]),
        })

    constellations.sort(key=lambda c: (c["number"] if c["number"] is not None else 9999))

    total_nodes = sum(c["points_cost"] for c in constellations)
    power_nodes = sum(1 for c in constellations for n in c["nodes"] if n["kind"] == "power")
    stat_nodes = total_nodes - power_nodes

    # число девоушен-шрайнов в мире (по числу уникальных .dbr шаблонов интерактивных
    # объектов) - это НЕ то же самое, что итоговый лимит очков (см. ниже), но полезно
    # для понимания, откуда очки берутся физически (плюс награды за квесты).
    shrine_count = con.execute(
        "SELECT COUNT(*) FROM records WHERE name LIKE 'records/interactive/devotionshrine%.dbr' "
        "AND name NOT LIKE '%blank%'"
    ).fetchone()[0]

    # Итоговый лимит очков девоушена - это игровая константа, найдена напрямую:
    # records/creatures/pc/playerlevels.dbr -> maxDevotionPoints. Это авторитетный
    # источник (не community-число "обычно 55" из брифа - оно совпало, но здесь
    # взято из самой БД, а не предположено).
    plevels = con.execute(
        "SELECT fields FROM records WHERE name='records/creatures/pc/playerlevels.dbr'"
    ).fetchone()
    max_devotion_points = None
    if plevels:
        pf = json.loads(plevels[0])
        max_devotion_points = pf.get("maxDevotionPoints")

    out = {
        "affinities": affinities,
        "meta": {
            "constellations": len(constellations),
            "constellations_skipped": len(skipped),
            "total_nodes": total_nodes,
            "stat_nodes": stat_nodes,
            "power_nodes": power_nodes,
            "devotion_shrine_dbr_templates": shrine_count,
            "max_devotion_points": max_devotion_points,
            "max_devotion_points_source": "records/creatures/pc/playerlevels.dbr:maxDevotionPoints",
            "total_devotion_points_note": (
                f"Лимит очков девоушена персонажу = {max_devotion_points} - взято "
                "напрямую из игровой константы records/creatures/pc/playerlevels.dbr "
                "(поле maxDevotionPoints). Как эти очки физически раздаются игроку "
                f"(святилища + квесты) из статического дампа не восстановлено: найдено "
                f"{shrine_count} уникальных шаблонов devotionshrine*.dbr, но это число "
                "шаблонов объекта, а не гарантированно количество расставленных на "
                "картах экземпляров, и квестовые награды в очках девоушена в дампе "
                "не просуммированы."
            ),
        },
        "constellations": constellations,
    }

    path, size = write_json("devotions.json", out, indent=1)

    # --- покрытие ---
    print(f"Созвездий обработано: {len(constellations)}")
    print(f"Созвездий пропущено: {len(skipped)}")
    for cname, why in skipped:
        print(f"  - {cname}: {why}")
    print(f"Узлов всего: {total_nodes} (стат: {stat_nodes}, силы: {power_nodes})")
    print("Типы узлов (сырой .dbr type):")
    for t, n in sorted(node_type_counts.items(), key=lambda x: -x[1]):
        print(f"   {t}: {n}")
    print("Типы триггеров небесных сил:")
    for t, n in sorted(trigger_type_counts.items(), key=lambda x: -x[1]):
        print(f"   {t}: {n}")
    if unresolved_field_samples:
        print("Неопознанное/не резолвится:")
        for s in sorted(unresolved_field_samples):
            print(f"   - {s}")
    print(f"Выход: {path} ({size} байт)")


if __name__ == "__main__":
    main()
