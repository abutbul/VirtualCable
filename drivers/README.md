# VB-CABLE Test Driver Package

The release ZIP contains one x64 Windows test driver package. It creates one playback endpoint, `CABLE Input`, and one recording endpoint, `CABLE Output`.

## Install on a test machine

This is a test-signed kernel driver, not a production-signed public release. Use a disposable Windows 10/11 x64 VM or test machine. Secure Boot and BitLocker settings may affect test-signing setup.

1. Extract the entire ZIP to a local folder.
2. Open an elevated Command Prompt and run `bcdedit /set TESTSIGNING ON`.
3. Reboot Windows. Secure Boot may need to be disabled for test-signing mode.
4. Open elevated PowerShell in the extracted folder and run `.\Install-Cable.ps1`.
5. In Windows Sound settings, choose `CABLE Input` as a playback device and `CABLE Output` as a recording device. Play audio to the former and capture from the latter.

Uninstall from elevated PowerShell with `.\Install-Cable.ps1 -Uninstall`, then reboot as needed. Turn test signing off with `bcdedit /set TESTSIGNING OFF` and reboot after testing.

## Current driver scope

The first driver milestone is fixed 48 kHz, 16-bit PCM. Playback audio is copied through a nonpaged shared ring buffer to the recording endpoint; the recording path downmixes stereo to mono. WASAPI loopback has an independent ring reader. Other sample rates, bit depths, channel counts, persistent latency configuration, and the reference manual's statistics/control panel are not implemented yet. This package must not be described as fully matching the manual.

The driver is based on Microsoft's SysVAD sample. Microsoft and WIL license notices are included in the ZIP.