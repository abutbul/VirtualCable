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
        "CABLE-A Input",
        "CABLE-B Input",
        "Microphone (USB)",
        "System Default Input"
    };

    public static IReadOnlyList<string> GetExampleOutputDevices() => new[]
    {
        "CABLE-A Output",
        "CABLE-B",
        "Speakers (Realtek)",
        "Headphones (USB)"
    };

    public static IReadOnlyList<VirtualCableRoute> BuildDefaultRoutes() => new[]
    {
        new VirtualCableRoute
        {
            Name = "CABLE-A",
            Summary = "Routes the virtual input to the A recording endpoint.",
            InputDevice = "CABLE-A Input",
            OutputDevice = "CABLE-A Output",
            Enabled = true
        },
        new VirtualCableRoute
        {
            Name = "CABLE-B",
            Summary = "Routes the virtual input to the B recording endpoint.",
            InputDevice = "CABLE-B Input",
            OutputDevice = "CABLE-B",
            Enabled = true
        }
    };
}
