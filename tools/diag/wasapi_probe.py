"""Probe how the Windows audio service (audiosrv/audiodg) sees the VirtualCable endpoints.

Usage (from the repo root; needs `pip install numpy soundcard`):
  python tools/diag/wasapi_probe.py endpoints            MMDevices registry: name, state, form factor, KS filter,
                                                         stored device/mix format, FxProperties
  python tools/diag/wasapi_probe.py open [--cable A]     GetMixFormat, shared/exclusive IsFormatSupported/Initialize,
                                                         IAudioClient2 categories + RAW, MME waveInOpen/waveOutOpen
  python tools/diag/wasapi_probe.py policy               IPolicyConfig (Sound control panel API) device/mix formats
  python tools/diag/wasapi_probe.py compare --endpoint {0.0.1.00000000}.{GUID} [--enable-temporarily]
                                                         run `open` against another endpoint (e.g. Realtek Stereo Mix)
                                                         to tell a system-wide capture problem from a driver one

HRESULTs: 0x88890008 AUDCLNT_E_UNSUPPORTED_FORMAT, 0x80070490 ERROR_NOT_FOUND (audiosrv could not build
the endpoint's mix format), 0x8889000A AUDCLNT_E_DEVICE_IN_USE. See docs/DEBUGGING.md.
"""
import argparse
import ctypes
import os
import struct
import sys
import time
import uuid
import winreg

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))   # tools/ (cable_e2e_test)
import cable_e2e_test as t  # noqa: E402
import soundcard as sc  # noqa: E402
from soundcard import mediafoundation as mf  # noqa: E402

ffi = mf._ffi
HR = ctypes.c_long
MMDEV = r'SOFTWARE\Microsoft\Windows\CurrentVersion\MMDevices\Audio'
PKEY = {
    'name': '{a45c254e-df1c-4efd-8020-67d146a850e0},2',            # PKEY_Device_DeviceDesc (endpoint name)
    'iface': '{b3f8fa53-0004-438e-9003-51a46e139bfc},6',           # device name shown in parentheses
    'formfactor': '{1da5d803-d492-4edd-8c23-e0c0ffee7f0e},0',      # PKEY_AudioEndpoint_FormFactor
    'jacksubtype': '{1da5d803-d492-4edd-8c23-e0c0ffee7f0e},8',     # pin category GUID
    'ksfilter': '{233164c8-1b2c-4c7d-bc68-b671687a2567},1',        # KS wave filter path
    'devfmt': '{f19f064d-082c-4e27-bc73-6882a1bb8e4c},0',          # PKEY_AudioEngine_DeviceFormat
    'mixfmt': '{e4870e26-3cc5-4cd2-ba46-ca0a9a70ed04},0',          # mix format cached by audiosrv
}
FORM_FACTORS = {0: 'RemoteNetwork', 1: 'Speakers', 2: 'LineLevel', 3: 'Headphones', 4: 'Microphone',
                5: 'Headset', 6: 'Handset', 7: 'UnknownDigitalPassthrough', 8: 'SPDIF', 9: 'DigitalAudioDisplay', 10: 'Unknown'}


def hx(hr):
    return f'0x{hr & 0xffffffff:08X}'


def vcall(ptr, index, *argtypes):
    vtbl = ctypes.cast(ctypes.c_void_p.from_address(ptr).value, ctypes.POINTER(ctypes.c_void_p))
    return ctypes.WINFUNCTYPE(HR, ctypes.c_void_p, *argtypes)(vtbl[index])


def wfx_desc(b):
    if not b or len(b) < 18:
        return 'none'
    tag, ch, sr, avg, align, bits = struct.unpack_from('<HHIIHH', b)
    s = f'{ch}ch {sr}Hz {bits}-bit tag=0x{tag:X}'
    if tag == 0xFFFE and len(b) >= 40:
        mask = struct.unpack_from('<I', b, 20)[0]
        sub = uuid.UUID(bytes_le=bytes(b[24:40]))
        s += f' mask=0x{mask:X} {"float" if str(sub).startswith("00000003") else "pcm"}'
    return s


def wfx(ch, bits=16, float_=False, mask=None):
    mask = mask if mask is not None else {1: 0x4, 2: 0x3}.get(ch, 0)
    sub = uuid.UUID('00000003-0000-0010-8000-00AA00389B71' if float_ else '00000001-0000-0010-8000-00AA00389B71').bytes_le
    align = ch * bits // 8
    return ctypes.create_string_buffer(struct.pack('<HHIIHHHHI16s', 0xFFFE, ch, 48000, 48000 * align, align, bits, 22, bits, mask, sub))


