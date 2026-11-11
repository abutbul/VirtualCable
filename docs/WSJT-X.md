# Using VirtualCable with WSJT-X and Web Radio Control

This guide sets up FT8 (or any WSJT-X mode) on a remote radio served by Web Radio Control (WRC). The
browser plays the radio's receive audio into a cable, and WSJT-X decodes it. WSJT-X's transmit audio
goes back through a second cable into the browser. Frequency and PTT go through `wrc-proxy`, which
speaks the Hamlib `rigctld` protocol. It follows the WRC guide
[Working digital modes – Windows](https://legacy.doc.webradiocontrol.tech/user-guide/working-digital-modes/windows/)
with VirtualCable in place of VB-CABLE A/B.

## How the pieces connect

```
                 receive audio                                          
 WRC (Chrome) ──► CABLE-A Input ══ cable A ══► CABLE-A Output ──► WSJT-X  (Audio > Input)
   playback        (playback device)            (recording device)

                 transmit audio
 WSJT-X ───────► CABLE-B Input ══ cable B ══► CABLE-B Output ──► WRC (Chrome microphone)
 (Audio > Output)  (playback device)           (recording device)

 WSJT-X ── Hamlib NET rigctl ──► wrc-proxy (localhost:4532) ──► WRC ──► radio (frequency, mode, PTT)
```

Naming follows VB-CABLE: **`CABLE-x Input` is a playback device** (you play *into* the cable) and
**`CABLE-x Output` is a recording device** (you record what comes *out* of it). Whatever is played
to `CABLE-A Input` comes out of `CABLE-A Output` (and nowhere else), typically 185–205 ms later.

## 1. Requirements

* VirtualCable driver **v4 (DriverVer 10.52.44.702) or newer**. Earlier builds could not open the
  recording endpoints on Windows 10 at all: WSJT-X shows *"Error in Sound Input"*, Python/WASAPI
  gets `AUDCLNT_E_UNSUPPORTED_FORMAT`. See [DEBUGGING.md, F5](DEBUGGING.md#f5--capture-endpoints-could-not-be-opened-audclnt_e_unsupported_format).
* All eight endpoints present: Sound control panel → *Playback* lists `CABLE-A Input` …
  `CABLE-D Input (VirtualCable)`, *Recording* lists `CABLE-A Output` … `CABLE-D Output (VirtualCable)`.
  `python tools/cable_e2e_test.py list` checks this.
* WSJT-X 2.6 or newer (official release), `wrc-proxy` running and connected to your WRC session.
* PC clock synchronised (FT8 needs |DT| below about 1 s). Windows time sync is usually enough, but a
  tool such as Meinberg NTP or Dimension 4 is more reliable.

## 2. Windows sound settings

Open the classic Sound control panel (`mmsys.cpl`):

1. **Playback** tab: right-click `CABLE-A Input` → *Set as Default Device*. Chrome then plays the
   radio into cable A.
2. **Recording** tab: right-click `CABLE-B Output` → *Set as Default Device*. Chrome then uses cable B
   as its microphone (transmit audio).
3. Leave `CABLE-A Input` and `CABLE-B Input` at **100 % volume**; the playback volume scales the signal
   going through the cable.
4. Optional: `CABLE-A Input` → *Properties* → *Listen* is not needed. To hear the radio while
   WSJT-X decodes, use the WRC page's own monitoring or `CABLE-A Output` → *Listen to this device*
   on your speakers.

Making the cables the defaults also sends system sounds and other apps into cable A. If you prefer to
keep your normal speakers as the default, route only Chrome instead: Windows *Settings → System →
Sound → App volume and device preferences* → `chrome.exe` output `CABLE-A Input`, input
`CABLE-B Output` (Chrome must be playing to appear in that list). Chrome's own microphone choice is
under *Settings → Privacy and security → Site settings → Microphone*.

Write down the old default devices so you can restore them afterwards.

## 3. Browser (Web Radio Control)

1. Open the WRC session and reserve the radio as usual.
2. Press **Play** (receive audio). Without it nothing reaches cable A and WSJT-X's waterfall stays
   empty: Chrome only creates an audio stream once the page plays.
3. Allow the **microphone** when Chrome asks. It is used only for transmit audio (`CABLE-B Output`);
   nothing is sent unless PTT is keyed.
4. If Chrome was already open before you changed the default devices, reload the WRC tab (or restart
   Chrome) so it picks up the new devices.

## 4. WSJT-X settings

*File → Settings*:

### General
* *My Call*, *My Grid*: yours. Needed for decoding your own replies and for transmitting.

### Radio
| Setting | Value |
|---|---|
| Rig | **Hamlib NET rigctl** |
| CAT Control → Network Server | **`localhost:4532`** (the wrc-proxy port) |
| Poll Interval | 1 s |
| PTT Method | **CAT** to transmit through WRC; **VOX** for receive-only (WSJT-X then never sends a PTT command) |
| Mode | **Data/Pkt** (the radio goes to PKTUSB/USB-D) |
| Split Operation | **Fake It** |

Press **Test CAT**: the button turns green and WSJT-X's dial frequency now matches the WRC page.
Only press *Test PTT* if you are licensed and allowed to transmit on that radio and frequency, because
it keys the transmitter.

With **Rig = None**, WSJT-X does not talk to the radio at all. It decodes fine, but the frequency it
shows is just its own band selection: it neither follows nor changes the radio. Its decode log is
labelled with that frequency, and it is wrong whenever the radio is on another band.

### Audio
| Setting | Value |
|---|---|
| Soundcard → Input | **`CABLE-A Output (VirtualCable)`**, **Mono** |
| Soundcard → Output | **`CABLE-B Input (VirtualCable)`**, **Mono** |

Do **not** pick `CABLE-A Input` as the output. It is cable A's playback side, so WSJT-X's transmit tones
would come back out of `CABLE-A Output` and be decoded as received signals, mixed with the radio. The
cables are stereo 48 kHz; WSJT-X's *Mono* setting works directly, no resampling settings are needed.

### Frequencies (optional: restrict bands)
WSJT-X has no "allowed bands" option, but its band list comes from *Settings → Frequencies →
Working Frequencies*. Select the FT8 rows for bands you must not use, right-click → *Delete*, OK.
The band menu then offers only what is left (e.g. 14.074, 21.074, 28.074 MHz for 20/15/10 m).
Right-click → *Reset* restores the defaults.

## 5. Start and check

1. Press **Monitor** in WSJT-X (it listens; it never transmits).
2. The **input level bar** (bottom left) should sit around 30 dB on a quiet band; if it is red, lower
   the WRC page's volume. The waterfall shows the FT8 signals within one 15 s slot.
3. Decodes appear in *Band Activity* at the end of each slot. Every decode is also written to
   `%LOCALAPPDATA%\WSJT-X\ALL.TXT`, labelled with WSJT-X's dial frequency.
4. Leave **Enable Tx** off unless you intend to transmit.

Checking the cable without WSJT-X (receive-only, prints decodes and reads the dial from wrc-proxy):

```
python tools/ft8_monitor.py --cable A --slots 8 --rig localhost:4532
```

## 6. Troubleshooting

| Symptom | Cause / fix |
|---|---|
| WSJT-X frequency differs from the WRC page | Rig is *None*. Set Hamlib NET rigctl, `localhost:4532` (section 4) and press Test CAT. |
| WSJT-X "jumps" to another band | With CAT on, WSJT-X shows whatever the radio is set to, so something is tuning the radio: the WRC page's band/frequency controls, a script, or the **mouse wheel over WSJT-X's band menu** (scrolling a drop-down changes the band and, with CAT, retunes the radio). Restrict the band list (section 4) to prevent accidental bands. In FT8 mode WSJT-X never scans bands on its own; *Band Hopping* exists only in WSPR mode. |
| Waterfall flat, no decodes | Chrome is not playing: press Play in WRC. Check Chrome outputs to `CABLE-A Input` (Windows *App volume and device preferences* shows per-app devices). `python tools/ft8_monitor.py` shows the cable's level: around −30 dBFS with signals, about −240 dBFS (digital silence) means nothing is playing into the cable. |
| "Error in Sound Input" / device missing | Driver older than v4 (DEBUGGING.md F5), or the endpoint is disabled in the Sound panel (*Show Disabled Devices*). Run `python tools/diag/wasapi_probe.py open`. |
| Decodes with large DT (> 1 s) | PC clock is off; resync it. The cable adds about 0.2 s, which is within FT8's tolerance. |
| Own transmit tones show up as decodes | WSJT-X output is set to `CABLE-A Input`; set it to `CABLE-B Input`. |
| Transmit goes out silent | Chrome's microphone is not `CABLE-B Output`, or the microphone permission was refused; check the site settings. |

## Test results (Windows 10 Pro 19045, driver v4 10.52.44.702, 2026-11-11)

Live WRC receive audio, receive only (PTT verified `0` before and after every frequency change; no
transmission). Radio tuned through wrc-proxy to the FT8 calling frequencies in data mode; decoding
with `tools/ft8_monitor.py` (jt9) on `CABLE-A Output`, and in parallel by WSJT-X itself.

| Band | Dial | Slots | Decodes | Cable level | Examples heard |
|---|---|---|---|---|---|
| 20 m | 14.074 MHz | 3 | 26 / 32 / 37 | −28 to −30 dBFS | I0XNH, R4CGV, IK4LZH (+19 dB), HA1BF, OK1AYM, SP4FEU, OE5PEN, HF5A, 5H3DX, TF3PPN, UR7FM/MM |
| 15 m | 21.074 MHz | 8 | 19 | −31 to −34 dBFS | ZS4AW (+5 dB), ZR6FAR, TN8GD, TJ1GD, D2ACE, 4X5MZ |
| 10 m | 28.074 MHz | 8 | 11 | −33 dBFS | C91RU, Z21ML, ZR6PE, LW2EDM |

* Decode timing DT −1.5…+1.8 s, mostly 0.1–0.9 s: the cable's ~0.2 s latency does not affect
  decoding.
* WSJT-X decoded the same 20 m traffic from `CABLE-A Output` concurrently (WSJT-X and
  `ft8_monitor.py` recording the same cable at the same time; each capture stream has its own read
  position).
* `cable_e2e_test.py passthrough` PASS on A–D (−6.0 dBFS, chirp correlation 1.00, isolation
  −180 dBFS, latency 184–206 ms); an `ft8sim` signal at −12 dB through CABLE-A and CABLE-B decodes at
  the source SNR.
