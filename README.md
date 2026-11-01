# VB-Cable A+B Alternative

This project is a Windows-targeted desktop prototype for a virtual audio cable manager with the same conceptual naming as VB-Audio's `CABLE-A` and `CABLE-B` devices.

## Included endpoints

- `CABLE-A Input`
- `CABLE-B Input`
- `CABLE-A Output`
- `CABLE-B`

## Important note

This repository provides the desktop app shell, default routing model, and a Windows desktop user interface. A true virtual audio cable driver that creates new Windows audio endpoints at the OS level normally requires a kernel-mode driver or a lower-level WASAPI/DirectSound integration that is beyond a normal user-mode app. This project is therefore a practical desktop prototype and management layer for the requested concept.

## Run on Windows 10+

1. Open the solution in Visual Studio 2022 or build from the command line.
2. Restore NuGet packages and build the solution.
3. Launch `VBCableAlternative.App`.

## Build check

From the repo root, run:

```bash
dotnet test /p:EnableWindowsTargeting=true
```

This validates the routing catalog from the Ubuntu development environment while targeting the Windows desktop app.
