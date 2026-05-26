using System.Windows;
using System.Windows.Controls;
using D4LootFilter.ViewModels;

namespace D4LootFilter.Views;

public partial class ProfilesView : UserControl
{
    public ProfilesView()
    {
        InitializeComponent();
    }

    private async void OnImportClick(object sender, RoutedEventArgs e)
    {
        if (DataContext is ProfilesViewModel vm)
            await vm.ImportAsync();
    }

    private void OnActivateClick(object sender, RoutedEventArgs e)
    {
        if (DataContext is ProfilesViewModel vm)
            vm.Activate();
    }

    private void OnDeleteClick(object sender, RoutedEventArgs e)
    {
        if (DataContext is ProfilesViewModel vm)
            vm.Delete();
    }
}
