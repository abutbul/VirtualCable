# Driver Feature Task List

Scope reference: VB-CABLE Reference Manual, revision 3, October 2024 (`VBCABLE_ReferenceManual.pdf`, published by VB-Audio with the VB-CABLE package; not stored in this repository). The feature-by-feature comparison with evidence is in [docs/SPEC_GAPS.md](../docs/SPEC_GAPS.md); items below reference its rows (`#n`) and risks (`R1`–`R4`) where relevant.

Current baseline: four test-signed endpoint pairs build on Windows. The driver path is fixed at stereo 48 kHz, 16-bit PCM playback and capture. Installed and verified on Windows 10 Pro 19045 (driver v4, 10.52.44.702), including live FT8 reception in WSJT-X (see `docs/WSJT-X.md`); Windows 11 is not yet tested.

## P0: Validate the current four-cable release

- [x] Install the package on a Windows 10 x64 test machine with test signing enabled (19045). Windows 11 still to do.
- [x] Verify all eight endpoints appear in Windows Sound settings with the correct playback/recording roles.
- [x] Play and capture a known signal through each matching A, B, C, and D pair.
- [x] Verify isolation: audio sent to one cable never appears on the other three recording endpoints.
- [x] Verify WASAPI loopback capture on all four playback endpoints.
- [x] Real application: Web Radio Control audio → CABLE-A → WSJT-X decodes FT8 on 20/15/10 m, with a second recorder on the same cable at the same time.
- [ ] Exercise simultaneous clients and repeated start/stop, device refresh, suspend/resume, and reboot.
- [ ] Check Device Manager, driver logs, and Windows audio diagnostics for errors; preserve test results with OS build and driver package hash.

## P0: Fix correctness risks found in the spec review

- [ ] R1: Stop concurrent render pins from interleaving into one ring. Each cable allows 1 host + 3 offload render streams (`simple.h`, `speakerwavtable.h`) and every one appends to the ring in `ReadBytes`. Remove the offload pins (not a VB-CABLE feature) or mix into the ring; add a test with two simultaneous writers.
- [ ] R2: Make the capture volume, mute and peak-meter nodes real or remove them. Today the stream never reads volume/mute and `CSYSVADHW::GetMixerPeakMeter` returns a constant, so the Recording tab slider, mute and level meter are fake.
- [ ] R3: Add an explicit format guard in `ReadBytes`/`WriteBytes` (PCM, 16-bit, 2 ch) so a future table change cannot feed 24-bit or float data into the 16-bit stereo ring; remove the unreachable mono down-mix branch or keep it covered by a test.
- [ ] Make the underflow counter skip the intentional pre-fill at stream start, so it can serve as the pull-loss statistic.

## P1: Match the manual's audio format behavior

