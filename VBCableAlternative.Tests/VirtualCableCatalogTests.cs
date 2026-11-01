using VBCableAlternative.Core;

namespace VBCableAlternative.Tests;

public class VirtualCableCatalogTests
{
    [Fact]
    public void BuildDefaultRoutes_CreatesExpectedCablePairs()
    {
        var routes = VirtualCableCatalog.BuildDefaultRoutes();

        Assert.Equal(4, routes.Count);
        Assert.Equal("CABLE-A", routes[0].Name);
        Assert.Equal("CABLE-A Input", routes[0].InputDevice);
        Assert.Equal("CABLE-A Output", routes[0].OutputDevice);

        Assert.Equal("CABLE-B", routes[1].Name);
        Assert.Equal("CABLE-B Input", routes[1].InputDevice);
        Assert.Equal("CABLE-B", routes[1].OutputDevice);

        Assert.Equal("CABLE-C", routes[2].Name);
        Assert.Equal("CABLE-C Input", routes[2].InputDevice);
        Assert.Equal("CABLE-C", routes[2].OutputDevice);

        Assert.Equal("CABLE-D", routes[3].Name);
        Assert.Equal("CABLE-D Input", routes[3].InputDevice);
        Assert.Equal("CABLE-D", routes[3].OutputDevice);
    }

    [Fact]
    public void BuildRoutes_AllowsCustomCableIds()
    {
        var routes = VirtualCableCatalog.BuildRoutes(new[] { "Z" });

        Assert.Single(routes);
        Assert.Equal("CABLE-Z", routes[0].Name);
        Assert.Equal("CABLE-Z Input", routes[0].InputDevice);
        Assert.Equal("CABLE-Z", routes[0].OutputDevice);
    }
}
