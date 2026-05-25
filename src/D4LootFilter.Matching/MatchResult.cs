namespace D4LootFilter.Matching;

public record AffixMatchResult(
    string OcrText,
    string AffixName,
    bool IsGa,
    bool IsMatched,
    int LineIndex
);

public record MatchSummary(
    int MatchedCount,
    int TotalBuildAffixes,
    int GaMatchedCount,
    List<string> MissingAffixes
);
