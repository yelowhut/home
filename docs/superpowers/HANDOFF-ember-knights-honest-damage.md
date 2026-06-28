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
> Воссоздано на 2-м ПК 2026-06-29. Системный dotnet SDK 8.0.421 подошёл (не runtime-only).
> Артефакты в `build/tools/` качаются вручную: `cpp2il.exe` (github, ~15 МБ),
> `BepInEx-be735/` (builds.bepinex.dev, ~32 МБ), `unity-libs/2022.3.62/` (unity.bepinex.dev,
> ~1.8 МБ) — см. шапку `gen-interop.ps1`.
1. **.NET SDK 8**: системный (`C:\Program Files\dotnet`) подходит, если это SDK (есть в
   `dotnet --list-sdks`), а не только runtime. Иначе — user-local:
   `https://dot.net/v1/dotnet-install.ps1 -Channel 8.0 -InstallDir $env:USERPROFILE\.dotnet`.
2. **Interop + BepInEx**: `build/gen-interop.ps1` (тянет be.735 + v31-Cpp2IL в `build/tools/`,
   генерит interop в `lib/interop/` офлайн). Хелпер: `build/gen-interop-host/`.
3. **Сборка**: `dotnet build src/HonestDamage.Plugin -c Release -o build/work/plugin-bin`.
4. **Пакет/деплой**: `build/deploy-pack.ps1 -Target dist|live` → `BepInEx/plugins/`.
   ВНИМАНИЕ: игру ЗАКРЫТЬ перед деплоем (dll лочится).

**Подводные камни этой среды (решены в коде/конфиге):**
- **Путь к игре** разный на ПК. Скрипты теперь резолвят `$env:EMBERKNIGHTS_DIR`, иначе
  пробуют `Program Files\Steam` и `C:\games\steam`. (Здесь игра в `C:\games\steam`.)
- **Прокси Primo**: `HTTP(S)_PROXY` в `.claude/settings.json` рвут restore/скачивания.
  `github`/`raw.githubusercontent` — в `NO_PROXY` (напрямую). nuget.org доступен И напрямую,
  И через прокси, но прокси флапает под нагрузкой → собирать с **обнулённым** `HTTP_PROXY`/
  `HTTPS_PROXY` (прямой доступ к nuget.org доказан). Для bepinex.dev — `curl.exe` (читает env).
- **Корпоративный NuGet-источник** `Primo-Nexus` (в user-global `NuGet.Config`) недоступен
  вне офиса → фатал NU1301. Лечится репо-`NuGet.config` (`<clear/>` + только nuget.org).
- **net6.0 targeting pack** нет на диске (только 8.0/10.0) → тянется с nuget.org при сборке.
- **deploy на чистую игру**: пофикшены 2 бага (copy `core` расплющивался в `BepInEx/`;
  `BepInEx.cfg` не создавался) — см. commit `5b70a83`.

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

## 6. Баг расчёта оружия — ФИКС РЕАЛИЗОВАН (commit `dc9684a`), ждёт верификации в игре
Симптом был (лук, ATK=9.6, моды: SpreadShot, Ricochet, Invigorate, EmpoweredArrows):
- Факт игрока: 1-й удар **10**, 2-й **10**, 3-й = **спред** (≈5/стрелу), заряд **20**.
- Мод показывал: **10 / 12 / 12**, заряд **25** (комбо бралось по порядку массива Id 1/2/3).

Что сделано в `InventoryInjector.cs`:
1. `GetRelevantAttackDefs` теперь диспетчеризует по типу оружия. Для лука — новый
   `BuildBowCombo`: удары 1 и 2 = `NormalAttackId` (оба ×1.0 → 10/10), удар 3 =
   `ThirdAttackId`, **заменяется** на `SpreadshotAttackId` при `HasMod(Bow_SpreadShot_14)`
   (моды лука REPLACE, не ADD). Заряд = `ChargeAttackId`.
2. Остальные типы оружия — fallback `BuildOrderedCombo` (первые 3 по порядку + заряд),
   пока их именованные индексы не подтверждены в игре.
3. **Заряд оставлен на `DamageMulMax`** с TODO в `ComputeAttackDamage`: наблюдение 20 ≠
   DamageMulMax×ATK (=25) и ≠ DamageMul×ATK (=13.4). «Честное» значение не подобрано —
   **сверить с фактом 20 в игре** и откалибровать.

Фикс **спекулятивный** (по §5/§7, без свежего `[NAMED]`-лога): код скомпилировался, значит
поля `NormalAttackId/ThirdAttackId/ChargeAttackId` реально есть на `XBowSettings`. Но что
именно эти Id (mul) — НЕ проверено в рантайме.

Данные `[ALL]` (лук, из старого диаг-лога): Id1=1.0, Id2=1.2, Id3=1.2, Id4=0.46(spread/стрелу,
≈верно), Id7=1.4/2.6(charge), Id10=0.6, Id13=1.2, Id14=0.75/1.0.

## 7. СЛЕДУЮЩИЙ ШАГ — ВЕРИФИКАЦИЯ В ИГРЕ (нужны руки человека)
Мод собран и задеплоен в живую игру (`C:\games\steam\...\EmberKnights`, be.735, §3-конфиг).
1. Запустить игру (**первый запуск ~1–2 мин** — BepInEx сам генерит interop в пустой
   `BepInEx/interop/`). Взять **лук**, ударить, открыть инвентарь.
2. Посмотреть голубую строку урона у лука. Ожидается (≈, ATK 9.6): `HIT:10 HIT:10` +
   3-й = спред, заряд. **Сверить с фактом: 1-й 10, 2-й 10, 3-й спред ~5/стрелу, заряд 20.**
3. Если заряд показывает **25** (а в игре 20) — откалибровать TODO charge-value в
   `ComputeAttackDamage` (см. §6.3). Если комбо/спред разъехались — F9 → прислать последние
   ~120 строк `BepInEx/honest-damage-diag.log` (секции `[NAMED]`/`[ALL]`).

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