# ----------------------------------------------------------------- endpoints (registry)
def cmd_endpoints(_args):
    for flow in ('Render', 'Capture'):
        with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, f'{MMDEV}\\{flow}') as root:
            i = 0
            while True:
                try:
                    ep = winreg.EnumKey(root, i)
                except OSError:
                    break
                i += 1
                vals = {}
                try:
                    with winreg.OpenKey(root, ep + r'\Properties') as p:
                        for k, v in PKEY.items():
                            try:
                                vals[k] = winreg.QueryValueEx(p, v)[0]
                            except OSError:
                                pass
                    with winreg.OpenKey(root, ep) as k:
                        state = winreg.QueryValueEx(k, 'DeviceState')[0]
                except OSError:
                    continue
                if 'root#media#' not in str(vals.get('ksfilter', '')).lower() or state != 1:
                    continue
                try:
                    winreg.OpenKey(root, ep + r'\FxProperties').Close()
                    fx = 'yes'
                except OSError:
                    fx = 'no'
                print(f'{flow:<7} {ep} {vals.get("name")} ({vals.get("iface")})')
                print(f'        form factor={FORM_FACTORS.get(vals.get("formfactor"), vals.get("formfactor"))} '
                      f'filter={str(vals.get("ksfilter", "")).rsplit(chr(92), 1)[-1]} FxProperties={fx}')
                print(f'        device format: {wfx_desc(vals.get("devfmt", b"")[8:])}   mix format: '
                      f'{wfx_desc(vals.get("mixfmt", b"")[8:]) if vals.get("mixfmt") else "MISSING"}')


# ----------------------------------------------------------------- open attempts
def try_open(dev, label):
    print(f'== {label}: {dev.name}  id={dev.id}')

    def client():
        pp = dev._audio_client()
        return int(ffi.cast('uintptr_t', pp[0]))

    ac = client()
    fmt = ctypes.c_void_p()
    hr = vcall(ac, 8, ctypes.POINTER(ctypes.c_void_p))(ac, ctypes.byref(fmt))
    mix = ctypes.string_at(fmt.value, 40) if hr == 0 and fmt.value else None
    print(f'   GetMixFormat                 -> {hx(hr)} {wfx_desc(mix) if mix else ""}')
    if mix:
        hr = vcall(ac, 3, ctypes.c_int, ctypes.c_uint32, ctypes.c_longlong, ctypes.c_longlong, ctypes.c_void_p, ctypes.c_void_p)(
            ac, 0, 0, 200000, 0, fmt.value, None)
        print(f'   Initialize(shared, mix fmt)  -> {hx(hr)}')
    for ch in (1, 2):
        ac = client()
        f = wfx(ch)
        hr1 = vcall(ac, 7, ctypes.c_int, ctypes.c_void_p, ctypes.c_void_p)(ac, 1, f, None)
        hr2 = vcall(ac, 3, ctypes.c_int, ctypes.c_uint32, ctypes.c_longlong, ctypes.c_longlong, ctypes.c_void_p, ctypes.c_void_p)(
            ac, 1, 0, 200000, 200000, f, None)
        print(f'   exclusive {ch}ch 16-bit 48k     -> IsFormatSupported {hx(hr1)}  Initialize {hx(hr2)}')
    # IAudioClient2::SetClientProperties (category / RAW) then GetMixFormat
    for cat, opt, lbl in ((0, 0, 'Other'), (0, 1, 'Other+RAW'), (3, 0, 'Communications'), (11, 1, 'Media+RAW')):
        ac = client()
        ac2 = ctypes.c_void_p()
        iid = (ctypes.c_byte * 16).from_buffer_copy(uuid.UUID('726778CD-F60A-4EDA-82DE-E47610CD78AA').bytes_le)
        if vcall(ac, 0, ctypes.c_void_p, ctypes.POINTER(ctypes.c_void_p))(ac, ctypes.byref(iid), ctypes.byref(ac2)):
            continue
        props = ctypes.create_string_buffer(struct.pack('<IiiI', 16, 0, cat, opt))
        h1 = vcall(ac2.value, 16, ctypes.c_void_p)(ac2.value, props)
        fmt = ctypes.c_void_p()
        h2 = vcall(ac, 8, ctypes.POINTER(ctypes.c_void_p))(ac, ctypes.byref(fmt))
        print(f'   {lbl:<16} SetClientProperties {hx(h1)} GetMixFormat {hx(h2)}')


