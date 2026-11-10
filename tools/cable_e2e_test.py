"""End-to-end test harness for the CABLE-A..D virtual audio endpoints.

Requires: numpy, soundcard  (pip install numpy soundcard)

Subcommands
  list                       Show playback/recording/loopback endpoints.
  passthrough [--cables AB]  Tone into each CABLE-x Input, record every CABLE-y Output:
                             checks pass-through, isolation, latency (chirp correlation).
  loopback    [--cables AB]  Tone into CABLE-x Input, WASAPI-loopback capture of the same endpoint.
  ft8 --wav F [--cable A] [--jt9 PATH]
                             Play an FT8 WAV (e.g. from WSJT-X ft8sim or a WebSDR/KiwiSDR
                             recording) into CABLE-x Input, record CABLE-x Output, write a
                             12 kHz WAV and decode it with WSJT-X's jt9.

  --play NAME / --rec NAME   Override endpoint names (substring match). With a real speaker as
                             --play and --rec "loopback:<speaker>" you can validate the harness
                             itself on a machine without the driver.
"""
import argparse
import os
import shutil
import subprocess
import sys
import tempfile
import threading
import time
import wave

import numpy as np
import soundcard as sc

SR = 48000
CABLES = "ABCD"


# ---------------------------------------------------------------- devices
def find_speaker(name):
    for s in sc.all_speakers():
        if name.lower() in s.name.lower():
            return s
    return None


def find_mic(name):
    loopback = name.lower().startswith("loopback:")
    if loopback:
        name = name.split(":", 1)[1]
    for m in sc.all_microphones(include_loopback=True):
        if name.lower() in m.name.lower() and bool(m.isloopback) == loopback:
            return m
    return None


def cable_in(c):
    return f"CABLE-{c} Input"


def cable_out(c):
    return f"CABLE-{c} Output"


# ---------------------------------------------------------------- signals
def tone(freq, seconds, amp=0.5):
    t = np.arange(int(seconds * SR)) / SR
    return (amp * np.sin(2 * np.pi * freq * t)).astype(np.float32)


def chirp(seconds=0.25, f0=500, f1=6000, amp=0.5):
    t = np.arange(int(seconds * SR)) / SR
    k = (f1 - f0) / seconds
    return (amp * np.sin(2 * np.pi * (f0 * t + 0.5 * k * t * t)) * np.hanning(len(t))).astype(np.float32)


def level_at(x, freq):
    """Amplitude (linear, ~peak) of a sinusoid at freq in mono signal x."""
    x = x - np.mean(x)
    n = len(x)
    if n == 0:
        return 0.0
    w = np.hanning(n)
    spec = np.abs(np.fft.rfft(x * w))
    bins = np.fft.rfftfreq(n, 1 / SR)
    i = int(np.argmin(np.abs(bins - freq)))
    return 2 * spec[max(i - 2, 0): i + 3].max() / w.sum()


def db(x):
    return 20 * np.log10(max(x, 1e-9))


def resample(x, src, dst):
    """FFT resampler (band-limited); fine for test-length clips."""
    if src == dst:
        return x
    n_out = int(round(len(x) * dst / src))
    X = np.fft.rfft(x)
    n_bins = n_out // 2 + 1
    Y = np.zeros(n_bins, dtype=complex)
    m = min(n_bins, len(X))
    Y[:m] = X[:m]
    return (np.fft.irfft(Y, n_out) * (n_out / len(x))).astype(np.float32)


def read_wav(path):
    with wave.open(path, "rb") as w:
        sr, ch, sw, n = w.getframerate(), w.getnchannels(), w.getsampwidth(), w.getnframes()
        raw = w.readframes(n)
    if sw != 2:
        raise SystemExit(f"{path}: only 16-bit PCM WAV supported")
    x = np.frombuffer(raw, dtype="<i2").astype(np.float32) / 32768
    if ch > 1:
        x = x.reshape(-1, ch).mean(axis=1)
    return resample(x, sr, SR)


