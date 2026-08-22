using System.Collections.Generic;

namespace HonestDamage.Core
{
    public static class DamageMapping
    {
        private static readonly IReadOnlyList<Attrib> WeaponAttackAttribs =
            new[] { Attrib.ATK, Attrib.FinalPlayerDamageMultiplier };

        private static readonly IReadOnlyList<Attrib> AbilityAttribs =
            new[] { Attrib.ATK, Attrib.AbilityNumHitsModifier, Attrib.FinalPlayerDamageMultiplier };

        private static readonly IReadOnlyList<Attrib> SpellAttribs =
            new[] { Attrib.SpellDamageModifier, Attrib.FinalPlayerDamageMultiplier };

        private static readonly IReadOnlyList<Attrib> ThrowAttribs =
            new[] { Attrib.ATK, Attrib.ThrowDamageModifier, Attrib.FinalPlayerDamageMultiplier };

        private static readonly IReadOnlyList<Attrib> PetAttribs =
            new[] { Attrib.FinalPlayerDamageMultiplier };

        private static readonly IReadOnlyList<Attrib> EmptyAttribs =
            new Attrib[0];

        public static IReadOnlyList<Attrib> ScalingAttribs(DamageKind kind)
        {
            switch (kind)
            {
                case DamageKind.WeaponAttack:
                    return WeaponAttackAttribs;
                case DamageKind.Ability:
                    return AbilityAttribs;
                case DamageKind.Spell:
                    return SpellAttribs;
                case DamageKind.Throw:
                    return ThrowAttribs;
                case DamageKind.Pet:
                    return PetAttribs;
                default:
                    return EmptyAttribs;
            }
        }
    }
}
