# Debugging the VirtualCable driver

This guide records how the driver was brought up and debugged on a real Windows 10 machine, the tools
written for that, and what each finding was. Start here before changing the driver: most failure
modes below look alike from an application ("device not found", "unsupported format") but sit in
very different layers.

## Where things can go wrong

```
 application (WSJT-X, browser, Python)            tools/cable_e2e_test.py, tools/diag/wasapi_probe.py
   │ WASAPI / MME / DirectSound
 audioses.dll (client side)        ── maps internal errors to AUDCLNT_E_* (e.g. ERROR_NOT_FOUND → UNSUPPORTED_FORMAT)
   │ RPC
 audiosrv  (Windows Audio service) ── endpoint "characteristics": device/mix format, volume, spatial, sessions
 AudioEndpointBuilder              ── creates endpoints from KS filters, names them, stores MMDevices properties
 audiodg   (audio engine)          ── opens the KS pins, mixes/converts
   │ IOCTL_KS_PROPERTY / KsCreatePin            tools/diag/ksprobe.py talks to this layer directly
 portcls + VirtualCable miniports  ── wave (stream) + topology (naming, jack, volume) filters per cable
   │
 per-cable ring buffer             ── EndpointsCommon/minwavertstream.cpp (StoreVirtualCableFrames / ReadVirtualCableFrames)
```