def write_wav(path, x, sr):
    x = np.clip(x, -1, 1)
    with wave.open(path, "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(sr)
        w.writeframes((x * 32767).astype("<i2").tobytes())


# ---------------------------------------------------------------- play + record
def play_and_record(speaker, mics, signal, lead=0.5, tail=1.0):
    """Start all recorders, play signal (mono -> stereo) after `lead` s, return mono arrays."""
    total = int((lead + len(signal) / SR + tail) * SR)
    results = {}
    errors = []
    ready = threading.Barrier(len(mics) + 1)

    def rec(m):
        try:
            with m.recorder(samplerate=SR, channels=1, blocksize=480) as r:
                ready.wait()
                data = r.record(numframes=total)
            results[m.name if not m.isloopback else "loopback:" + m.name] = data[:, 0].astype(np.float32)
        except Exception as e:  # noqa: BLE001
            errors.append(f"record {m.name}: {e}")
            try:
                ready.abort()
            except Exception:  # noqa: BLE001
                pass

    threads = [threading.Thread(target=rec, args=(m,)) for m in mics]
    for t in threads:
        t.start()
    stereo = np.column_stack([signal, signal])
    try:
        with speaker.player(samplerate=SR, channels=2, blocksize=480) as p:
            ready.wait()
            p.play(np.zeros((int(lead * SR), 2), dtype=np.float32))
            p.play(stereo)
            p.play(np.zeros((int(tail * SR), 2), dtype=np.float32))
    except threading.BrokenBarrierError:
        pass
    for t in threads:
        t.join()
    if errors:
        raise RuntimeError("; ".join(errors))
    return results


def latency_ms(rec, ref, lead):
    """Delay of ref inside rec beyond the scheduled `lead`, via cross-correlation."""
    n = len(rec) + len(ref)
    nfft = 1 << (n - 1).bit_length()
    corr = np.fft.irfft(np.fft.rfft(rec, nfft) * np.conj(np.fft.rfft(ref, nfft)), nfft)[: len(rec)]
    peak = int(np.argmax(np.abs(corr)))
    strength = np.abs(corr[peak]) / (np.sqrt(np.sum(ref ** 2) * np.sum(rec[peak: peak + len(ref)] ** 2)) + 1e-12)
    return (peak / SR - lead) * 1000, float(strength)


# ---------------------------------------------------------------- tests
def cmd_list(_):
    print("Playback endpoints:")
    for s in sc.all_speakers():
        print("  ", s.name)
    print("Recording endpoints (incl. loopback):")
    for m in sc.all_microphones(include_loopback=True):
        print("  ", ("[loopback] " if m.isloopback else "") + m.name)
    missing = [n for c in CABLES for n in (cable_in(c), cable_out(c))
               if not (find_speaker(n) if "Input" in n else find_mic(n))]
    print("\nMissing cable endpoints:", ", ".join(missing) if missing else "none")
    return 0 if not missing else 1


def cmd_passthrough(args):
    freqs = {"A": 700, "B": 1100, "C": 1700, "D": 2300}
    cables = [c for c in args.cables if find_speaker(cable_in(c)) or args.play]
    outs = {c: find_mic(args.rec or cable_out(c)) for c in CABLES}
    outs = {c: m for c, m in outs.items() if m is not None}
    if args.rec:  # self-test mode: single recorder
        outs = {"X": find_mic(args.rec)}
    if not cables or not outs:
        print("Cable endpoints not found; run `list`.")
        return 2
    failed = False
    for c in cables:
        spk = find_speaker(args.play or cable_in(c))
        f = freqs[c]
        ref = chirp()
        sig = np.concatenate([ref, np.zeros(SR // 4, np.float32), tone(f, 2.0)])
        lead = 0.5
        rec = play_and_record(spk, list(outs.values()), sig, lead=lead)
        print(f"\n== {spk.name}  (tone {f} Hz)")
        for oc, m in outs.items():
            key = ("loopback:" if m.isloopback else "") + m.name
            x = rec[key]
            lat, corr = latency_ms(x, ref, lead)
            # analyze the steady tone section, skipping the latency/startup region
            tone_start = int((lead + 0.5 + max(lat, 0) / 1000 + 0.3) * SR)
            seg = x[tone_start: tone_start + SR]
            lvl = db(level_at(seg, f))
            peak = db(np.max(np.abs(x)) if len(x) else 0)
            expected = (oc == c) or oc == "X"
            if expected:
                ok = lvl > -12 and corr > 0.5
                print(f"  {m.name:<28} target: tone {lvl:6.1f} dBFS, chirp corr {corr:.2f}, latency {lat:7.1f} ms  {'PASS' if ok else 'FAIL'}")
            else:
                ok = peak < -70
                print(f"  {m.name:<28} isolation: peak {peak:6.1f} dBFS  {'PASS' if ok else 'FAIL (leak)'}")
            failed |= not ok
    print("\nRESULT:", "FAIL" if failed else "PASS")
    return 1 if failed else 0


def cmd_loopback(args):
    failed = False
    for c in args.cables:
        spk = find_speaker(args.play or cable_in(c))
        lb = find_mic(args.rec or "loopback:" + cable_in(c))
        if not spk or not lb:
            print(f"CABLE-{c}: endpoint or loopback not found")
            failed = True
            continue
        rec = play_and_record(spk, [lb], tone(1000, 1.5), lead=0.3)
        x = next(iter(rec.values()))
        lvl = db(level_at(x[int(0.6 * SR): int(1.6 * SR)], 1000))
        ok = lvl > -12
        failed |= not ok
        print(f"loopback {spk.name:<28} tone {lvl:6.1f} dBFS  {'PASS' if ok else 'FAIL'}")
    return 1 if failed else 0


def find_jt9(explicit):
    cands = [explicit] if explicit else []
    cands += [shutil.which("jt9"), r"C:\WSJT\wsjtx\bin\jt9.exe",
              r"C:\Program Files\wsjtx\bin\jt9.exe", r"C:\Program Files (x86)\wsjtx\bin\jt9.exe"]
    return next((p for p in cands if p and os.path.exists(p)), None)


def cmd_ft8(args):
    spk = find_speaker(args.play or cable_in(args.cable))
    mic = find_mic(args.rec or cable_out(args.cable))
    if not spk or not mic:
        print("endpoints not found; run `list`")
        return 2
    x = read_wav(args.wav)[: 15 * SR]
    x = x / (np.max(np.abs(x)) + 1e-9) * 0.5
    print(f"Playing {args.wav} ({len(x)/SR:.1f}s) -> {spk.name}, recording {mic.name}")
    rec = play_and_record(spk, [mic], x, lead=0.0, tail=1.0)
    y = next(iter(rec.values()))[: 15 * SR]
    out = args.out or os.path.join(tempfile.gettempdir(), "cable_ft8_capture_12k.wav")
    write_wav(out, resample(y, SR, 12000), 12000)
    print(f"Captured {db(np.max(np.abs(y))):.1f} dBFS peak -> {out}")
    jt9 = find_jt9(args.jt9)
    if not jt9:
        print("jt9.exe not found (install WSJT-X or pass --jt9). Decode the WAV manually.")
        return 0
    work = tempfile.mkdtemp(prefix="jt9_")
    for f in (args.wav, out):
        r = subprocess.run([jt9, "-8", "-d", "3", "-a", work, "-t", work, f],
                           cwd=work, capture_output=True, text=True, timeout=120)
        decodes = [l for l in r.stdout.splitlines() if l.strip() and "<DecodeFinished>" not in l]
        print(f"\njt9 decodes for {os.path.basename(f)} ({len(decodes)}):")
        for l in decodes:
            print("  ", l)
    return 0


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("cmd", choices=["list", "passthrough", "loopback", "ft8"])
    ap.add_argument("--cables", default="ABCD")
    ap.add_argument("--cable", default="A")
    ap.add_argument("--play")
    ap.add_argument("--rec")
    ap.add_argument("--wav")
    ap.add_argument("--out")
    ap.add_argument("--jt9")
    args = ap.parse_args()
    return {"list": cmd_list, "passthrough": cmd_passthrough,
            "loopback": cmd_loopback, "ft8": cmd_ft8}[args.cmd](args)


if __name__ == "__main__":
    sys.exit(main())
