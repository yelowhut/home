using System.Collections.Generic;
using HonestDamage.Core;
using Xunit;

public class AttribResolverTests
{
    [Fact]
    public void Resolve_NoMods_ReturnsBase()
    {
        Assert.Equal(100f, AttribResolver.Resolve(100f, new Modifier[0], Attrib.ATK));
    }

    [Fact]
    public void Resolve_SumsAdd_ThenMultipliesMul()
    {
        var mods = new[]
        {
            new Modifier(Attrib.ATK, 50f, ModOp.Add),
            new Modifier(Attrib.ATK, 1.2f, ModOp.Mul),
        };
        // (100 + 50) * 1.2 = 180
        Assert.Equal(180f, AttribResolver.Resolve(100f, mods, Attrib.ATK));
    }

    [Fact]
    public void Resolve_IgnoresOtherAttribs()
    {
        var mods = new[] { new Modifier(Attrib.CritChance, 99f, ModOp.Add) };
        Assert.Equal(100f, AttribResolver.Resolve(100f, mods, Attrib.ATK));
    }

    [Fact]
    public void ResolveWith_AddsExtraOnTopOfCurrent()
    {
        var current = new[] { new Modifier(Attrib.ATK, 50f, ModOp.Add) };
        var extra = new[] { new Modifier(Attrib.ATK, 1.5f, ModOp.Mul) };
        // (100 + 50) * 1.5 = 225
        Assert.Equal(225f, AttribResolver.ResolveWith(100f, current, extra, Attrib.ATK));
    }
}
