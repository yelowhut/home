using System;
using System.Text;
using TMPro;
using UnityEngine;

namespace HonestDamage.Plugin.Injectors
{
    /// <summary>
    /// Etap-2 Task 2 — Inventory UI injector.
    ///
    /// Shows stat-scaled ("honest") damage as additive cyan labels near the inventory
    /// weapon and ability panels.  Never modifies original game text.
    ///
    /// Weapon attacks: uses GameCode.XPlayerSYS.CreateAttackDp for exact values; falls
    /// back to ATK × DamageMul if the interop call fails.
    /// Ability damage:  XAbilityDef.Effects[0].TapValue × SpellDamageModifier.
    ///                  [calibrate] — provisional; confirm vs damage log once abilities
    ///                  are testable.
    ///
    /// UI anchor strategy:
    ///   - Find the active "UIInventoryV2" Canvas via FindObjectsOfType.
    ///   - Locate the "WeaponDetails" TextMeshProUGUI for the weapon label.
    ///   - Locate "AbilitySlot_X" child panels for ability labels.
    ///   Names are discovered experimentally via honest-damage-diag.log [UI-TREE] section.
    ///
    /// Polling: called from TickComponent.Update() every InjectorTickInterval frames.
    ///
    /// Type notes (confirmed from dump.cs):
    ///   GameCode.XPlayerSYS.CreateAttackDp(XEntity, XAttribsCMP, XBaseAttackDef, XWeaponDef, float)
    ///   GameCode.PlayerUtils.GetWeaponDef(XEntity) → XWeaponDef
    ///   XWeaponDef.WeaponType (eWeaponType), AttackBase
    ///   GameCode.Defs.weaponDefs (WeaponDataFile) — global static DefManager singleton
    ///   WeaponDataFile.SwordSettings/BowSettings/… (per-type XWeaponSettings subclass)
    ///   XBaseAttackDef: IsChargeAtk, IsSkillShot, IsRollAtk, IsLastVariantAtk, DamageMul, DamageMulMax
    ///   XAbilityDef.Effects[]: TapValue, ChargeValue
    ///   eAttrib.SpellDamageModifier for ability scaling
    /// </summary>
    public static class InventoryInjector
    {
        // ---- Constants -------------------------------------------------------

        private const string LabelName    = "HD_Honest";
        private const string InventoryCanvasName = "UIInventoryV2";

        // Cyan colour for injected labels
        private static readonly Color HonestColor = new Color(0f, 1f, 1f, 1f);

        // ---- State -----------------------------------------------------------

        // Tracks whether we've already written the [WEAPON-ATTACKS] diag section.
        private static bool _diagDumped = false;

        // ---- Public entry point ----------------------------------------------

        /// <summary>
        /// Called from TickComponent.Update() every N frames.  All exceptions swallowed.
        /// </summary>
        public static void Tick()
        {
            Plugin.Guard("InventoryInjector.Tick", () =>
            {
                if (!Plugin.OverlayEnabled || !(Plugin.EnableInventory?.Value ?? true))
                    return;

                // Find the active UIInventoryV2 canvas.
                Canvas? invCanvas = FindActiveInventoryCanvas();
                if (invCanvas == null)
                    return;

                var entity  = PlayerLocator.GetLocalEntity();
                var attribs = PlayerLocator.GetLocalAttribs();
                if (entity == null || attribs == null)
                    return;

                // Dump weapon-attacks diag once per session (on first inventory tick).
                if (!_diagDumped)
                {
                    _diagDumped = true;
                    Plugin.Guard("InventoryInjector.FirstTickDiag", () =>
                    {
                        var sb = new StringBuilder();
                        sb.AppendLine("==================== WEAPON-ATTACKS (first inventory tick) ====================");
                        Diagnostics.DumpWeaponAttacks(sb);
                        var logPath = System.IO.Path.Combine(BepInEx.Paths.BepInExRootPath, "honest-damage-diag.log");
                        System.IO.File.AppendAllText(logPath, sb.ToString());
                        Plugin.Log.LogInfo("[InventoryInjector] Weapon-attacks diag appended to honest-damage-diag.log");
                    });
                }

                // ---- Weapon label ------------------------------------------------
                Plugin.Guard("InventoryInjector.WeaponLabel", () =>
                    InjectWeaponLabel(invCanvas, entity, attribs));

                // ---- Ability labels ----------------------------------------------
                Plugin.Guard("InventoryInjector.AbilityLabels", () =>
                    InjectAbilityLabels(invCanvas, entity, attribs));
            });
        }

