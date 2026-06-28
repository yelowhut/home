# Ember Knights «Honest Damage» — HANDOFF (resume on another PC)

Дата паузы: 2026-06-28. Ветка: **`ek-honest-damage`**. Репо: github.com/yelowhut/home.
Это единственный durable-источник для продолжения на другой машине: рабочий журнал
`.superpowers/sdd/progress.md`, interop, `dist/`, `build/tools/`, диаг-логи и память
Claude — **gitignored или локальны** и на другой ПК НЕ переедут. Всё нужное — здесь.

Проект: `ember-knights-honest-damage/`. Дизайн/план: `docs/superpowers/specs|plans/2026-06-28-ember-knights-honest-damage*.md`.

---

## 1. Что это и где
BepInEx IL2CPP-мод для Ember Knights (`C:\Program Files (x86)\Steam\steamapps\common\EmberKnights`,
Unity 2022.3.62f3, IL2CPP **metadata v31**, билд игры 2.3.1). Показывает реальный
stat-scaled урон оружия/абилок/скиллов; на экране выбора — задел под what-if.
- `src/HonestDamage.Core` — чистое ядро (netstandard2.1), юнит-тесты (`tests/`).
- `src/HonestDamage.Plugin` — плагин (net6.0): `Plugin.cs`, `PlayerLocator.cs`,
  `GameDataAdapter.cs`, `Diagnostics.cs`, `Injectors/SelectionInjector.cs`,
  `Injectors/InventoryInjector.cs`.

## 2. Сборка на ЧИСТОМ ПК (всё это gitignored — воссоздать заново)
1. **.NET SDK 8** (на паузном ПК ставился user-local в `C:\Users\<u>\.dotnet`):
   `https://dot.net/v1/dotnet-install.ps1 -Channel 8.0 -InstallDir $env:USERPROFILE\.dotnet`.
   Использовать ИМЕННО этот dotnet (системный в Program Files может быть runtime-only).
2. **Interop + BepInEx**: запустить `ember-knights-honest-damage/build/gen-interop.ps1`
   — он тянет **BepInEx 6.0.0-be.735** (IL2CPP win-x64) и v31-совместимый Cpp2IL в
   `build/tools/`, генерирует interop в `lib/interop/` офлайн (без запуска игры).
   Хелпер генератора: `build/gen-interop-host/`.
3. **Сборка**: `dotnet build src/HonestDamage.Plugin -c Release`.
4. **Пакет/деплой**: `build/deploy-pack.ps1 -Target dist|live`. Деплой кладёт
   `HonestDamage.Plugin.dll` + `HonestDamage.Core.dll` в `BepInEx/plugins/`.
   ВНИМАНИЕ: игру надо ЗАКРЫТЬ перед заменой dll (файл лочится).

## 3. КРИТИЧЕСКАЯ рабочая конфигурация (выстрадано)
- **BepInEx 6.0.0-be.735** + **само-генерация interop в рантайме**:
  `UpdateInteropAssemblies=true`, пустая `BepInEx/interop/`, первый запуск ~1–2 мин.
- be.697 НЕ работает (старый Cpp2IL не знает v31; падает bootstrap `BadImageFormatException`).
- **НЕ** подкладывать наш сгенерированный interop вручную — он несовместим с кодом самого
  BepInEx; работает только interop, который BepInEx сгенерил сам своим тулчейном.
- Il2CppInterop 1.4.6 идентичен в be.697/be.735 → ABI плагина не меняется.

## 4. Откалиброванные факты
- **Статы**: `Get(eAttrib)` уже возвращает финальное значение (использовать напрямую).
  Формула агрегации (если понадобится what-if): `(base + ΣAdd) × Π(1+Mul)`. `GetRaw==Get`
  (НЕ база). Core enum `Attrib` зеркалит игровой `eAttrib`: Count=43, ATK=1,
  SpellDamageModifier=11, CritDmgMUL=7, FinalPlayerDamageMultiplier=38 (проверено в игре).
- **Урон оружия** = `Get(ATK) × XBaseAttackDef.DamageMul` (заряд: ×DamageMulMax — НО см. баг §6).
  `GameCode.XPlayerSYS.CreateAttackDp(...)` возвращает шаблон с `DamageAmount=0` — НЕ годится
  для значения (финал считается при попадании). Базовый удар = ATK×1.0 (подтверждено логом).
- **Крит** = `×(1 + Get(CritDmgMUL))`. У игрока CritDmgMUL=0.5 → крит ×1.5 (НЕ ×2),
  шанс 23% (был 0.05 в др. забеге). Формат показа (выбран пользователем) — **вариант C**:
  `HIT:22 (crit 32)`.
- **Игрок кэшируется** через read-only postfix на `XPlayerSYS.CreateAttackDp` (стреляет при
  любой атаке игрока) → `PlayerLocator.Seed`. Резерв: postfix на `XEntity.TakeDamage` (когда
  по игроку попали), фильтр игрока по `XPlayerCMP`. (Файл: `Diagnostics.cs`.)

## 5. Доступ к данным (interop)
- Игрок: `PlayerLocator.GetLocalEntity()` / `GetLocalAttribs()`.
- Оружие: `entity.GetInventory()` (`GameCode.XInventoryCMP`) → `.Weapon` (`GameCode.XWeaponInst`):
  `.EquippedMods` (`List<eWeaponModType>`), `.WeaponDef`, `.HasMod(eWeaponModType)`.
  Либо `GameCode.PlayerUtils.GetWeaponDef(entity)`.