The key technique: **compare layers and compare endpoints.** If `ksprobe.py` can create, buffer and
run a pin but WASAPI cannot open the same endpoint, the driver's stream path is fine and the problem
is how audiosrv interprets the endpoint. If one endpoint fails and a similar one works (playback vs
capture, our capture vs the system's Stereo Mix), diff their properties.

## Setup

```
bcdedit /set TESTSIGNING ON            (elevated; reboot; Secure Boot may need to be off)
powershell -ExecutionPolicy Bypass -File <package>\Install-Cable.ps1     (elevated)

python -m venv .venv-test
.venv-test\Scripts\python -m pip install -r tools\requirements.txt
```

For FT8 tests install WSJT-X (official GitHub release); it provides `jt9.exe` (decoder) and
`ft8sim.exe` (generates a known FT8 signal at a chosen SNR).

## Tools

| Tool | Admin | What it tells you |
|---|---|---|
| `tools/cable_e2e_test.py list` | no | All 8 endpoints present (falls back to KS filter mapping when names differ) |
| `tools/cable_e2e_test.py passthrough` | no | Signal, isolation between cables, latency, through the recording endpoints |
| `tools/cable_e2e_test.py loopback` | no | Same ring buffer via WASAPI loopback of `CABLE-x Input`; works even when capture endpoints don't |
| `tools/cable_e2e_test.py ft8 --wav F [--rec "loopback:CABLE-A Input"]` | no | FT8 through the cable, decoded by `jt9` |
| `tools/diag/ksprobe.py pins\|formats\|modes\|topo\|stream\|all` | no | Driver-level truth: pin layout/names/instances, format acceptance, data intersection, per-mode default formats, topology nodes/jacks, a full WaveRT stream start like audiodg does |
| `tools/diag/wasapi_probe.py endpoints` | no | MMDevices registry: endpoint name, form factor, KS filter, stored device and **mix format** |
| `tools/diag/wasapi_probe.py open` | no | GetMixFormat, shared/exclusive IsFormatSupported/Initialize, stream categories + RAW mode, MME |
| `tools/diag/wasapi_probe.py policy` | no | Device/mix format as the Sound control panel sees them (IPolicyConfig) |
| `tools/diag/wasapi_probe.py interfaces [--cable A]` | no | Activates endpoint volume / meter / topology (client side, straight to KS) and the session manager (answered by audiosrv); shows hardware volume support. Session calls failing with `0x80070490` = audiosrv has not registered the endpoint |
| `tools/diag/wasapi_probe.py rearrive [--cable A]` | no | Disables and re-enables the cable's endpoints (audiosrv re-processes their arrival), then `open` |
| `tools/diag/wasapi_probe.py compare --endpoint ID [--enable-temporarily]` | no | Same open tests against another endpoint (e.g. Realtek Stereo Mix) to separate driver vs system problems |
| `tools/diag/exclusive_capture_test.py [play] [rec] [ch]` | no | Exclusive-mode capture with per-call HRESULTs |
| `tools/diag/capture-trace.ps1 [-Cable A] [-NoRearrive]` | **yes** | ETW trace of the audio service while the endpoints re-arrive (`rearrive`) and are opened, then `summarize_trace.py` |
| `tools/diag/summarize_trace.py audio.xml [--endpoint GUID]` | no | WIL failures (module, source file:line, HRESULT), the error propagation chain, per-endpoint activity |
| `tools/diag/check_driver_imports.py TabletAudioSample.sys` | no | Every kernel import exists on this Windows build (catches Code 39 before installing) |

Other sources: `%WINDIR%\inf\setupapi.dev.log` (install), `%TEMP%\VirtualCable-Install.log`
(installer transcript), `Get-PnpDevice -InstanceId 'ROOT\MEDIA\*'` and
`Get-PnpDeviceProperty ... DEVPKEY_Device_ProblemCode,DEVPKEY_Device_DevNodeStatus` (device state).

## Workflow by symptom

1. **Install fails** → read the end of `setupapi.dev.log`. `0xe0000228 There are no compatible drivers`
   means the INF models section doesn't match this OS build (see F1).
2. **Installed but no endpoints / Code 39 / Code 10** → `check_driver_imports.py` on the `.sys` (F2);
   problem code and DevNodeStatus via `Get-PnpDeviceProperty`. Code 10 with
   `0x80000011 STATUS_DEVICE_BUSY` on a second `ROOT\MEDIA\000N` is a duplicate devnode (F6).
3. **Endpoints exist but names are generic** → `ksprobe.py pins` shows what the bridge pins report
   (`name=`), `wasapi_probe.py endpoints` shows what Windows stored (F4).
4. **No audio** → `cable_e2e_test.py loopback` (driver ring path) vs `passthrough` (capture endpoints).
5. **An endpoint can't be opened** → `ksprobe.py stream` (driver) vs `wasapi_probe.py open` (service).
   If only the service fails: `ksprobe.py modes` first (a processing mode this Windows doesn't know
   breaks the whole endpoint), `wasapi_probe.py interfaces` (does audiosrv answer for the endpoint at
   all?), `wasapi_probe.py compare` against a system endpoint, then `capture-trace.ps1` and read the
   WIL failures (F5).

## Findings log

### F1 — INF only matched Windows 11 22H2+
`devcon` failed with exit code 2; setupapi.dev.log: `No matching drivers found in single INF`,
`0xe0000228`. The INX models were decorated `NT$ARCH$.10.0...22621` (from the upstream sample). Fix:
decorate `10.0...19041` (Windows 10 2004+). CI fails if the decoration regresses.

### F2 — Driver imported Windows 11-only kernel exports
`check_driver_imports.py`: `ntoskrnl.exe` missing `ExAllocateFromNPagedLookasideList` /
`ExFreeToNPagedLookasideList` on Windows 10 19045. Current WDK headers turn these inline helpers into
imports. Pinning `_NT_TARGET_VERSION` to 19041 does **not** work: the sample needs Windows 11 types
(audio posture, resource groups) and stops compiling. Fix: a small shim in `sysvad/common.cpp` maps
them to `ExAllocatePool2` / `ExFreePoolWithTag` (they only serve the BT/USB sideband sample paths).
CI runs `dumpbin /imports` and fails on these names.

### F3 — Ring buffer latency and shared reader slots
A capture client opened after playback had started (e.g. WSJT-X after the radio stream) inherited a
backlog that never drained (readers consume at the writer's rate) — up to ~680 ms latency with
glitches on overrun. Fix: resync a reader whose backlog exceeds target + 100 ms. Later each
capture/loopback stream got its own read cursor (it starts at the current write position), because a
single per-cable reader slot would make concurrent recorders steal frames from each other.
Measured: ~185–205 ms end-to-end (7168-frame target + engine buffering), bit-exact level.

### F4 — Endpoint names
Windows names an endpoint from its topology **bridge pin**: `KSPROPERTY_PIN_NAME`, which portcls
answers from the pin descriptor's Name GUID looked up under the device's `MediaCategories` registry
key (written by the INF). The upstream sample shared one topology table across all cables, so all
endpoints were identical (`Speakers (...)` / `External Microphone Headphone (...)`), which makes them
unusable in apps that pick devices by name (browsers, WSJT-X). Fix: per-cable topology pin tables
(`EndpointsCommon/cablenames.h`) + INF `MediaCategories` entries `CABLE-A Input` … `CABLE-D Output`;
device name `VirtualCable`.
Result on Windows 10: capture endpoints became `CABLE-x Output (VirtualCable)`, but playback stayed
`Speakers (VirtualCable)` although `ksprobe.py pins` shows the bridge pin reporting `CABLE-A Input`:
Windows ignores the pin name for a Speaker-category, integrated (`ePortConnIntegratedDevice`) jack.
Fix: line-out category (`KSNODETYPE_LINE_CONNECTOR`) on a regular 3.5 mm jack, like the capture
side whose names are honoured. Verified with v3 (9.24.39.900): all eight endpoints are named
`CABLE-x Input/Output (VirtualCable)`, playback form factor LineLevel.
Naming is VB-CABLE's convention (reference manual): **CABLE Input is the playback device** (apps
play *into* the cable) and **CABLE Output is the recording device** (apps record what comes *out*).
So in the Sound panel the Playback tab lists `CABLE-x Input` and the Recording tab `CABLE-x Output`;
the wrc-proxy instructions use the same names.

### F5 — Capture endpoints could not be opened (AUDCLNT_E_UNSUPPORTED_FORMAT)
Every way of opening `CABLE-x Output` failed: shared `GetMixFormat`/`Initialize`, exclusive mode
(`IsFormatSupported` S_OK for mono but `Initialize` fails), every stream category and RAW mode, MME
(`WAVERR_BADFORMAT`). Playback and loopback on the same cables worked.

Ruled out, each with `ksprobe.py` (all behaved exactly like the working render pin):
format acceptance (PROPOSEDATAFORMAT), data intersection, per-mode default formats (PROPOSEDATAFORMAT2),
pin creation with DEFAULT/RAW mode attributes, concurrent instances, WaveRT buffer with notification,
notification event, ACQUIRE→PAUSE→RUN, topology path (bridge → volume → mute → peak meter → physical
connection → ADC → streaming pin), jack (connected), volume/mute nodes. Also not the cause:
microphone privacy settings (allowed), effects/APOs (none), and the capture pin instance limit
(`MICIN_MAX_INPUT_STREAMS` 1 → 5 changed nothing).

`capture-trace.ps1` + `summarize_trace.py` then showed the actual failure inside the audio service:

```
audiosrv.dll endpointcharacteristics.cpp:8095,8175,8524,8892,8944,6852  0x80070490 ERROR_NOT_FOUND
AudioServerGetMixFormat                       0x80070490
MapAEResultToAudioClient                      0x88890008 AUDCLNT_E_UNSUPPORTED_FORMAT (from ERROR_NOT_FOUND)
CPerEndpointVolumeAudioSession::CompleteConstruction  0x80070490   (on Initialize)
```

i.e. audiosrv could not build the endpoint's characteristics/mix format (the trace shows it reading
the device format, then the spatial-format step, then failing); "unsupported format" is just the
client-side mapping. `wasapi_probe.py endpoints/policy` confirm: device format present, mix format
missing (`0x80070490`), and setting one through IPolicyConfig fails the same way.
`wasapi_probe.py compare --endpoint <Realtek Stereo Mix> --enable-temporarily` showed that a system
capture endpoint opens fine, so capture works on the machine. Everything that works here is stereo;
the failing endpoints were the only mono ones. Tried: capture is stereo 16-bit 48 kHz (also
VB-CABLE's default).

Result of the stereo build (v3, 9.24.39.900): **not the cause.** Capture still fails identically
(mix format `0x80070490`, exclusive 2ch `IsFormatSupported` S_OK but `Initialize` `0x88890008`).
Narrowed further with `wasapi_probe.py interfaces`:

```
                         EndpointVolume  hwsupport  Meter  DeviceTopology  SessionManager2 calls
CABLE-x Input  (render)  ok              0x0        ok     ok              ok
CABLE-x Output (capture) ok              0x7        ok     ok              0x80070490 (all three)
```

The session manager is answered by audiosrv and involves no format, so the failure is inside
audiosrv's per-endpoint state, not in format negotiation. Disabling and re-enabling the endpoint
(`wasapi_probe.py rearrive`, no admin needed) reproduces it every time (deterministic, not an
install-time race).

`capture-trace.ps1` with re-arrival showed the arrival itself succeeds
(`EndpointCharacteristics Discovery ... hr=0x0`, evaluating the SPEECH and COMMUNICATIONS modes with
`IsMicArray=true`); the failure is when the mix format is resolved per processing mode
(`GetSpatialFormatForAudioFormatMustKeepDisabled` → `endpointcharacteristics.cpp:8095…6852`
`ERROR_NOT_FOUND`). A KS property sweep showed the capture and render pins answer the same
properties the same way; the difference is in the **mode list**:

```
ksprobe.py modes
== wavespeaker streaming pin 0: RAW DEFAULT MEDIA MOVIE COMMUNICATIONS NOTIFICATION  (all known)
== wavemicin   streaming pin 1: RAW DEFAULT SPEECH COMMUNICATIONS
                                FAR_FIELD_SPEECH  UNKNOWN to this Windows audiosrv
```

`AUDIO_SIGNALPROCESSINGMODE_FAR_FIELD_SPEECH` {28941cba-3be6-4a78-9a76-30fd91559b64} comes from the
upstream (Windows 11) sample's `MicInPinSupportedDeviceModes`. Its GUID does not occur in Windows 10's
audiosrv.dll / AudioEndpointBuilder.dll / audioeng.dll at all (SPEECH, COMMUNICATIONS, NOTIFICATION
do), so audiosrv cannot resolve the endpoint's modes and every client call fails with "not found",
which clients see as `AUDCLNT_E_UNSUPPORTED_FORMAT`. This explains why only capture failed, why
mono → stereo changed nothing and why the system's Stereo Mix works.
Fix: the capture pin advertises only RAW and DEFAULT (a cable is a pass-through; SPEECH /
COMMUNICATIONS clients fall back to DEFAULT). Hardware volume/mute/meter nodes (`hwsupport=0x7`) were
the other suspect and are not involved.
Lesson: run `ksprobe.py modes` after touching any `*PinSupportedDeviceModes` table; anything newer
than the oldest supported Windows breaks that endpoint there.

### F6 — Duplicate devnode after a failed install
A failed `devcon install` still creates `ROOT\MEDIA\0000` without a driver; reinstalling adds
`ROOT\MEDIA\0001`, which then fails with Code 10 / `STATUS_DEVICE_BUSY` while 0000 works.
`Install-Cable.ps1 -Uninstall` removes all nodes with the hardware ID; run it before reinstalling.

### Notes
* Each CI build creates a new test-signing certificate; reinstalling adds another
  "VirtualCable Local Test Signing" certificate to the machine stores (remove them after testing).
* The MMDevices endpoint GUIDs change when the device is reinstalled; scripts resolve cables by their
  KS wave filter (`wavespeaker[b-d]`, `wavemicin[b-d]`) rather than by GUID or name.

## Reference

MMDevices endpoint properties (`HKLM\SOFTWARE\Microsoft\Windows\CurrentVersion\MMDevices\Audio\{Render,Capture}\{guid}\Properties`):

| Value name | Meaning |
|---|---|
| `{a45c254e-df1c-4efd-8020-67d146a850e0},2` | endpoint name (PKEY_Device_DeviceDesc) |
| `{b3f8fa53-0004-438e-9003-51a46e139bfc},6` | device name shown in parentheses |
| `{1da5d803-d492-4edd-8c23-e0c0ffee7f0e},0` | form factor (1 Speakers, 2 LineLevel, 4 Microphone, …) |
| `{1da5d803-d492-4edd-8c23-e0c0ffee7f0e},8` | bridge pin category GUID |
| `{233164c8-1b2c-4c7d-bc68-b671687a2567},1` | KS wave filter path (`…\wavespeakerc`) — maps endpoint → cable |
| `{f19f064d-082c-4e27-bc73-6882a1bb8e4c},0` | device format (PKEY_AudioEngine_DeviceFormat) |
| `{e4870e26-3cc5-4cd2-ba46-ca0a9a70ed04},0` | mix format cached by audiosrv (missing ⇒ endpoint can't be opened) |

KS property ids used (KSPROPSETID_Pin): CINSTANCES 0, CTYPES 1, DATAFLOW 2, DATARANGES 3,
DATAINTERSECTION 4, COMMUNICATION 7, PHYSICALCONNECTION 10, CATEGORY 11, NAME 12, PROPOSEDATAFORMAT 14,
PROPOSEDATAFORMAT2 15. `KsCreatePin2` needs COM initialized (else `0x800401F0`).

Win32 errors from KS IOCTLs: 1168 not found / property unsupported, 1169 no match (format rejected),
50 not supported, 87 invalid parameter, 122 buffer too small, 1450 insufficient resources,
1170 property set not found.

HRESULTs: `0x88890008` AUDCLNT_E_UNSUPPORTED_FORMAT (also returned when audiosrv hits
ERROR_NOT_FOUND), `0x80070490` ERROR_NOT_FOUND, `0x80070491` (from KsCreatePin: format/pin mismatch),
`0x800705AA` ERROR_NO_SYSTEM_RESOURCES (pin instance limit reached).

ETW providers recorded by `capture-trace.ps1`: Microsoft-Windows-Audio (manifest) plus the
TraceLogging providers Microsoft.Windows.Audio.{Service, Engine, KernelStreamingEndpoint,
AudioEngineUtil, DeviceGraph, AudioDG, EndpointBuilder, EndpointCharacteristics, Client,
MultimediaDevice}, Microsoft.Audio.AudioClient, Microsoft.Audio.CrossProcess. The manifest provider
alone only logs state changes; the WIL failure events come from the TraceLogging providers.