        // ---- Weapon label logic ----------------------------------------------

        private static void InjectWeaponLabel(Canvas invCanvas,
                                              GameCode.XEntity entity,
                                              GameCode.XAttribsCMP attribs)
        {
            XWeaponDef? weaponDef = null;
            Plugin.Guard("InventoryInjector.GetWeaponDef", () =>
            {
                weaponDef = GameCode.PlayerUtils.GetWeaponDef(entity);
            });
            if (weaponDef == null) return;

            // Find the anchor TMP (WeaponDetails or any TMP under the weapon section).
            TextMeshProUGUI? anchor = FindWeaponAnchorTMP(invCanvas.gameObject);
            if (anchor == null) return;

            // Build the weapon damage string.
            string weaponText = BuildWeaponDamageText(entity, attribs, weaponDef);
            if (string.IsNullOrEmpty(weaponText)) return;

            // Append into the WeaponDetails text itself (flows in the existing description
            // layout) rather than a floating sibling label — a separate clone overlapped the
            // in-game price text in the shop. Idempotent: re-applied with current stats each tick.
            AppendHonestToText(anchor, weaponText);
        }

        // ---- Ability labels logic --------------------------------------------

        private static void InjectAbilityLabels(Canvas invCanvas,
                                                GameCode.XEntity entity,
                                                GameCode.XAttribsCMP attribs)
        {
            GameCode.XInventoryCMP? inv = null;
            Plugin.Guard("InventoryInjector.GetInventory", () =>
            {
                inv = entity.GetInventory();
            });
            if (inv == null) return;

            var slots = inv.AbilitySlots;
            if (slots == null) return;

            float spellMul = 1f;
            Plugin.Guard("InventoryInjector.SpellMul", () =>
            {
                spellMul = attribs.Get(eAttrib.SpellDamageModifier);
            });

            // Walk ability slots.
            for (int i = 0; i < slots.Length; i++)
            {
                int slotIndex = i; // capture for lambda
                Plugin.Guard($"InventoryInjector.AbilitySlot[{slotIndex}]", () =>
                {
                    var slot = slots[slotIndex];
                    if (slot == null) return;

                    var abilityInst = slot.Ability;
                    if (abilityInst == null) return;

                    XAbilityDef? abDef = null;
                    Plugin.Guard($"InventoryInjector.AbilitySlot[{slotIndex}].Def", () =>
                    {
                        abDef = abilityInst.Def;
                    });
                    if (abDef == null) return;

                    // Build ability damage text.
                    string abilityText = BuildAbilityDamageText(abDef, spellMul);
                    if (string.IsNullOrEmpty(abilityText)) return;

                    // Find the UI anchor for this ability slot.
                    TextMeshProUGUI? anchor = FindAbilityAnchorTMP(invCanvas.gameObject, slotIndex);
                    if (anchor == null) return;

                    Transform? anchorParent = anchor.gameObject.transform.parent;
                    if (anchorParent == null) return;

                    AttachOrUpdateLabel(anchor.gameObject, anchorParent, abilityText);
                });
            }
        }

        // ---- Damage computation helpers ------------------------------------

