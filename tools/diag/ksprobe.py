"""Probe the VirtualCable driver's KS filters directly (no audio service involved).

Usage (from the repo root, any user, driver installed):
  python tools/diag/ksprobe.py pins    [--cable A]   pin layout, names, categories, instances, physical connections
  python tools/diag/ksprobe.py formats [--cable A]   PROPOSEDATAFORMAT, DATAINTERSECTION, data ranges, per-mode defaults
  python tools/diag/ksprobe.py modes   [--cable A]   signal-processing modes of each streaming pin, flagging modes this
                                                     Windows' audio service does not know (breaks the endpoint, F5)
  python tools/diag/ksprobe.py topo    [--cable A]   topology nodes, connections, jack descriptions, volume/mute
  python tools/diag/ksprobe.py stream  [--cable A]   create pin -> WaveRT buffer -> notification -> RUN, like audiodg does
  python tools/diag/ksprobe.py all     [--cable A]

Each command runs on the cable's playback side (wave/topology "speaker" filters) and capture side
("micin" filters) so the two can be compared. Win32 errors: 1168 = not found / unsupported property,
1169 = no match (format rejected), 50 = not supported, 87 = invalid parameter, 122 = buffer too small.
See docs/DEBUGGING.md.
"""
import argparse
import ctypes
import struct
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import kslib as ks  # noqa: E402


def filters_for(cable):
    wave_r, wave_c = ks.WAVE_FILTERS[cable]
    return [(ks.topology_of(wave_r), 'playback topology'), (wave_r, 'playback wave'),
            (wave_c, 'capture wave'), (ks.topology_of(wave_c), 'capture topology')]


def stream_pin(flt):
    """Index of the system render/capture streaming pin (communication SINK, not loopback)."""
    for pin in range(flt.pin_count()):
        comm, _ = flt.pin_prop(ks.PIN_COMMUNICATION, pin, 4)
        cat, _ = flt.pin_prop(ks.PIN_CATEGORY, pin, 16)
        if comm and struct.unpack('<I', comm)[0] == 1 and cat and ks.name_of(cat) == 'KSCATEGORY_AUDIO':
            return pin
    return None


def cmd_pins(prefix, cable):
    for name, label in filters_for(cable):
        with ks.Filter(name, prefix) as f:
            print(f'== {name} ({label})')
            r, _ = f.ioctl(ks.KSPROPSETID_Topology + struct.pack('<II', 0, ks.GET))
            if r:
                print('   filter categories:', [ks.name_of(g) for g in ks.multiple_item_guids(r)])
            for pin in range(f.pin_count()):
                df, _ = f.pin_prop(ks.PIN_DATAFLOW, pin, 4)
                comm, _ = f.pin_prop(ks.PIN_COMMUNICATION, pin, 4)
                cat, _ = f.pin_prop(ks.PIN_CATEGORY, pin, 16)
                nm, e_nm = f.pin_prop(ks.PIN_NAME, pin, 512)
                ci, _ = f.pin_prop(ks.PIN_CINSTANCES, pin, 8)
                pc, _ = f.pin_prop(ks.PIN_PHYSICALCONNECTION, pin, 512)
                flow = {1: 'IN', 2: 'OUT'}.get(struct.unpack('<I', df)[0] if df else 0, '?')
                commn = {0: 'NONE', 1: 'SINK', 2: 'SOURCE', 3: 'BOTH', 4: 'BRIDGE'}.get(struct.unpack('<I', comm)[0] if comm else -1, '?')
                inst = f'instances {struct.unpack("<II", ci)[1]}/{struct.unpack("<II", ci)[0]}' if ci else ''
                phys = f' -> {pc[8:].decode("utf-16-le").rstrip(chr(0)).split(chr(92))[-1]} pin {struct.unpack_from("<I", pc, 4)[0]}' if pc else ''
                pname = repr(nm.decode('utf-16-le').rstrip(chr(0))) if nm else f'(err {e_nm})'
                print(f'   pin {pin}: {flow:<3} {commn:<6} {ks.name_of(cat) if cat else "?":<26} name={pname} {inst}{phys}')


