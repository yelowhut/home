namespace HonestDamage.Core
{
    // Значения соответствуют игровому eAttrib (см. dump.cs). Порядок важен только
    // для маппинга в адаптере; в Core используем как непрозрачный ключ.
    public enum Attrib
    {
        None = 0, ATK, ATKRate, DEF, MaxHP, MaxCurses, CritChance, CritDmgMUL,
        MoveSpeed, MoveSpeedMUL, AbilityNumHitsModifier, SpellDamageModifier,
        RareDropModifier, EpicDropModifier, LegendaryDropModifier, GoldDropModifier,
        SmallHeartDropModifier, LargeHeartDropModifier, SmallHpPotionDropModifier,
        LargeHpPotionDropModifier, SmallManaPotionDropModifier, LargeManaPotionDropModifier,
        SpellCooldownModifier, BonusHealingModifier, ThrowDamageModifier,
        ChargeDurationModifier, BlockChance, SmallStatPotionDropModifier,
        LargeStatPotionDropModifier, HealingPrevented, EnemyAbilityCooldownModifier,
        EnemyFinalDamageMultiplier, SkillChargeIncrease, BonusBurnDamageModifier,
        MagicDEF, EnemyATKModifier, MaxArmor, UNUSED_1, FinalPlayerDamageMultiplier,
        MaxWisps, MaxKitsunes, MaxHydras, MaxYalee, Count
    }

    public enum ModOp { Add = 0, Mul = 1 }
}
