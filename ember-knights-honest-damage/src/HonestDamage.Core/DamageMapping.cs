using System.Collections.Generic;

namespace HonestDamage.Core
{
    public static class DamageMapping
    {
        public static IReadOnlyList<Attrib> ScalingAttribs(DamageKind kind)
        {
            switch (kind)
            {
                case DamageKind.WeaponAttack:
                    return new[] { Attrib.ATK, Attrib.FinalPlayerDamageMultiplier };
                case DamageKind.Ability:
                    return new[] { Attrib.ATK, Attrib.AbilityNumHitsModifier, Attrib.FinalPlayerDamageMultiplier };
                case DamageKind.Spell:
                    return new[] { Attrib.SpellDamageModifier, Attrib.FinalPlayerDamageMultiplier };
                case DamageKind.Throw:
                    return new[] { Attrib.ATK, Attrib.ThrowDamageModifier, Attrib.FinalPlayerDamageMultiplier };
                case DamageKind.Pet:
                    return new[] { Attrib.FinalPlayerDamageMultiplier };
                default:
                    return new Attrib[0];
            }
        }
    }
}
