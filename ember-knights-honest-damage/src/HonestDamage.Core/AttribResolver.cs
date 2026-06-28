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