- [ ] Define the supported Windows versions, audio APIs, and format contract before expanding advertised formats. Record XP–8.1, 32-bit and Hi-Fi Cable / ASIO Bridge (#22, #23) as in or out of scope.
- [ ] Replace the raw 16-bit stereo ring frame with an internal canonical format (N channels at the Internal SR) so conversion has one place to happen.
- [ ] Extend `tools/cable_e2e_test.py` (hard-coded 48 kHz) to an exclusive-mode format matrix, which proves the driver, not the Windows audio engine, does the conversion.
- [ ] Add PCM 16-bit and 24-bit support, with 1-8 channels on supported Windows versions; test legacy limitations separately if XP-Win7 remains a target.
- [ ] Implement conversion between playback and recording formats when sample rate, channel count, or sample resolution differs.
- [ ] Add format negotiation tests covering minimum/maximum rates, channel layouts, 16/24-bit data, and incompatible formats.
- [ ] Verify each cable's stream remains isolated with multiple clients and differing playback/capture formats.

Acceptance: every advertised format produces valid output at the requested recording format; unsupported combinations are rejected rather than silently corrupted.

## P1: Implement the control panel's core controls

- [ ] Add a driver private interface (KS private property set, see `ihvprivatepropertyset.h`, or a control device with IOCTLs): readable without admin, writable with admin. Expose the existing per-cable dropped/underflow counters through it first.
- [ ] Add configurable internal sample rate with the documented standard rates: 44.1, 48, 88.2, 96, 176.4, and 192 kHz.
- [ ] Add configurable maximum pipe allocation and live latency adjustment, with bounds checked against buffer allocation and stream rate.
- [ ] Persist settings in driver/device configuration; require and detect administrator elevation for persistent changes.
- [ ] Report current driver name/version, maximum latency, internal sample rate, and live latency.
- [ ] Report active stream counts, active input/output formats, and loopback state per cable.
- [ ] Add buffer counters for the documented size buckets and report input push loss, output pull loss, and DMA fault counters.
- [ ] Add validation and warnings when observed buffer requirements exceed configured latency.
- [ ] Build the Control Panel UI in the manager on top of the private interface: status header, I/O formats, statistics with red alerts, per-channel input level meters (dB / % toggle), and the options menu (Internal SR, Max Latency, Loopback on/off, Volume Control on/off, Reset pin name & icon) (#17–#20).

Acceptance: changing settings applies safely to active streams, persisted settings survive reboot, and counters are covered by repeatable streaming tests.

## P2: Complete endpoint behavior and settings

- [ ] Implement the documented Windows volume-control behavior for playback endpoints and test mute/volume through Windows controls. Manual default: volume does not change the signal unless the option is on; today Windows always applies software volume because the render topology has no volume node (#14).
- [x] Verify loopback streaming is enabled by default and captures the correct cable's rendered signal without cross-cable leakage.
- [ ] Add the Loopback on/off option (manual: an option, on by default).
- [ ] Add the second input per cable: a Speaker pin (1–8 ch, configurable via *Configure*) next to the Line Out pin (up to 16 ch), mutually exclusive in use (#6). Solve naming first: Windows 10 ignored the pin name on a Speaker-category integrated jack (DEBUGGING.md F4).
- [ ] Decide whether the recording pin should be Line In (`KSNODETYPE_LINE_CONNECTOR`) as in the manual instead of Microphone; re-verify naming and the microphone privacy behavior (#7).
- [ ] Implement supported pin-name and icon reset/customization behavior where allowed by Windows; document that the driver name itself cannot change.
- [ ] Confirm speaker and line-out pin/channel configuration constraints and document mutually exclusive input modes where applicable.

## P1: Deliver a robust manager and installer

- [x] Ship a manager `.exe` in the same release ZIP with install, uninstall, refresh/status, and per-cable endpoint visibility.
- [ ] Make install/uninstall elevation explicit; report signing, reboot, Secure Boot, and test-mode requirements before taking action.
- [ ] Avoid relying on an unbundled WDK DevCon executable on the target machine; use a supported installation mechanism and test it on clean Windows VMs.
- [ ] Ensure install is idempotent and upgrades cleanly; uninstall removes all four cable endpoints and associated driver packages. Today `Install-Cable.ps1 -Uninstall` only runs `devcon remove`: add `pnputil /delete-driver <oemNN.inf> /uninstall` and optional removal of the test certificates.
- [ ] Prompt for a reboot after install and uninstall, as the manual's setup does.
- [ ] Add recovery instructions for failed install, stale endpoints, rollback, and test-signing shutdown.
- [ ] Create a production-signed release path only after Microsoft Hardware Dev Center signing and hardware certification requirements are met.

## P2: Expand build and release verification

- [ ] Test installation and audio paths on clean Windows 10 and Windows 11 x64 VMs.
- [ ] Decide on and, if in scope, build and test an ARM64 package (the manual supports Win10/11 ARM64).
- [ ] Remove unused leftovers: the empty `VBCableAlternative/` WPF project and the example device lists in `VBCableAlternative.Core/VirtualCableCatalog.cs`.
- [x] Add automated package checks for the SYS, INF, CAT, manager EXE, license notices, and all eight endpoint names.
- [ ] Add static driver analysis, Driver Verifier runs, and appropriate HLK audio tests; document expected limitations and failures.
- [ ] Test upgrade, uninstall, reboot, and reinstall cycles on snapshots.
- [ ] Publish one ZIP per release and label test-signed packages as prereleases until production signing is available.
- [ ] Record tested OS/build, supported formats, known issues, signing status, and package checksum in each release.
