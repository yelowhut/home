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
