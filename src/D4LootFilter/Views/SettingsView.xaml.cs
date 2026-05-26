using System.Windows;
using System.Windows.Controls;
using D4LootFilter.ViewModels;

namespace D4LootFilter.Views;

public partial class SettingsView : UserControl
{
    public SettingsView()
    {
        InitializeComponent();
    }

    private void OnSave(object sender, RoutedEventArgs e)
    {
        if (DataContext is SettingsViewModel vm) vm.Save();
    }

    private void OnReset(object sender, RoutedEventArgs e)
    {
        if (DataContext is SettingsViewModel vm) vm.ResetToDefaults();
    }
}
