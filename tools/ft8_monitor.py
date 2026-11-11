"""Receive-only FT8 monitor for a VirtualCable recording endpoint.

Records `CABLE-x Output` in 15 s slots aligned to UTC, decodes each slot with WSJT-X's `jt9` and prints
the decodes, the slot's audio level and (optionally) the radio's dial frequency read from a rigctld
server such as wrc-proxy. It is an independent check of the receive path: if this decodes and WSJT-X
does not, the problem is in WSJT-X's settings, not in the cable.

It never transmits and never changes the radio: the only rigctld command it sends is `f` (read
frequency).

usage:
  python tools/ft8_monitor.py [--cable A] [--slots 8] [--rig localhost:4532] [--log ft8.log]
                              [--jt9 PATH] [--work DIR]
"""
import argparse
import datetime as dt
import os
import shutil
import socket
import subprocess
import tempfile
import time
import warnings
import wave

import numpy as np
import soundcard as sc

warnings.filterwarnings('ignore')
RATE = 48000
JT9_CANDIDATES = [
    os.path.expandvars(r'%LOCALAPPDATA%\wsjtx\bin\jt9.exe'),
    r'C:\WSJT\wsjtx\bin\jt9.exe',
    r'C:\Program Files\wsjtx\bin\jt9.exe',
]

# windowed-sinc low-pass at 5 kHz, then decimate 48 kHz -> 12 kHz (jt9's input rate)
_n = np.arange(-96, 97)
_h = np.sinc(2 * 5000 / RATE * _n) * np.hamming(len(_n))
_h /= _h.sum()


def find_jt9(explicit):
    for p in [explicit] + JT9_CANDIDATES + [shutil.which('jt9') or '']:
        if p and os.path.isfile(p):
            return p
    raise SystemExit('jt9.exe not found; install WSJT-X or pass --jt9')


def rig_freq(addr):
    if not addr:
        return 0
    host, port = addr.rsplit(':', 1)
    try:
        with socket.create_connection((host, int(port)), timeout=3) as s:
            f = s.makefile('rw', newline='\n')
            f.write('f\n')
            f.flush()
            return int(f.readline().strip())
    except (OSError, ValueError):
        return 0


def decodes(proc):
    out = proc.stdout.read().splitlines()
    return [ln.strip() for ln in out if ln.strip() and 'DecodeFinished' not in ln and not ln.startswith('<')]


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--cable', default='A', help='cable letter (records "CABLE-<x> Output")')
    ap.add_argument('--slots', type=int, default=8, help='number of 15 s FT8 slots to record')
    ap.add_argument('--rig', default='', help='rigctld host:port to read the dial frequency from (read only)')
    ap.add_argument('--log', default='', help='append decodes to this file')
    ap.add_argument('--jt9', default='', help='path to jt9.exe')
    ap.add_argument('--work', default='', help='folder for slot WAVs (default: a temp folder)')
    a = ap.parse_args()

    jt9 = find_jt9(a.jt9)
    work = a.work or tempfile.mkdtemp(prefix='ft8mon_')
    os.makedirs(work, exist_ok=True)
    name = f'CABLE-{a.cable.upper()} Output'
    mic = next((m for m in sc.all_microphones() if name in m.name), None)
    if mic is None:
        raise SystemExit(f'recording endpoint "{name}" not found')

    def log(line):
        print(line, flush=True)
        if a.log:
            with open(a.log, 'a', encoding='utf-8') as fh:
                fh.write(line + '\n')

    def report(item):
        t0, freq, level, proc = item
        proc.wait()
        lines = decodes(proc)
        dial = f'dial {freq / 1e6:.3f} MHz  ' if freq else ''
        log(f'== {t0:%Y-%m-%d %H:%M:%S}Z  {dial}level {level:5.1f} dBFS  decodes {len(lines)}')
        for ln in lines:
            log('   ' + ln)

    pending = []
    with mic.recorder(samplerate=RATE, channels=1, blocksize=RATE // 10) as r:
        r.record(numframes=RATE // 10)                      # prime the stream
        now = time.time()
        start = now + (15 - now % 15)
        r.record(numframes=int((start - now) * RATE))       # skip to the next slot boundary
        for i in range(a.slots):
            t0 = dt.datetime.fromtimestamp(round(start) + 15 * i, dt.timezone.utc)
            freq = rig_freq(a.rig)
            x = r.record(numframes=15 * RATE)[:, 0]
            y = np.convolve(x, _h, mode='same')[::4]
            peak = max(float(np.max(np.abs(y))), 0.05)
            pcm = (y / peak * 0.5 * 32767).astype('<i2')
            wav = os.path.join(work, t0.strftime('%y%m%d_%H%M%S') + '.wav')
            with wave.open(wav, 'wb') as w:
                w.setnchannels(1)
                w.setsampwidth(2)
                w.setframerate(12000)
                w.writeframes(pcm.tobytes())
            tmp = os.path.join(work, f'jt9_{i}')
            os.makedirs(tmp, exist_ok=True)
            level = 20 * np.log10(np.sqrt(np.mean(x ** 2)) + 1e-12)
            pending.append((t0, freq, level, subprocess.Popen(
                [jt9, '-8', '-d', '3', '-a', tmp, '-t', tmp, wav], cwd=tmp, stdout=subprocess.PIPE, text=True)))
            while pending and pending[0][3].poll() is not None:   # print finished slots in order
                report(pending.pop(0))
    for item in pending:
        report(item)


if __name__ == '__main__':
    main()
