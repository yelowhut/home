namespace D4LootFilter.Scraper.Tests;

public class MobalyticsClientTests
{
    [Trait("Category", "Integration")]
    [Fact]
    public async Task FetchBuildAsync_LiveApi_ReturnsValidResponse()
    {
        var client = new MobalyticsClient();

        var json = await client.FetchBuildAsync("barbarian-whirl-wind-barb");

        Assert.Contains("buildVariants", json);
        Assert.Contains("genericBuilder", json);
        Assert.Contains("gearStats", json);
    }

    [Trait("Category", "Integration")]
    [Fact]
    public async Task FetchBuildAsync_LiveApi_ContainsVariantNames()
    {
        var client = new MobalyticsClient();

        var json = await client.FetchBuildAsync("barbarian-whirl-wind-barb");

        Assert.Contains("childrenVariants", json);
    }
}