- Дефы: `GameCode.Defs.weaponDefs` (`WeaponDataFile`) → `.BowSettings`/`.SwordSettings`/…
  (`XBowSettings`/`XSwordSettings` : `XWeaponSettings`), у каждого `AttackDefs[]` +
  именованные индексы (Bow: `NormalAttackId/ThirdAttackId/ChargeAttackId`,
  `Spreadshot/Rapidshot/Markedshot/VolleyCharge/BombChargeAttackId`; Sword:
  `NormalAttack1/2/3`, `ComboAttacks`, `LungeModAttackIndex`, `WhirlwindModAttackIndex`,
  `Mod56_*`, `Mod59*`).
- `XBaseAttackDef`: `Id`, `DamageMul`, `DamageMulMax`, `IsChargeAtk`, `IsSkillShot`,
  `IsRollAtk`, `IsLastVariantAtk`, `DamageParams dp`.
- Абилки: `inv.AbilitySlots[i].Ability.Def` (`XAbilityDef`, `.Effects[0].TapValue`).
- Моды↔спец-атаки: `Bow_SpreadShot_14↔SpreadshotAttackId`, `Bow_RapidShot_13↔Rapidshot`,
  `Bow_MarkedShot_15↔Markedshot`, `Bow_Volley_17↔VolleyCharge`, `Bow_BombArrow_18↔BombCharge`.

## 6. ⛔ ТЕКУЩИЙ БАГ (на чём остановились) — расчёт оружия неточен
Симптом (лук, ATK=9.6, моды: SpreadShot, Ricochet, Invigorate, EmpoweredArrows):
- Факт игрока: 1-й удар **10**, 2-й **10**, 3-й = **спред** (≈5/стрелу), заряд **20**.
- Мод показывает: **10 / 12 / 12**, заряд **25**.

Причины:
1. **Комбо выбирается по порядку массива** (`GetRelevantAttackDefs` берёт первые 3
   не-charge дефа = Id 1,2,3 с mul 1.0/1.2/1.2). Реальное комбо лука ≠ порядку массива:
   по факту 1-й и 2-й оба ×1.0 (=10), 3-й = спред. НАДО выбирать по **именованным индексам**
   (`NormalAttackId`, `ThirdAttackId`), а не первые три подряд.
2. **3-я атака заменяется модом** (SpreadShot): показывать спред вместо базовой 3-й,
   когда мод взят (мод REPLACE, а не ADD — сейчас логика только добавляет).
3. **Заряд**: показываю `DamageMulMax` (2.6 → 25), реальный полный заряд ≈ ×2.0 (=20).
   Уточнить, какое значение заряда «честное» (вероятно НЕ DamageMulMax).

Данные `[ALL]` (лук, из диаг-лога): Id1=1.0, Id2=1.2, Id3=1.2, Id4=0.46(spread/стрелу,
≈верно), Id7=1.4/2.6(charge), Id10=0.6, Id13=1.2, Id14=0.75/1.0.

## 7. СЛЕДУЮЩИЙ ШАГ (с чего продолжить)
1. Диагностика именованных индексов УЖЕ собрана и закоммичена (commit `e6a351f`): при F9
   в инвентаре пишет в `BepInEx/honest-damage-diag.log` секции **`[NAMED]`** (какой Id —
   Normal/Third/Charge/Spread...) и **`[ALL]`** (все атаки+муљи). На новом ПК: собрать,
   задеплоить, в игре ударить→инвентарь(лук)→F9→прочитать `[NAMED]`.
2. По `[NAMED]` переписать `InventoryInjector.GetRelevantAttackDefs`: выбирать комбо по
   именованным индексам (Normal/Third), а не по порядку; заряд по `ChargeAttackId`; для
   3-й атаки показывать спред-замену, если `HasMod(Bow_SpreadShot)`; подобрать «честное»
   значение заряда (сверить с фактом 20).
3. Сверить итог с фактом игрока (1-й 10, 2-й 10, 3-й спред ~5/стрелу, заряд 20).

## 8. Прочие открытые пункты
- **Чакрам/абилки в инвентаре — пусто.** Добавлено verbose-логирование `[AbilityDiag]`
  (commit `a6ddf3e`), но в логе оно НЕ появилось → цикл по `inv.AbilitySlots` либо не
  выполняется, либо `Verbose`/троттл/не найден слот. Разобрать: проверить `[AbilityDiag]`
  в `LogOutput.log`, при отсутствии — почему `InjectAbilityLabels` не доходит.
- **Экран выбора (`SelectionInjector`)**: голубая строка `≈ …` под `Damage: X/Y/Z` —
  пользователь так и НЕ подтвердил, видна ли. Проверить.
- **What-if «сейчас → станет»** на экране выбора — ещё не реализован (расчёт-ядро готово).
- Прочие типы оружия (Staff/Hammer/Star/Reaper/DarkCap/Fists/Gun) — пока только база+заряд,
  без мод-маппинга (`// TODO mod-map`).
- Крит-показ реализован (вариант C), но числа поедут после фикса §6/§7.

## 9. Подтверждённый статус (что работает)
Мод грузится в игру (be.735), F8 toggle / F9 диаг-дамп, проактивный кэш игрока,
read-only (мультиплеер-safe). Оружие показывает строку урона В ОПИСАНИИ (без наложения
на ценник), мод-зависимый отбор спец-атак по `HasMod`, крит рядом. Точность чисел —
дорабатывается (§6).
