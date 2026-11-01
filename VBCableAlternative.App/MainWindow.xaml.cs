using System.Collections.ObjectModel;
using System.Windows;
using VBCableAlternative.Core;

namespace VBCableAlternative.App
{
    public partial class MainWindow : Window
    {
        public ObservableCollection<VirtualCableRoute> Routes { get; } = new();
        public ObservableCollection<string> InputDevices { get; } = new();
        public ObservableCollection<string> OutputDevices { get; } = new();

        public MainWindow()
        {
            InitializeComponent();
            DataContext = this;
            Title = "VB-CABLE Prototype";
            LoadDefaultDevices();
        }

        private void LoadDefaultDevices()
        {
            InputDevices.Clear();
            OutputDevices.Clear();

            foreach (var device in VirtualCableCatalog.GetExampleInputDevices())
            {
                InputDevices.Add(device);
            }

            foreach (var device in VirtualCableCatalog.GetExampleOutputDevices())
            {
                OutputDevices.Add(device);
            }

            Routes.Clear();
            foreach (var route in VirtualCableCatalog.BuildDefaultRoutes())
            {
                Routes.Add(route);
            }
        }

        private void RefreshButton_Click(object sender, RoutedEventArgs e)
        {
            LoadDefaultDevices();
        }

        private void ButtonExit_Click(object sender, RoutedEventArgs e)
        {
            Application.Current.Shutdown();
        }
    }
}
