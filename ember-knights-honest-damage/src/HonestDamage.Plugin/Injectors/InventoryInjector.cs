using System;
using System.Collections.Generic;
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
    /// Weapon attacks: ATK × DamageMul (charge: DamageMulMax).
    ///   CreateAttackDp returns DamageAmount=0 at creation time — value is resolved
    ///   per-hit against a target, so it is not useful here.
    /// Ability damage:  XAbilityDef.Effects[0].TapValue × SpellDamageModifier.
    ///                  [calibrate] — provisional; confirm vs damage log once abilities
    ///                  are testable.
    ///
    /// Crit display (Change 2): each attack shown as "KIND:base (crit X)".
    ///   critMul = 1f + attribs.Get(eAttrib.CritDmgMUL).
    ///
    /// Mod-aware attack selection (Change 1):
    ///   Base combo (first 3 non-charge non-skillshot non-roll) + first charge: ALWAYS.
    ///   Special/mod attacks: shown only if the corresponding mod is in EquippedMods.
    ///   Bow and Sword have explicit mod→attack-Id/index tables; others: base+charge only.
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
    ///   GameCode.XInventoryCMP.Weapon → GameCode.XWeaponInst
    ///   GameCode.XWeaponInst.EquippedMods → List<eWeaponModType>
    ///   GameCode.XWeaponInst.HasMod(eWeaponModType) → bool
    ///   GameCode.PlayerUtils.GetWeaponDef(XEntity) → XWeaponDef
    ///   XWeaponDef.WeaponType (eWeaponType), AttackBase
    ///   GameCode.Defs.weaponDefs (WeaponDataFile) — global static DefManager singleton
    ///   WeaponDataFile.SwordSettings (XSwordSettings) / BowSettings (XBowSettings) / …
    ///   XBaseAttackDef: IsChargeAtk, IsSkillShot, IsRollAtk, IsLastVariantAtk, DamageMul, DamageMulMax, Id
    ///   XBowSettings: NormalAttackId, ChargeAttackId, ThirdAttackId,
    ///                 RapidshotAttackId, SpreadshotAttackId, MarkedshotAttackId,
    ///                 VolleyChargeAttackId, BombChargeAttackId
    ///   XSwordSettings: NormalAttack1/2/3, LungeModAttackIndex, WhirlwindModAttackIndex,
    ///                   Mod56_MultiStabAttackIndex, Mod56_FinalStabAttackIndex,
    ///                   Mod59Ultimate_ThirdAttackIndex, AttackDefs[]
    ///   eAttrib.CritDmgMUL = 7 (crit bonus multiplier; 1f + value = full crit multiplier)
    ///   eAttrib.SpellDamageModifier for ability scaling
    /// </summary>
    public static class InventoryInjector
    {
        // ---- Constants -------------------------------------------------------

        private const string LabelName    = "HD_Honest";
        private const string InventoryCanvasName = "UIInventoryV2";

        // Cyan colour for injected labels
        private static readonly Color HonestColor = new Color(0f, 1f, 1f, 1f);

        // Throttle timer for the Verbose ability-slot diagnostic log.
        private static float _lastAbilityLog = -999f;

        // ---- Labeled attack result -------------------------------------------

        /// <summary>
        /// A single attack def together with the mod it belongs to (None = base attack).
        /// Public so Diagnostics.DumpWeaponAttacks can use it.
        /// </summary>
        public struct LabeledAttack
        {
            public XBaseAttackDef Def;
            /// <summary>eWeaponModType.None for base combo/charge; otherwise the mod that unlocks it.</summary>
            public eWeaponModType SourceMod;

            public LabeledAttack(XBaseAttackDef def, eWeaponModType sourceMod)
            {
                Def       = def;
                SourceMod = sourceMod;
            }
        }

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
                        Diagnostics.DumpWeaponAttacks(sb, entity, attribs);
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

                    // Find the UI anchor for this ability slot.
                    TextMeshProUGUI? anchor = FindAbilityAnchorTMP(invCanvas.gameObject, slotIndex);

                    // Throttled diagnostic (Verbose): reveals why a slot shows nothing —
                    // empty text (no damage effect in def) vs anchor not found.
                    if ((Plugin.VerboseDiag?.Value ?? false) &&
                        UnityEngine.Time.realtimeSinceStartup - _lastAbilityLog > 2f)
                    {
                        _lastAbilityLog = UnityEngine.Time.realtimeSinceStartup;
                        Plugin.Log.LogInfo($"[AbilityDiag] slot={slotIndex} def={abDef} " +
                            $"text=\"{abilityText}\" anchorFound={(anchor != null)}");
                    }

                    if (string.IsNullOrEmpty(abilityText)) return;
                    if (anchor == null) return;

                    Transform? anchorParent = anchor.gameObject.transform.parent;
                    if (anchorParent == null) return;

                    AttachOrUpdateLabel(anchor.gameObject, anchorParent, abilityText);
                });
            }
        }

        // ---- Damage computation helpers ------------------------------------

        /// <summary>
        /// Builds the weapon damage display string showing honest damage (with crit) for
        /// the player's actual build (base combo + only equipped mod attacks).
        /// Format: ≈ HIT:22 (crit 32)  HIT:26 (crit 39)  CHG:56 (crit 84)
        /// </summary>
        private static string BuildWeaponDamageText(GameCode.XEntity entity,
                                                    GameCode.XAttribsCMP attribs,
                                                    XWeaponDef weaponDef)
        {
            var defs = GetRelevantAttackDefs(weaponDef, entity);
            if (defs == null || defs.Count == 0)
            {
                // Ultimate fallback: just show ATK.
                float atkOnly = 0f;
                Plugin.Guard("InventoryInjector.ATKFallback", () =>
                    atkOnly = attribs.Get(eAttrib.ATK));
                return $"≈ ATK {atkOnly:F0} (no attacks found)";
            }

            // Compute crit multiplier: 1 + CritDmgMUL (e.g. 0.5 → ×1.5 on crit).
            float critMul = 1f;
            Plugin.Guard("InventoryInjector.CritMul", () =>
            {
                critMul = 1f + attribs.Get(eAttrib.CritDmgMUL);
            });

            var sb = new StringBuilder("≈ ");
            bool first = true;

            foreach (var la in defs)
            {
                if (la.Def == null) continue;

                float baseAmt = ComputeAttackDamage(entity, attribs, la.Def, weaponDef);
                float critAmt = baseAmt * critMul;
                string kind   = la.Def.IsChargeAtk ? "CHG" : "HIT";

                if (!first) sb.Append("  ");
                sb.Append($"{kind}:{baseAmt:F0} (crit {critAmt:F0})");
                first = false;
            }

            return first ? "" : sb.ToString();
        }

        /// <summary>
        /// Computes honest damage for one attack def.
        /// Damage = ATK * DamageMul (charge: DamageMulMax).
        /// CreateAttackDp is NOT used — it returns DamageAmount=0 at creation time.
        /// </summary>
        private static float ComputeAttackDamage(GameCode.XEntity entity,
                                                 GameCode.XAttribsCMP attribs,
                                                 XBaseAttackDef def,
                                                 XWeaponDef weaponDef)
        {
            float result = 0f;
            Plugin.Guard("InventoryInjector.ComputeAttackDamage", () =>
            {
                float atk = attribs.Get(eAttrib.ATK);
                // TODO charge-value: DamageMulMax appears to overstate a full charge.
                //   Bow observed: full charge = 20 for ATK 9.6 (≈ ×2.08), but DamageMulMax=2.6
                //   gives 25 and DamageMul=1.4 gives ~13 — neither matches. Using DamageMulMax
                //   as a provisional upper bound; recalibrate against the in-game charge number.
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
        /// Returns labeled (def, sourceMod) pairs for the given weapon reflecting the
        /// player's CURRENT BUILD:
        ///   - Base combo (first 3 non-charge/non-skillshot/non-roll) + first charge: always.
        ///   - Special/mod attacks: only if that mod is in the player's EquippedMods.
        ///   - De-duplicated by attack Id.
        ///   - Falls back to base+charge if weaponInst is null/unreadable (Guard).
        ///
        /// Public so Diagnostics.DumpWeaponAttacks can reuse it.
        /// </summary>
        /// <summary>Diagnostic: full raw AttackDefs array for the weapon type (all Ids/muls).</summary>
        public static XBaseAttackDef[]? GetAllAttackDefsForDiag(XWeaponDef weaponDef)
        {
            XBaseAttackDef[]? result = null;
            Plugin.Guard("InventoryInjector.GetAllAttackDefsForDiag", () =>
            {
                var wdf = GameCode.Defs?.weaponDefs;
                if (wdf == null) return;
                result = GetAttackDefArray(wdf, weaponDef.WeaponType);
            });
            return result;
        }

        public static List<LabeledAttack>? GetRelevantAttackDefs(XWeaponDef weaponDef,
                                                                  GameCode.XEntity? entity)
        {
            List<LabeledAttack>? result = null;

            Plugin.Guard("InventoryInjector.GetRelevantAttackDefs", () =>
            {
                WeaponDataFile? wdf = null;
                Plugin.Guard("InventoryInjector.GetWeaponDataFile", () =>
                {
                    wdf = GameCode.Defs?.weaponDefs;
                });
                if (wdf == null) return;

                // --- Step 1: read the raw array for this weapon type.
                XBaseAttackDef[]? allDefs = GetAttackDefArray(wdf, weaponDef.WeaponType);
                if (allDefs == null) return;

                // --- Step 2: get the player's weapon instance for HasMod() queries.
                // XWeaponInst.HasMod(eWeaponModType) is the canonical check (dump.cs line 87208).
                // EquippedMods is Il2CppSystem.Collections.Generic.List, not .NET List —
                // use HasMod() instead of list iteration for mod membership tests.
                GameCode.XWeaponInst? weaponInst = null;
                if (entity != null)
                {
                    Plugin.Guard("InventoryInjector.GetWeaponInst", () =>
                    {
                        weaponInst = entity.GetInventory()?.Weapon;
                    });
                }

                // --- Step 3: base combo + primary charge, selected per weapon type.
                // Bow: combo follows NAMED indices (Normal, Normal, Third) — NOT array order.
                //   Observed in-game (ATK 9.6): hit1=10, hit2=10 (both ×1.0 = NormalAttackId),
                //   hit3=Third (×1.2) — and Third is REPLACED by Spreadshot when that mod is
                //   equipped (mods replace, not add). See handoff §6/§7.
                // Other weapons: fall back to first-3-by-array-order until their named
                //   indices are confirmed in-game (TODO named-combo).
                var labeled   = new List<LabeledAttack>();
                var seenIds   = new HashSet<int>();

                if (weaponDef.WeaponType == eWeaponType.Bow && wdf.BowSettings != null)
                {
                    BuildBowCombo(labeled, seenIds, allDefs, wdf.BowSettings, weaponInst);
                }
                else
                {
                    BuildOrderedCombo(labeled, seenIds, allDefs);
                }

                // --- Step 4: mod-specific attacks for equipped mods.
                // These are resolved directly by Id/index — NOT filtered through the
                // IsSkillShot / single-charge / MaxCombo gates above.
                // weaponInst == null means no inventory yet — safe fallback: base+charge only.
                if (weaponInst != null)
                {
                    AppendModAttacks(labeled, seenIds, allDefs, wdf, weaponDef.WeaponType, weaponInst);
                }

                result = labeled;
            });

            return result;
        }

        /// <summary>
        /// Bow base combo by NAMED indices: Normal, Normal, Third (+ primary charge).
        /// The two opening shots both use NormalAttackId (observed 10/10 in-game for ATK 9.6).
        /// The third hit is REPLACED by Spreadshot when the SpreadShot mod is equipped —
        /// bow mods swap the variant rather than adding a 4th hit (handoff §6).
        /// </summary>
        private static void BuildBowCombo(List<LabeledAttack>      labeled,
                                          HashSet<int>              seenIds,
                                          XBaseAttackDef[]          allDefs,
                                          XBowSettings              s,
                                          GameCode.XWeaponInst?     weaponInst)
        {
            // Hits 1 & 2: NormalAttackId (intentional repeat — the combo opens with two normals).
            var normal = FindAttackById(allDefs, s.NormalAttackId);
            if (normal != null)
            {
                labeled.Add(new LabeledAttack(normal, eWeaponModType.None)); // hit 1
                labeled.Add(new LabeledAttack(normal, eWeaponModType.None)); // hit 2 (same def)
                seenIds.Add(normal.Id);
            }

            // Hit 3: Third, or Spreadshot if the SpreadShot mod replaces it.
            bool hasSpread = false;
            if (weaponInst != null)
            {
                Plugin.Guard("InventoryInjector.BowHasSpread", () =>
                    hasSpread = weaponInst.HasMod(eWeaponModType.Bow_SpreadShot_14));
            }
            int thirdId = (hasSpread && s.SpreadshotAttackId != 0) ? s.SpreadshotAttackId
                                                                   : s.ThirdAttackId;
            var third = FindAttackById(allDefs, thirdId);
            if (third != null && !seenIds.Contains(third.Id))
            {
                labeled.Add(new LabeledAttack(third,
                    hasSpread ? eWeaponModType.Bow_SpreadShot_14 : eWeaponModType.None));
                seenIds.Add(third.Id);
            }

            // Primary charge.
            var charge = FindAttackById(allDefs, s.ChargeAttackId);
            if (charge != null && !seenIds.Contains(charge.Id))
            {
                labeled.Add(new LabeledAttack(charge, eWeaponModType.None));
                seenIds.Add(charge.Id);
            }
        }

        /// <summary>
        /// Fallback base combo for weapons whose named indices aren't yet confirmed in-game:
        /// first 3 non-charge/non-skillshot/non-roll attacks (array order) + first charge.
        /// TODO named-combo: replace per weapon type once [NAMED] diag confirms the real chain.
        /// </summary>
        private static void BuildOrderedCombo(List<LabeledAttack> labeled,
                                              HashSet<int>         seenIds,
                                              XBaseAttackDef[]     allDefs)
        {
            const int MaxCombo = 3;
            XBaseAttackDef? chargeBase = null;

            foreach (var d in allDefs)
            {
                if (d == null) continue;
                if (d.IsSkillShot || d.IsRollAtk) continue;
                if (d.IsChargeAtk)
                {
                    if (chargeBase == null) chargeBase = d; // keep only first/primary charge
                    continue;
                }
                if (labeled.Count < MaxCombo)
                {
                    labeled.Add(new LabeledAttack(d, eWeaponModType.None));
                    seenIds.Add(d.Id);
                }
            }
            if (chargeBase != null && !seenIds.Contains(chargeBase.Id))
            {
                labeled.Add(new LabeledAttack(chargeBase, eWeaponModType.None));
                seenIds.Add(chargeBase.Id);
            }
        }

        /// <summary>Returns the first attack def whose Id equals <paramref name="id"/> (0 = unset → null).</summary>
        private static XBaseAttackDef? FindAttackById(XBaseAttackDef[] allDefs, int id)
        {
            if (id == 0) return null;
            foreach (var d in allDefs)
            {
                if (d != null && d.Id == id) return d;
            }
            return null;
        }

        /// <summary>
        /// Appends mod-specific attack defs to <paramref name="labeled"/>, skipping any
        /// attack Id already in <paramref name="seenIds"/>.
        /// Uses <see cref="GameCode.XWeaponInst.HasMod"/> for mod-membership queries
        /// (EquippedMods is Il2CppSystem.Collections.Generic.List — not a .NET List).
        /// </summary>
        private static void AppendModAttacks(List<LabeledAttack>          labeled,
                                             HashSet<int>                  seenIds,
                                             XBaseAttackDef[]              allDefs,
                                             WeaponDataFile                wdf,
                                             eWeaponType                   weaponType,
                                             GameCode.XWeaponInst          weaponInst)
        {
            Plugin.Guard("InventoryInjector.AppendModAttacks", () =>
            {
                switch (weaponType)
                {
                    // ---------------------------------------------------------------- BOW
                    // Bow attack fields are Ids — match by iterating AttackDefs and
                    // comparing def.Id to the settings field value.
                    case eWeaponType.Bow:
                    {
                        var s = wdf.BowSettings;
                        if (s == null) break;

                        // mod → (attackId, label) pairs for every mod that adds an attack.
                        // Volley/Bomb are IsChargeAtk and would normally be dropped by the
                        // single-charge gate — resolve them directly here.
                        var bowModMap = new (eWeaponModType Mod, int AttackId)[]
                        {
                            (eWeaponModType.Bow_RapidShot_13,  s.RapidshotAttackId),
                            (eWeaponModType.Bow_SpreadShot_14, s.SpreadshotAttackId),
                            (eWeaponModType.Bow_MarkedShot_15, s.MarkedshotAttackId),
                            (eWeaponModType.Bow_Volley_17,     s.VolleyChargeAttackId),
                            (eWeaponModType.Bow_BombArrow_18,  s.BombChargeAttackId),
                        };

                        foreach (var entry in bowModMap)
                        {
                            if (entry.AttackId == 0) continue; // id=0 means unset
                            // XWeaponInst.HasMod() is the canonical check (Il2Cpp list, not .NET list).
                            bool hasMod = false;
                            Plugin.Guard($"InventoryInjector.HasMod[{entry.Mod}]", () =>
                                hasMod = weaponInst.HasMod(entry.Mod));
                            if (!hasMod) continue;

                            // Find by Id in the full array (Bow uses Ids, not indices).
                            foreach (var d in allDefs)
                            {
                                if (d == null) continue;
                                if (d.Id != entry.AttackId) continue;
                                if (!seenIds.Contains(d.Id))
                                {
                                    labeled.Add(new LabeledAttack(d, entry.Mod));
                                    seenIds.Add(d.Id);
                                }
                                break;
                            }
                        }
                        break;
                    }

                    // --------------------------------------------------------------- SWORD
                    // Sword attack fields are array INDICES — use AttackDefs[index] with
                    // bounds check.
                    //
                    // Confirmed mappings (from dump.cs XSwordSettings + eWeaponModType):
                    //   LungeModAttackIndex      → eWeaponModType.Sword_Lunge_6
                    //   WhirlwindModAttackIndex  → eWeaponModType.Sword_Whirlwind_7
                    //   Mod56_* fields           → eWeaponModType.Sword_Flurry_56
                    //   Mod59Ultimate_*          → eWeaponModType.Sword_SpinAttack_Ultimate_59
                    // NOTE: Mod56 = Sword_Flurry_56, NOT Slice_5 (spec typo — Slice is passive).
                    case eWeaponType.Sword:
                    {
                        var s = wdf.SwordSettings;
                        if (s?.AttackDefs == null) break;

                        // Lunge (mod 6)
                        AddSwordModAtk(labeled, seenIds, s.AttackDefs,
                                       s.LungeModAttackIndex,
                                       eWeaponModType.Sword_Lunge_6, weaponInst);

                        // Whirlwind (mod 7)
                        AddSwordModAtk(labeled, seenIds, s.AttackDefs,
                                       s.WhirlwindModAttackIndex,
                                       eWeaponModType.Sword_Whirlwind_7, weaponInst);

                        // Flurry (mod 56): two attack defs (MultiStab + FinalStab).
                        // Show FinalStab (the finishing hit) as the representative damage.
                        // TODO verify: field confirmed by dump name "Mod56_*"; mod confirmed
                        //   as Sword_Flurry_56=56 (NOT Slice_5 which is a passive).
                        AddSwordModAtk(labeled, seenIds, s.AttackDefs,
                                       s.Mod56_FinalStabAttackIndex,
                                       eWeaponModType.Sword_Flurry_56, weaponInst);

                        // SpinAttack Ultimate (mod 59): third-attack variant index.
                        // TODO verify: field confirmed by dump name "Mod59Ultimate_*"; mod=59.
                        AddSwordModAtk(labeled, seenIds, s.AttackDefs,
                                       s.Mod59Ultimate_ThirdAttackIndex,
                                       eWeaponModType.Sword_SpinAttack_Ultimate_59, weaponInst);

                        break;
                    }

                    // --------------------------------------------------------------- OTHER WEAPON TYPES
                    // Staff, Hammer, Star, Reaper, DarkCap, Fists, Gun:
                    // Base combo + charge only — no mod-attack mapping yet.
                    // TODO mod-map: add explicit mod→attackId/index tables here once the
                    //   attack defs for each mod are identified in the dump.
                    default:
                        break;
                }
            });
        }

        /// <summary>
        /// Helper: adds sword mod attack by array index if the mod is equipped and the index
        /// is valid and not already shown.
        /// Uses XWeaponInst.HasMod() (Il2Cpp) for the membership test.
        /// </summary>
        private static void AddSwordModAtk(List<LabeledAttack>       labeled,
                                           HashSet<int>               seenIds,
                                           XSwordAttackDef[]          defs,
                                           int                        index,
                                           eWeaponModType             mod,
                                           GameCode.XWeaponInst       weaponInst)
        {
            if (index < 0 || index >= defs.Length) return;
            bool hasMod = false;
            Plugin.Guard($"InventoryInjector.SwordHasMod[{mod}]", () =>
                hasMod = weaponInst.HasMod(mod));
            if (!hasMod) return;
            var d = defs[index];
            if (d == null) return;
            if (!seenIds.Contains(d.Id))
            {
                labeled.Add(new LabeledAttack(d, mod));
                seenIds.Add(d.Id);
            }
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