def cmd_formats(prefix, cable):
    wave_r, wave_c = ks.WAVE_FILTERS[cable]
    for name in (wave_r, wave_c):
        with ks.Filter(name, prefix) as f:
            pin = stream_pin(f)
            print(f'== {name} streaming pin {pin}')
            r, e = f.pin_prop(ks.PIN_DATARANGES, pin, 4096)
            if r:
                count, off = struct.unpack_from('<I', r, 4)[0], 8
                for _ in range(count):
                    size, flags = struct.unpack_from('<II', r, off)
                    if size >= 84:
                        maxch, minb, maxb, minsr, maxsr = struct.unpack_from('<IIIII', r, off + 64)
                        print(f'   data range: maxch={maxch} bits={minb}-{maxb} sr={minsr}-{maxsr} sub={ks.name_of(r[off+32:off+48])}'
                              + (' (+attributes)' if flags & 2 else ''))
                    off += (size + 7) & ~7
            for ch in (1, 2):
                for rate in (48000, 44100):
                    # SET: the proposed format travels in the property *value* buffer
                    r, e = f.ioctl(ks.KSPROPSETID_Pin + struct.pack('<IIII', ks.PIN_PROPOSEDATAFORMAT, ks.SET, pin, 0),
                                   outbuf=ctypes.create_string_buffer(ks.ksdataformat(ch, rate)))
                    print(f'   PROPOSEDATAFORMAT {ch}ch {rate}: {"ACCEPTED" if e == 0 else f"rejected (err {e})"}')
            for maxch in (1, 2, 8):
                rng = struct.pack('<IIII16s16s16s', 88, 0, 0, 0, ks.KSDATAFORMAT_TYPE_AUDIO, ks.KSDATAFORMAT_SUBTYPE_PCM,
                                  ks.KSDATAFORMAT_SPECIFIER_WAVEFORMATEX) + struct.pack('<IIIII', maxch, 8, 32, 8000, 192000) + b'\0' * 4
                r, e = f.pin_prop(ks.PIN_DATAINTERSECTION, pin, 256, extra=struct.pack('<II', 8 + len(rng), 1) + rng)
                print(f'   DATAINTERSECTION client maxch={maxch}: ' + (ks.describe_format(r) if r else f'err {e}'))
            for mode in ('RAW', 'DEFAULT', 'COMMUNICATIONS', 'SPEECH'):
                attr = struct.pack('<II16s16s', 40, 0, ks.KSATTRIBUTEID_AUDIOSIGNALPROCESSING_MODE, ks.guid(ks.MODES[mode]))
                r, e = f.pin_prop(ks.PIN_PROPOSEDATAFORMAT2, pin, 512, extra=struct.pack('<II', 8 + len(attr), 1) + attr)
                print(f'   default format for mode {mode:<15}: ' + (ks.describe_format(r) if r else f'err {e}'))


def cmd_modes(prefix, cable):
    """A mode GUID that audiosrv.dll does not contain cannot be resolved by the audio service: on
    Windows 10 an advertised AUDIO_SIGNALPROCESSINGMODE_FAR_FIELD_SPEECH made GetMixFormat fail with
    ERROR_NOT_FOUND and every open of the endpoint fail with AUDCLNT_E_UNSUPPORTED_FORMAT."""
    audiosrv = open(os.path.join(os.environ.get('SystemRoot', r'C:\Windows'), 'System32', 'audiosrv.dll'), 'rb').read()
    names = {ks.guid(v): k for k, v in ks.MODES.items()}
    bad = 0
    for name in ks.WAVE_FILTERS[cable]:
        with ks.Filter(name, prefix) as f:
            pin = stream_pin(f)
            r, e = f.ioctl(ks.KSPROPSETID_AudioSignalProcessing + struct.pack('<IIII', 0, ks.GET, pin, 0), 1024)
            print(f'== {name} streaming pin {pin}: ' + ('' if r else f'err {e}'))
            for g in (ks.multiple_item_guids(r) if r else []):
                known = bytes(g) in audiosrv
                bad += not known
                print(f'   {names.get(bytes(g), ks.name_of(g)):<18} {"known to this Windows" if known else "UNKNOWN to this Windows audiosrv -> remove it"}')
    return 1 if bad else 0


