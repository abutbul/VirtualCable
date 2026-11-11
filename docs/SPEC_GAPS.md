# Gap analysis: VirtualCable vs. the VB-CABLE Reference Manual

Reference: `VBCABLE_ReferenceManual.pdf` (V. Burel, revision 3, October 2024; published by VB-Audio
with the VB-CABLE package, not stored in this repository). Page numbers below are the manual's.

Baseline: the code after PR-1 was merged — driver v4 (10.52.44.702), four cable pairs
`CABLE-A … CABLE-D`, verified on Windows 10 Pro 19045 (see [DEBUGGING.md](DEBUGGING.md)). Every
finding below was checked against the source, not only the READMEs; file references point to the
evidence.

Status key: **Met** · **Partial** · **Missing** · **Differs** (works, but not the way the manual
describes) · **Out of scope?** (needs a decision).

## Summary

| # | Area (manual page) | Manual | Ours today | Status |
|---|---|---|---|---|
| 1 | Endpoints (p.3, 6) | Playback "CABLE Input" + recording "CABLE Output", visible to MME / WASAPI / KS / DirectSound | 4 pairs `CABLE-x Input/Output`, all APIs open (shared, exclusive, MME) | **Met** (4 cables instead of 1) |
| 2 | Default format (p.6–7) | Stereo 48 kHz on Win10/11 | Stereo 48 kHz 16-bit | **Met** |
| 3 | Sample rates on I/O (p.3, 11) | 8 kHz – 192 kHz, independently on input and output | 48 kHz only | **Missing** |
| 4 | Bit depth (p.3) | 16 and 24 bit | 16 bit only | **Missing** |
| 5 | Channels (p.3, 6–8) | Speaker input 1–8 ch (7.1), Line-Out input up to 16 ch, output up to 16 ch | 2 ch only | **Missing** |
| 6 | Two inputs per cable on Win10/11 (p.6) | "Speaker" pin (configurable via *Configure*) + "Line Out" pin | One Line-Out pin | **Missing** / **Differs** |
| 7 | Recording pin type (p.8) | "Line In" pin | Microphone-category pin | **Differs** |
| 8 | Any-format-in / any-format-out conversion (p.3) | Done by the cable (SRC + channel/bit-depth conversion) | Only via the Windows audio engine in shared mode; exclusive/KS clients must use 48k/16/2ch | **Partial** |
| 9 | Internal sample rate + SRC (p.11) | Configurable: 44.1/48/88.2/96/176.4/192 kHz, live, persisted | Fixed 48 kHz, no SRC | **Missing** |
| 10 | Max Latency (pipe size) (p.10–11, 14–15) | Default 7168 samples, larger allocations selectable, persisted | Target fixed at 7168 frames, ring fixed at 32768 frames | **Partial** (default only) |
| 11 | Live latency adjustment (p.12) | Editable on the fly | Compile-time constant | **Missing** |
| 12 | Multiple clients (p.3) | Several players on the input at once | Shared-mode mixing by Windows; several recorders each with their own cursor | **Met** (see risk R1) |
| 13 | Loopback (p.13) | WASAPI loopback of CABLE Input, an option, on by default | Always on, verified A–D | **Met** (no off switch) |
| 14 | Windows volume control (p.13) | Optional; by default volume has no effect on the signal | Playback volume always scales the signal; recording volume/mute do nothing | **Differs** |
| 15 | Pin name / icon customization, reset (p.13, 26) | Rename/icon persistent on Win10/11; *Reset* in the Control Panel | Windows rename not tested for persistence; no reset | **Partial** |
| 16 | Driver name fixed (p.26) | Cannot be changed | `VirtualCable` | **Met** |
| 17 | Control Panel: status (p.10) | Driver name/version, Max Latency, Internal SR, Latency, I/O formats, stream count S0/S1…, loopback flag L | Manager shows only installed / not installed per cable | **Missing** |
| 18 | Control Panel: statistics (p.10, 14–15, 25) | b128/b256/b512/b1024 buffer counters, push loss, pull loss, DMA error F/H, red alert when latency too small | Two internal counters exist in the driver, nothing exposed | **Missing** |
| 19 | Control Panel: input level meters (p.22, 25) | Per-channel level, dB / % toggle | None (and the driver's capture peak meter reports a constant) | **Missing** |
| 20 | Control Panel: options menu (p.11–13) | Internal SR, Max Latency, Loopback on/off, Volume Control on/off, Reset pin name & icon; admin needed to persist | None | **Missing** |
| 21 | Install / uninstall (p.4–5) | Signed setup exe, run as admin, same exe offers uninstall, reboot after both | Manager + PowerShell + DevCon; test-signed only, needs TESTSIGNING; no reboot handling; driver package left in the driver store | **Partial** |
| 22 | Supported OS (p.4) | XP SP2 → Win11, 32/64-bit, Win10/11 ARM64 | Win10 2004+ x64 only; Win11 untested | **Partial** / **Out of scope?** |
| 23 | Hi-Fi Cable & ASIO Bridge (p.16–18) | Separate product: up to 384 kHz, 32k latency, ASIO routing, alerts | Not present | **Out of scope?** |

## Detailed gaps

### A. Audio formats and conversion (rows 3–9)

**Current code**
- Render pin: `SPEAKER_HOST_MAX_CHANNELS 2`, `16..16` bit, `48000..48000` Hz —
  [speakerwavtable.h:24-30](../drivers/windows-driver-samples/audio/sysvad/EndpointsCommon/speakerwavtable.h:24).
- Capture pin: `MICIN_DEVICE_MAX_CHANNELS 2`, 16-bit, 48 kHz —
  [micinwavtable.h:21-27](../drivers/windows-driver-samples/audio/sysvad/TabletAudioSample/micinwavtable.h:21).
- The ring buffer element is hard-wired to stereo 16-bit (`VIRTUAL_CABLE_FRAME { SHORT Left; SHORT Right; }`)
  — [minwavertstream.cpp:28-32](../drivers/windows-driver-samples/audio/sysvad/EndpointsCommon/minwavertstream.cpp:28).
  `ReadBytes` silently ignores any render stream that is not 2-channel
  ([minwavertstream.cpp:1709](../drivers/windows-driver-samples/audio/sysvad/EndpointsCommon/minwavertstream.cpp:1709))
  and copies raw bytes assuming 16-bit.
- Capture has a mono down-mix branch ([minwavertstream.cpp:146-150](../drivers/windows-driver-samples/audio/sysvad/EndpointsCommon/minwavertstream.cpp:146)),
  but mono is no longer advertised, so it is dead code.

**What the manual requires**
- Any of 8–192 kHz, 16/24 bit, 1–8 ch (Speaker) or up to 16 ch (Line Out / output), negotiated
  independently on each side, with the cable converting (p.3, 11).
- A fixed internal rate ("Internal SR"); I/O at the internal rate passes bit-exact, otherwise SRC (p.11).

**Work needed**
1. Change the ring to an internal canonical format (e.g. 32-bit float or 32-bit int, N channels at
   the Internal SR) instead of raw 16-bit stereo frames.
2. Write-side and read-side converters: integer 16/24 (and 32-bit/float if advertised) ↔ internal;
   channel up/down-mix with defined channel-mask mapping; a quality SRC (polyphase) at DISPATCH_LEVEL
   that is safe in the WaveRT position/timer path.
3. Expand the data ranges in both wave tables, plus `PinSupportedDeviceModes` default formats. Re-run
   `tools/diag/ksprobe.py modes formats` after every table change (F5 lesson in DEBUGGING.md).
4. Extend `tools/cable_e2e_test.py` (currently hard-coded `SR = 48000`, 2 ch play / 1 ch record) to a
   format matrix in exclusive mode, which is the only way to prove the driver, not the audio
   engine, does the conversion.

Note: today, shared-mode applications already get any format because the Windows audio engine
converts to 48k/16/2ch. The gap is visible to exclusive-mode, KS and ASIO-wrapper clients, and for
>2 channel use.

### B. Endpoint topology (rows 6, 7, 14, 15)

- **Two inputs per cable** (p.6): VB-CABLE on Win10/11 exposes a Speaker pin (8 ch, *Configure*
  button for speaker setup) and a Line Out pin (16 ch); "both cable inputs cannot be used at the
  same time" (p.7). We expose one Line-Out pin
  ([speakertoptable.h:72](../drivers/windows-driver-samples/audio/sysvad/EndpointsCommon/speakertoptable.h:72)).
  Constraint found in F4: Windows 10 ignored our pin name on a Speaker-category integrated jack, so
  adding the Speaker pin needs a naming solution first (e.g. a `ePortConnJack` speaker, or
  FriendlyName overrides in the INF).
- **Recording pin is Microphone, manual says Line In** (p.8):
  [micintoptable.h:76](../drivers/windows-driver-samples/audio/sysvad/TabletAudioSample/micintoptable.h:76).
  Practical effect: the cable outputs are subject to the Windows microphone privacy switch and show
  as microphones. Decide whether to switch to `KSNODETYPE_LINE_CONNECTOR` and re-verify naming.
- **Volume control** (p.13): the manual's default is that Windows volume does *not* change the
  signal, with an option to enable it. Our render topology has no volume node, so Windows applies
  software volume — the README has to tell users to keep `CABLE-x Input` at 100 %. On the capture
  side the topology *does* advertise volume, mute and peak-meter nodes
  ([micintoptable.h:168-182](../drivers/windows-driver-samples/audio/sysvad/TabletAudioSample/micintoptable.h:168)),
  but the stream never reads them (no `GetMixerVolume`/`GetMixerMute` call in
  `minwavertstream.cpp`), so the recording slider and mute are no-ops, and the peak meter returns a
  constant `PEAKMETER_SIGNED_MAXIMUM/2` ([hw.cpp:286-345](../drivers/windows-driver-samples/audio/sysvad/hw.cpp:286)).
  Needed: a render volume node that is pass-through unless the "Volume Control" option is on; a real
  capture mute (or remove the nodes); a peak meter computed from the ring.
- **Pin name / icon** (p.13, 26): Windows' own rename/icon change is allowed; persistence across
  reboot and driver reinstall is untested. *Reset pin name and icon* needs a Control Panel action
  (delete the MMDevices `PKEY_Device_DeviceDesc` / icon overrides, admin).

### C. Latency and pipe (rows 10, 11)

- Current constants: target latency 7168 frames (149 ms at 48 kHz), ring 32768 frames (683 ms),
  resync threshold target + 4800
  ([minwavertstream.cpp:13-19](../drivers/windows-driver-samples/audio/sysvad/EndpointsCommon/minwavertstream.cpp:13)).
  The default matches the manual (7168), measured end-to-end 185–205 ms.
- The ring is a static array of 4 × 32768 frames
  ([minwavertstream.cpp:35](../drivers/windows-driver-samples/audio/sysvad/EndpointsCommon/minwavertstream.cpp:35));
  the manual's "Max Latency" is a pipe size allocated at driver init from a persisted setting, and
  "Latency" can be lowered/raised live up to it (p.10–12).
- Needed: per-cable (or global) Max Latency read from the registry at `DriverEntry`, ring allocated
  from non-paged pool accordingly; a live Latency value changeable through a private property;
  bounds checking against the ring; when Internal SR ≠ I/O SR the effective latency scales by
  InternalSR / IO-SR (p.14), which the control panel should display.
- The 192 kHz use case (p.11) does not fit in a 7168-sample pipe; it becomes relevant once item A
  adds high rates.

### D. Statistics and diagnostics (rows 17–19)

- The driver keeps `g_VirtualCableDroppedFrames` (reader resync = pull-side loss) and
  `g_VirtualCableUnderflowFrames` (zero-fill) per cable
  ([minwavertstream.cpp:37-38, 130, 159](../drivers/windows-driver-samples/audio/sysvad/EndpointsCommon/minwavertstream.cpp:37)),
  but nothing reads them. The underflow counter also counts the intentional pre-fill at stream start,
  so it is not yet a usable "loss" metric.
- Missing against p.10 / 25: buffer-size histograms b128/b256/b512/b1024 per side (count the size
  of each `ReadBytes`/`WriteBytes` displacement), push loss (writer overruns a reader), pull loss
  (reader underruns after pre-fill), stream counts S0/S1…, loopback-in-use flag, current I/O
  format per side, per-channel input levels, and a "latency too small" flag
  (biggest bucket × 3 × SR ratio > Latency, p.14–15).
- Enabling step for all of D and the Control Panel: a private KS property set (the sample already
  has `ihvprivatepropertyset.h`) or a control device object with IOCTLs, readable without admin and
  writable with admin.

### E. Control Panel application (rows 17–20)

[VirtualCableManager](../VBCableAlternative.App/MainWindow.xaml.cs) is an install/uninstall/status
tool: it checks whether eight endpoint names exist via `Get-PnpDevice`. Everything in the manual's
Control Panel (p.9–13, 22, 25) is missing: status header (name, version, Max Latency, Internal SR,
Latency), I/O format display, statistics with red alerts, level meters (dB/% toggle), the options
menu (Internal SR, Max Latency, Loopback on/off, Volume Control on/off, Reset pin name & icon), and
"run as administrator to persist" behaviour. It depends on D's driver interface.

Housekeeping found while reviewing: `VBCableAlternative/` (an empty WPF window) and the example
device lists in `VBCableAlternative.Core/VirtualCableCatalog.cs` (`"Microphone (USB)"`,
`"Speakers (Realtek)"` …) are unused leftovers; the catalog test only covers route names.

### F. Installation, signing, platforms (rows 21–23)

- **Signing** is the biggest practical gap: the manual's driver installs on any PC; ours needs
  `bcdedit /set TESTSIGNING ON`, often Secure Boot off, and machine-wide trust of a per-build
  self-signed certificate. A production path needs EV certificate + Microsoft Hardware Dev Center
  attestation signing (HLK for Windows-certified distribution).
- **Install** relies on bundled WDK `devcon.exe`; the manual's setup is a single elevated exe that
  detects an existing install and offers removal (p.4–5). We have no reboot prompt.
- **Uninstall** runs `devcon remove` only
  ([Install-Cable.ps1:39-42](../drivers/Install-Cable.ps1:39)): the driver package stays in the
  driver store (`pnputil /delete-driver oemNN.inf /uninstall` is missing) and the test certificates
  stay in the machine stores. The manual also documents a Device Manager fallback (p.5); we document
  F6 (duplicate devnode) but no general recovery.
- **Platforms**: INF targets `NTamd64.10.0...19041` (Windows 10 2004+). Windows 11 is untested;
  ARM64 (supported by the manual for Win10/11) is not built; 32-bit and XP–8.1 are not supported.
  Recommend recording XP–8.1 and 32-bit as explicitly out of scope, and ARM64 as a decision.
- **Hi-Fi Cable / ASIO Bridge** (p.16–18) is a different VB-Audio product described in the same
  manual (no SRC, up to 384 kHz, 32k-sample latency, ASIO pass-through and clock/latency alerts).
  Recommend declaring it out of scope.

## Risks found during the review (not stated by the manual, but they affect compliance)

- **R1 — concurrent render pins write into the same ring without mixing.** Each cable's render
  filter allows 1 host stream + 3 offload streams
  ([simple.h:30-32](../drivers/windows-driver-samples/audio/sysvad/EndpointsCommon/simple.h:30),
  [speakerwavtable.h:53-55](../drivers/windows-driver-samples/audio/sysvad/EndpointsCommon/speakerwavtable.h:53)).
  Every render stream's `ReadBytes` appends to the cable ring, so two active pins would interleave
  blocks rather than sum them, and double the write rate. On desktop Windows 10 the audio engine
  normally uses only the host pin, which is why tests pass; offload is not a VB-CABLE feature.
  Suggest removing the offload pins (or mixing into the ring) and adding a test with two exclusive /
  offload writers.
- **R2 — capture volume, mute and meter advertised but fake** (see B). Apps and the Sound panel
  show a moving slider and a level that do not reflect the signal.
- **R3 — format assumptions are implicit.** If any future table change advertises 24-bit or float
  stereo, `ReadBytes` would copy those bytes into a 16-bit stereo ring without error (it only
  checks the channel count). Add an explicit format guard until item A lands.
- **R4 — stale scope reference.** [drivers/TASKLIST.md](../drivers/TASKLIST.md) cited
  `documentation.txt`; fixed to `VBCABLE_ReferenceManual.pdf` / `.txt`.

## Intentional differences (keep)

- Four independent cables `CABLE-A … CABLE-D` in one driver (VB-Audio sells single, A+B and C+D
  packages separately). Isolation verified at −180 dBFS.
- Device name `VirtualCable`, endpoint names `CABLE-x Input (VirtualCable)` / `CABLE-x Output
  (VirtualCable)` — same Input = playback / Output = recording convention as the manual.
- Capture advertises only RAW and DEFAULT processing modes (F5 fix for Windows 10).

## Suggested order

1. Driver private interface (D) + expose existing counters; fix R1/R2/R3. Small, unblocks the rest.
2. Configurable Max Latency / Latency with registry persistence (C).
3. Control Panel v1 on top of 1–2: status, statistics, alerts, latency menu (E).
4. Internal format + converters + SRC, then widen advertised formats (A); Internal SR option.
5. Second input pin (Speaker, 8 ch) and Line-In capture category (B); volume-control option.
6. Install/uninstall hardening, Windows 11 + ARM64 validation, production signing (F).

Each gap and risk here has a checklist item in [drivers/TASKLIST.md](../drivers/TASKLIST.md).
