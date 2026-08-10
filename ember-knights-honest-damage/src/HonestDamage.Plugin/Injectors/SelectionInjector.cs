using System;
using System.Text.RegularExpressions;
using TMPro;
using UnityEngine;

namespace HonestDamage.Plugin.Injectors
{
    /// <summary>
    /// Etap-2 Task 1 — Selection-screen UI injector.
    ///
    /// Attaches an additive "HD_Honest" sibling label under each Damage TMP on the
    /// UIItemSelect(Clone) canvas showing stat-scaled ("honest") damage values.
    ///
    /// Type notes (confirmed from dump.cs / Il2CppDumper, TypeDefIndex 3052):
    ///   UIItemSelectSlotRefs — global namespace (no enclosing class/namespace)
    ///   .Damage field        — UITinyText (global namespace, TypeDefIndex 3631)
    ///   UITinyText.TMPText   — TextMeshProUGUI (the actual TMP component)
    ///
    /// Polling strategy: Tick() is called from TickComponent.Update() at most every
    /// InjectorTickInterval frames (~5×/sec at 60 fps).  FindObjectsOfType scan is
    /// never per-frame.
    ///
    /// Scaling: skills scale with SpellDamageModifier (attribs.Get(eAttrib.SpellDamageModifier)).
    /// [calibrate] This is provisional — may need separate multiplier per skill type once
    /// damage log calibration (etap-2 task 2) is complete.
    /// </summary>
    public static class SelectionInjector
    {
        // ---- Regex for parsing base damage numbers from TMP text ----------

        // First: strip all rich-text tags (e.g. <color=#00FF00>) so we don't match
        // hex digits inside tag attributes.
        private static readonly Regex _tagStripper = new Regex(@"<[^>]*>", RegexOptions.Compiled);

        // Then: extract all decimal integers (unsigned, 1+ digits).
        private static readonly Regex _numExtractor = new Regex(@"\d+", RegexOptions.Compiled);

        // ---- Constants ----------------------------------------------------

        private const string LabelName = "HD_Honest";

        // Cyan colour for injected label
        private static readonly Color HonestColor = new Color(0f, 1f, 1f, 1f);

        // ---- Public entry point -------------------------------------------

        /// <summary>
        /// Called from TickComponent.Update() every N frames (caller is responsible
        /// for the frame-throttle).  All exceptions are swallowed via Plugin.Guard.
        /// </summary>
        public static void Tick()
        {
            Plugin.Guard("SelectionInjector.Tick", () =>
            {
                if (!Plugin.OverlayEnabled || !Plugin.EnableRewards.Value)
                    return;

                var attribs = PlayerLocator.GetLocalAttribs();
                if (attribs == null)
                    return; // player not yet cached — silent skip (user hasn't been hit yet)

                // SpellDamageModifier is the current stat-scale for skill base damage.
                // [calibrate] Provisional — confirm vs damage-log when calibration is done.
                float scale = attribs.Get(eAttrib.SpellDamageModifier);

                // FindObjectsOfType returns all active AND inactive instances;
                // we filter by activeInHierarchy below.
                // Type: UIItemSelectSlotRefs is in the global namespace (confirmed dump.cs
                // TypeDefIndex 3052, "// Namespace: " empty).
                var slots = UnityEngine.Object.FindObjectsOfType<UIItemSelectSlotRefs>();
                if (slots == null) return;

                foreach (var slot in slots)
                {
                    Plugin.Guard("SelectionInjector.ProcessSlot", () =>
                    {
                        if (slot == null) return;
                        if (!slot.gameObject.activeInHierarchy) return;

                        ProcessSlot(slot, scale);
                    });
                }
            });
        }

        // ---- Per-slot logic ----------------------------------------------

        private static void ProcessSlot(UIItemSelectSlotRefs slot, float scale)
        {
            // Access the Damage UITinyText field directly from the slot refs struct.
            // UIItemSelectSlotRefs.Damage : UITinyText (offset 0xC8 per dump.cs).
            UITinyText? damageWidget = slot.Damage;
            if (damageWidget == null) return;

            // UITinyText.TMPText is the underlying TextMeshProUGUI (offset 0x30).
            TextMeshProUGUI? tmp = damageWidget.TMPText;
            if (tmp == null) return;

            // Skip if the TMP is on an inactive GameObject.
            if (!tmp.gameObject.activeInHierarchy) return;

            string rawText = tmp.text;
            if (string.IsNullOrEmpty(rawText)) return;

            // Strip rich-text tags (e.g. <color=#00FF00>) before number extraction
            // to avoid matching hex digits in colour attributes.
            string stripped = _tagStripper.Replace(rawText, "");

            // Skip empty slots: "Damage:" with no numbers.
            var numMatches = _numExtractor.Matches(stripped);
            if (numMatches.Count == 0) return;

            // Build the scaled string (e.g. "≈ 10/13/16 with stats").
            // Round to nearest integer — sub-integer precision is noise at this level.
            var sb = new System.Text.StringBuilder("≈ ");
            for (int i = 0; i < numMatches.Count; i++)
            {
                if (i > 0) sb.Append('/');
                if (int.TryParse(numMatches[i].Value, out int baseVal))
                {
                    int scaled = Mathf.RoundToInt(baseVal * scale);
                    sb.Append(scaled);
                }
                else
                {
                    sb.Append(numMatches[i].Value); // fallback: keep digits as-is
                }
            }
            sb.Append(" with stats");
            string honestText = sb.ToString();

            // ---- Attach or update the HD_Honest sibling label ------------

            // The label lives as a sibling of the TMPText's GameObject (same parent),
            // so it doesn't interfere with the Damage node's own layout.
            Transform? tmpParent = tmp.gameObject.transform.parent;
            if (tmpParent == null) return;

            // Check for an existing label (idempotent).
            Transform? existingLabel = FindDirectChild(tmpParent, LabelName);

            if (existingLabel != null)
            {
                // Update text in-place — no re-instantiation.
                var existingTmp = existingLabel.gameObject.GetComponent<TextMeshProUGUI>();
                if (existingTmp != null)
                    existingTmp.text = honestText;
            }
            else
            {
                // First injection: Instantiate a clone of the TMP's GameObject as a sibling.
                // Cloning inherits font asset, material, RectTransform sizing — guaranteed
                // visible.  A bare AddComponent<TextMeshProUGUI>() has no font and is invisible.
                Plugin.Guard("SelectionInjector.Instantiate", () =>
                {
                    GameObject clone = UnityEngine.Object.Instantiate(
                        tmp.gameObject,
                        tmpParent);
                    clone.name = LabelName;

                    var cloneTmp = clone.GetComponent<TextMeshProUGUI>();
                    if (cloneTmp == null) return;

                    cloneTmp.text = honestText;
                    cloneTmp.color = HonestColor;

                    // Slightly smaller font so it reads as secondary information.
                    cloneTmp.fontSize = Mathf.Max(8f, cloneTmp.fontSize * 0.85f);

                    // Ensure the clone is active even if the source object was inactive.
                    clone.SetActive(true);
                });
            }
        }

        // ---- Hierarchy helper --------------------------------------------

        /// <summary>
        /// Finds a direct child (non-recursive) of <paramref name="parent"/> by name.
        /// </summary>
        private static Transform? FindDirectChild(Transform parent, string name)
        {
            if (parent == null) return null;
            for (int i = 0; i < parent.childCount; i++)
            {
                Transform child = parent.GetChild(i);
                if (child != null && child.name == name) return child;
            }
            return null;
        }
    }
}
