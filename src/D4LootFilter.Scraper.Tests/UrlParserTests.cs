// src/D4LootFilter.Scraper.Tests/UrlParserTests.cs
namespace D4LootFilter.Scraper.Tests;

public class UrlParserTests
{
    [Theory]
    [InlineData("https://mobalytics.gg/diablo-4/builds/barbarian-whirl-wind-barb", "barbarian-whirl-wind-barb")]
    [InlineData("https://mobalytics.gg/diablo-4/builds/sorcerer-ball-lightning", "sorcerer-ball-lightning")]
    [InlineData("https://mobalytics.gg/diablo-4/builds/barbarian-whirl-wind-barb?ws-ngf5-1=activeVariantId,5", "barbarian-whirl-wind-barb")]
    [InlineData("http://mobalytics.gg/diablo-4/builds/some-build", "some-build")]
    [InlineData("mobalytics.gg/diablo-4/builds/some-build", "some-build")]
    [InlineData("https://mobalytics.gg/diablo-4/builds/some-build/", "some-build")]
    public void ParseSlug_ValidUrls_ReturnsSlug(string url, string expectedSlug)
    {
        var result = UrlParser.ParseSlug(url);
        Assert.Equal(expectedSlug, result);
    }

    [Theory]
    [InlineData("https://google.com/something")]
    [InlineData("https://mobalytics.gg/diablo-4/tier-list")]
    [InlineData("https://mobalytics.gg/diablo-4/builds/")]
    [InlineData("https://mobalytics.gg/diablo-4/builds")]
    [InlineData("")]
    [InlineData("not-a-url")]
    public void ParseSlug_InvalidUrls_ThrowsArgumentException(string url)
    {
        Assert.Throws<ArgumentException>(() => UrlParser.ParseSlug(url));
    }
}
