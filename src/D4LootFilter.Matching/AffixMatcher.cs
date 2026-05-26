using D4LootFilter.Matching.Models;
using FuzzySharp;

namespace D4LootFilter.Matching;

public class AffixMatcher
{
    private readonly AffixNormalizer _normalizer = new();
    private int _maxDistance;
    public int MaxDistance { get => _maxDistance; set => _maxDistance = value; }

    public AffixMatcher(int maxDistance = 2)
    {
        _maxDistance = maxDistance;
    }

    public List<AffixMatchResult> Match(IReadOnlyList<string> ocrLines, List<Affix> buildAffixes)
    {
        var results = new List<AffixMatchResult>();
        var normalizedBuildAffixes = buildAffixes
            .Select(a => (Affix: a, Normalized: a.Name.ToLowerInvariant()))
            .ToList();

        for (int i = 0; i < ocrLines.Count; i++)
        {
            var line = ocrLines[i];
            if (!_normalizer.IsLikelyAffix(line))
                continue;

            var normalized = _normalizer.Normalize(line);
            if (string.IsNullOrWhiteSpace(normalized))
                continue;

            var bestMatch = FindBestMatch(normalized, normalizedBuildAffixes);
            if (bestMatch != null)
            {
                results.Add(new AffixMatchResult(line, bestMatch.Value.Affix.Name, bestMatch.Value.Affix.IsGa, true, i));
            }
            else
            {
                results.Add(new AffixMatchResult(line, normalized, false, false, i));
            }
        }

        return results;
    }

    private (Affix Affix, string Normalized)? FindBestMatch(
        string normalized,
        List<(Affix Affix, string Normalized)> buildAffixes)
    {
        var exact = buildAffixes.FirstOrDefault(b => b.Normalized == normalized);
        if (exact.Affix != null)
            return exact;

        foreach (var candidate in buildAffixes)
        {
            var distance = Fuzz.Ratio(normalized, candidate.Normalized);
            if (distance >= 85)
                return candidate;
        }

        foreach (var candidate in buildAffixes)
        {
            if (normalized.Contains(candidate.Normalized) || candidate.Normalized.Contains(normalized))
                return candidate;
        }

        return null;
    }

    public static MatchSummary Summarize(List<AffixMatchResult> results, List<Affix> buildAffixes)
    {
        var matchedNames = results.Where(r => r.IsMatched).Select(r => r.AffixName).ToHashSet();
        var missing = buildAffixes
            .Where(a => !matchedNames.Contains(a.Name))
            .Select(a => a.Name)
            .ToList();

        return new MatchSummary(
            MatchedCount: results.Count(r => r.IsMatched),
            TotalBuildAffixes: buildAffixes.Count,
            GaMatchedCount: results.Count(r => r.IsMatched && r.IsGa),
            MissingAffixes: missing
        );
    }
}