        /// <summary>
        /// Builds the weapon damage display string showing honest damage for combo and
        /// charged attacks.  Tries CreateAttackDp; falls back to ATK × DamageMul.
        /// </summary>
        private static string BuildWeaponDamageText(GameCode.XEntity entity,
                                                    GameCode.XAttribsCMP attribs,
                                                    XWeaponDef weaponDef)
        {
            var defs = GetRelevantAttackDefs(weaponDef);
            if (defs == null || defs.Length == 0)
            {
                // Ultimate fallback: just show ATK.
                float atkOnly = 0f;
                Plugin.Guard("InventoryInjector.ATKFallback", () =>
                    atkOnly = attribs.Get(eAttrib.ATK));
                return $"≈ ATK {atkOnly:F0} (no attacks found)";
            }

            var sb = new StringBuilder("≈ ");
            bool first = true;

            foreach (var def in defs)
            {
                if (def == null) continue;

                float amount = ComputeAttackDamage(entity, attribs, def, weaponDef);
                string kind  = def.IsChargeAtk ? "CHG" : "HIT";

                if (!first) sb.Append("  ");
                sb.Append($"{kind}:{amount:F0}");
                first = false;
            }

            return first ? "" : sb.ToString();
        }

        /// <summary>
        /// Computes honest damage for one attack def.
        /// Preferred: CreateAttackDp.  Fallback: ATK × DamageMul.
        /// </summary>
        private static float ComputeAttackDamage(GameCode.XEntity entity,
                                                 GameCode.XAttribsCMP attribs,
                                                 XBaseAttackDef def,
                                                 XWeaponDef weaponDef)
        {
            // Damage = ATK * DamageMul (verified against the TakeDamage log: a basic hit
            // with DamageMul=1.0 deals exactly ATK). CreateAttackDp is NOT used for the
            // value — it builds a damage *template* and returns DamageAmount=0 at creation
            // time (the final amount is resolved per-hit against a target).
            float result = 0f;
            Plugin.Guard("InventoryInjector.ComputeAttackDamage", () =>
            {
                float atk = attribs.Get(eAttrib.ATK);
                float mul = def.IsChargeAtk ? def.DamageMulMax : def.DamageMul;
                result    = atk * mul;
            });
            return result;
        }

        /// <summary>
        /// Builds ability damage text: TapValue (and ChargeValue if different) × SpellDamageModifier.
        /// [calibrate] Provisional.
        /// </summary>
        private static string BuildAbilityDamageText(XAbilityDef abDef, float spellMul)
        {
            var effects = abDef.Effects;
            if (effects == null || effects.Length == 0) return "";

            var effect = effects[0];
            if (effect == null) return "";

            float tap    = effect.TapValue    * spellMul;
            float charge = effect.ChargeValue * spellMul;

            if (tap <= 0f && charge <= 0f) return "";

            if (charge > 0f && Math.Abs(charge - tap) > 0.5f)
                return $"≈ {tap:F0} / CHG:{charge:F0}";

            return $"≈ {tap:F0}";
        }

        // ---- AttackDef selection — shared with Diagnostics ------------------

        /// <summary>
        /// Returns the relevant combo + charged AttackDef objects for the given weapon.
        /// Uses flag-based selection (IsChargeAtk) across all weapon types — uniform
        /// and robust against per-weapon index naming differences.
        ///
        /// Skips: IsRollAtk, IsSkillShot (not primary user-facing attacks).
        /// Public so Diagnostics.DumpWeaponAttacks can reuse it.
        /// </summary>
        public static XBaseAttackDef[]? GetRelevantAttackDefs(XWeaponDef weaponDef)
        {
            XBaseAttackDef[]? result = null;

            Plugin.Guard("InventoryInjector.GetRelevantAttackDefs", () =>
            {
                WeaponDataFile? wdf = null;
                Plugin.Guard("InventoryInjector.GetWeaponDataFile", () =>
                {
                    wdf = GameCode.Defs?.weaponDefs;
                });
                if (wdf == null) return;

                // Get the raw array for this weapon type.
                XBaseAttackDef[]? allDefs = GetAttackDefArray(wdf, weaponDef.WeaponType);
                if (allDefs == null) return;

                // Show only the BASE combo (first few normal hits) + the primary charge.
                // AttackDefs[] also contains mod/special attacks (Spreadshot, Volley, Bomb,
                // RapidShot, ...) the player may not have unlocked — showing them all was the
                // "junk". We skip them here. (Proper per-mod gating via HasMod(player, mod) is
                // a future refinement so equipped mod-attacks can be shown too.)
                const int MaxCombo = 3;
                var combo = new System.Collections.Generic.List<XBaseAttackDef>();
                XBaseAttackDef? charge = null;
                foreach (var d in allDefs)
                {
                    if (d == null) continue;
                    if (d.IsSkillShot || d.IsRollAtk) continue;
                    if (d.IsChargeAtk)
                    {
                        if (charge == null) charge = d;   // keep only the first/primary charge
                        continue;
                    }
                    if (combo.Count < MaxCombo) combo.Add(d);
                }
                if (charge != null) combo.Add(charge);

                result = combo.ToArray();
            });

            return result;
        }

