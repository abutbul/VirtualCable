# VB-CABLE Test Driver Package

The release ZIP contains one x64 Windows test driver package and `VirtualCableManager.exe`. It creates four independent endpoint pairs: `CABLE-A Input` / `CABLE-A Output` through `CABLE-D Input` / `CABLE-D Output`.

Run `VirtualCableManager.exe` to see endpoint status, refresh detection, or install/uninstall the driver. Install and uninstall request administrator approval. The ZIP includes the PowerShell helper and DevCon utility used by the manager.

## Install on a test machine

This is a test-signed kernel driver, not a production-signed public release. Use a disposable Windows 10/11 x64 VM or test machine. Secure Boot and BitLocker settings may affect test-signing setup.

1. Extract the entire ZIP to a local folder.
2. Open an elevated Command Prompt and run `bcdedit /set TESTSIGNING ON`.
3. Reboot Windows. If Windows blocks enabling test signing because of Secure Boot, disable Secure Boot in firmware only on the dedicated test machine. Check that the BitLocker recovery key is available before changing firmware security settings.
4. Run `VirtualCableManager.exe` and choose **Install driver**, then approve the Windows administrator prompt. The installer imports the included test certificate into the Local Machine Trusted Root and Trusted Publishers stores; there is no separate certificate-install step. This is machine-wide trust for a test-only certificate. Alternatively, use elevated PowerShell: `powershell -ExecutionPolicy Bypass -File Install-Cable.ps1`.
5. In Windows Sound settings, confirm that all eight endpoints are present: four playback devices and four recording devices.

If installation fails, the manager displays the install transcript and its path under `%TEMP%`. Running the PowerShell helper directly writes `%TEMP%\VirtualCable-Install.log`. Windows also records driver installation details in `%WINDIR%\inf\setupapi.dev.log`. After testing, uninstall the driver and remove the `VirtualCable Local Test Signing` certificate from Local Computer Trusted Root Certification Authorities and Trusted Publishers if it is no longer needed.

## Verify the audio paths

1. Open a player and recorder/monitor application that can select explicit audio devices.
2. Select `CABLE-A Input` as playback and `CABLE-A Output` as recording. Play a known signal and record or monitor it.
3. Repeat with matching B, C, and D endpoints.
4. Check isolation: send audio only to `CABLE-A Input`, monitor all four outputs, and confirm only `CABLE-A Output` receives it. Repeat for B, C, and D.
5. Test WASAPI loopback capture on each cable's playback endpoint separately from recording capture.

Steps 2–5 are automated by `tools/cable_e2e_test.py` (needs `pip install numpy soundcard`):

```
python tools/cable_e2e_test.py list          # all 8 endpoints present?
python tools/cable_e2e_test.py passthrough   # signal, isolation and latency for A–D
python tools/cable_e2e_test.py loopback      # WASAPI loopback on each CABLE-x Input
python tools/cable_e2e_test.py ft8 --wav 000000_000001.wav --cable A   # FT8 through the cable, decoded by WSJT-X jt9
```

Keep each `CABLE-x Input` volume at 100% in Windows; the playback volume scales the signal.

The driver currently supports stereo 48 kHz, 16-bit PCM playback and mono 48 kHz, 16-bit PCM recording. Other rates, bit depths, channel counts, persistent latency configuration, and the reference manual's statistics/control panel are not implemented. A successful build alone does not establish that endpoint creation or pass-through works; record the Windows version, endpoint list, and signal/isolation results when testing.

## Uninstall

Choose **Uninstall** in `VirtualCableManager.exe`, or run `powershell -ExecutionPolicy Bypass -File Install-Cable.ps1 -Uninstall` from elevated PowerShell. Turn test signing off with `bcdedit /set TESTSIGNING OFF` and reboot after testing.

The driver is based on Microsoft's SysVAD sample. Microsoft and WIL license notices are included in the ZIP.