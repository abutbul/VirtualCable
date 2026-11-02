using VBCableAlternative.Core;

namespace VBCableAlternative.Tests;

public class VirtualCableCatalogTests
{
    [Fact]
    public void BuildDefaultRoutes_CreatesFourIndependentManualEndpointPairs()
    {
        var routes = VirtualCableCatalog.BuildDefaultRoutes();

        Assert.Equal(4, routes.Count);
        for (var index = 0; index < routes.Count; index++)
        {
            var cableId = ((char)('A' + index)).ToString();
            Assert.Equal($"CABLE-{cableId}", routes[index].Name);
            Assert.Equal($"CABLE-{cableId} Input", routes[index].InputDevice);
            Assert.Equal($"CABLE-{cableId} Output", routes[index].OutputDevice);
        }
    }
}
