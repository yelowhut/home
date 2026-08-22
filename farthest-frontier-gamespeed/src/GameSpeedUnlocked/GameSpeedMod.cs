using System;
using System.Collections.Generic;
using System.Globalization;
using System.Reflection;
using System.Text;
using HarmonyLib;
using Il2Cpp;
using Il2CppInterop.Runtime;
using Il2CppInterop.Runtime.InteropTypes;
using Il2CppInterop.Runtime.InteropTypes.Arrays;
using MelonLoader;
using UnityEngine;

[assembly: MelonInfo(typeof(FarthestFrontier.GameSpeed.GameSpeedMod), "GameSpeedUnlocked", "1.2.0", "yelow")]
[assembly: MelonGame("Crate Entertainment", "Farthest Frontier")]

// Patches are applied explicitly in ApplyPatches() so that failures get logged.
// MelonLoader's automatic PatchAll swallows every patch exception in a bare catch,
// which makes a broken patch indistinguishable from a working one.
[assembly: HarmonyDontPatchAll]

namespace FarthestFrontier.GameSpeed;

/// <summary>
/// Adds higher game speeds (x5 / x10 by default) to Farthest Frontier.
///
/// The game keeps its selectable speeds in <c>TimeManager.timeScales</c> (vanilla:
/// 0.5, 1, 2, 3) and picks one by index. Two things cap the reachable index: the array
/// length, and <c>SettingsManager.maxGameSpeed</c>. This mod appends the extra speeds to
/// the array and lifts the settings cap to match, so the existing speed buttons and
/// hotkeys reach them without any new UI.
///
/// Both halves are done twice over, by independent means: through Harmony patches, and
/// through a polling fallback that touches the live objects directly. The fallback alone
/// is enough to make the mod work, so a Harmony patch that fails to apply cannot break it.
/// </summary>
public class GameSpeedMod : MelonMod
{
    private const string CategoryId = "GameSpeedUnlocked";
    private const float Epsilon = 0.0001f;

    /// <summary>How often the fallback re-asserts the speeds, in frames.</summary>
    private const int RecheckInterval = 120;

    private static MelonPreferences_Entry<string> _extraSpeedsEntry;
    private static MelonPreferences_Entry<bool> _scaleFixedDeltaTimeEntry;

    private static float[] _extraSpeeds = Array.Empty<float>();

    /// <summary>Highest index reachable once the speeds are installed; -1 until then.</summary>
    private static int _topIndex = -1;

    private static float _baseFixedDeltaTime;
    private static bool _baseFixedDeltaTimeCaptured;

    /// <summary>Native pointer of the TimeManager the speeds are already installed on.</summary>
    private static IntPtr _installedOn = IntPtr.Zero;

    /// <summary>Captured from the getter patch, so the cap can also be raised directly.</summary>
    private static SettingsManager _settings;

    private static int _frameGate;
    private static bool _loggedMissingTimeManager;
    private static bool _loggedCapPatch;
    private static bool _capRaised;

    public override void OnInitializeMelon()
    {
        MelonPreferences_Category category = MelonPreferences.CreateCategory(CategoryId, "Game Speed Unlocked");
        category.SetFilePath("UserData/GameSpeedUnlocked.cfg");

        _extraSpeedsEntry = category.CreateEntry(
            "ExtraSpeeds",
            "5, 10",
            description: "Extra game speeds, comma separated. Only values above the game's own maximum (3x) are added.");
        _scaleFixedDeltaTimeEntry = category.CreateEntry(
            "ScaleFixedDeltaTime",
            false,
            description: "Scale Time.fixedDeltaTime with the game speed. Much cheaper physics at 5x/10x, "
                       + "but arrows and animals get less precise. Leave false for vanilla physics.");
        category.SaveToFile(false);

        _extraSpeeds = ParseSpeeds(_extraSpeedsEntry.Value);
        if (_extraSpeeds.Length == 0)
        {
            MelonLogger.Warning(
                $"No usable speeds in ExtraSpeeds (\"{_extraSpeedsEntry.Value}\") - the mod will not change anything.");
            return;
        }

        MelonLogger.Msg($"Extra speeds requested: {FormatSpeeds(_extraSpeeds)}");
        ApplyPatches();
    }

    // ---------------------------------------------------------------- patching