        /// <summary>
        /// Maps eWeaponType → the typed AttackDef array from WeaponDataFile,
        /// returning XBaseAttackDef[] for uniform iteration.
        /// </summary>
        private static XBaseAttackDef[]? GetAttackDefArray(WeaponDataFile wdf, eWeaponType weaponType)
        {
            XBaseAttackDef[]? result = null;

            Plugin.Guard("InventoryInjector.GetAttackDefArray", () =>
            {
                switch (weaponType)
                {
                    case eWeaponType.Sword:
                    {
                        var s = wdf.SwordSettings;
                        if (s?.AttackDefs == null) break;
                        var tmp = new XBaseAttackDef[s.AttackDefs.Length];
                        for (int i = 0; i < s.AttackDefs.Length; i++) tmp[i] = s.AttackDefs[i];
                        result = tmp;
                        break;
                    }
                    case eWeaponType.Bow:
                    {
                        var s = wdf.BowSettings;
                        if (s?.AttackDefs == null) break;
                        var tmp = new XBaseAttackDef[s.AttackDefs.Length];
                        for (int i = 0; i < s.AttackDefs.Length; i++) tmp[i] = s.AttackDefs[i];
                        result = tmp;
                        break;
                    }
                    case eWeaponType.Hammer:
                    {
                        var s = wdf.HammerSettings;
                        if (s?.AttackDefs == null) break;
                        var tmp = new XBaseAttackDef[s.AttackDefs.Length];
                        for (int i = 0; i < s.AttackDefs.Length; i++) tmp[i] = s.AttackDefs[i];
                        result = tmp;
                        break;
                    }
                    case eWeaponType.Staff:
                    {
                        var s = wdf.StaffSettings;
                        if (s?.AttackDefs == null) break;
                        var tmp = new XBaseAttackDef[s.AttackDefs.Length];
                        for (int i = 0; i < s.AttackDefs.Length; i++) tmp[i] = s.AttackDefs[i];
                        result = tmp;
                        break;
                    }
                    case eWeaponType.Star:
                    {
                        var s = wdf.StarSettings;
                        if (s?.AttackDefs == null) break;
                        var tmp = new XBaseAttackDef[s.AttackDefs.Length];
                        for (int i = 0; i < s.AttackDefs.Length; i++) tmp[i] = s.AttackDefs[i];
                        result = tmp;
                        break;
                    }
                    case eWeaponType.Reaper:
                    {
                        var s = wdf.ReaperSettings;
                        if (s?.AttackDefs == null) break;
                        var tmp = new XBaseAttackDef[s.AttackDefs.Length];
                        for (int i = 0; i < s.AttackDefs.Length; i++) tmp[i] = s.AttackDefs[i];
                        result = tmp;
                        break;
                    }
                    case eWeaponType.DarkCap:
                    {
                        var s = wdf.DarkCapSettings;
                        if (s?.AttackDefs == null) break;
                        var tmp = new XBaseAttackDef[s.AttackDefs.Length];
                        for (int i = 0; i < s.AttackDefs.Length; i++) tmp[i] = s.AttackDefs[i];
                        result = tmp;
                        break;
                    }
                    case eWeaponType.Fists:
                    {
                        var s = wdf.FistSettings;
                        if (s?.AttackDefs == null) break;
                        var tmp = new XBaseAttackDef[s.AttackDefs.Length];
                        for (int i = 0; i < s.AttackDefs.Length; i++) tmp[i] = s.AttackDefs[i];
                        result = tmp;
                        break;
                    }
                    case eWeaponType.Gun:
                    {
                        var s = wdf.GunSettings;
                        if (s?.AttackDefs == null) break;
                        var tmp = new XBaseAttackDef[s.AttackDefs.Length];
                        for (int i = 0; i < s.AttackDefs.Length; i++) tmp[i] = s.AttackDefs[i];
                        result = tmp;
                        break;
                    }
                    default:
                        break;
                }
            });

            return result;
        }