def mme(capture):
    winmm = ctypes.WinDLL('winmm')
    caps_size = 2 + 2 + 4 + 64 + 4 + 2 + 2 + (2 if not capture else 0) + (4 if not capture else 0)
    n = winmm.waveInGetNumDevs() if capture else winmm.waveOutGetNumDevs()
    for i in range(n):
        caps = ctypes.create_string_buffer(caps_size + 16)
        (winmm.waveInGetDevCapsW if capture else winmm.waveOutGetDevCapsW)(i, caps, caps_size)
        name = caps.raw[8:72].decode('utf-16-le').split('\0')[0]
        if 'CABLE' not in name and 'VirtualCable' not in name and 'Speakers (V' not in name:
            continue
        for ch in (1, 2):
            fx = ctypes.create_string_buffer(struct.pack('<HHIIHHH', 1, ch, 48000, 48000 * 2 * ch, 2 * ch, 16, 0))
            h = ctypes.c_void_p()
            r = (winmm.waveInOpen if capture else winmm.waveOutOpen)(ctypes.byref(h), i, fx, None, None, 0)
            if r == 0:
                (winmm.waveInClose if capture else winmm.waveOutClose)(h)
            print(f'   MME {"in " if capture else "out"} #{i} {name!r} {ch}ch -> {r}{" (WAVERR_BADFORMAT)" if r == 32 else ""}')


def cmd_open(args):
    try_open(t.find_speaker(t.cable_in(args.cable)), f'CABLE-{args.cable} Input (render)')
    try_open(t.find_mic(t.cable_out(args.cable)), f'CABLE-{args.cable} Output (capture)')
    mme(capture=False)
    mme(capture=True)


# ----------------------------------------------------------------- IPolicyConfig
def policy_config():
    ole32 = ctypes.WinDLL('ole32')
    ole32.CoInitializeEx(None, 0)
    pc = ctypes.c_void_p()
    clsid = (ctypes.c_byte * 16).from_buffer_copy(uuid.UUID('870AF99C-171D-4F9E-AF0D-E63DF40C2BC9').bytes_le)
    iid = (ctypes.c_byte * 16).from_buffer_copy(uuid.UUID('F8679F50-850A-41CF-9C72-430F290290C8').bytes_le)
    hr = ole32.CoCreateInstance(ctypes.byref(clsid), None, 1, ctypes.byref(iid), ctypes.byref(pc))
    if hr:
        raise OSError(f'CoCreateInstance(PolicyConfig) {hx(hr)}')
    return pc.value


def policy_show(pc, label, dev_id):
    mix, devf = ctypes.c_void_p(), ctypes.c_void_p()
    h1 = vcall(pc, 3, ctypes.c_wchar_p, ctypes.POINTER(ctypes.c_void_p))(pc, dev_id, ctypes.byref(mix))
    h2 = vcall(pc, 4, ctypes.c_wchar_p, ctypes.c_int, ctypes.POINTER(ctypes.c_void_p))(pc, dev_id, 0, ctypes.byref(devf))
    print(f'{label:<26} mix {hx(h1)} [{wfx_desc(ctypes.string_at(mix.value, 40)) if h1 == 0 else "-"}]  '
          f'device {hx(h2)} [{wfx_desc(ctypes.string_at(devf.value, 40)) if h2 == 0 else "-"}]')


def cmd_policy(_args):
    pc = policy_config()
    for c in 'ABCD':
        for label, dev in ((t.cable_in(c), t.find_speaker(t.cable_in(c))), (t.cable_out(c), t.find_mic(t.cable_out(c)))):
            if dev:
                policy_show(pc, label, dev.id)


def cmd_compare(args):
    pc = policy_config()
    vis = vcall(pc, 14, ctypes.c_wchar_p, ctypes.c_int)   # IPolicyConfig::SetEndpointVisibility
    if args.enable_temporarily:
        print(f'enable {args.endpoint}: {hx(vis(pc, args.endpoint, 1))}')
        time.sleep(1.5)
    try:
        policy_show(pc, 'compare endpoint', args.endpoint)
        devs = list(sc.all_microphones()) + list(sc.all_speakers())
        dev = next((d for d in devs if args.endpoint.lower() in d.id.lower()), None)
        if dev:
            try_open(dev, 'compare endpoint')
        else:
            print('endpoint not active (use --enable-temporarily for a disabled one)')
    finally:
        if args.enable_temporarily:
            print(f'disable again: {hx(vis(pc, args.endpoint, 0))}')


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('cmd', choices=['endpoints', 'open', 'policy', 'compare'])
    ap.add_argument('--cable', default='A', choices=list('ABCD'))
    ap.add_argument('--endpoint', help='endpoint id for compare, e.g. {0.0.1.00000000}.{c7ac12bc-...}')
    ap.add_argument('--enable-temporarily', action='store_true', help='compare: enable a disabled endpoint, then disable it again')
    args = ap.parse_args()
    {'endpoints': cmd_endpoints, 'open': cmd_open, 'policy': cmd_policy, 'compare': cmd_compare}[args.cmd](args)


if __name__ == '__main__':
    main()
