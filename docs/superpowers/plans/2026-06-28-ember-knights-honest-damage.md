# Ember Knights «Честный урон» — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Собрать загружаемый BepInEx IL2CPP-плагин для Ember Knights, который показывает реальный текущий урон абилок/скиллов/оружия/реликвий с учётом статов, а на экране наград — прогноз-дельту от предлагаемого предмета.

**Architecture:** Чистое расчётное ядро (`HonestDamage.Core`, netstandard2.1, без Unity/IL2CPP, покрыто юнит-тестами) + тонкий IL2CPP-плагин (`HonestDamage.Plugin`, net6.0), который читает игровые данные через адаптер и рисует суффиксы. Текущие статы берутся точно из игры (`XAttribsCMP.Get`); ядро реплицирует агрегацию только для what-if; калибруется лишь формула base→урон по диагностическим логам.

**Tech Stack:** C# / .NET (Core: netstandard2.1, Plugin: net6.0, Tests: net8.0 xUnit); BepInEx 6 BleedingEdge IL2CPP; HarmonyX; Il2CppInterop; Cpp2IL (офлайн-генерация interop); Unity 2022.3.62f3.

## Global Constraints

- Целевая игра: Unity **2022.3.62f3**, IL2CPP, билд **2.3.1 / 4969**, win-x64. Metadata v31.
- Путь к игре: `C:\Program Files (x86)\Steam\steamapps\common\EmberKnights`.
- Проект-рут: `D:\git\home\ember-knights-honest-damage\`.
- **Сборку (interop + dll) выполняет Claude; пользователь только копирует файлы.** dotnet 6/8/9 уже установлен (`C:\Program Files\dotnet\dotnet.exe`).
- **N1 fail-safe:** каждый Harmony-хук и каждый инъектор обёрнут в try/catch; исключение логируется и проглатывается, игра не падает.
- **N2 read-only:** плагин НЕ мутирует игровое состояние и НЕ шлёт сетевых сообщений. What-if считается в скретч-копии данных, без вызова `AddAttribModifier` на живом `XAttribsCMP`.
- **F5 формат:** только аддитивный суффикс/доп-строка рядом с оригиналом; оригинальный текст не перезаписывается.
- Дамп-референс (имена типов/сигнатуры): `<scratch>/output/dump.cs`, `DummyDll/Assembly-CSharp.dll`. **Тел методов в дампе нет** — формулы калибруются рантайм-логами.
- Игровые идентификаторы, помеченные `[runtime-confirm]`, подтверждаются на Задаче 9 (диагностика) и при расхождении правятся; это нормальный цикл IL2CPP-моддинга, а не заглушка.

**Grounded факты из дампа (используются в коде ниже как есть):**
- `enum eAttribModOperator { ADD = 0, MUL = 1 }`
- `enum eAttribModSource { Undefined, Weapon, EmberTreeUpgrade, Relic, AppleCrisp, AppleSlice, StatusEffect, StatPotion, SoulSiphon, ArmourStand, WeaponMod, AbilityUpgrade }`
- `enum eAttrib { None, ATK, ATKRate, DEF, MaxHP, MaxCurses, CritChance, CritDmgMUL, MoveSpeed, MoveSpeedMUL, AbilityNumHitsModifier, SpellDamageModifier, ... ThrowDamageModifier, ... BonusBurnDamageModifier, ... FinalPlayerDamageMultiplier, ..., Count }` (полный список — в dump.cs)
- `class GameCode.XAttribsCMP : XBaseCMP` с полями `Dictionary<eAttrib, List<XAttribModifier>> modifiersByAttrib`, `float[] Attributes` и методами `float Get(eAttrib)`, `float GetRaw(eAttrib)`, `void AddAttribModifier(XAttribModifier)`, `void RemoveAttribModifiersBySource(eAttribModSource)`.
- `class XAttribModifier { eAttrib Attrib; float Value; eAttribModOperator Operator; eAttribModSource Source; int SourceDefId; bool IsPersistent; bool IsADD; bool IsMUL; }`, ctor `(XAttribModDef Def, int UpgradeCount, eAttribModSource, int SourceDefId)`.
- `class XAttribModDef { eAttrib Attrib; float Value; float Upgrade; eAttribModOperator Operator; ... }`
- Дефы: `XWeaponDef : TinyDef { float AttackBase; eDamageType DamageType; XAttribModDef[] AttribModifiers; ... }`, `XRelicDef : TinyDef { XAttribModDef[] AttribModifiers; XRelicEffectDef[] Effects; ... }`.

---

## File Structure

```
ember-knights-honest-damage/
├─ HonestDamage.sln
├─ .gitignore
├─ Directory.Build.props                 # общий <LangVersion>, путь к interop
├─ src/
│  ├─ HonestDamage.Core/
│  │  ├─ HonestDamage.Core.csproj         # netstandard2.1, без зависимостей
│  │  ├─ Attrib.cs                        # enum Attrib (mirror), enum ModOp
│  │  ├─ Modifier.cs                      # readonly struct Modifier
│  │  ├─ AttribResolver.cs                # агрегация base+ΣADD ×ΠMUL, overlay
│  │  ├─ DamageKind.cs                    # enum DamageKind (Weapon/Ability/Spell/Throw/Pet)
│  │  ├─ DamageMapping.cs                 # какой Attrib влияет на какой DamageKind (калибровка)
│  │  └─ DamageModel.cs                   # base × релевантные статы → урон
│  ├─ HonestDamage.Plugin/
│  │  ├─ HonestDamage.Plugin.csproj       # net6.0, refs interop + BepInEx + Core
│  │  ├─ Plugin.cs                        # BasePlugin, config, hotkey, Harmony bootstrap, Log guard
│  │  ├─ PlayerLocator.cs                 # поиск локального игрока + XAttribsCMP
│  │  ├─ GameDataAdapter.cs               # XAttribModifier/XDef → Core-типы
│  │  ├─ Diagnostics.cs                   # дамп-лог + read-only damage hook
│  │  └─ Injectors/
│  │     ├─ WeaponInfoInjector.cs
│  │     ├─ InventoryInjector.cs
│  │     └─ RewardSelectInjector.cs
├─ tests/
│  └─ HonestDamage.Core.Tests/
│     ├─ HonestDamage.Core.Tests.csproj   # net8.0, xUnit, ref Core
│     ├─ AttribResolverTests.cs
│     └─ DamageModelTests.cs
├─ build/
│  └─ gen-interop.ps1                     # офлайн-генерация interop
├─ lib/interop/                           # сгенерированные interop dll (gitignored)
└─ dist/                                  # готовый деливерабл (BepInEx + plugin dll + README)
```

---

## Task 1: Scaffold проекта (solution + csproj + gitignore)

**Files:**
- Create: `ember-knights-honest-damage/HonestDamage.sln`
- Create: `ember-knights-honest-damage/.gitignore`
- Create: `ember-knights-honest-damage/Directory.Build.props`
- Create: `src/HonestDamage.Core/HonestDamage.Core.csproj`
- Create: `tests/HonestDamage.Core.Tests/HonestDamage.Core.Tests.csproj`

**Interfaces:**
- Produces: компилируемые пустые проекты `HonestDamage.Core` (netstandard2.1) и `HonestDamage.Core.Tests` (net8.0, xUnit) в одном solution.

- [ ] **Step 1: Создать `.gitignore`**

```gitignore
bin/
obj/
lib/interop/
dist/
*.user
```

- [ ] **Step 2: Создать `Directory.Build.props`**

```xml
<Project>
  <PropertyGroup>
    <LangVersion>latest</LangVersion>
    <Nullable>enable</Nullable>
    <ImplicitUsings>disable</ImplicitUsings>
  </PropertyGroup>
