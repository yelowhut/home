using HonestDamage.Core;
using Xunit;

public class DamageModelTests
{
    private static StatSnapshot Stats(params (Attrib a, float v)[] vals)
    {
        var arr = new float[(int)Attrib.Count];
        foreach (var (a, v) in vals) arr[(int)a] = v;
        return new StatSnapshot(arr);
    }

    [Fact]
    public void Compute_Weapon_ScalesByAtkPercent()
    {
        var stats = Stats((Attrib.ATK, 200f), (Attrib.FinalPlayerDamageMultiplier, 1f));
        // base 50 * (200/100) * 1 = 100
        Assert.Equal(100f, DamageModel.Compute(DamageKind.WeaponAttack, 50f, stats));
    }

    [Fact]
    public void Compute_TreatsZeroModifierAsNeutral()
    {
        var stats = Stats((Attrib.ATK, 100f)); // FinalPlayerDamageMultiplier = 0 -> neutral
        // base 50 * (100/100) * 1 = 50
        Assert.Equal(50f, DamageModel.Compute(DamageKind.WeaponAttack, 50f, stats));
    }

    [Fact]
    public void Compute_Spell_UsesSpellModifier()
    {
        var stats = Stats((Attrib.SpellDamageModifier, 1.5f));
        // base 80 * 1.5 = 120
        Assert.Equal(120f, DamageModel.Compute(DamageKind.Spell, 80f, stats));
    }

    [Fact]
    public void Compute_Spell_AppliesFinalPlayerDamageMultiplier()
    {
        var stats = Stats((Attrib.SpellDamageModifier, 2f), (Attrib.FinalPlayerDamageMultiplier, 1.5f));
        // base 80 * 2 * 1.5 = 240
        Assert.Equal(240f, DamageModel.Compute(DamageKind.Spell, 80f, stats));
    }
}
