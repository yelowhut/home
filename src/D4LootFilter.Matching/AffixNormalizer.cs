using System.Text.RegularExpressions;

namespace D4LootFilter.Matching;

public partial class AffixNormalizer
{
    [GeneratedRegex(@"^.*?(?=[+\-]\d)")]
    private static partial Regex LeadingGlyphsRegex();

    [GeneratedRegex(@"^[+\-]?[\d,.]+%?\s*")]
    private static partial Regex LeadingNumbersRegex();

    [GeneratedRegex(@"\s*[+\-]?\[[\d\s,.\-]+\].*$")]
    private static partial Regex TrailingRangeRegex();

    [GeneratedRegex(@"^[^+\-a-zA-Z0-9]*[+\-][\d]")]
    private static partial Regex AffixPatternRegex();

    public string Normalize(string ocrLine)
    {
        var text = LeadingGlyphsRegex().Replace(ocrLine, "");
        text = LeadingNumbersRegex().Replace(text, "");
        text = TrailingRangeRegex().Replace(text, "");
        return text.Trim().ToLowerInvariant();
    }

    public bool IsLikelyAffix(string ocrLine)
    {
        return AffixPatternRegex().IsMatch(ocrLine);
    }
}
