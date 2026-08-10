using System;
using System.Collections.Generic;
using Il2CppInterop.Runtime.InteropTypes.Arrays;
using HonestDamage.Core;

namespace HonestDamage.Plugin
{
    /// <summary>
    /// Adapts live IL2CPP game objects to Core domain types.
    ///
    /// Namespace notes (confirmed by compile testing against interop DLLs):
    ///   - XAttribsCMP, XEntity, XWorld  → GameCode.* (nested in the GameCode class)
    ///   - XAttribModifier, XAttribModDef → global namespace
    ///   - eAttrib, eAttribModOperator    → global namespace
    ///   - DamageParams                   → global namespace
    /// </summary>
    public static class GameDataAdapter
    {
        /// <summary>
        /// Snapshot all attribute values from the live component.
        /// </summary>
        public static StatSnapshot Snapshot(GameCode.XAttribsCMP cmp)
        {
            var arr = new float[(int)Attrib.Count];
            for (int i = 0; i < arr.Length; i++)
            {
                int idx = i; // capture for lambda
                Plugin.Guard($"Snapshot[{idx}]", () =>
                {
                    arr[idx] = cmp.Get((eAttrib)idx);
                });
            }
            return new StatSnapshot(arr);
        }

        /// <summary>
        /// Snapshot all raw (base) attribute values (before modifiers).
        /// Used by the [ATTRIBS] section to show game.Get vs AttribResolver.Resolve.
        /// </summary>
        public static float[] RawSnapshot(GameCode.XAttribsCMP cmp)
        {
            var arr = new float[(int)Attrib.Count];
            for (int i = 0; i < arr.Length; i++)
            {
                int idx = i;
                Plugin.Guard($"RawSnapshot[{idx}]", () =>
                {
                    arr[idx] = cmp.GetRaw((eAttrib)idx);
                });
            }
            return arr;
        }

        /// <summary>
        /// Flattens the modifiersByAttrib dictionary into a flat Modifier list.
        /// eAttribModOperator.ADD=0 maps to ModOp.Add; MUL=1 maps to ModOp.Mul.
        /// </summary>
        public static List<Modifier> CurrentModifiers(GameCode.XAttribsCMP cmp)
        {
            var list = new List<Modifier>();
            Plugin.Guard("CurrentModifiers", () =>
            {
                foreach (var kv in cmp.modifiersByAttrib)
                {
                    foreach (var m in kv.Value)
                    {
                        list.Add(new Modifier(
                            (Attrib)(int)m.Attrib,
                            m.Value,
                            (ModOp)(int)m.Operator));
                    }
                }
            });
            return list;
        }

        /// <summary>
        /// Builds hypothetical modifiers from an XAttribModDef array (what-if / weapon preview).
        /// value = def.Value + def.Upgrade * upgradeCount
        /// </summary>
        public static List<Modifier> ModifiersFromDef(Il2CppReferenceArray<XAttribModDef> defs, int upgradeCount)
        {
            var list = new List<Modifier>();
            if (defs == null) return list;
            foreach (var d in defs)
            {
                if (d == null) continue;
                float val = d.Value + d.Upgrade * upgradeCount;
                list.Add(new Modifier(
                    (Attrib)(int)d.Attrib,
                    val,
                    (ModOp)(int)d.Operator));
            }
            return list;
        }
    }
}