    private void ApplyPatches()
    {
        // Installs the speeds as early as possible, and re-installs on scene reload.
        TryPatch(typeof(TimeManager), "Awake", postfix: nameof(InstallPostfix));

        // Belt and braces: these are called from managed code, so they still land even if
        // hooking a natively-invoked Unity message like Awake does not work.
        TryPatch(typeof(TimeManager), "GetTimeScale", prefix: nameof(InstallPrefix));
        TryPatch(typeof(TimeManager), "IncreaseTimeScale", prefix: nameof(InstallPrefix));
        TryPatch(typeof(TimeManager), "SetTimeScale", prefix: nameof(InstallPrefix));

        // Lifts the settings cap that would otherwise hide the new speeds.
        TryPatch(typeof(SettingsManager), "get_maxGameSpeed", postfix: nameof(MaxGameSpeedPostfix));

        // Applies the optional physics-step scaling whenever the speed changes.
        TryPatch(typeof(TimeManager), "UpdateTimeScale", postfix: nameof(UpdateTimeScalePostfix));

        int applied = 0;
        foreach (MethodBase _ in HarmonyInstance.GetPatchedMethods())
        {
            applied++;
        }

        if (applied == 0)
        {
            MelonLogger.Warning("No Harmony patch applied - falling back to polling, which handles this on its own.");
        }
    }

    private void TryPatch(Type type, string methodName, string prefix = null, string postfix = null)
    {
        try
        {
            MethodInfo target = AccessTools.Method(type, methodName);
            if (target == null)
            {
                MelonLogger.Error($"Patch target not found: {type.Name}.{methodName}");
                return;
            }

            HarmonyInstance.Patch(
                target,
                prefix == null ? null : new HarmonyMethod(AccessTools.Method(typeof(GameSpeedMod), prefix)),
                postfix == null ? null : new HarmonyMethod(AccessTools.Method(typeof(GameSpeedMod), postfix)));
        }
        catch (Exception ex)
        {
            MelonLogger.Error($"Could not patch {type.Name}.{methodName}: {ex.Message}");
        }
    }

    public static void InstallPostfix(TimeManager __instance) => InstallSpeeds(__instance);

    public static void InstallPrefix(TimeManager __instance) => InstallSpeeds(__instance);

    public static void MaxGameSpeedPostfix(SettingsManager __instance, ref int __result)
    {
        _settings = __instance;

        if (_topIndex <= __result)
        {
            return;
        }

        if (!_loggedCapPatch)
        {
            _loggedCapPatch = true;
            MelonLogger.Msg($"Raising the speed cap from {__result} to {_topIndex}.");
        }

        __result = _topIndex;
    }

    public static void UpdateTimeScalePostfix(TimeManager __instance) => ApplyFixedDeltaTime(__instance);

    // ---------------------------------------------------------------- fallback

    /// <summary>
    /// Re-asserts the speeds against the live objects. This needs no Harmony patch to
    /// work, so it is what actually guarantees the mod functions.
    /// </summary>
    public override void OnUpdate()
    {
        if (_extraSpeeds.Length == 0 || ++_frameGate < RecheckInterval)
        {
            return;
        }

        _frameGate = 0;

        TimeManager timeManager = Find<TimeManager>();
        if (timeManager == null)
        {
            if (!_loggedMissingTimeManager)
            {
                _loggedMissingTimeManager = true;
                MelonLogger.Msg("Waiting for a TimeManager (no game loaded yet).");
            }

            return;
        }

        _loggedMissingTimeManager = false;
        InstallSpeeds(timeManager);
    }

    /// <summary>
    /// Raises <c>SettingsManager.maxGameSpeed</c> directly, in case the patch on its
    /// getter never applied. Harmless if the mod is later removed: vanilla is still
    /// bounded by the length of its own (short) speed array.
    /// </summary>
    private static void RaiseSettingsCap()
    {
        if (_capRaised || _topIndex < 0)
        {
            return;
        }

        SettingsManager settings = _settings != null ? _settings : Find<SettingsManager>();
        if (settings == null)
        {
            return;
        }

        // The getter is patched, so its current value cannot be read back meaningfully -
        // just write the value once. The setter itself no-ops when it already matches.
        try
        {
            settings.maxGameSpeed = _topIndex;
            _capRaised = true;
            MelonLogger.Msg($"SettingsManager.maxGameSpeed set to {_topIndex}.");
        }
        catch (Exception ex)
        {
            MelonLogger.Error($"Could not set maxGameSpeed: {ex.Message}");
        }
    }

    /// <summary>
    /// Finds a live instance without the generic <c>FindObjectOfType&lt;T&gt;()</c>:
    /// IL2CPP only keeps generic instantiations the game itself uses, so the generic
    /// overload is not guaranteed to exist at runtime. The <c>Type</c> overload always is.
    /// </summary>
    private static T Find<T>() where T : Il2CppObjectBase
    {
        try
        {
            UnityEngine.Object found = UnityEngine.Object.FindObjectOfType(Il2CppType.Of<T>());
            return found == null ? null : found.TryCast<T>();
        }
        catch (Exception ex)
        {
            MelonLogger.Error($"Could not look up {typeof(T).Name}: {ex.Message}");
            return null;
        }
    }

    // ---------------------------------------------------------------- the work

