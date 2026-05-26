using System.Text.RegularExpressions;

namespace D4LootFilter.Scraper;

public static partial class UrlParser
{
    [GeneratedRegex(@"(?:https?://)?mobalytics\.gg/diablo-4/builds/([a-z0-9][a-z0-9\-]+[a-z0-9])/?(?:\?.*)?$", RegexOptions.IgnoreCase)]
    private static partial Regex BuildUrlRegex();

    public static string ParseSlug(string url)
    {
        var match = BuildUrlRegex().Match(url);
        if (!match.Success)
            throw new ArgumentException($"Invalid Mobalytics build URL: {url}");
        return match.Groups[1].Value;
    }
}
