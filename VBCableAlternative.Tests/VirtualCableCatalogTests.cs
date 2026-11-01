using VBCableAlternative.Core;

namespace VBCableAlternative.Tests;

public class VirtualCableCatalogTests
{
    [Fact]
    public void BuildDefaultRoutes_CreatesManualPlaybackAndRecordingEndpoints()
    {
        var routes = VirtualCableCatalog.BuildDefaultRoutes();

        var route = Assert.Single(routes);
        Assert.Equal("VB-CABLE", route.Name);
        Assert.Equal("CABLE Input", route.InputDevice);
        Assert.Equal("CABLE Output", route.OutputDevice);
    }
}
