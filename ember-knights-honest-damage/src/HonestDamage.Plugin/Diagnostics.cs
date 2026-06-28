using System;
using System.IO;
using System.Reflection;
using System.Text;
using BepInEx;
using HarmonyLib;
using HonestDamage.Core;
using UnityEngine;

namespace HonestDamage.Plugin
{
    /// <summary>
    /// Diagnostics: writes a calibration log on F9 and provides a read-only
    /// Harmony postfix on XEntity.TakeDamage for damage pair logging.
    ///
    /// DumpNow() sections:
    ///   [ATTRIBS]   — game.Get(eAttrib) | GetRaw | AttribResolver.Resolve(raw, mods, attrib)
    ///   [MODIFIERS] — flat modifier list (Attrib, Op, Value, Source, SourceDefId)
    ///   [UI-TREE]   — Canvas hierarchy dump for later injection-point discovery
    /// </summary>
    public static class Diagnostics
    {
        private static string LogPath =>
            Path.Combine(Paths.BepInExRootPath, "honest-damage-diag.log");

        // ------------------------------------------------------------------ DumpNow

        public static void DumpNow()
        {
            Plugin.Guard("Diagnostics.DumpNow", () =>
            {
                var sb = new StringBuilder();
                sb.AppendLine("==================== HONEST DAMAGE DIAG ====================");
                sb.AppendLine($"Timestamp: {DateTime.Now:yyyy-MM-dd HH:mm:ss}");
                sb.AppendLine($"Top canvas (likely current screen): {TopCanvasName()}");
                sb.AppendLine();

                var cmp = PlayerLocator.GetLocalAttribs();
                if (cmp == null)
                {
                    sb.AppendLine("[ATTRIBS] (no player attribs — take a hit first, then press F9)");
                    sb.AppendLine("[MODIFIERS] (no player attribs)");
                }
                else
                {
                    // [ATTRIBS]
                    sb.AppendLine("[ATTRIBS]  (attrib = game.Get | raw = GetRaw | resolved = AttribResolver.Resolve(raw, mods, attrib))");
                    var mods   = GameDataAdapter.CurrentModifiers(cmp);
                    var rawArr = GameDataAdapter.RawSnapshot(cmp);

                    for (int i = 0; i < (int)Attrib.Count; i++)
                    {
                        Attrib a = (Attrib)i;
                        float gameVal     = 0f;
                        float rawVal      = rawArr[i];
                        float resolvedVal = 0f;

                        Plugin.Guard($"DumpNow.Attrib[{i}]", () =>
                        {
                            gameVal     = cmp.Get((eAttrib)i);
                            resolvedVal = AttribResolver.Resolve(rawVal, mods, a);
                        });

                        sb.AppendLine($"  {a,-40} game={gameVal,10:F4}  raw={rawVal,10:F4}  resolved={resolvedVal,10:F4}");
                    }
                    sb.AppendLine();

                    // [MODIFIERS]
                    sb.AppendLine("[MODIFIERS]");
                    foreach (var m in mods)
                        sb.AppendLine($"  {m.Attrib,-40} {m.Op,-4} {m.Value,10:F4}");
                    sb.AppendLine();
                }

                // [WEAPON-ATTACKS] — per-attack honest damage for equipped weapon
                sb.AppendLine("[WEAPON-ATTACKS]");
                Plugin.Guard("DumpNow.WeaponAttacks", () => DumpWeaponAttacks(sb));
                sb.AppendLine();

                // [UI-TREE] — canvas hierarchy dump (CORRECTION 4)
                sb.AppendLine("[UI-TREE]");
                Plugin.Guard("DumpNow.UITree", () => DumpUITree(sb));
                sb.AppendLine();

                File.AppendAllText(LogPath, sb.ToString());
                Plugin.Log.LogInfo($"[Diagnostics] Appended dump to {LogPath}");
            });
        }

        // Returns the enabled Canvas with the highest sortingOrder — usually the
        // top-most/active screen (helps label each appended F9 dump by screen).
        private static string TopCanvasName()
        {
            string best = "(none)";
            int bestOrder = int.MinValue;
            Plugin.Guard("TopCanvasName", () =>
            {
                foreach (var c in GameObject.FindObjectsOfType<Canvas>())
                {
                    if (c != null && c.enabled && c.sortingOrder >= bestOrder)
                    {
                        bestOrder = c.sortingOrder;
                        best = $"{c.gameObject.name} (sortOrder={c.sortingOrder})";
                    }
                }
            });
            return best;
        }