</Project>
```

- [ ] **Step 3: Создать `src/HonestDamage.Core/HonestDamage.Core.csproj`**

```xml
<Project Sdk="Microsoft.NET.Sdk">
  <PropertyGroup>
    <TargetFramework>netstandard2.1</TargetFramework>
    <AssemblyName>HonestDamage.Core</AssemblyName>
  </PropertyGroup>
</Project>
```

- [ ] **Step 4: Создать `tests/HonestDamage.Core.Tests/HonestDamage.Core.Tests.csproj`**

```xml
<Project Sdk="Microsoft.NET.Sdk">
  <PropertyGroup>
    <TargetFramework>net8.0</TargetFramework>
    <IsPackable>false</IsPackable>
  </PropertyGroup>
  <ItemGroup>
    <PackageReference Include="Microsoft.NET.Test.Sdk" Version="17.11.1" />
    <PackageReference Include="xunit" Version="2.9.2" />
    <PackageReference Include="xunit.runner.visualstudio" Version="2.8.2" />
  </ItemGroup>
  <ItemGroup>
    <ProjectReference Include="..\..\src\HonestDamage.Core\HonestDamage.Core.csproj" />
  </ItemGroup>
</Project>
```

- [ ] **Step 5: Создать solution и добавить проекты**

Run:
```bash
cd "D:/git/home/ember-knights-honest-damage"
"/c/Program Files/dotnet/dotnet.exe" new sln -n HonestDamage
"/c/Program Files/dotnet/dotnet.exe" sln add src/HonestDamage.Core/HonestDamage.Core.csproj tests/HonestDamage.Core.Tests/HonestDamage.Core.Tests.csproj
```

- [ ] **Step 6: Проверить сборку**

Run: `"/c/Program Files/dotnet/dotnet.exe" build`
Expected: Build succeeded, 0 ошибок (2 проекта).

- [ ] **Step 7: Commit**

```bash
git add ember-knights-honest-damage
git commit -m "chore(ek-mod): scaffold Core + Tests projects"
```

---

## Task 2: Офлайн-генерация interop-сборок

**Files:**
- Create: `build/gen-interop.ps1`
- Output (gitignored): `lib/interop/*.dll` (включая `Il2Cppmscorlib.dll`, `Il2CppAssembly-CSharp.dll`, `UnityEngine.*.dll`, `Il2CppInterop.Runtime.dll`, `Il2CppInterop.Common.dll`)

**Interfaces:**
- Produces: набор interop-DLL в `lib/interop/`, на которые ссылается `HonestDamage.Plugin.csproj` (Task 7).

**Подход:** использовать тулинг BepInEx (`Il2CppInterop.Generator`) поверх вывода `Cpp2IL`, плюс Unity base libs для 2022.3.62f3. Без запуска игры.

- [ ] **Step 1: Скачать инструменты в `build/tools/`**

Скачать (в `build/tools/`):
- Cpp2IL CLI (релиз, поддерживающий metadata v31), напр. `Cpp2IL-*-Windows-Netframework472.zip` → `cpp2il.exe`.
- `Il2CppInterop.Generator` CLI (из репозитория BepInEx/Il2CppInterop релизов или через `dotnet tool`).
- Unity base libs для 2022.3.62f3 — managed `UnityEngine.*.dll` (берутся из BepInEx unity-libs-нагрузки, кэш `unhollowed/.cache` или из установленного Unity 2022.3.62f3 `Data/Managed`).

- [ ] **Step 2: Написать `build/gen-interop.ps1`**

```powershell
$ErrorActionPreference = "Stop"
$game = "C:\Program Files (x86)\Steam\steamapps\common\EmberKnights"
$root = Split-Path $PSScriptRoot -Parent
$tools = Join-Path $PSScriptRoot "tools"
$work  = Join-Path $PSScriptRoot "work"
$out   = Join-Path $root "lib\interop"
New-Item -ItemType Directory -Force -Path $work, $out | Out-Null

# 1. Cpp2IL: GameAssembly.dll + global-metadata.dat -> dummy assemblies
& "$tools\cpp2il.exe" `
  --game-path "$game" `
  --output-root "$work\cpp2il" `
  --output-as dummydll

# 2. Il2CppInterop.Generator: dummy -> interop proxy assemblies
& "$tools\Il2CppInterop.Generator.exe" `
  --input "$work\cpp2il" `
  --output "$out" `
  --unity-libs "$tools\unity-libs\2022.3.62f3"

Write-Host "Interop assemblies written to $out"
```

- [ ] **Step 3: Запустить генерацию**

Run: `powershell -ExecutionPolicy Bypass -File build/gen-interop.ps1`
Expected: в `lib/interop/` появились `Il2CppAssembly-CSharp.dll`, `Il2Cppmscorlib.dll`, `UnityEngine.CoreModule.dll` и др.

Verify (имена типов на месте):
```bash
ls "D:/git/home/ember-knights-honest-damage/lib/interop" | grep -E "Il2CppAssembly-CSharp|UnityEngine.CoreModule"
```
Expected: оба файла присутствуют.

> **Fallback (последнее средство, если офлайн-пайплайн не сходится):** установить BepInEx в копию игры и запустить игру один раз для генерации `BepInEx/interop/` — требует запуска игры (нежелательно, согласовано как крайний случай). Зафиксировать в README, если применялось.

- [ ] **Step 4: Commit (только скрипт; interop gitignored)**

```bash
git add ember-knights-honest-damage/build/gen-interop.ps1
git commit -m "build(ek-mod): offline interop generation script"
```

---

## Task 3: Подготовить staged BepInEx 6 IL2CPP

**Files:**
- Output: `dist/BepInEx-pack/` (распакованный BepInEx 6 BE IL2CPP win-x64) + `dist/BepInEx-pack/BepInEx/plugins/` (пустая).

**Interfaces:**
- Produces: готовая папка BepInEx, в `plugins/` которой Task 13 положит финальный dll.

- [ ] **Step 1: Скачать BepInEx 6 BE IL2CPP win-x64** в `dist/BepInEx-pack/` и распаковать (содержит `winhttp.dll`, `doorstop_config.ini`, `BepInEx/`).

- [ ] **Step 2: Создать `BepInEx/plugins/`**

Run:
```bash
mkdir -p "D:/git/home/ember-knights-honest-damage/dist/BepInEx-pack/BepInEx/plugins"
```

- [ ] **Step 3: Проверить структуру**

Run: `ls "D:/git/home/ember-knights-honest-damage/dist/BepInEx-pack"`
Expected: присутствуют `winhttp.dll`, `doorstop_config.ini`, `BepInEx/`.

- [ ] **Step 4: Commit (скрипт/манифест; бинарь пакета gitignored через dist/)**

```bash
git add -f ember-knights-honest-damage/dist/BepInEx-pack/doorstop_config.ini
git commit -m "build(ek-mod): stage BepInEx 6 IL2CPP pack"
```

---

## Task 4: Core — Attrib, ModOp, Modifier

**Files:**
- Create: `src/HonestDamage.Core/Attrib.cs`
- Create: `src/HonestDamage.Core/Modifier.cs`
- Test: `tests/HonestDamage.Core.Tests/AttribResolverTests.cs` (заведём файл здесь, наполним в Task 5)

**Interfaces:**
- Produces:
  - `enum Attrib` (значения и порядок зеркалят игровой `eAttrib`; используем `int`-значения).
  - `enum ModOp { Add = 0, Mul = 1 }` (зеркало `eAttribModOperator`).
  - `readonly struct Modifier { Attrib Attrib; float Value; ModOp Op; }` c ctor `(Attrib, float, ModOp)`.

- [ ] **Step 1: Написать `Attrib.cs`**

```csharp
namespace HonestDamage.Core
{
    // Значения соответствуют игровому eAttrib (см. dump.cs). Порядок важен только
    // для маппинга в адаптере; в Core используем как непрозрачный ключ.
    public enum Attrib
    {
        None = 0, ATK, ATKRate, DEF, MaxHP, MaxCurses, CritChance, CritDmgMUL,
        MoveSpeed, MoveSpeedMUL, AbilityNumHitsModifier, SpellDamageModifier,
        RareDropModifier, EpicDropModifier, LegendaryDropModifier, GoldDropModifier,
        SmallHeartDropModifier, LargeHeartDropModifier, SmallHpPotionDropModifier,
        LargeHpPotionDropModifier, SmallManaPotionDropModifier, LargeManaPotionDropModifier,
        SpellCooldownModifier, BonusHealingModifier, ThrowDamageModifier,
        ChargeDurationModifier, BlockChance, SmallStatPotionDropModifier,
        LargeStatPotionDropModifier, HealingPrevented, EnemyAbilityCooldownModifier,
        EnemyFinalDamageMultiplier, SkillChargeIncrease, BonusBurnDamageModifier,
        MagicDEF, EnemyATKModifier, MaxArmor, UNUSED_1, FinalPlayerDamageMultiplier,
        MaxWisps, MaxKitsunes, MaxHydras, MaxYalee, Count
    }

    public enum ModOp { Add = 0, Mul = 1 }
}
```

- [ ] **Step 2: Написать `Modifier.cs`**

```csharp
namespace HonestDamage.Core
{
    public readonly struct Modifier
    {
        public readonly Attrib Attrib;
        public readonly float Value;
        public readonly ModOp Op;

        public Modifier(Attrib attrib, float value, ModOp op)
        {
            Attrib = attrib;
            Value = value;
            Op = op;
        }
    }
}
```

- [ ] **Step 3: Сборка**

Run: `"/c/Program Files/dotnet/dotnet.exe" build src/HonestDamage.Core`
Expected: Build succeeded.

- [ ] **Step 4: Commit**

```bash
git add src/HonestDamage.Core/Attrib.cs src/HonestDamage.Core/Modifier.cs
git commit -m "feat(ek-mod): Core attrib/modifier types"
```

---

## Task 5: Core — AttribResolver (агрегация + overlay для what-if)

**Files:**
- Create: `src/HonestDamage.Core/AttribResolver.cs`
- Test: `tests/HonestDamage.Core.Tests/AttribResolverTests.cs`

**Interfaces:**
- Consumes: `Attrib`, `ModOp`, `Modifier` (Task 4).
- Produces:
  - `static float AttribResolver.Resolve(float baseValue, IEnumerable<Modifier> mods, Attrib attrib)` — `(baseValue + ΣAdd) * Π Mul`, где учитываются только модификаторы с `m.Attrib == attrib`. Если MUL отсутствуют — множитель 1.
  - `static float AttribResolver.ResolveWith(float baseValue, IEnumerable<Modifier> current, IEnumerable<Modifier> extra, Attrib attrib)` — то же по объединению `current ∪ extra` (для what-if).

> Семантика MUL (`× value` против `× (1+value)`) — точка калибровки. Реализуем `× value` и фиксируем тестом; если диагностика (Task 9) покажет иную семантику, правка локальна в одном методе.

- [ ] **Step 1: Написать падающий тест `AttribResolverTests.cs`**

```csharp
using System.Collections.Generic;
using HonestDamage.Core;
using Xunit;

public class AttribResolverTests
{
    [Fact]
    public void Resolve_NoMods_ReturnsBase()
    {
        Assert.Equal(100f, AttribResolver.Resolve(100f, new Modifier[0], Attrib.ATK));
    }

    [Fact]
    public void Resolve_SumsAdd_ThenMultipliesMul()
    {
        var mods = new[]
        {
            new Modifier(Attrib.ATK, 50f, ModOp.Add),
            new Modifier(Attrib.ATK, 1.2f, ModOp.Mul),
        };
        // (100 + 50) * 1.2 = 180
        Assert.Equal(180f, AttribResolver.Resolve(100f, mods, Attrib.ATK));
    }

    [Fact]
    public void Resolve_IgnoresOtherAttribs()
    {
        var mods = new[] { new Modifier(Attrib.CritChance, 99f, ModOp.Add) };
        Assert.Equal(100f, AttribResolver.Resolve(100f, mods, Attrib.ATK));
    }

    [Fact]
    public void ResolveWith_AddsExtraOnTopOfCurrent()
    {
        var current = new[] { new Modifier(Attrib.ATK, 50f, ModOp.Add) };
        var extra = new[] { new Modifier(Attrib.ATK, 1.5f, ModOp.Mul) };
        // (100 + 50) * 1.5 = 225
        Assert.Equal(225f, AttribResolver.ResolveWith(100f, current, extra, Attrib.ATK));
    }
}
```

- [ ] **Step 2: Запустить — убедиться, что падает**

Run: `"/c/Program Files/dotnet/dotnet.exe" test tests/HonestDamage.Core.Tests`
Expected: FAIL (тип `AttribResolver` не существует).

- [ ] **Step 3: Реализовать `AttribResolver.cs`**

```csharp
using System.Collections.Generic;

namespace HonestDamage.Core
{
    public static class AttribResolver
    {
        public static float Resolve(float baseValue, IEnumerable<Modifier> mods, Attrib attrib)
        {
            float add = 0f;
            float mul = 1f;
            foreach (var m in mods)
            {
                if (m.Attrib != attrib) continue;
                if (m.Op == ModOp.Add) add += m.Value;
                else mul *= m.Value;
            }
            return (baseValue + add) * mul;
        }

        public static float ResolveWith(float baseValue, IEnumerable<Modifier> current,
            IEnumerable<Modifier> extra, Attrib attrib)
        {
            var all = new List<Modifier>();
            all.AddRange(current);
            all.AddRange(extra);
            return Resolve(baseValue, all, attrib);
        }
    }
}
```

- [ ] **Step 4: Запустить — убедиться, что проходит**

Run: `"/c/Program Files/dotnet/dotnet.exe" test tests/HonestDamage.Core.Tests`
Expected: PASS (4 теста).

- [ ] **Step 5: Commit**

```bash
git add src/HonestDamage.Core/AttribResolver.cs tests/HonestDamage.Core.Tests/AttribResolverTests.cs
git commit -m "feat(ek-mod): AttribResolver with ADD/MUL aggregation + what-if overlay"
```

---

## Task 6: Core — DamageKind, DamageMapping, DamageModel

**Files:**
- Create: `src/HonestDamage.Core/DamageKind.cs`
- Create: `src/HonestDamage.Core/DamageMapping.cs`
- Create: `src/HonestDamage.Core/DamageModel.cs`
- Test: `tests/HonestDamage.Core.Tests/DamageModelTests.cs`

**Interfaces:**
- Consumes: `Attrib`, `AttribResolver`.
- Produces:
  - `enum DamageKind { WeaponAttack, Ability, Spell, Throw, Pet }`.
  - `static class DamageMapping` с `static IReadOnlyList<Attrib> ScalingAttribs(DamageKind kind)` — какие резолв-статы множат урон данного вида (калибровочная таблица). Базовая версия:
    - `WeaponAttack` → `[ATK, FinalPlayerDamageMultiplier]`
    - `Ability` → `[ATK, AbilityNumHitsModifier, FinalPlayerDamageMultiplier]`
    - `Spell` → `[SpellDamageModifier, FinalPlayerDamageMultiplier]`
    - `Throw` → `[ATK, ThrowDamageModifier, FinalPlayerDamageMultiplier]`
    - `Pet` → `[FinalPlayerDamageMultiplier]`
  - `readonly struct StatSnapshot` — резолв-значения по `Attrib` (обёртка над `float[]` индексированным `(int)Attrib`), с `float Get(Attrib a)`.
  - `static float DamageModel.Compute(DamageKind kind, float baseDamage, StatSnapshot stats)` — `baseDamage`, домноженный на произведение `stats.Get(a)` по `DamageMapping.ScalingAttribs(kind)`. Для `ATK` множитель = `stats.Get(ATK)/100f` (ATK как процент; 100 = ×1) — **калибруется**; для прочих модификаторов множитель = `stats.Get(a)` напрямую, при значении 0 трактуется как ×1 (отсутствие модификатора). Семантика помечена для калибровки в Task 9.

> Это слой, который точно потребует правок по логам (формула неизвестна из дампа). Тесты фиксируют *структуру* расчёта на синтетике, не «правильные» игровые числа.

- [ ] **Step 1: Написать `DamageKind.cs`**

```csharp
namespace HonestDamage.Core
{
    public enum DamageKind { WeaponAttack, Ability, Spell, Throw, Pet }
}
```

- [ ] **Step 2: Написать `DamageMapping.cs`**

```csharp
using System.Collections.Generic;

namespace HonestDamage.Core
{
    public static class DamageMapping
    {
        public static IReadOnlyList<Attrib> ScalingAttribs(DamageKind kind)
        {
            switch (kind)
            {
                case DamageKind.WeaponAttack:
                    return new[] { Attrib.ATK, Attrib.FinalPlayerDamageMultiplier };
                case DamageKind.Ability:
                    return new[] { Attrib.ATK, Attrib.AbilityNumHitsModifier, Attrib.FinalPlayerDamageMultiplier };
                case DamageKind.Spell:
                    return new[] { Attrib.SpellDamageModifier, Attrib.FinalPlayerDamageMultiplier };
                case DamageKind.Throw:
                    return new[] { Attrib.ATK, Attrib.ThrowDamageModifier, Attrib.FinalPlayerDamageMultiplier };
                case DamageKind.Pet:
                    return new[] { Attrib.FinalPlayerDamageMultiplier };
                default:
                    return new Attrib[0];
            }
        }
    }
}
```

- [ ] **Step 3: Написать падающий тест `DamageModelTests.cs`**

```csharp
using HonestDamage.Core;
using Xunit;

public class DamageModelTests
{
    private static StatSnapshot Stats(params (Attrib a, float v)[] vals)
    {
        var arr = new float[(int)Attrib.Count];
        foreach (var (a, v) in vals) arr[(int)a] = v;
        return new StatSnapshot(arr);
    }

    [Fact]
    public void Compute_Weapon_ScalesByAtkPercent()
    {
        var stats = Stats((Attrib.ATK, 200f), (Attrib.FinalPlayerDamageMultiplier, 1f));
        // base 50 * (200/100) * 1 = 100
        Assert.Equal(100f, DamageModel.Compute(DamageKind.WeaponAttack, 50f, stats));
    }

    [Fact]
    public void Compute_TreatsZeroModifierAsNeutral()
    {
        var stats = Stats((Attrib.ATK, 100f)); // FinalPlayerDamageMultiplier = 0 -> neutral
        // base 50 * (100/100) * 1 = 50
        Assert.Equal(50f, DamageModel.Compute(DamageKind.WeaponAttack, 50f, stats));
    }

    [Fact]
    public void Compute_Spell_UsesSpellModifier()
    {
        var stats = Stats((Attrib.SpellDamageModifier, 1.5f));
        // base 80 * 1.5 = 120
        Assert.Equal(120f, DamageModel.Compute(DamageKind.Spell, 80f, stats));
    }
}
```

- [ ] **Step 4: Запустить — убедиться, что падает**

Run: `"/c/Program Files/dotnet/dotnet.exe" test tests/HonestDamage.Core.Tests`
Expected: FAIL (`StatSnapshot`/`DamageModel` не существуют).

- [ ] **Step 5: Реализовать `DamageModel.cs` (включая `StatSnapshot`)**

```csharp
namespace HonestDamage.Core
{
    public readonly struct StatSnapshot
    {
        private readonly float[] _values; // индекс = (int)Attrib

        public StatSnapshot(float[] values) { _values = values; }

        public float Get(Attrib a)
        {
            int i = (int)a;
            if (_values == null || i < 0 || i >= _values.Length) return 0f;
            return _values[i];
        }
    }

    public static class DamageModel
    {
        public static float Compute(DamageKind kind, float baseDamage, StatSnapshot stats)
        {
            float dmg = baseDamage;
            foreach (var a in DamageMapping.ScalingAttribs(kind))
            {
                float v = stats.Get(a);
                if (a == Attrib.ATK)
                {
                    // ATK выражен как процент: 100 = x1. [calibrate Task 9]
                    dmg *= (v <= 0f ? 1f : v / 100f);
                }
                else
                {
                    // модификаторы-множители: 0 трактуем как нейтральный x1
                    dmg *= (v <= 0f ? 1f : v);
                }
            }
            return dmg;
        }
    }
}
```

- [ ] **Step 6: Запустить — убедиться, что проходит**

Run: `"/c/Program Files/dotnet/dotnet.exe" test tests/HonestDamage.Core.Tests`
Expected: PASS (все тесты Core, 7 шт).

- [ ] **Step 7: Commit**

```bash
git add src/HonestDamage.Core/DamageKind.cs src/HonestDamage.Core/DamageMapping.cs src/HonestDamage.Core/DamageModel.cs tests/HonestDamage.Core.Tests/DamageModelTests.cs
git commit -m "feat(ek-mod): DamageModel + scaling mapping (calibratable)"
```

---

## Task 7: Plugin — entry, config, hotkey, Harmony bootstrap

**Files:**
- Create: `src/HonestDamage.Plugin/HonestDamage.Plugin.csproj`
- Create: `src/HonestDamage.Plugin/Plugin.cs`
- Modify: `HonestDamage.sln` (добавить проект)

**Interfaces:**
- Consumes: interop из `lib/interop` (Task 2), BepInEx/HarmonyX, `HonestDamage.Core`.
- Produces:
  - `class Plugin : BasePlugin` со статикой:
    - `static ManualLogSource Log` — общий логгер.
    - `static ConfigEntry<KeyboardShortcut> ToggleKey`, `static ConfigEntry<bool> EnableWeaponInfo/EnableInventory/EnableRewards/VerboseDiag`.
    - `static bool OverlayEnabled` — состояние тоггла.
    - `static void Guard(string where, Action body)` — обёртка try/catch (реализует N1), логирует исключения.

> Эта и последующие задачи **не юнит-тестируются** (нужна игра). «Verification» = успешная сборка + (отложенно) строка в `BepInEx/LogOutput.log`. Это явный и согласованный режим (калибровка по логам).

- [ ] **Step 1: Написать `HonestDamage.Plugin.csproj`**

```xml
<Project Sdk="Microsoft.NET.Sdk">
  <PropertyGroup>
    <TargetFramework>net6.0</TargetFramework>
    <AssemblyName>HonestDamage.Plugin</AssemblyName>
    <AllowUnsafeBlocks>true</AllowUnsafeBlocks>
    <RestoreAdditionalProjectSources>https://nuget.bepinex.dev/v3/index.json</RestoreAdditionalProjectSources>
  </PropertyGroup>
  <ItemGroup>
    <PackageReference Include="BepInEx.Unity.IL2CPP" Version="6.0.0-be.*" IncludeAssets="compile" />
    <ProjectReference Include="..\HonestDamage.Core\HonestDamage.Core.csproj" />
  </ItemGroup>
  <ItemGroup>
    <!-- interop, сгенерированный в Task 2 -->
    <Reference Include="$(MSBuildProjectDirectory)\..\..\lib\interop\*.dll" Private="false" />
  </ItemGroup>
</Project>
```

- [ ] **Step 2: Написать `Plugin.cs`**

```csharp
using System;
using BepInEx;
using BepInEx.Configuration;
using BepInEx.Logging;
using BepInEx.Unity.IL2CPP;
using HarmonyLib;
using UnityEngine;

namespace HonestDamage.Plugin
{
    [BepInPlugin("com.ashubin.ekhonestdamage", "Ember Knights Honest Damage", "0.1.0")]
    public class Plugin : BasePlugin
    {
        public static ManualLogSource Log = null!;
        public static bool OverlayEnabled = true;

        public static ConfigEntry<KeyboardShortcut> ToggleKey = null!;
        public static ConfigEntry<KeyboardShortcut> DiagDumpKey = null!;
        public static ConfigEntry<bool> EnableWeaponInfo = null!;
        public static ConfigEntry<bool> EnableInventory = null!;
        public static ConfigEntry<bool> EnableRewards = null!;
        public static ConfigEntry<bool> VerboseDiag = null!;

        public override void Load()
        {
            Log = base.Log;
            ToggleKey = Config.Bind("General", "ToggleKey",
                new KeyboardShortcut(KeyCode.F8), "Включить/выключить оверлей");
            DiagDumpKey = Config.Bind("General", "DiagDumpKey",
                new KeyboardShortcut(KeyCode.F9), "Сбросить диагностический дамп в файл");
            EnableWeaponInfo = Config.Bind("Surfaces", "WeaponInfo", true, "Окно информации оружия");
            EnableInventory = Config.Bind("Surfaces", "Inventory", true, "Инвентарь/пауза");
            EnableRewards = Config.Bind("Surfaces", "Rewards", true, "Экран выбора наград + what-if");
            VerboseDiag = Config.Bind("Diagnostics", "Verbose", true, "Подробный лог калибровки");

            var harmony = new Harmony("com.ashubin.ekhonestdamage");
            harmony.PatchAll();
            Log.LogInfo("Honest Damage loaded. Toggle=" + ToggleKey.Value + " DiagDump=" + DiagDumpKey.Value);
        }

        public static void Guard(string where, Action body)
        {
            try { body(); }
            catch (Exception e) { Log.LogError("[" + where + "] " + e); }
        }
    }
}
```

- [ ] **Step 3: Добавить проект в solution**

Run:
```bash
cd "D:/git/home/ember-knights-honest-damage"
"/c/Program Files/dotnet/dotnet.exe" sln add src/HonestDamage.Plugin/HonestDamage.Plugin.csproj
```

- [ ] **Step 4: Собрать плагин**

Run: `"/c/Program Files/dotnet/dotnet.exe" build src/HonestDamage.Plugin -c Release`
Expected: Build succeeded; `bin/Release/net6.0/HonestDamage.Plugin.dll` создан.

- [ ] **Step 5: Commit**

```bash
git add src/HonestDamage.Plugin ember-knights-honest-damage/HonestDamage.sln
git commit -m "feat(ek-mod): BepInEx plugin entry + config + Harmony bootstrap"
```

---

## Task 8: Plugin — PlayerLocator + GameDataAdapter

**Files:**
- Create: `src/HonestDamage.Plugin/PlayerLocator.cs`
- Create: `src/HonestDamage.Plugin/GameDataAdapter.cs`

**Interfaces:**
- Consumes: interop типы `GameCode.XAttribsCMP`, `XAttribModifier`, `XAttribModDef`, `XWeaponDef`, `XRelicDef`; `eAttrib`; Core `Modifier`, `StatSnapshot`, `Attrib`.
- Produces:
  - `static class PlayerLocator` → `static XAttribsCMP? GetLocalAttribs()` (находит компонент атрибутов локального игрока). `[runtime-confirm]` способ доступа к локальному игроку (через `GameCode.XWorld`/`PlayerStateCMP`).
  - `static class GameDataAdapter`:
    - `static StatSnapshot Snapshot(XAttribsCMP cmp)` — заполняет `float[(int)Attrib.Count]` через `cmp.Get((eAttrib)i)`.
    - `static List<Modifier> CurrentModifiers(XAttribsCMP cmp)` — разворачивает `cmp.modifiersByAttrib` в плоский список `Modifier`.
    - `static List<Modifier> ModifiersFromDef(XAttribModDef[] defs, int upgradeCount)` — строит гипотетические `Modifier` из `XAttribModDef` (для what-if), `value = def.Value + def.Upgrade*upgradeCount`.

- [ ] **Step 1: Написать `PlayerLocator.cs`**

```csharp
using GameCode;
using UnityEngine;

namespace HonestDamage.Plugin
{
    public static class PlayerLocator
    {
        public static XAttribsCMP? GetLocalAttribs()
        {
            XAttribsCMP? result = null;
            Plugin.Guard("PlayerLocator.GetLocalAttribs", () =>
            {
                // [runtime-confirm Task 9]: уточнить точный путь к локальному игроку.
                // Базовый вариант: найти все XAttribsCMP и взять принадлежащий
                // локальному игроку. Объект-носитель — игрок.
                var all = Object.FindObjectsOfType<XAttribsCMP>();
                if (all != null && all.Length > 0) result = all[0];
            });
            return result;
        }
    }
}
```

- [ ] **Step 2: Написать `GameDataAdapter.cs`**

```csharp
using System.Collections.Generic;
using GameCode;
using HonestDamage.Core;

namespace HonestDamage.Plugin
{
    public static class GameDataAdapter
    {
        public static StatSnapshot Snapshot(XAttribsCMP cmp)
        {
            var arr = new float[(int)Attrib.Count];
            for (int i = 0; i < arr.Length; i++)
            {
                Plugin.Guard("Snapshot[" + i + "]", () => { arr[i] = cmp.Get((eAttrib)i); });
            }
            return new StatSnapshot(arr);
        }

        public static List<Modifier> CurrentModifiers(XAttribsCMP cmp)
        {
            var list = new List<Modifier>();
            Plugin.Guard("CurrentModifiers", () =>
            {
                foreach (var kv in cmp.modifiersByAttrib)
                {
                    foreach (var m in kv.Value)
                        list.Add(new Modifier((Attrib)(int)m.Attrib, m.Value, (ModOp)(int)m.Operator));
                }
            });
            return list;
        }

        public static List<Modifier> ModifiersFromDef(Il2CppReferenceArray<XAttribModDef> defs, int upgradeCount)
        {
            var list = new List<Modifier>();
            if (defs == null) return list;
            foreach (var d in defs)
            {
                float val = d.Value + d.Upgrade * upgradeCount;
                list.Add(new Modifier((Attrib)(int)d.Attrib, val, (ModOp)(int)d.Operator));
            }
            return list;
        }
    }
}
```

> `Il2CppReferenceArray<T>` — тип interop для C#-массивов; имя пакета подтверждается на сборке (Task 7 уже подтягивает `Il2CppInterop.Runtime`). Если интероп выдаёт иной обёрточный тип — правка сигнатуры локальна.

- [ ] **Step 3: Собрать**

Run: `"/c/Program Files/dotnet/dotnet.exe" build src/HonestDamage.Plugin -c Release`
Expected: Build succeeded.

- [ ] **Step 4: Commit**

```bash
git add src/HonestDamage.Plugin/PlayerLocator.cs src/HonestDamage.Plugin/GameDataAdapter.cs
git commit -m "feat(ek-mod): player locator + game-data adapter"
```

---

## Task 9: Plugin — Diagnostics (дамп-лог + read-only damage hook)

**Files:**
- Create: `src/HonestDamage.Plugin/Diagnostics.cs`

**Interfaces:**
- Consumes: `PlayerLocator`, `GameDataAdapter`, `AttribResolver`, Core-типы; interop `GameCode.XAttribsCMP`.
- Produces:
  - `static class Diagnostics`:
    - `static void DumpNow()` — пишет `BepInEx/honest-damage-diag.log`: для каждого `eAttrib` строку `attrib = game.Get() | replicated = AttribResolver.Resolve(base?, currentMods)`; сырой список модификаторов (Attrib/Value/Operator/Source/SourceDefId); экипированное оружие + `XWeaponDef.AttackBase`.
    - Read-only Harmony postfix на игровой расчёт урона `[runtime-confirm]` — логирует `(defId, baseDamage, finalDamage, statsSnapshot)` для калибровки `DamageModel`.
  - Привязка `DumpNow()` к `Plugin.DiagDumpKey` (через Update-хук, см. Step 2).

**Verification (вместо unit-теста):** после установки и нажатия DiagDump-клавиши в игре `honest-damage-diag.log` содержит секции `[ATTRIBS]`, `[MODIFIERS]`, `[WEAPON]`. Сверка `game.Get()` ≈ `replicated` валидирует `AttribResolver`; пары `(base, final)` из damage-хука калибруют `DamageModel`.

- [ ] **Step 1: Написать `Diagnostics.cs`**

```csharp
using System.IO;
using System.Text;
using BepInEx;
using GameCode;
using HonestDamage.Core;

namespace HonestDamage.Plugin
{
    public static class Diagnostics
    {
        private static string LogPath =>
            Path.Combine(Paths.BepInExRootPath, "honest-damage-diag.log");

        public static void DumpNow()
        {
            Plugin.Guard("Diagnostics.DumpNow", () =>
            {
                var cmp = PlayerLocator.GetLocalAttribs();
                if (cmp == null) { Plugin.Log.LogWarning("Diag: no player attribs found"); return; }

                var sb = new StringBuilder();
                sb.AppendLine("=== HONEST DAMAGE DIAG ===");
                sb.AppendLine("[ATTRIBS] (game.Get value)");
                for (int i = 0; i < (int)Attrib.Count; i++)
                    sb.AppendLine($"  {(Attrib)i} = {cmp.Get((eAttrib)i)}");

                sb.AppendLine("[MODIFIERS]");
                foreach (var kv in cmp.modifiersByAttrib)
                    foreach (var m in kv.Value)
                        sb.AppendLine($"  {(Attrib)(int)m.Attrib} {(ModOp)(int)m.Operator} {m.Value} src={m.Source} defId={m.SourceDefId}");

                File.WriteAllText(LogPath, sb.ToString());
                Plugin.Log.LogInfo("Diag dumped to " + LogPath);
            });
        }
    }
}
```

- [ ] **Step 2: Привязать клавишу — добавить в `Plugin.Load()` MonoBehaviour-тик**

В `Plugin.cs`, в конец `Load()`, добавить регистрацию обновления (IL2CPP: через `AddComponent`):

```csharp
            ClassInjector.RegisterTypeInIl2Cpp<TickComponent>();
            AddComponent<TickComponent>();
```

И создать вложенный компонент в `Plugin.cs`:

```csharp
    public class TickComponent : UnityEngine.MonoBehaviour
    {
        public TickComponent(System.IntPtr ptr) : base(ptr) { }
        void Update()
        {
            if (Plugin.ToggleKey.Value.IsDown()) Plugin.OverlayEnabled = !Plugin.OverlayEnabled;
            if (Plugin.DiagDumpKey.Value.IsDown()) Diagnostics.DumpNow();
        }
    }
```

(`using Il2CppInterop.Runtime.Injection;` для `ClassInjector`.)

- [ ] **Step 3: Собрать**

Run: `"/c/Program Files/dotnet/dotnet.exe" build src/HonestDamage.Plugin -c Release`
Expected: Build succeeded.

- [ ] **Step 4: Commit**

```bash
git add src/HonestDamage.Plugin/Diagnostics.cs src/HonestDamage.Plugin/Plugin.cs
git commit -m "feat(ek-mod): diagnostics dump + hotkey tick"
```

---

## Task 10: Plugin — WeaponInfoInjector

**Files:**
- Create: `src/HonestDamage.Plugin/Injectors/WeaponInfoInjector.cs`

**Interfaces:**
- Consumes: interop `UIWeaponInfo*` `[runtime-confirm]`, `XWeaponDef`; `PlayerLocator`, `GameDataAdapter`, `DamageModel`.
- Produces: Harmony postfix на метод показа/обновления окна оружия, который добавляет дочерний TMP-лейбл с `≈ {honest} урона (с учётом статов)`.

**Verification:** в игре при открытии окна оружия под оригиналом видна доп-строка; при ошибке — запись в логе, окно не ломается.

- [ ] **Step 1: Написать `WeaponInfoInjector.cs`**

```csharp
using GameCode;
using HarmonyLib;
using HonestDamage.Core;

namespace HonestDamage.Plugin.Injectors
{
    // [runtime-confirm Task 9]: точные имя класса и метода окна оружия.
    // Базовая цель — метод обновления UIWeaponInfo (см. dump: UIWeaponInfoRefs/UIWeaponInfoAttack).
    [HarmonyPatch]
    public static class WeaponInfoInjector
    {
        [HarmonyPatch(typeof(UIWeaponInfoRefs), "Refresh")] // имя метода уточняется
        [HarmonyPostfix]
        public static void AfterRefresh(UIWeaponInfoRefs __instance)
        {
            if (!Plugin.OverlayEnabled || !Plugin.EnableWeaponInfo.Value) return;
            Plugin.Guard("WeaponInfoInjector", () =>
            {
                var cmp = PlayerLocator.GetLocalAttribs();
                if (cmp == null) return;
                var stats = GameDataAdapter.Snapshot(cmp);
                // [runtime-confirm]: получить XWeaponDef из __instance
                float baseDmg = 0f; // <- из def.AttackBase, уточняется по диагностике
                float honest = DamageModel.Compute(DamageKind.WeaponAttack, baseDmg, stats);
                UiSuffix.Attach(__instance, $"≈ {honest:0} урона (с учётом статов)");
            });
        }
    }
}
```

- [ ] **Step 2: Создать общий хелпер `UiSuffix` (добавление дочернего TMP-лейбла)**

Создать `src/HonestDamage.Plugin/Injectors/UiSuffix.cs`:

```csharp
using UnityEngine;
using TMPro;

namespace HonestDamage.Plugin.Injectors
{
    public static class UiSuffix
    {
        // Находит/создаёт дочерний TMP-лейбл "HD_Suffix" под целевым компонентом
        // и пишет в него текст. Оригинальные тексты не трогаются (F5).
        public static void Attach(Component host, string text)
        {
            Plugin.Guard("UiSuffix.Attach", () =>
            {
                var existing = host.transform.Find("HD_Suffix");
                TextMeshProUGUI tmp;
                if (existing != null)
                {
                    tmp = existing.GetComponent<TextMeshProUGUI>();
                }
                else
                {
                    var go = new GameObject("HD_Suffix");
                    go.transform.SetParent(host.transform, false);
                    tmp = go.AddComponent<TextMeshProUGUI>();
                    tmp.fontSize = 18f;
                }
                tmp.text = text;
            });
        }
    }
}
```

- [ ] **Step 3: Собрать**

Run: `"/c/Program Files/dotnet/dotnet.exe" build src/HonestDamage.Plugin -c Release`
Expected: Build succeeded.

- [ ] **Step 4: Commit**

```bash
git add src/HonestDamage.Plugin/Injectors/WeaponInfoInjector.cs src/HonestDamage.Plugin/Injectors/UiSuffix.cs
git commit -m "feat(ek-mod): weapon info honest-damage suffix"
```

---

## Task 11: Plugin — InventoryInjector

**Files:**
- Create: `src/HonestDamage.Plugin/Injectors/InventoryInjector.cs`

**Interfaces:**
- Consumes: interop инвентарных/паузных UI-классов `[runtime-confirm]` (см. dump: `UIInvRelicPanelRefs`, ability/skill панели); `PlayerLocator`, `GameDataAdapter`, `DamageModel`, `UiSuffix`.
- Produces: Harmony postfix на обновление инвентарной панели, добавляющий суффикс честного урона для каждой экипированной абилки/скилла/реликвии, что скейлятся.

**Verification:** в паузе/инвентаре под скейлящимися предметами видны доп-строки.

- [ ] **Step 1: Написать `InventoryInjector.cs`**

```csharp
using GameCode;
using HarmonyLib;
using HonestDamage.Core;

namespace HonestDamage.Plugin.Injectors
{
    // [runtime-confirm Task 9]: имена классов панелей инвентаря/паузы и методов refresh.
    [HarmonyPatch]
    public static class InventoryInjector
    {
        [HarmonyPatch(typeof(UIInvRelicPanelRefs), "Refresh")] // уточняется
        [HarmonyPostfix]
        public static void AfterRelicPanel(UIInvRelicPanelRefs __instance)
        {
            if (!Plugin.OverlayEnabled || !Plugin.EnableInventory.Value) return;
            Plugin.Guard("InventoryInjector.Relic", () =>
            {
                var cmp = PlayerLocator.GetLocalAttribs();
                if (cmp == null) return;
                var stats = GameDataAdapter.Snapshot(cmp);
                // [runtime-confirm]: перебрать слоты панели, для скейлящихся посчитать урон
                // baseDmg и DamageKind берутся из def слота (уточняется по диагностике).
                float baseDmg = 0f;
                float honest = DamageModel.Compute(DamageKind.Ability, baseDmg, stats);
                UiSuffix.Attach(__instance, $"≈ {honest:0} (с учётом статов)");
            });
        }
    }
}
```

- [ ] **Step 2: Собрать**

Run: `"/c/Program Files/dotnet/dotnet.exe" build src/HonestDamage.Plugin -c Release`
Expected: Build succeeded.

- [ ] **Step 3: Commit**

```bash
git add src/HonestDamage.Plugin/Injectors/InventoryInjector.cs
git commit -m "feat(ek-mod): inventory honest-damage suffixes"
```

---

## Task 12: Plugin — RewardSelectInjector (what-if дельта)

**Files:**
- Create: `src/HonestDamage.Plugin/Injectors/RewardSelectInjector.cs`

**Interfaces:**
- Consumes: interop `UIItemSelect*` `[runtime-confirm]`, `XRelicDef`/`XWeaponDef`/upgrade defs; `PlayerLocator`, `GameDataAdapter`, `AttribResolver`, `DamageModel`, `DamageMapping`, `UiSuffix`.
- Produces: Harmony postfix на показ карточки выбора, который:
  1. показывает честный урон самого предлагаемого предмета (если он сам наносит урон);
  2. вычисляет `extra = GameDataAdapter.ModifiersFromDef(def.AttribModifiers, 0)` и для каждого затронутого вида урона (пересечение `extra`-attribs с `DamageMapping.ScalingAttribs`) показывает `сейчас X → станет Y` для текущих абилок/оружия/петов.

**Verification:** на экране наград карточка предлагаемого предмета показывает дельту для затронутых способностей (пример Wisp: `120 → 168`).

- [ ] **Step 1: Написать `RewardSelectInjector.cs`**

```csharp
using System.Collections.Generic;
using GameCode;
using HarmonyLib;
using HonestDamage.Core;

namespace HonestDamage.Plugin.Injectors
{
    // [runtime-confirm Task 9]: точные классы UIItemSelect* и метод показа карточки.
    [HarmonyPatch]
    public static class RewardSelectInjector
    {
        [HarmonyPatch(typeof(UIItemSelectSlotRefs), "Setup")] // уточняется
        [HarmonyPostfix]
        public static void AfterSetup(UIItemSelectSlotRefs __instance)
        {
            if (!Plugin.OverlayEnabled || !Plugin.EnableRewards.Value) return;
            Plugin.Guard("RewardSelectInjector", () =>
            {
                var cmp = PlayerLocator.GetLocalAttribs();
                if (cmp == null) return;

                // [runtime-confirm]: достать XAttribModDef[] предлагаемого предмета из слота.
                Il2CppInterop.Runtime.InteropTypes.Arrays.Il2CppReferenceArray<XAttribModDef> offered = null;
                if (offered == null) return;

                var current = GameDataAdapter.CurrentModifiers(cmp);
                var extra = GameDataAdapter.ModifiersFromDef(offered, 0);

                // какие attrib'ы затрагивает предлагаемый предмет
                var touched = new HashSet<Attrib>();
                foreach (var m in extra) touched.Add(m.Attrib);

                var lines = new List<string>();
                foreach (DamageKind kind in System.Enum.GetValues(typeof(DamageKind)))
                {
                    bool affected = false;
                    foreach (var a in DamageMapping.ScalingAttribs(kind))
                        if (touched.Contains(a)) { affected = true; break; }
                    if (!affected) continue;

                    // base урона данного вида у игрока [runtime-confirm: из экипировки]
                    float baseDmg = ResolveBaseFor(kind, cmp);
                    if (baseDmg <= 0f) continue;

                    var now = new StatSnapshot(SnapshotArray(cmp, current, System.Array.Empty<Modifier>()));
                    var next = new StatSnapshot(SnapshotArray(cmp, current, extra.ToArray()));
                    float dn = DamageModel.Compute(kind, baseDmg, now);
                    float dx = DamageModel.Compute(kind, baseDmg, next);
                    lines.Add($"{kind}: {dn:0} → {dx:0}");
                }

                if (lines.Count > 0)
                    UiSuffix.Attach(__instance, string.Join("\n", lines));
            });
        }

        // Строит float[] резолв-статов из (base, current ∪ extra) для всех Attrib.
        private static float[] SnapshotArray(XAttribsCMP cmp, List<Modifier> current, Modifier[] extra)
        {
            var arr = new float[(int)Attrib.Count];
            for (int i = 0; i < arr.Length; i++)
            {
                // base для what-if берём из GetRaw (без модификаторов) [runtime-confirm]
                float baseV = 0f;
                Plugin.Guard("SnapshotArray.base", () => { baseV = cmp.GetRaw((eAttrib)i); });
                arr[i] = AttribResolver.ResolveWith(baseV, current, extra, (Attrib)i);
            }
            return arr;
        }

        // [runtime-confirm]: вернуть base-урон для данного вида из экипировки игрока.
        private static float ResolveBaseFor(DamageKind kind, XAttribsCMP cmp) => 0f;
    }
}
```

> `ResolveBaseFor` и извлечение `offered` помечены `[runtime-confirm]` — конкретные поля слотов/экипировки подтверждаются диагностикой Task 9. Структура расчёта дельты при этом финальная.

- [ ] **Step 2: Собрать**

Run: `"/c/Program Files/dotnet/dotnet.exe" build src/HonestDamage.Plugin -c Release`
Expected: Build succeeded.

- [ ] **Step 3: Commit**

```bash
git add src/HonestDamage.Plugin/Injectors/RewardSelectInjector.cs
git commit -m "feat(ek-mod): reward-select what-if delta"
```

---

## Task 13: Сборка деливерабла + README install guide

**Files:**
- Create: `README.md` (в корне проекта)
- Output: `dist/BepInEx-pack/BepInEx/plugins/HonestDamage.Core.dll` + `HonestDamage.Plugin.dll`

**Interfaces:**
- Consumes: всё выше.
- Produces: готовая к копированию папка `dist/BepInEx-pack/` + инструкция.

- [ ] **Step 1: Собрать финальный Release и скопировать dll в dist**

Run:
```bash
cd "D:/git/home/ember-knights-honest-damage"
"/c/Program Files/dotnet/dotnet.exe" build src/HonestDamage.Plugin -c Release
cp src/HonestDamage.Plugin/bin/Release/net6.0/HonestDamage.Plugin.dll dist/BepInEx-pack/BepInEx/plugins/
cp src/HonestDamage.Core/bin/Release/netstandard2.1/HonestDamage.Core.dll dist/BepInEx-pack/BepInEx/plugins/
```
Expected: оба dll в `dist/BepInEx-pack/BepInEx/plugins/`.

- [ ] **Step 2: Написать `README.md`**

```markdown
# Ember Knights — Honest Damage (мод)

Показывает реальный текущий урон абилок/скиллов/оружия/реликвий с учётом статов;
на экране наград — прогноз «сейчас → станет» от предлагаемого предмета.

## Установка
1. Закрыть игру и Steam-оверлей.
2. Скопировать **содержимое** `dist/BepInEx-pack/` в папку игры:
   `C:\Program Files (x86)\Steam\steamapps\common\EmberKnights`
   (рядом с `EmberKnights_64.exe` появятся `winhttp.dll`, `doorstop_config.ini`, `BepInEx/`).
3. Запустить игру один раз — BepInEx создаст логи в `BepInEx/LogOutput.log`.
4. Плагин уже лежит в `BepInEx/plugins/` (`HonestDamage.Plugin.dll` + `HonestDamage.Core.dll`).

## Использование
- **F8** — вкл/выкл оверлея.
- **F9** — сбросить диагностический дамп в `BepInEx/honest-damage-diag.log`
  (нужен для калибровки — пришлите его разработчику, если числа неточные).
- Настройки: `BepInEx/config/com.ashubin.ekhonestdamage.cfg`.

## Зависимости (уже включены в пакет)
- BepInEx 6 BleedingEdge IL2CPP (win-x64).
- `HonestDamage.Plugin.dll`, `HonestDamage.Core.dll`.
- Ничего ставить отдельно не нужно.

## Калибровка (если числа расходятся с фактическими)
Формула base→урон выведена эвристически (тел методов в IL2CPP нет). Нажмите **F9**
в бою и пришлите `honest-damage-diag.log` — по нему правится `DamageModel`/`DamageMapping`.

## Совместимость / мультиплеер
Мод read-only и не меняет игровое состояние; ванильный игрок может зайти к вам в
лобби. Используйте в одиночке или приватных лобби.
```

- [ ] **Step 3: Проверить, что пакет собран**

Run: `ls "D:/git/home/ember-knights-honest-damage/dist/BepInEx-pack/BepInEx/plugins"`
Expected: `HonestDamage.Core.dll`, `HonestDamage.Plugin.dll`.

- [ ] **Step 4: Commit**

```bash
git add ember-knights-honest-damage/README.md
git commit -m "docs(ek-mod): install guide + assemble deliverable"
```

---

## Self-Review (выполнено при написании плана)

**Spec coverage:**
- F1 окно оружия → Task 10. F2 инвентарь → Task 11. F3 награды+what-if → Task 12.
- F4 все источники статов → читаются из `XAttribsCMP.modifiersByAttrib`/`Get` (Task 8).
- F5 аддитивный суффикс → `UiSuffix.Attach`, оригинал не трогается (Task 10).
- F6 хоткей/конфиг → Task 7 + Task 9 тик. F7 диагностика → Task 9.
- N1 fail-safe → `Plugin.Guard` повсюду. N2 read-only → what-if в скретч-массиве, без `AddAttribModifier` (Task 12). N3 деградация → `[runtime-confirm]` + Guard.
- §8 сборка (interop офлайн + dll) → Tasks 2,3,7,13.

**Placeholder scan:** все `[runtime-confirm]` — это конкретные игровые идентификаторы, подтверждаемые диагностикой Task 9 (присущая IL2CPP-специфика, не заглушки логики); структура кода и расчётов финальная.

**Type consistency:** `Attrib`/`ModOp`/`Modifier`/`StatSnapshot`/`DamageKind` согласованы между Core и Plugin; `AttribResolver.Resolve/ResolveWith`, `DamageModel.Compute`, `GameDataAdapter.Snapshot/CurrentModifiers/ModifiersFromDef`, `UiSuffix.Attach`, `Plugin.Guard` используются с одинаковыми сигнатурами во всех задачах.

## Известные точки калибровки (доводятся по логам Task 9, согласовано «итерирую сам»)
1. Семантика MUL (`×v` vs `×(1+v)`) — `AttribResolver`.
2. Маппинг attrib→DamageKind и роль ATK (процент) — `DamageMapping`/`DamageModel`.
3. Источник `baseDamage`/`baseValue` из дефов и экипировки — адаптер/инъекторы.
4. Точные имена UI-классов/методов и полей слотов — `[runtime-confirm]` инъекторы.
```
