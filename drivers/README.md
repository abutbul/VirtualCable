# VB-CABLE Test Driver Package

The release ZIP contains one x64 Windows test driver package. It creates four independent endpoint pairs: `CABLE-A Input` / `CABLE-A Output` through `CABLE-D Input` / `CABLE-D Output`.

## Install on a test machine

This is a test-signed kernel driver, not a production-signed public release. Use a disposable Windows 10/11 x64 VM or test machine. Secure Boot and BitLocker settings may affect test-signing setup.

1. Extract the entire ZIP to a local folder.
2. Open an elevated Command Prompt and run `bcdedit /set TESTSIGNING ON`.
3. Reboot Windows. Secure Boot may need to be disabled for test-signing mode.
4. Open elevated PowerShell in the extracted folder and run `powershell -ExecutionPolicy Bypass -File Install-Cable.ps1`.
5. In Windows Sound settings, confirm that all eight endpoints are present: four playback devices and four recording devices.

## Verify the audio paths

1. Open a player and recorder/monitor application that can select explicit audio devices.
2. Select `CABLE-A Input` as playback and `CABLE-A Output` as recording. Play a known signal and record or monitor it.
3. Repeat with matching B, C, and D endpoints.
4. Check isolation: send audio only to `CABLE-A Input`, monitor all four outputs, and confirm only `CABLE-A Output` receives it. Repeat for B, C, and D.
5. Test WASAPI loopback capture on each cable's playback endpoint separately from recording capture.

The driver currently supports stereo 48 kHz, 16-bit PCM playback and mono 48 kHz, 16-bit PCM recording. Other rates, bit depths, channel counts, persistent latency configuration, and the reference manual's statistics/control panel are not implemented. A successful build alone does not establish that endpoint creation or pass-through works; record the Windows version, endpoint list, and signal/isolation results when testing.

## Uninstall

From elevated PowerShell in the extracted folder, run `powershell -ExecutionPolicy Bypass -File Install-Cable.ps1 -Uninstall`. Turn test signing off with `bcdedit /set TESTSIGNING OFF` and reboot after testing.

The driver is based on Microsoft's SysVAD sample. Microsoft and WIL license notices are included in the ZIP.