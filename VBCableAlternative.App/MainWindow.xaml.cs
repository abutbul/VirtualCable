using System.Collections.ObjectModel;
using System.Diagnostics;
using System.IO;
using System.Windows;

namespace VBCableAlternative.App
{
    public partial class MainWindow : Window
    {
        private readonly ObservableCollection<CableEndpointStatus> _cables = new();
        private readonly string _installerPath = Path.Combine(AppContext.BaseDirectory, "Install-Cable.ps1");

        public MainWindow()
        {
            InitializeComponent();
            EndpointGrid.ItemsSource = _cables;
            for (var index = 0; index < 4; index++)
            {
                var name = $"CABLE-{(char)('A' + index)}";
                _cables.Add(new CableEndpointStatus(name, $"{name} Input", $"{name} Output"));
            }

            Loaded += async (_, _) => await RefreshStatusAsync();
        }

        private async Task RefreshStatusAsync()
        {
            SetBusy(true);
            try
            {
                var startInfo = new ProcessStartInfo
                {
                    FileName = "powershell.exe",
                    Arguments = "-NoProfile -NonInteractive -Command \"Get-PnpDevice -Class AudioEndpoint -ErrorAction SilentlyContinue | ForEach-Object { $_.FriendlyName }\"",
                    UseShellExecute = false,
                    RedirectStandardOutput = true,
                    RedirectStandardError = true,
                    CreateNoWindow = true
                };

                using var process = Process.Start(startInfo);
                if (process is null)
                {
                    throw new InvalidOperationException("Could not start PowerShell to check endpoint status.");
                }

                var output = await process.StandardOutput.ReadToEndAsync();
                var error = await process.StandardError.ReadToEndAsync();
                await process.WaitForExitAsync();
                if (process.ExitCode != 0)
                {
                    throw new InvalidOperationException(string.IsNullOrWhiteSpace(error) ? "Windows endpoint query failed." : error.Trim());
                }

                var endpoints = output.Split(Environment.NewLine, StringSplitOptions.RemoveEmptyEntries)
                    .Select(name => name.Trim())
                    .ToHashSet(StringComparer.OrdinalIgnoreCase);
                foreach (var cable in _cables)
                {
                    cable.Update(endpoints);
                }

                var installedCount = _cables.Count(cable => cable.IsInstalled);
                StatusText.Text = installedCount == 4
                    ? "All four cable pairs are installed"
                    : installedCount == 0
                        ? "Driver endpoints are not installed"
                        : $"Detected {installedCount} of 4 cable pairs";
                StatusIndicator.Fill = installedCount == 4
                    ? System.Windows.Media.Brushes.SeaGreen
                    : installedCount == 0
                        ? System.Windows.Media.Brushes.SlateGray
                        : System.Windows.Media.Brushes.DarkOrange;
            }
            catch (Exception exception)
            {
                StatusText.Text = $"Status check failed: {exception.Message}";
                StatusIndicator.Fill = System.Windows.Media.Brushes.Firebrick;
            }
            finally
            {
                SetBusy(false);
                EndpointGrid.Items.Refresh();
            }
        }

        private async Task RunInstallerAsync(bool uninstall)
        {
            if (!File.Exists(_installerPath))
            {
                MessageBox.Show(this,
                    "Install-Cable.ps1 was not found. Extract the complete manager and driver ZIP before using these actions.",
                    "Driver package missing", MessageBoxButton.OK, MessageBoxImage.Error);
                return;
            }

            var action = uninstall ? "uninstall" : "install";
            var confirmation = MessageBox.Show(this,
                $"Windows will ask for administrator approval to {action} the four virtual cable pairs.",
                $"Confirm driver {action}", MessageBoxButton.OKCancel, MessageBoxImage.Warning);
            if (confirmation != MessageBoxResult.OK)
            {
                return;
            }

            try
            {
                var arguments = $"-ExecutionPolicy Bypass -File \"{_installerPath}\"" + (uninstall ? " -Uninstall" : string.Empty);
                var startInfo = new ProcessStartInfo("powershell.exe", arguments)
                {
                    UseShellExecute = true,
                    Verb = "runas",
                    WorkingDirectory = AppContext.BaseDirectory
                };
                using var process = Process.Start(startInfo);
                if (process is null)
                {
                    throw new InvalidOperationException("The elevated installer process did not start.");
                }

                await process.WaitForExitAsync();
                if (process.ExitCode != 0)
                {
                    throw new InvalidOperationException($"Installer exited with code {process.ExitCode}.");
                }

                StatusText.Text = "Driver action completed. Refreshing endpoints...";
                await RefreshStatusAsync();
            }
            catch (System.ComponentModel.Win32Exception exception) when (exception.NativeErrorCode == 1223)
            {
                StatusText.Text = "Administrator approval was cancelled.";
            }
            catch (Exception exception)
            {
                MessageBox.Show(this, exception.Message, "Driver action failed", MessageBoxButton.OK, MessageBoxImage.Error);
                await RefreshStatusAsync();
            }
        }

        private void SetBusy(bool busy)
        {
            RefreshButton.IsEnabled = !busy;
            InstallButton.IsEnabled = !busy;
            UninstallButton.IsEnabled = !busy;
        }

        private async void RefreshButton_Click(object sender, RoutedEventArgs e)
        {
            await RefreshStatusAsync();
        }

        private async void InstallButton_Click(object sender, RoutedEventArgs e)
        {
            await RunInstallerAsync(uninstall: false);
        }

        private async void UninstallButton_Click(object sender, RoutedEventArgs e)
        {
            await RunInstallerAsync(uninstall: true);
        }
    }

    public sealed class CableEndpointStatus(string name, string input, string output)
    {
        public string Name { get; } = name;
        public string Input { get; } = input;
        public string Output { get; } = output;
        public string Status { get; private set; } = "Checking";
        public bool IsInstalled { get; private set; }

        public void Update(HashSet<string> installedEndpoints)
        {
            var hasInput = installedEndpoints.Contains(Input);
            var hasOutput = installedEndpoints.Contains(Output);
            IsInstalled = hasInput && hasOutput;
            Status = IsInstalled ? "Installed" : hasInput || hasOutput ? "Incomplete" : "Not installed";
        }
    }
}
