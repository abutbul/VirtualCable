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
        "CABLE-B",
        "CABLE-C",
        "CABLE-D",
        "Speakers (Realtek)",
        "Headphones (USB)"
    };

    public static IReadOnlyList<VirtualCableRoute> BuildDefaultRoutes() => BuildRoutes(new[] { "A", "B", "C", "D" });

    public static IReadOnlyList<VirtualCableRoute> BuildRoutes(IEnumerable<string> cableIds)
    {
        return cableIds
            .Select(id => new VirtualCableRoute
            {
                Name = $"CABLE-{id}",
                Summary = $"Routes the {id} virtual input to the {id} output endpoint.",
                InputDevice = $"CABLE-{id} Input",
                OutputDevice = id == "A" ? "CABLE-A Output" : $"CABLE-{id}",
                Enabled = true
            })
            .ToArray();
    }
}
