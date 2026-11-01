using VBCableAlternative.Core;

namespace VBCableAlternative.Tests;

public class VirtualCableCatalogTests
{
    [Fact]
    public void BuildDefaultRoutes_CreatesExpectedCablePairs()
    {
        var routes = VirtualCableCatalog.BuildDefaultRoutes();

        Assert.Equal(2, routes.Count);
        Assert.Equal("CABLE-A", routes[0].Name);
        Assert.Equal("CABLE-A Input", routes[0].InputDevice);
        Assert.Equal("CABLE-A Output", routes[0].OutputDevice);

        Assert.Equal("CABLE-B", routes[1].Name);
        Assert.Equal("CABLE-B Input", routes[1].InputDevice);
        Assert.Equal("CABLE-B", routes[1].OutputDevice);
    }
}