def cmd_topo(prefix, cable):
    for name, label in filters_for(cable):
        if not name.startswith('topology'):
            continue
        with ks.Filter(name, prefix) as f:
            print(f'== {name} ({label})')
            r, _ = f.ioctl(ks.KSPROPSETID_Topology + struct.pack('<II', 1, ks.GET))
            nodes = [ks.name_of(g) for g in ks.multiple_item_guids(r)] if r else []
            print('   nodes:', nodes)
            r, _ = f.ioctl(ks.KSPROPSETID_Topology + struct.pack('<II', 2, ks.GET))
            if r:
                cnt = struct.unpack_from('<I', r, 4)[0]
                fmt = lambda n: 'FILTER' if n == 0xFFFFFFFF else f'node{n}'
                print('   connections:', [f'{fmt(a)}.{b}->{fmt(c)}.{d}' for a, b, c, d in
                                          (struct.unpack_from('<IIII', r, 8 + 16 * i) for i in range(cnt))])
            for pin in range(f.pin_count()):
                r, _ = f.ioctl(ks.KSPROPSETID_Jack + struct.pack('<IIII', 1, ks.GET, pin, 0))
                if r:
                    mask, color, ctype, geo, gen, port, conn = struct.unpack_from('<IIIIIII', r, 8)
                    print(f'   pin {pin} jack: chmask=0x{mask:X} conntype={ctype} geo={geo} portconn={port} connected={conn}')
            for node, ntype in enumerate(nodes):
                pid = {'KSNODETYPE_VOLUME': ks.AUDIO_VOLUMELEVEL, 'KSNODETYPE_MUTE': ks.AUDIO_MUTE}.get(ntype)
                if pid is None:
                    continue
                for ch in (0, 1):
                    r, e = f.ioctl(ks.KSPROPSETID_Audio + struct.pack('<IIIIII', pid, ks.GET | ks.TOPOLOGY_FLAG, node, 0, ch, 0))
                    print(f'   node {node} {ntype} ch{ch}: ' + (f'{struct.unpack_from("<i", r)[0]}' if r else f'err {e}'))


def cmd_stream(prefix, cable):
    wave_r, wave_c = ks.WAVE_FILTERS[cable]
    for name in (wave_r, wave_c):
        with ks.Filter(name, prefix) as f:
            pin = stream_pin(f)
            print(f'== {name} streaming pin {pin}')
            for ch in (2, 1):
                hp, err = ks.create_pin(f, pin, ks.ksdataformat(ch, mode='DEFAULT'))
                print(f'   KsCreatePin {ch}ch 48k 16-bit, DEFAULT mode -> 0x{err:X}')
                if not hp:
                    continue
                r, e = ks.pin_ioctl(hp, ks.KSPROPSETID_RtAudio, 8, ks.GET, outsize=4)
                print(f'   RTAUDIO_QUERY_NOTIFICATION_SUPPORT -> err {e}' + (f' value={struct.unpack("<I", r)[0]}' if r else ''))
                r, e = ks.pin_ioctl(hp, ks.KSPROPSETID_RtAudio, 5, ks.GET, struct.pack('<QII', 0, 4800 * ch * 2, 2), outsize=16)
                print(f'   RTAUDIO_BUFFER_WITH_NOTIFICATION   -> err {e}' + (f' size={struct.unpack_from("<I", r, 8)[0]}' if r else ''))
                ev = ks.k32.CreateEventW(None, False, False, None)
                r, e = ks.pin_ioctl(hp, ks.KSPROPSETID_RtAudio, 6, ks.GET, struct.pack('<Q', ev))
                print(f'   RTAUDIO_REGISTER_NOTIFICATION_EVENT -> err {e}')
                for state, sname in ((1, 'ACQUIRE'), (2, 'PAUSE'), (3, 'RUN')):
                    r, e = ks.pin_ioctl(hp, ks.KSPROPSETID_Connection, 0, ks.SET, inbuf_value=struct.pack('<I', state))
                    print(f'   CONNECTION_STATE {sname:<7} -> err {e}')
                w = ks.k32.WaitForSingleObject(ev, 500)
                print(f'   notification within 500 ms -> {"signalled" if w == 0 else "timeout"}')
                for state in (2, 1, 0):
                    ks.pin_ioctl(hp, ks.KSPROPSETID_Connection, 0, ks.SET, inbuf_value=struct.pack('<I', state))
                ks.k32.CloseHandle(hp)
                ks.k32.CloseHandle(ev)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('cmd', choices=['pins', 'formats', 'modes', 'topo', 'stream', 'all'])
    ap.add_argument('--cable', default='A', choices=list('ABCD'))
    args = ap.parse_args()
    prefix = ks.driver_filter_prefix()
    print(f'driver filters: {prefix}*')
    cmds = {'pins': cmd_pins, 'formats': cmd_formats, 'modes': cmd_modes, 'topo': cmd_topo, 'stream': cmd_stream}
    for name in (cmds if args.cmd == 'all' else [args.cmd]):
        cmds[name](prefix, args.cable)


if __name__ == '__main__':
    main()
