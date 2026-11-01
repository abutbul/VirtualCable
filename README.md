# VB-Cable A+B Alternative

This project is a Windows-targeted desktop prototype for a virtual audio cable manager inspired by VB-Audio's cable pattern. It models the requested virtual endpoints for A/B/C/D cable routing and exposes them through a small WPF desktop dashboard.

## Included endpoints

- `CABLE-A Input`
- `CABLE-B Input`
- `CABLE-C Input`
- `CABLE-D Input`
- `CABLE-A Output`
- `CABLE-B`
- `CABLE-C`
- `CABLE-D`

## Important note

This repository provides the app shell, default routing model, and a Windows desktop user interface. A true virtual audio cable driver that creates new Windows audio endpoints at the OS level normally requires a kernel-mode driver or a deeper Windows audio integration than a user-mode app can provide. This project is therefore a practical prototype and management layer for the requested concept.

## Run on Windows 10+

1. Open the solution in Visual Studio 2022 or build from the command line.
2. Restore NuGet packages and build the solution.
3. Launch `VBCableAlternative.App`.

## Build checks

From the repo root, run:

```bash
dotnet test VBCableAlternative.sln /p:EnableWindowsTargeting=true --nologo
```

This validates the cable catalog from the Ubuntu development environment while targeting the Windows desktop app.

## CI coverage

The repository includes a GitHub Actions workflow that builds four cable variants: A, B, C, and D.