        // ------------------------------------------------------------------ WEAPON-ATTACKS dump

        /// <summary>
        /// Appends a [WEAPON-ATTACKS] section to <paramref name="sb"/>.
        /// Called by DumpNow (F9) and by InventoryInjector on its first tick.
        /// Uses GameCode.Defs.weaponDefs for AttackDefs, CreateAttackDp for honest values.
        /// </summary>
        internal static void DumpWeaponAttacks(StringBuilder sb)
        {
            var entity  = PlayerLocator.GetLocalEntity();
            var attribs = PlayerLocator.GetLocalAttribs();

            if (entity == null || attribs == null)
            {
                sb.AppendLine("  (no player entity cached — take a hit first)");
                return;
            }

            XWeaponDef? weaponDef = null;
            Plugin.Guard("DumpWeaponAttacks.GetWeaponDef", () =>
            {
                weaponDef = GameCode.PlayerUtils.GetWeaponDef(entity);
            });

            if (weaponDef == null)
            {
                sb.AppendLine("  (GetWeaponDef returned null)");
                return;
            }

            sb.AppendLine($"  WeaponType={weaponDef.WeaponType}  AttackBase={weaponDef.AttackBase:F2}");

            var attackDefs = Injectors.InventoryInjector.GetRelevantAttackDefs(weaponDef);
            if (attackDefs == null || attackDefs.Length == 0)
            {
                float atk = attribs.Get(eAttrib.ATK);
                sb.AppendLine($"  No AttackDefs found — ATK fallback: {atk:F1}");
                return;
            }

            foreach (var def in attackDefs)
            {
                if (def == null) continue;
                Plugin.Guard($"DumpWeaponAttacks.Def[{def.Id}]", () =>
                {
                    string kind = def.IsChargeAtk ? "CHARGE" : "COMBO";
                    // ATK * DamageMul (CreateAttackDp returns DamageAmount=0 at creation — see InventoryInjector).
                    float atk = attribs.Get(eAttrib.ATK);
                    float min = atk * def.DamageMul;
                    float max = atk * def.DamageMulMax;
                    sb.AppendLine($"  [{kind}] Id={def.Id,-4} DamageMul={def.DamageMul:F3}  DamageMulMax={def.DamageMulMax:F3}  honest≈{min:F1}" + (max > min + 0.05f ? $"–{max:F1}" : ""));
                });
            }
        }

        // ------------------------------------------------------------------ UI-TREE dump

        private static void DumpUITree(StringBuilder sb)
        {
            Canvas[] canvases = GameObject.FindObjectsOfType<Canvas>();
            sb.AppendLine($"  Active canvases: {canvases.Length}");

            foreach (var canvas in canvases)
            {
                if (canvas == null || canvas.gameObject == null) continue;
                sb.AppendLine($"  Canvas: {canvas.gameObject.name} (enabled={canvas.enabled}, sortOrder={canvas.sortingOrder})");
                Plugin.Guard($"DumpUITree.Canvas[{canvas.gameObject.name}]", () =>
                {
                    DumpGameObject(sb, canvas.gameObject, 2);
                });
            }
        }

        private static void DumpGameObject(StringBuilder sb, GameObject go, int depth)
        {
            if (go == null) return;

            string indent = new string(' ', depth * 2);

            // Collect component type names
            Component[] comps = go.GetComponents<Component>();
            var compNames = new StringBuilder();
            foreach (var c in comps)
            {
                if (c == null) continue;
                compNames.Append(c.GetIl2CppType().FullName);
                compNames.Append(", ");
            }

            // Check for text components (for value logging)
            string textValue = "";
            Plugin.Guard($"DumpGameObject.TextCheck[{go.name}]", () =>
            {
                var tmp = go.GetComponent<TMPro.TextMeshProUGUI>();
                if (tmp != null) textValue = $" [TMPro: \"{tmp.text}\"]";
                else
                {
                    var uit = go.GetComponent<UnityEngine.UI.Text>();
                    if (uit != null) textValue = $" [UIText: \"{uit.text}\"]";
                }
            });

            sb.AppendLine($"{indent}{go.name} (active={go.activeSelf})  {compNames}{textValue}");

            // Recurse into children (cap depth to avoid infinite loops / huge logs)
            if (depth < 10)
            {
                for (int i = 0; i < go.transform.childCount; i++)
                {
                    var child = go.transform.GetChild(i)?.gameObject;
                    if (child != null)
                        DumpGameObject(sb, child, depth + 1);
                }
            }
        }

        // ------------------------------------------------------------------ TakeDamage postfix hook