        // ---- UI helpers ------------------------------------------------------

        /// <summary>
        /// Finds the active UIInventoryV2 canvas, or null if the inventory is not open.
        /// </summary>
        private static Canvas? FindActiveInventoryCanvas()
        {
            Canvas? found = null;
            Plugin.Guard("InventoryInjector.FindCanvas", () =>
            {
                foreach (var canvas in UnityEngine.Object.FindObjectsOfType<Canvas>())
                {
                    if (canvas == null) continue;
                    if (!canvas.gameObject.activeInHierarchy) continue;
                    if (canvas.gameObject.name == InventoryCanvasName)
                    {
                        found = canvas;
                        return;
                    }
                }
            });
            return found;
        }

        /// <summary>
        /// Finds a TextMeshProUGUI inside the inventory root that serves as the weapon
        /// anchor point. Searches for a child named "WeaponDetails"; if not found,
        /// returns the first TMP in a child named containing "Weapon".
        /// </summary>
        private static TextMeshProUGUI? FindWeaponAnchorTMP(GameObject invRoot)
        {
            TextMeshProUGUI? found = null;
            Plugin.Guard("InventoryInjector.FindWeaponAnchorTMP", () =>
            {
                // Try well-known name first.
                var t = FindDeepChild(invRoot.transform, "WeaponDetails");
                if (t != null)
                {
                    found = t.gameObject.GetComponent<TextMeshProUGUI>();
                    if (found != null) return;
                }

                // Secondary: first TMP inside any child whose name contains "Weapon".
                found = FindFirstTMPInChildContaining(invRoot.transform, "Weapon");
            });
            return found;
        }

        /// <summary>
        /// Finds the ability anchor TMP for slot <paramref name="slotIndex"/> within the
        /// inventory root.  Searches by common naming conventions (AbilitySlot_0, etc.)
        /// falling back to the Nth TMP in a child containing "Ability".
        /// </summary>
        private static TextMeshProUGUI? FindAbilityAnchorTMP(GameObject invRoot, int slotIndex)
        {
            TextMeshProUGUI? found = null;
            Plugin.Guard($"InventoryInjector.FindAbilityAnchorTMP[{slotIndex}]", () =>
            {
                // Try common naming: AbilitySlot_0, AbilitySlot1, Ability_0, etc.
                string[] candidates =
                {
                    $"AbilitySlot_{slotIndex}",
                    $"AbilitySlot{slotIndex}",
                    $"Ability_{slotIndex}",
                    $"Ability{slotIndex}",
                };

                foreach (var name in candidates)
                {
                    var t = FindDeepChild(invRoot.transform, name);
                    if (t != null)
                    {
                        var tmp = FindFirstTMPInTree(t);
                        if (tmp != null) { found = tmp; return; }
                    }
                }

                // Fallback: find the Nth TMP in any "Ability"-named subtree.
                found = FindNthTMPInChildContaining(invRoot.transform, "Ability", slotIndex);
            });
            return found;
        }

        // ---- Label injection (mirrors SelectionInjector pattern) ------------

        // Marker that begins our appended line inside a game TMP text block. Used to
        // strip the previously-appended line so re-applying with new stats is idempotent.
        private const string HonestMark = "\n<color=#00E5FF>";

