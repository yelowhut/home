using System;
using BepInEx;
using BepInEx.Configuration;
using BepInEx.Logging;
using BepInEx.Unity.IL2CPP;
using HarmonyLib;
using Il2CppInterop.Runtime.Injection;
using UnityEngine;

namespace HonestDamage.Plugin
{
    [BepInPlugin("com.ashubin.ekhonestdamage", "Ember Knights Honest Damage", "0.1.0")]
    public class Plugin : BasePlugin
    {
        // BepInEx 6.0.0-pre.2 ships without KeyboardShortcut in BepInEx.Core.
        // We use KeyCode string config and poll via Unity Input in TickComponent.
        public new static ManualLogSource Log = null!;
        public static bool OverlayEnabled = true;

        public static ConfigEntry<string> ToggleKeyName = null!;
        public static ConfigEntry<string> DiagDumpKeyName = null!;
        public static ConfigEntry<bool> EnableWeaponInfo = null!;
        public static ConfigEntry<bool> EnableInventory = null!;
        public static ConfigEntry<bool> EnableRewards = null!;
        public static ConfigEntry<bool> VerboseDiag = null!;

        // Parsed at Load() from config strings; defaults match the brief (F8/F9)
        internal static KeyCode ToggleKey    = KeyCode.F8;
        internal static KeyCode DiagDumpKey  = KeyCode.F9;

        public override void Load()
        {
            Log = base.Log;  // Log must be set before Guard is usable

            // M1: Config.Bind wrapped in Guard so a bind failure degrades gracefully.
            // Fields have safe defaults (declared at class level) so a bind failure is non-fatal.
            Guard("Config.Bind", () =>
            {
                ToggleKeyName   = Config.Bind("General", "ToggleKey",   "F8",  "Unity KeyCode name for overlay toggle");
                DiagDumpKeyName = Config.Bind("General", "DiagDumpKey", "F9",  "Unity KeyCode name for diagnostic dump");
                EnableWeaponInfo = Config.Bind("Surfaces", "WeaponInfo", true, "Weapon info overlay");
                EnableInventory  = Config.Bind("Surfaces", "Inventory",  true, "Inventory/pause overlay");
                EnableRewards    = Config.Bind("Surfaces", "Rewards",    true, "Reward selection overlay");
                // I3: VerboseDiag defaults to false to avoid flooding LogOutput.log on first run.
                VerboseDiag      = Config.Bind("Diagnostics", "Verbose", false, "Verbose calibration log (throttled to ~1 line/sec)");
            });

            // Parse KeyCode names (safe fallback to F8/F9 on parse failure)
            Guard("ParseKeys", () =>
            {
                if (ToggleKeyName != null && System.Enum.TryParse<KeyCode>(ToggleKeyName.Value,   true, out var tk))  ToggleKey   = tk;
                if (DiagDumpKeyName != null && System.Enum.TryParse<KeyCode>(DiagDumpKeyName.Value, true, out var dk))  DiagDumpKey = dk;
            });

            // CORRECTION 2: eAttrib ordinal sanity check at load time.
            Guard("AttribSanityCheck", () =>
            {
                int gameCount = (int)eAttrib.Count;
                int coreCount = (int)HonestDamage.Core.Attrib.Count;
                if (gameCount != coreCount)
                    Log.LogWarning($"[AttribSanityCheck] MISMATCH: game eAttrib.Count={gameCount}, Core.Attrib.Count={coreCount}");
                else
                    Log.LogInfo($"[AttribSanityCheck] OK: Count={gameCount}");

                // Sentinel spot-checks
                void CheckSentinel(string name, int gameIdx, int coreIdx)
                {
                    if (gameIdx != coreIdx)
                        Log.LogWarning($"[AttribSanityCheck] {name} index mismatch: game={gameIdx} core={coreIdx}");
                    else
                        Log.LogInfo($"[AttribSanityCheck] {name}: game={gameIdx} core={coreIdx} OK");
                }

                CheckSentinel("ATK",                      (int)eAttrib.ATK,                      (int)HonestDamage.Core.Attrib.ATK);
                CheckSentinel("SpellDamageModifier",      (int)eAttrib.SpellDamageModifier,      (int)HonestDamage.Core.Attrib.SpellDamageModifier);
                CheckSentinel("FinalPlayerDamageMultiplier", (int)eAttrib.FinalPlayerDamageMultiplier, (int)HonestDamage.Core.Attrib.FinalPlayerDamageMultiplier);
            });

            // Harmony bootstrap
            var harmony = new Harmony("com.ashubin.ekhonestdamage");
            Guard("HarmonyPatchAll", () => harmony.PatchAll());

            // Register and attach the Update tick component (IL2CPP requires ClassInjector)
            Guard("RegisterTickComponent", () =>
            {
                ClassInjector.RegisterTypeInIl2Cpp<TickComponent>();
                AddComponent<TickComponent>();
            });

            Log.LogInfo($"Honest Damage loaded. ToggleKey={ToggleKey} DiagDumpKey={DiagDumpKey}");
        }

        /// <summary>
        /// Wraps a body in try/catch, logging exceptions without crashing the plugin.
        /// Implements Guard (N1).
        /// </summary>
        public static void Guard(string where, Action body)
        {
            try { body(); }
            catch (Exception e) { Log.LogError($"[{where}] {e}"); }
        }
    }

    /// <summary>
    /// MonoBehaviour tick for hotkey polling. IL2CPP requires ClassInjector registration
    /// before AddComponent and a native-pointer constructor.
    /// </summary>
    public class TickComponent : MonoBehaviour
    {
        public TickComponent(IntPtr ptr) : base(ptr) { }

        // Frame counter for throttling heavy scans (FindObjectsOfType).
        // SelectionInjector.Tick() runs at most once every 12 frames (~5×/sec at 60 fps).
        private int _frameCounter = 0;
        private const int InjectorTickInterval = 12;

        private void Update()
        {
            Plugin.Guard("TickComponent.Update", () =>
            {
                if (Input.GetKeyDown(Plugin.ToggleKey))
                    Plugin.OverlayEnabled = !Plugin.OverlayEnabled;

                if (Input.GetKeyDown(Plugin.DiagDumpKey))
                    Diagnostics.DumpNow();

                // Throttled selection-screen injector.
                _frameCounter++;
                if (_frameCounter >= InjectorTickInterval)
                {
                    _frameCounter = 0;
                    Injectors.SelectionInjector.Tick();
                }
            });
        }
    }
}