        [HarmonyPatch]
        private static class TakeDamagePostfix
        {
            /// <summary>
            /// Resolves the patch target defensively using AccessTools.
            /// If the method is not found, logs WARN and skips (no throw).
            /// </summary>
            static MethodBase? TargetMethod()
            {
                var m = AccessTools.Method(
                    typeof(GameCode.XEntity),
                    "TakeDamage",
                    new[] { typeof(DamageParams), typeof(bool) });

                if (m == null)
                {
                    Plugin.Log.LogWarning("[Diagnostics] TakeDamage method not found via AccessTools — damage hook skipped.");
                }
                return m;
            }

            // Last time a per-hit damage line was logged (Time.realtimeSinceStartup).
            private static float _lastDamageLogTime = -999f;
            private const float DamageLogCooldown = 1f; // at most 1 line/second

            static void Postfix(GameCode.XEntity __instance, DamageParams __0, bool __1)
            {
                Plugin.Guard("TakeDamage.Postfix", () =>
                {
                    // I1: Seed the player cache FIRST, unconditionally — VerboseDiag must not gate this.
                    // I2: Only seed from a player entity (one that carries XPlayerCMP), not enemies.
                    Plugin.Guard("TakeDamage.SeedLocator", () =>
                    {
                        if (__instance == null) return;
                        // XPlayerCMP is the canonical player-marker component (confirmed in interop proxy).
                        // Enemies never carry it, so this discriminates player from enemy reliably.
                        var playerCmp = __instance.GetCMP<GameCode.XPlayerCMP>();
                        if (playerCmp == null) return;

                        var attribs = __instance.GetCMP<GameCode.XAttribsCMP>();
                        if (attribs != null)
                            PlayerLocator.Seed(__instance, attribs);
                    });

                    // I3: Per-hit log gated by VerboseDiag (default false) AND a 1-second throttle.
                    if (!(Plugin.VerboseDiag?.Value ?? false)) return;

                    float now = UnityEngine.Time.realtimeSinceStartup;
                    if (now - _lastDamageLogTime < DamageLogCooldown) return;
                    _lastDamageLogTime = now;

                    // Log the damage event for calibration
                    string entityName = "<unknown>";
                    Plugin.Guard("TakeDamage.GetName", () =>
                    {
                        entityName = __instance?.ToString() ?? "<null>";
                    });

                    Plugin.Log.LogInfo(
                        $"[TakeDamage] victim={entityName} " +
                        $"DamageAmount={__0.DamageAmount:F3} " +
                        $"DamageRate={__0.DamageRate:F3} " +
                        $"DamageType={__0.DamageType} " +
                        $"ExtraAbilityNumHits={__0.ExtraAbilityNumHits} " +
                        $"OverrideDisplayValue={__0.OverrideDisplayValue:F3} " +
                        $"CritChance={__0.CritChance:F3} " +
                        $"AbilityDefId={__0.AbilityDefId} " +
                        $"IgnoreUpgrades={__0.IgnoreUpgrades} " +
                        $"ReleaseType={__0.ReleaseType} " +
                        $"IgnoreOnlineCheck={__1}");
                });
            }
        }

        // ------------------------------------------------------------------ CreateAttackDp seed (proactive)

        /// <summary>
        /// Read-only postfix on XPlayerSYS.CreateAttackDp. The game calls this with the
        /// attacking PLAYER's XEntity + XAttribsCMP on every player attack (fires constantly
        /// in combat), so the player cache is populated from the ATTACKER side — labels appear
        /// without the player needing to TAKE a hit first. No game state is mutated.
        /// </summary>
        [HarmonyPatch]
        private static class CreateAttackDpSeedPostfix
        {
            static MethodBase? TargetMethod()
            {
                var m = AccessTools.Method(
                    typeof(GameCode.XPlayerSYS),
                    "CreateAttackDp",
                    new[] { typeof(GameCode.XEntity), typeof(GameCode.XAttribsCMP),
                            typeof(XBaseAttackDef), typeof(XWeaponDef), typeof(float) });
                if (m == null)
                    Plugin.Log.LogWarning("[Diagnostics] CreateAttackDp not found via AccessTools — proactive player seed skipped.");
                return m;
            }

            static void Postfix(GameCode.XEntity __0, GameCode.XAttribsCMP __1)
            {
                Plugin.Guard("CreateAttackDp.SeedLocator", () =>
                {
                    if (__0 != null && __1 != null)
                        PlayerLocator.Seed(__0, __1);
                });
            }
        }
    }
}
