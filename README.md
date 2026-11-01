# VB-CABLE Prototype

This project is a Windows-targeted WPF prototype modeled on the VB-CABLE reference manual.

## Manual endpoint model

- `CABLE Input` is the playback device. Applications play audio to it.
- `CABLE Output` is the recording device. Recording applications receive the audio from it.

## Driver status

The repository does not yet contain a Windows audio driver, INF package, signed catalog, or driver setup program. Therefore, running this prototype does not install a driver or create Windows audio endpoints. It does not implement the manual's audio streaming, format conversion, latency, buffer statistics, or WASAPI loopback features. A real installer release must include a working driver package and be tested and signed for the supported Windows versions.

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

## Build artifact

GitHub Actions builds one Windows x64 ZIP named `VirtualCable-Prototype-win-x64.zip`. This is the WPF prototype only, not a driver installer.
