# VB-CABLE Virtual Audio Driver

This repository contains an early Windows virtual audio driver based on Microsoft's SysVAD/PortCls sample.

> [!WARNING]
> **This is currently a test driver.** It is signed with a self-signed test certificate, not by Microsoft, so Windows only loads it on a machine configured to accept test-signed drivers. Install it only on a dedicated test PC or VM. We plan to sign the driver properly (Microsoft attestation signing through the Hardware Dev Center) in a future release, after which none of the steps below will be needed.

## Preparing a test machine

Windows refuses test-signed kernel drivers unless test signing is turned on. Do this once per machine:

1. **Back up first.** If the system drive uses BitLocker, save the recovery key (`manage-bde -protectors -get C:` or your Microsoft account) — changing boot or firmware settings can trigger a recovery prompt.
2. **Check Secure Boot.** With Secure Boot on, Windows will not enable test signing. Run `Confirm-SecureBootUEFI` in an elevated PowerShell: `True` means you must disable Secure Boot in the UEFI/BIOS setup first (only on the test machine). On a Hyper-V VM: VM Settings → Security → untick *Enable Secure Boot*.
3. **Turn on test signing** from an elevated Command Prompt or PowerShell:

   ```bat
   bcdedit /set testsigning on
   ```

4. **Reboot.** A "Test Mode" watermark in the bottom-right corner of the desktop confirms it is active (`bcdedit /enum {current}` shows `testsigning Yes`).
5. **Install** with `VirtualCableManager.exe` → *Install driver* (it asks for administrator approval and imports the package's test certificate into the machine's Trusted Root and Trusted Publishers stores). See [drivers/README.md](drivers/README.md) for details and verification.

To return the machine to normal: uninstall the driver (manager → *Uninstall*), remove the `VirtualCable Local Test Signing` certificates from *Local Computer → Trusted Root Certification Authorities* and *Trusted Publishers* (`certlm.msc`), run `bcdedit /set testsigning off` from an elevated prompt, reboot, and re-enable Secure Boot if you turned it off.

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

See [docs/SPEC_GAPS.md](docs/SPEC_GAPS.md) for a feature-by-feature comparison with the VB-CABLE reference manual, and [drivers/TASKLIST.md](drivers/TASKLIST.md) for remaining implementation and validation work.

See [docs/DEBUGGING.md](docs/DEBUGGING.md) for the debugging workflow, the diagnostic tools in `tools/diag/` (KS-level probes, WASAPI probes, audio-service ETW tracing) and the log of issues found while bringing the driver up on Windows 10.