    /// <summary>
    /// Appends the configured speeds to <c>TimeManager.timeScales</c>. Cheap to call
    /// repeatedly: it returns immediately once the speeds are in place on this instance.
    /// </summary>
    private static void InstallSpeeds(TimeManager timeManager)
    {
        if (timeManager == null || _extraSpeeds.Length == 0 || timeManager.Pointer == _installedOn)
        {
            return;
        }

        Il2CppStructArray<float> current = timeManager.timeScales;
        if (current == null || current.Length == 0)
        {
            MelonLogger.Warning("TimeManager.timeScales is empty - leaving it alone.");
            return;
        }

        List<float> scales = new List<float>(current.Length + _extraSpeeds.Length);
        for (int i = 0; i < current.Length; i++)
        {
            scales.Add(current[i]);
        }

        MelonLogger.Msg($"Game's own speeds: {FormatSpeeds(scales)}");

        bool changed = false;
        foreach (float speed in _extraSpeeds)
        {
            // Only append above the maximum: inserting in the middle would shift every
            // index, and timeScaleIndex is a plain index into this array.
            if (speed <= scales[scales.Count - 1] + Epsilon)
            {
                continue;
            }

            scales.Add(speed);
            changed = true;
        }

        _installedOn = timeManager.Pointer;

        // Unlock up to the fastest speed actually asked for, no further. The game ships
        // more speeds in this array than its UI ever exposes, and unlocking all of them
        // would hand out speeds nobody requested.
        float fastestRequested = _extraSpeeds[_extraSpeeds.Length - 1];
        _topIndex = 0;
        for (int i = 0; i < scales.Count; i++)
        {
            if (scales[i] <= fastestRequested + Epsilon)
            {
                _topIndex = i;
            }
        }

        if (changed)
        {
            timeManager.timeScales = new Il2CppStructArray<float>(scales.ToArray());
            MelonLogger.Msg($"Added the missing speeds - now: {FormatSpeeds(scales)}");
        }

        MelonLogger.Msg(
            $"Top speed unlocked: {scales[_topIndex].ToString("0.##", CultureInfo.InvariantCulture)}x (index {_topIndex}).");

        RaiseSettingsCap();
    }

    /// <summary>
    /// Keeps the number of physics steps per real-world second constant as the game
    /// speed rises, instead of letting it grow with the time scale.
    /// </summary>
    private static void ApplyFixedDeltaTime(TimeManager timeManager)
    {
        if (timeManager == null)
        {
            return;
        }

        if (!_baseFixedDeltaTimeCaptured)
        {
            _baseFixedDeltaTime = Time.fixedDeltaTime;
            _baseFixedDeltaTimeCaptured = true;
        }

        if (_scaleFixedDeltaTimeEntry == null || !_scaleFixedDeltaTimeEntry.Value)
        {
            // Restore vanilla stepping if the setting was turned off mid-session.
            if (Math.Abs(Time.fixedDeltaTime - _baseFixedDeltaTime) > Epsilon)
            {
                Time.fixedDeltaTime = _baseFixedDeltaTime;
            }

            return;
        }

        Time.fixedDeltaTime = _baseFixedDeltaTime * Math.Max(1f, timeManager.GetTimeScale());
    }

    // ---------------------------------------------------------------- helpers

    private static float[] ParseSpeeds(string raw)
    {
        if (string.IsNullOrWhiteSpace(raw))
        {
            return Array.Empty<float>();
        }

        string[] tokens = raw.Split(new[] { ',', ';', ' ', '\t' }, StringSplitOptions.RemoveEmptyEntries);
        List<float> speeds = new List<float>(tokens.Length);

        foreach (string token in tokens)
        {
            // Accept both "7.5" and "7,5" style decimals by normalising the separator.
            string normalised = token.Trim().Replace(',', '.');
            if (!float.TryParse(normalised, NumberStyles.Float, CultureInfo.InvariantCulture, out float speed))
            {
                MelonLogger.Warning($"Ignoring unparsable speed \"{token}\" in ExtraSpeeds.");
                continue;
            }

            if (speed <= 0f)
            {
                MelonLogger.Warning($"Ignoring non-positive speed \"{token}\" in ExtraSpeeds.");
                continue;
            }

            speeds.Add(speed);
        }

        speeds.Sort();

        // Drop duplicates so the array stays strictly ascending.
        List<float> unique = new List<float>(speeds.Count);
        foreach (float speed in speeds)
        {
            if (unique.Count == 0 || speed > unique[unique.Count - 1] + Epsilon)
            {
                unique.Add(speed);
            }
        }

        return unique.ToArray();
    }

    private static string FormatSpeeds(IReadOnlyList<float> speeds)
    {
        StringBuilder builder = new StringBuilder();
        for (int i = 0; i < speeds.Count; i++)
        {
            if (i > 0)
            {
                builder.Append(", ");
            }

            builder.Append(speeds[i].ToString("0.##", CultureInfo.InvariantCulture)).Append('x');
        }

        return builder.ToString();
    }
}
