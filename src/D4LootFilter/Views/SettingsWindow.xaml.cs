using System.ComponentModel;
using System.Windows;

namespace D4LootFilter.Views;

public partial class SettingsWindow : Window
{
    public SettingsWindow()
    {
        InitializeComponent();
    }

    protected override void OnClosing(CancelEventArgs e)
    {
        e.Cancel = true;
        Hide();
    }

    public void ShowOnTab(int tabIndex)
    {
        Show();
        Activate();
        if (tabIndex >= 0 && tabIndex < MainTabs.Items.Count)
            MainTabs.SelectedIndex = tabIndex;
    }
}
