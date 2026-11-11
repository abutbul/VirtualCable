# VB-CABLE Virtual Audio Driver

This repository contains an early Windows virtual audio driver based on Microsoft's SysVAD/PortCls sample.

## Endpoints

- `CABLE-A Input` through `CABLE-D Input` are the playback endpoints.
- `CABLE-A Output` through `CABLE-D Output` are the corresponding recording endpoints.

The current driver path supports stereo 48 kHz, 16-bit PCM playback and recording (like VB-CABLE's default format). Each cable has an independent nonpaged ring buffer; every recording or loopback stream keeps its own read position, so several applications can record the same cable.

## Driver status

This is not yet a full implementation of the reference manual. The driver's exposed stream formats are fixed to 48 kHz PCM. User-configurable internal sample rates, resampling at the driver boundary, latency controls and statistics, and the complete control panel are not implemented. Shared-mode format conversion may be performed by Windows Audio Engine.

Verified on Windows 10 Pro 19045 with test signing (driver v4, 10.52.44.702): all eight endpoints appear with their `CABLE-x Input/Output` names; playback, recording (shared, exclusive, MME) and WASAPI loopback work on all four cables, with isolation between cables and about 185–205 ms latency; live FT8 from a Web Radio Control radio decodes in WSJT-X through the cable on 20, 15 and 10 m. Windows 11 has not been tested yet.

## Using it with WSJT-X

See [docs/WSJT-X.md](docs/WSJT-X.md) for the full setup with WSJT-X and Web Radio Control (`wrc-proxy`): which cable goes where, the Windows, browser and WSJT-X settings, troubleshooting, and the test results.

The code is derived from Microsoft's SysVAD sample and includes its license and the WIL license under `drivers/windows-driver-samples/`.

## Build and test

Run the catalog tests from the repository root:

```bash
dotnet test VBCableAlternative.sln /p:EnableWindowsTargeting=true --nologo
```

Build the kernel driver on Windows with Visual Studio and the Windows Driver Kit (WDK). GitHub Actions uses a Windows Server 2022 runner with the WDK and builds the x64 package.

## Single package

GitHub Actions publishes one ZIP, `VirtualCable-Driver-TestSigned-win-x64.zip`, containing the driver files and `VirtualCableManager.exe` for endpoint status, install, and uninstall. It is test-signed for a dedicated test machine, not production-signed for general distribution. Tagged test releases are prereleases. See [drivers/README.md](drivers/README.md) for installation, signal, and cable-isolation checks.

See [drivers/TASKLIST.md](drivers/TASKLIST.md) for remaining implementation and validation work from the reference manual.

See [docs/DEBUGGING.md](docs/DEBUGGING.md) for the debugging workflow, the diagnostic tools in `tools/diag/` (KS-level probes, WASAPI probes, audio-service ETW tracing) and the log of issues found while bringing the driver up on Windows 10.