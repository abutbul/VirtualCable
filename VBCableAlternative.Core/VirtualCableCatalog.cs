namespace VBCableAlternative.Core;

public sealed class VirtualCableRoute
{
    public string Name { get; init; } = string.Empty;
    public string Summary { get; init; } = string.Empty;
    public string InputDevice { get; set; } = string.Empty;
    public string OutputDevice { get; set; } = string.Empty;
    public bool Enabled { get; set; } = true;
}

public static class VirtualCableCatalog
{
    public static IReadOnlyList<string> GetExampleInputDevices() => new[]
    {
        "CABLE Input",
        "Microphone (USB)",
        "System Default Input"
    };

    public static IReadOnlyList<string> GetExampleOutputDevices() => new[]
    {
        "CABLE Output",
        "Speakers (Realtek)",
        "Headphones (USB)"
    };

    public static IReadOnlyList<VirtualCableRoute> BuildDefaultRoutes() => new[]
    {
        new VirtualCableRoute
        {
            Name = "VB-CABLE",
            Summary = "Playback audio sent to CABLE Input is exposed to recording apps through CABLE Output.",
            InputDevice = "CABLE Input",
            OutputDevice = "CABLE Output",
            Enabled = true
        }
    };
}
