# GameSpeedUnlocked — Farthest Frontier

MelonLoader mod that adds **x5** and **x10** game speeds to Farthest Frontier, which
normally caps out at x3.

Built and tested against **Farthest Frontier v1.0.6b** (IL2CPP, Unity 2022.3.62f3)
with **MelonLoader v0.7.3** (net6 runtime).

## Installing

The mod is a single DLL. Drop it into the game's `Mods` folder:

```
C:\games\Farthest Frontier\Mods\GameSpeedUnlocked.dll
```

To rebuild and deploy in one step:

```powershell
.\build.ps1                                    # defaults to C:\games\Farthest Frontier
.\build.ps1 -GameDir "D:\...\Farthest Frontier"
.\build.ps1 -NoDeploy                          # build only
```

The build references assemblies straight out of the game folder, so MelonLoader must
have run at least once to generate `MelonLoader\Il2CppAssemblies\`.

## Using it

No new keys or UI. The existing speed controls just go further:

- the **+ / −** speed buttons in the bottom bar,
- the game's own speed hotkeys.

The speed readout shows `5x` and `10x` as normal, so the cycle becomes
`½x → 1x → 2x → 3x → 5x → 10x`.

Note that the game's "slow down when attacked" options still snap you back to 1x
during a raid or animal attack. That is vanilla behaviour and is left alone.

## Configuration

First launch writes `UserData/GameSpeedUnlocked.cfg` in the game folder:

```toml
[GameSpeedUnlocked]
ExtraSpeeds = "5, 10"
ScaleFixedDeltaTime = false
```

**`ExtraSpeeds`** — the speeds to unlock, comma separated. The fastest one listed becomes
the new maximum, so `"5, 10"` gives `½x, 1x, 2x, 3x, 5x, 10x` and `"5"` stops at x5. A
value the game does not already have is appended to its speed array, so `"5, 10, 20"`
does work.

One cosmetic caveat: the game formats the speed label as a whole number, so a
fractional speed like `7.5` still displays as `8x` even though it runs at 7.5x.

**`ScaleFixedDeltaTime`** — off by default, which keeps vanilla physics. Turning it on
keeps the number of physics steps per real-world second constant instead of letting it
grow with the time scale, which noticeably reduces CPU cost at x10. The trade-off is
coarser physics stepping for the few things that use `FixedUpdate` — projectiles,
horses, dogs — so arrows may be less accurate. Core simulation (villagers, production,
the calendar) runs on `Update` and is unaffected either way.

## Expect x10 to be CPU-bound

x10 asks the simulation to do ten times the work per real second. On a large town you
will hit a point where the frame rate drops and the town no longer actually advances ten
times faster — that is the CPU, not a bug in the mod. `ScaleFixedDeltaTime = true` buys
back some headroom.

## How it works

**x5 and x10 already exist in the game.** They are not added by this mod — they ship in
`TimeManager.timeScales` and are simply unreachable. Confirmed at runtime:

```
[GameSpeedUnlocked] Game's own speeds: 0.5x, 1x, 2x, 3x, 5x, 10x
[GameSpeedUnlocked] Top speed unlocked: 10x (index 5).
```

That is worth stressing because the decompiled source is misleading. The field's *code*
default only has four entries:

```csharp
// TimeManager
public float[] timeScales = new float[4] { 0.5f, 1f, 2f, 3f };
public uint timeScaleIndex = 1u;

public float GetTimeScale() => timeScales[timeScaleIndex];
```

But it is a serialized `public float[]`, so the real runtime value comes from the scene,
and the scene ships six entries. The actual gate is the settings cap:

```csharp
public void SetTimeScale(uint index, bool allowNonVisible = false)
{
    if (!forceTimeScale && index >= 0 && index < timeScales.Length
        && (allowNonVisible || index <= UnitySingletonPersistent<SettingsManager>.Instance.maxGameSpeed))
    { ... }
}
```

`SettingsManager.maxGameSpeed` is 3 by default, and the in-game "max speed" toggle only
raises it to 4 — enough to reach index 4 (x5) but never index 5 (x10). So the mod's real
job is lifting that cap to the index of the fastest requested speed:

| Patch | Purpose |
| --- | --- |
| `SettingsManager.get_maxGameSpeed` (postfix) | Reports the cap as the new top index. |
| `TimeManager.Awake` (postfix) | Reads the speed array, works out that index. |
| `TimeManager.GetTimeScale` / `SetTimeScale` / `IncreaseTimeScale` (prefixes) | Same, from managed call sites. |
| `TimeManager.UpdateTimeScale` (postfix) | Applies optional `fixedDeltaTime` scaling. |

The cap is also written directly to `SettingsManager.maxGameSpeed` once per session, so
the feature survives even if the getter patch stops applying on a future version.

The mod still appends any requested speed the array lacks (`ExtraSpeeds = "5, 10, 20"`
would add 20x), appending only above the current maximum — inserting in the middle would
shift every index, and `timeScaleIndex` is a plain index into this array. Conversely it
never unlocks speeds *beyond* the fastest one requested, so the extra entries the game
hides stay hidden unless you ask for them.

Nothing else in the game hardcodes an assumption about the maximum speed — every other
reader of `Time.timeScale` either compares it against zero or divides it back out, and
the pause path restores it via `GetTimeScale()`.

## Two notes for anyone modding this game

Both cost real debugging time here.

**MelonLoader hides broken patches.** Its automatic `PatchAll` runs through
`MelonUtils.TryPatchAll`, which wraps the work in a bare `catch { }`:

```csharp
public static List<MethodInfo> TryPatchAll(this Harmony harmony, Type type, bool allowUnannotatedType)
{
    try { return harmony.CreateClassProcessor(type, allowUnannotatedType).Patch(); }
    catch { }
    return null;
}
```

A patch that never applies is therefore indistinguishable from one that works. This mod
applies its patches explicitly instead, logging each failure, and declares
`[assembly: HarmonyDontPatchAll]` so the automatic pass does not double up.

**The log lags a long way behind.** On this machine the game takes ~3.5 minutes to reach
the main menu with mods loaded, and MelonLoader's log can sit unflushed for minutes.
An empty log is not evidence that a hook did not fire — wait for it.

## Layout

```
build.ps1                                 build + deploy
src/GameSpeedUnlocked/
  GameSpeedUnlocked.csproj                references assemblies from the game folder
  GameSpeedMod.cs                         the whole mod
```
