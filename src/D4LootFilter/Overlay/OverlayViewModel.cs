using System.Collections.ObjectModel;
using System.ComponentModel;
using System.Runtime.CompilerServices;
using D4LootFilter.Matching;

namespace D4LootFilter.Overlay;

public class OverlayViewModel : INotifyPropertyChanged
{
    private bool _isVisible;
    private string _buildName = "";
    private string _slotName = "";
    private int _matchedCount;
    private int _totalCount;
    private int _gaMatchedCount;
    private ObservableCollection<AffixHighlight> _highlights = [];
    private ObservableCollection<string> _missingAffixes = [];

    public bool IsVisible
    {
        get => _isVisible;
        set => SetField(ref _isVisible, value);
    }

    public string BuildName
    {
        get => _buildName;
        set => SetField(ref _buildName, value);
    }

    public string SlotName
    {
        get => _slotName;
        set => SetField(ref _slotName, value);
    }

    public int MatchedCount
    {
        get => _matchedCount;
        set => SetField(ref _matchedCount, value);
    }

    public int TotalCount
    {
        get => _totalCount;
        set => SetField(ref _totalCount, value);
    }

    public int GaMatchedCount
    {
        get => _gaMatchedCount;
        set => SetField(ref _gaMatchedCount, value);
    }

    public ObservableCollection<AffixHighlight> Highlights
    {
        get => _highlights;
        set => SetField(ref _highlights, value);
    }

    public ObservableCollection<string> MissingAffixes
    {
        get => _missingAffixes;
        set => SetField(ref _missingAffixes, value);
    }

    public void Update(List<AffixMatchResult> results, MatchSummary summary, string buildName, string slotName,
        System.Drawing.Rectangle captureRegion, List<System.Drawing.Rectangle> boundingBoxes)
    {
        BuildName = buildName;
        SlotName = slotName;
        MatchedCount = summary.MatchedCount;
        TotalCount = summary.TotalBuildAffixes;
        GaMatchedCount = summary.GaMatchedCount;
        MissingAffixes = new ObservableCollection<string>(summary.MissingAffixes);

        var newHighlights = new ObservableCollection<AffixHighlight>();
        for (int i = 0; i < results.Count; i++)
        {
            var r = results[i];
            if (!r.IsMatched) continue;

            var bbox = i < boundingBoxes.Count ? boundingBoxes[i] : new System.Drawing.Rectangle();
            newHighlights.Add(new AffixHighlight
            {
                Text = r.AffixName,
                IsGa = r.IsGa,
                Left = captureRegion.X + bbox.X / 2.0,
                Top = captureRegion.Y + bbox.Y / 2.0,
                Width = bbox.Width / 2.0,
                Height = bbox.Height / 2.0,
            });
        }
        Highlights = newHighlights;
        IsVisible = results.Any(r => r.IsMatched);
    }

    public void Hide()
    {
        IsVisible = false;
        Highlights.Clear();
    }

    public event PropertyChangedEventHandler? PropertyChanged;

    private void SetField<T>(ref T field, T value, [CallerMemberName] string? name = null)
    {
        if (!EqualityComparer<T>.Default.Equals(field, value))
        {
            field = value;
            PropertyChanged?.Invoke(this, new PropertyChangedEventArgs(name));
        }
    }
}

public class AffixHighlight : INotifyPropertyChanged
{
    public string Text { get; set; } = "";
    public bool IsGa { get; set; }
    public double Left { get; set; }
    public double Top { get; set; }
    public double Width { get; set; }
    public double Height { get; set; }

    public event PropertyChangedEventHandler? PropertyChanged;
}
