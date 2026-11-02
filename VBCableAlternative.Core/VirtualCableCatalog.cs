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
        "CABLE-C Input",
        "CABLE-D Input",
        "Microphone (USB)",
        "System Default Input"
    };

    public static IReadOnlyList<string> GetExampleOutputDevices() => new[]
    {
        "CABLE-A Output",
        "CABLE-B Output",
        "CABLE-C Output",
        "CABLE-D Output",
        "Speakers (Realtek)",
        "Headphones (USB)"
    };

    public static IReadOnlyList<VirtualCableRoute> BuildDefaultRoutes() => new[] { "A", "B", "C", "D" }
        .Select(id => new VirtualCableRoute
        {
            Name = $"CABLE-{id}",
            Summary = $"Routes playback from CABLE-{id} Input to recording endpoint CABLE-{id} Output.",
            InputDevice = $"CABLE-{id} Input",
            OutputDevice = $"CABLE-{id} Output",
            Enabled = true
        })
        .ToArray();
}
