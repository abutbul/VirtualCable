# Driver Feature Task List

Scope reference: `documentation.txt` (VB-CABLE Reference Manual, revision 3, October 2024).

Current baseline: four test-signed endpoint pairs build on Windows. The driver path is fixed at stereo 48 kHz, 16-bit PCM playback to mono 48 kHz, 16-bit PCM capture. Endpoint creation and actual audio transport still require installation and signal verification on a Windows test VM.

## P0: Validate the current four-cable release

- [ ] Install the package on a disposable Windows 10/11 x64 VM with test signing enabled.
- [ ] Verify all eight endpoints appear in Windows Sound settings with the correct playback/recording roles.
- [ ] Play and capture a known signal through each matching A, B, C, and D pair.
- [ ] Verify isolation: audio sent to one cable never appears on the other three recording endpoints.
- [ ] Verify WASAPI loopback capture on all four playback endpoints.
- [ ] Exercise simultaneous clients and repeated start/stop, device refresh, suspend/resume, and reboot.
- [ ] Check Device Manager, driver logs, and Windows audio diagnostics for errors; preserve test results with OS build and driver package hash.

## P1: Match the manual's audio format behavior

- [ ] Define the supported Windows versions, audio APIs, and format contract before expanding advertised formats.
- [ ] Add PCM 16-bit and 24-bit support, with 1-8 channels on supported Windows versions; test legacy limitations separately if XP-Win7 remains a target.
- [ ] Implement conversion between playback and recording formats when sample rate, channel count, or sample resolution differs.
- [ ] Add format negotiation tests covering minimum/maximum rates, channel layouts, 16/24-bit data, and incompatible formats.
- [ ] Verify each cable's stream remains isolated with multiple clients and differing playback/capture formats.

Acceptance: every advertised format produces valid output at the requested recording format; unsupported combinations are rejected rather than silently corrupted.

## P1: Implement the control panel's core controls

- [ ] Add configurable internal sample rate with the documented standard rates: 44.1, 48, 88.2, 96, 176.4, and 192 kHz.
- [ ] Add configurable maximum pipe allocation and live latency adjustment, with bounds checked against buffer allocation and stream rate.
- [ ] Persist settings in driver/device configuration; require and detect administrator elevation for persistent changes.
- [ ] Report current driver name/version, maximum latency, internal sample rate, and live latency.
- [ ] Report active stream counts, active input/output formats, and loopback state per cable.
- [ ] Add buffer counters for the documented size buckets and report input push loss, output pull loss, and DMA fault counters.
- [ ] Add validation and warnings when observed buffer requirements exceed configured latency.

Acceptance: changing settings applies safely to active streams, persisted settings survive reboot, and counters are covered by repeatable streaming tests.

## P2: Complete endpoint behavior and settings

- [ ] Implement the documented Windows volume-control behavior for playback endpoints and test mute/volume through Windows controls.
- [ ] Verify loopback streaming is enabled by default and captures the correct cable's rendered signal without cross-cable leakage.
- [ ] Implement supported pin-name and icon reset/customization behavior where allowed by Windows; document that the driver name itself cannot change.
- [ ] Confirm speaker and line-out pin/channel configuration constraints and document mutually exclusive input modes where applicable.

## P1: Deliver a robust manager and installer

- [x] Ship a manager `.exe` in the same release ZIP with install, uninstall, refresh/status, and per-cable endpoint visibility.
- [ ] Make install/uninstall elevation explicit; report signing, reboot, Secure Boot, and test-mode requirements before taking action.
- [ ] Avoid relying on an unbundled WDK DevCon executable on the target machine; use a supported installation mechanism and test it on clean Windows VMs.
- [ ] Ensure install is idempotent and upgrades cleanly; uninstall removes all four cable endpoints and associated driver packages.
- [ ] Add recovery instructions for failed install, stale endpoints, rollback, and test-signing shutdown.
- [ ] Create a production-signed release path only after Microsoft Hardware Dev Center signing and hardware certification requirements are met.

## P2: Expand build and release verification

- [ ] Test installation and audio paths on clean Windows 10 and Windows 11 x64 VMs.
- [x] Add automated package checks for the SYS, INF, CAT, manager EXE, license notices, and all eight endpoint names.
- [ ] Add static driver analysis, Driver Verifier runs, and appropriate HLK audio tests; document expected limitations and failures.
- [ ] Test upgrade, uninstall, reboot, and reinstall cycles on snapshots.
- [ ] Publish one ZIP per release and label test-signed packages as prereleases until production signing is available.
- [ ] Record tested OS/build, supported formats, known issues, signing status, and package checksum in each release.