        /// <summary>
        /// Appends our honest-damage line to the END of the anchor's own TMP text, so it
        /// flows within the existing description layout (no floating label that can overlap
        /// other UI such as the shop price). Idempotent across ticks.
        /// </summary>
        private static void AppendHonestToText(TextMeshProUGUI tmp, string payload)
        {
            Plugin.Guard("InventoryInjector.AppendHonestToText", () =>
            {
                if (tmp == null) return;
                string t = tmp.text ?? "";
                int idx = t.IndexOf(HonestMark);     // strip any prior appended line
                if (idx >= 0) t = t.Substring(0, idx);
                tmp.text = t + HonestMark + payload + "</color>";
            });
        }

        private static void AttachOrUpdateLabel(GameObject anchor, Transform parent, string text)
        {
            Transform? existing = FindDirectChild(parent, LabelName);
            if (existing != null)
            {
                var existingTmp = existing.gameObject.GetComponent<TextMeshProUGUI>();
                if (existingTmp != null)
                    existingTmp.text = text;
            }
            else
            {
                Plugin.Guard("InventoryInjector.Instantiate", () =>
                {
                    var tmp = anchor.GetComponent<TextMeshProUGUI>();
                    if (tmp == null) return;

                    var clone = UnityEngine.Object.Instantiate(anchor, parent);
                    clone.name = LabelName;

                    var cloneTmp = clone.GetComponent<TextMeshProUGUI>();
                    if (cloneTmp == null) return;

                    cloneTmp.text     = text;
                    cloneTmp.color    = HonestColor;
                    cloneTmp.fontSize = Mathf.Max(8f, cloneTmp.fontSize * 0.85f);
                    clone.SetActive(true);
                });
            }
        }

        // ---- Transform search helpers ---------------------------------------

        private static Transform? FindDirectChild(Transform parent, string name)
        {
            if (parent == null) return null;
            for (int i = 0; i < parent.childCount; i++)
            {
                var c = parent.GetChild(i);
                if (c != null && c.name == name) return c;
            }
            return null;
        }

        private static Transform? FindDeepChild(Transform parent, string name)
        {
            if (parent == null) return null;
            for (int i = 0; i < parent.childCount; i++)
            {
                var c = parent.GetChild(i);
                if (c == null) continue;
                if (c.name == name) return c;
                var found = FindDeepChild(c, name);
                if (found != null) return found;
            }
            return null;
        }

        private static TextMeshProUGUI? FindFirstTMPInTree(Transform root)
        {
            if (root == null) return null;
            var t = root.GetComponent<TextMeshProUGUI>();
            if (t != null) return t;
            for (int i = 0; i < root.childCount; i++)
            {
                var c = root.GetChild(i);
                if (c == null) continue;
                var found = FindFirstTMPInTree(c);
                if (found != null) return found;
            }
            return null;
        }

        private static TextMeshProUGUI? FindFirstTMPInChildContaining(Transform parent, string keyword)
        {
            if (parent == null) return null;
            for (int i = 0; i < parent.childCount; i++)
            {
                var c = parent.GetChild(i);
                if (c == null) continue;
                if (c.name.IndexOf(keyword, StringComparison.OrdinalIgnoreCase) >= 0)
                {
                    var t = FindFirstTMPInTree(c);
                    if (t != null) return t;
                }
            }
            // Recurse into children if not found at this level.
            for (int i = 0; i < parent.childCount; i++)
            {
                var c = parent.GetChild(i);
                if (c == null) continue;
                var t = FindFirstTMPInChildContaining(c, keyword);
                if (t != null) return t;
            }
            return null;
        }

        private static TextMeshProUGUI? FindNthTMPInChildContaining(Transform parent, string keyword, int n)
        {
            if (parent == null) return null;
            int count = 0;
            for (int i = 0; i < parent.childCount; i++)
            {
                var c = parent.GetChild(i);
                if (c == null) continue;
                if (c.name.IndexOf(keyword, StringComparison.OrdinalIgnoreCase) >= 0)
                {
                    if (count == n)
                    {
                        return FindFirstTMPInTree(c);
                    }
                    count++;
                }
            }
            return null;
        }
    }
}
