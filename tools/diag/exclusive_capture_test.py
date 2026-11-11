"""Exclusive-mode WASAPI capture test for the cable recording endpoints.

Bypasses the shared-mode audio engine (and its mix-format negotiation): plays a tone into
CABLE-x Input and records CABLE-y Output with an exclusive 48 kHz / 16-bit stream.
Usage: python tools/diag/exclusive_capture_test.py [play_cable] [record_cable] [channels]   (default A A 2)
Each failing COM call is reported with its HRESULT (e.g. Initialize or Start), which tells how far
an exclusive stream gets on the capture endpoint. See docs/DEBUGGING.md.
"""
import ctypes, struct, sys, threading, time, uuid
import os
import numpy as np
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))   # tools/
import cable_e2e_test as t
from soundcard import mediafoundation as mf

ffi = mf._ffi
HR = ctypes.c_long
SR = 48000


def vcall(ptr, index, restype, *argtypes):
    vtbl = ctypes.cast(ctypes.c_void_p.from_address(ptr).value, ctypes.POINTER(ctypes.c_void_p))
    return ctypes.WINFUNCTYPE(restype, ctypes.c_void_p, *argtypes)(vtbl[index])


def check(hr, what):
    if hr < 0:
        raise RuntimeError(f'{what} failed: 0x{hr & 0xffffffff:08X}')


def record_exclusive(mic, seconds, channels=2):
    pp = mic._audio_client()
    ac = int(ffi.cast('uintptr_t', pp[0]))
    pcm = uuid.UUID('00000001-0000-0010-8000-00AA00389B71').bytes_le
    fmt = ctypes.create_string_buffer(struct.pack('<HHIIHHHHI16s', 0xFFFE, channels, SR, SR * 2 * channels, 2 * channels, 16, 22, 16,
                                                 {1: 0x4, 2: 0x3}[channels], pcm))
    check(vcall(ac, 3, HR, ctypes.c_int, ctypes.c_uint32, ctypes.c_longlong, ctypes.c_longlong, ctypes.c_void_p, ctypes.c_void_p)(
        ac, 1, 0, 200000, 100000, fmt, None), 'Initialize(exclusive)')
    cap = ctypes.c_void_p()
    iid = (ctypes.c_byte * 16).from_buffer_copy(uuid.UUID('C8ADBD64-E71E-48A0-A4DE-185C395CD317').bytes_le)
    check(vcall(ac, 14, HR, ctypes.c_void_p, ctypes.POINTER(ctypes.c_void_p))(ac, ctypes.byref(iid), ctypes.byref(cap)), 'GetService')
    check(vcall(ac, 10, HR)(ac), 'Start')
    chunks, total, gaps = [], 0, 0
    get = vcall(cap.value, 3, HR, ctypes.POINTER(ctypes.c_void_p), ctypes.POINTER(ctypes.c_uint32), ctypes.POINTER(ctypes.c_uint32),
                ctypes.POINTER(ctypes.c_uint64), ctypes.POINTER(ctypes.c_uint64))
    rel = vcall(cap.value, 4, HR, ctypes.c_uint32)
    end = time.time() + seconds
    while time.time() < end:
        data, frames, flags = ctypes.c_void_p(), ctypes.c_uint32(), ctypes.c_uint32()
        hr = get(cap.value, ctypes.byref(data), ctypes.byref(frames), ctypes.byref(flags), None, None)
        if hr == 0 and frames.value:
            chunks.append(np.frombuffer(ctypes.string_at(data.value, frames.value * 2 * channels), dtype='<i2')
                          .reshape(-1, channels)[:, 0].copy())
            total += frames.value
            gaps += bool(flags.value & 1)   # AUDCLNT_BUFFERFLAGS_DATA_DISCONTINUITY
            rel(cap.value, frames.value)
        else:
            time.sleep(0.003)
    vcall(ac, 11, HR)(ac)
    x = np.concatenate(chunks).astype(np.float32) / 32768 if chunks else np.zeros(0, np.float32)
    return x, gaps


def main():
    play_c = sys.argv[1] if len(sys.argv) > 1 else 'A'
    rec_c = sys.argv[2] if len(sys.argv) > 2 else 'A'
    channels = int(sys.argv[3]) if len(sys.argv) > 3 else 2
    spk, mic = t.find_speaker(t.cable_in(play_c)), t.find_mic(t.cable_out(rec_c))
    tone = t.tone(1000, 3.5)
    stereo = np.column_stack([tone, tone])

    def play():
        with spk.player(samplerate=SR, channels=2, blocksize=480) as p:
            p.play(stereo)
    th = threading.Thread(target=play)
    th.start()
    time.sleep(0.4)
    x, gaps = record_exclusive(mic, 2.5, channels)
    th.join()
    seg = x[int(0.7 * SR): int(1.7 * SR)]
    lvl = t.db(t.level_at(seg, 1000)) if len(seg) else -180
    peak = t.db(float(np.max(np.abs(x)))) if len(x) else -180
    # continuity: residual after removing the 1 kHz component (dropouts/repeats raise it)
    spec = np.abs(np.fft.rfft(seg * np.hanning(len(seg)))) if len(seg) else np.zeros(1)
    k = int(round(1000 * len(seg) / SR)) if len(seg) else 0
    sig = float(np.sum(spec[max(k - 3, 0):k + 4] ** 2))
    noise = float(np.sum(spec ** 2)) - sig
    snr = 10 * np.log10(sig / noise) if noise > 0 and sig > 0 else float('inf')
    print(f'play CABLE-{play_c} Input -> record CABLE-{rec_c} Output (exclusive {channels}ch): frames={len(x)} ({len(x)/SR:.2f}s) '
          f'tone={lvl:.1f} dBFS peak={peak:.1f} dBFS SNR={snr:.1f} dB discontinuity-flags={gaps}')


if __name__ == '__main__':
    main()
