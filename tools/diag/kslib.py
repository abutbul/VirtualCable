"""Minimal Kernel Streaming (KS) helpers for probing the VirtualCable driver from user mode.

Talks to the driver's KS filters directly with IOCTL_KS_PROPERTY / KsCreatePin2, bypassing the
Windows audio service (audiosrv/audiodg). If something works here but fails through WASAPI, the
problem is in how Windows' audio service interprets the endpoint, not in the driver's stream path.

No admin rights are needed. Windows only (ctypes + winreg).
"""
import ctypes
import ctypes.wintypes as wt
import struct
import uuid
import winreg

k32 = ctypes.WinDLL('kernel32', use_last_error=True)
k32.CreateFileW.restype = wt.HANDLE
k32.CreateFileW.argtypes = [wt.LPCWSTR, wt.DWORD, wt.DWORD, ctypes.c_void_p, wt.DWORD, wt.DWORD, wt.HANDLE]
k32.DeviceIoControl.argtypes = [wt.HANDLE, wt.DWORD, ctypes.c_void_p, wt.DWORD, ctypes.c_void_p, wt.DWORD,
                                ctypes.POINTER(wt.DWORD), ctypes.c_void_p]
k32.CreateEventW.restype = wt.HANDLE
INVALID_HANDLE = wt.HANDLE(-1).value
IOCTL_KS_PROPERTY = 0x2F0003

GET, SET, BASICSUPPORT, TOPOLOGY_FLAG = 0x1, 0x2, 0x200, 0x10000000


def guid(s):
    return uuid.UUID(s).bytes_le


# Property sets
KSPROPSETID_Pin = guid('8C134960-51AD-11CF-878A-94F801C10000')
KSPROPSETID_Topology = guid('720D4AC0-7533-11D0-A5D6-28DB04C10000')
KSPROPSETID_Audio = guid('45FFAAA0-6E1B-11D0-BCF2-444553540000')
KSPROPSETID_Jack = guid('4509F757-2D46-4637-8E62-CE7DB944F57B')
KSPROPSETID_RtAudio = guid('A855A48C-2F78-4729-9051-1968746B9EEF')
KSPROPSETID_Connection = guid('1D58C920-AC9B-11CF-A5D6-28DB04C10000')

# KSPROPERTY_PIN_* ids
PIN_CINSTANCES, PIN_CTYPES, PIN_DATAFLOW, PIN_DATARANGES, PIN_DATAINTERSECTION = 0, 1, 2, 3, 4
PIN_COMMUNICATION, PIN_PHYSICALCONNECTION, PIN_CATEGORY, PIN_NAME = 7, 10, 11, 12
PIN_PROPOSEDATAFORMAT, PIN_PROPOSEDATAFORMAT2 = 14, 15
# KSPROPERTY_AUDIO_* ids
AUDIO_CHANNEL_CONFIG, AUDIO_VOLUMELEVEL, AUDIO_MUTE = 3, 4, 13

KSDATAFORMAT_TYPE_AUDIO = guid('73647561-0000-0010-8000-00AA00389B71')
KSDATAFORMAT_SUBTYPE_PCM = guid('00000001-0000-0010-8000-00AA00389B71')
KSDATAFORMAT_SUBTYPE_IEEE_FLOAT = guid('00000003-0000-0010-8000-00AA00389B71')
KSDATAFORMAT_SPECIFIER_WAVEFORMATEX = guid('05589F81-C356-11CE-BF01-00AA0055595A')
KSINTERFACESETID_Standard = guid('1A8766A0-62CE-11CF-A5D6-28DB04C10000')
KSMEDIUMSETID_Standard = guid('4747B320-62CE-11CF-A5D6-28DB04C10000')
KSATTRIBUTEID_AUDIOSIGNALPROCESSING_MODE = guid('E1F89EB5-5F46-419B-967B-FF6770B98401')

MODES = {
    'RAW': '9E90EA20-B493-4FD1-A1A8-7E1361A956CF',
    'DEFAULT': 'C18E2F7E-933D-4965-B7D1-1EEF228D2AF3',
    'COMMUNICATIONS': '98951333-B9CD-48B1-A0A3-FF40682D73F7',
    'SPEECH': 'FC1CFC9B-B9D6-4CFA-B5E0-4BB2166878B2',
    'MEDIA': '4780004E-7133-41D8-8C74-660DADD2C0EE',
}

KNOWN_GUIDS = {
    'dff21ce1-f70f-11d0-b917-00a0c9223196': 'KSNODETYPE_SPEAKER',
    'dff21fe3-f70f-11d0-b917-00a0c9223196': 'KSNODETYPE_LINE_CONNECTOR',
    'dff21be1-f70f-11d0-b917-00a0c9223196': 'KSNODETYPE_MICROPHONE',
    '6994ad04-93ef-11d0-a3cc-00a0c9223196': 'KSCATEGORY_AUDIO',
    '65e8773d-8f56-11d0-a3b9-00a0c9223196': 'KSCATEGORY_CAPTURE',
    '65e8773e-8f56-11d0-a3b9-00a0c9223196': 'KSCATEGORY_RENDER',
    'dda54a40-1e4c-11d1-a050-405705c10000': 'KSCATEGORY_TOPOLOGY',
    'eb115ffc-10c8-4964-831d-6dcb02e6f23f': 'KSCATEGORY_REALTIME',
    '3a5acc00-c557-11d0-8a2b-00a0c9255ac1': 'KSNODETYPE_VOLUME',
    '02b223c0-c557-11d0-8a2b-00a0c9255ac1': 'KSNODETYPE_MUTE',
    'a085651e-5f0d-4b36-a869-d195d6ab4b9e': 'KSNODETYPE_PEAKMETER',
    '4d837fe0-c555-11d0-8a2b-00a0c9255ac1': 'KSNODETYPE_ADC',
    '507ae360-c554-11d0-8a2b-00a0c9255ac1': 'KSNODETYPE_DAC',
    '35caf6e4-f3b3-4168-bb4b-55e77a461c7e': 'KSNODETYPE_AUDIO_ENGINE',
    '8f42c0b2-91ce-4bcf-9ccd-0e599037ab35': 'KSCATEGORY_AUDIO_LOOPBACK (loopback pin)',
}


def name_of(guid_bytes):
    s = str(uuid.UUID(bytes_le=bytes(guid_bytes)))
    return KNOWN_GUIDS.get(s, s)


# ----------------------------------------------------------------- filter discovery
WAVE_FILTERS = {'A': ('wavespeaker', 'wavemicin'), 'B': ('wavespeakerb', 'wavemicinb'),
                'C': ('wavespeakerc', 'wavemicinc'), 'D': ('wavespeakerd', 'wavemicind')}


def topology_of(wave_filter):
    return wave_filter.replace('wave', 'topology', 1)


def driver_filter_prefix():
    """Find the KS device-interface prefix (\\\\?\\root#media#NNNN#{KSCATEGORY_AUDIO}\\) of the
    installed VirtualCable device from the endpoints' registered wave filter paths."""
    base = r'SOFTWARE\Microsoft\Windows\CurrentVersion\MMDevices\Audio\Render'
    with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, base) as root:
        i = 0
        while True:
            try:
                ep = winreg.EnumKey(root, i)
            except OSError:
                break
            i += 1
            try:
                with winreg.OpenKey(root, ep + r'\Properties') as p:
                    ref = str(winreg.QueryValueEx(p, '{233164c8-1b2c-4c7d-bc68-b671687a2567},1')[0])
                with winreg.OpenKey(root, ep) as k:
                    state = winreg.QueryValueEx(k, 'DeviceState')[0]
            except OSError:
                continue
            if state == 1 and ref.lower().endswith(chr(92) + 'wavespeaker') and 'root#media#' in ref.lower():
                path = ref.split('.', 1)[1]           # strip the "{2}." prefix
                return path[: -len('wavespeaker')]
    raise RuntimeError('VirtualCable endpoints not found (driver not installed or not started?)')


class Filter:
    def __init__(self, name, prefix=None):
        self.name = name
        self.h = k32.CreateFileW((prefix or driver_filter_prefix()) + name, 0xC0000000, 3, None, 3, 0, None)
        if self.h in (None, INVALID_HANDLE):
            raise OSError(ctypes.get_last_error(), f'cannot open KS filter {name}')

    def close(self):
        if self.h:
            k32.CloseHandle(self.h)
            self.h = None

    def __enter__(self):
        return self

    def __exit__(self, *a):
        self.close()

    def ioctl(self, inbuf, outsize=1024, outbuf=None):
        """Returns (bytes or None, win32 error)."""
        ib = ctypes.create_string_buffer(inbuf) if isinstance(inbuf, (bytes, bytearray)) else inbuf
        ob = outbuf if outbuf is not None else (ctypes.create_string_buffer(outsize) if outsize else None)
        n = wt.DWORD()
        ok = k32.DeviceIoControl(self.h, IOCTL_KS_PROPERTY, ib, ctypes.sizeof(ib) if not isinstance(inbuf, (bytes, bytearray)) else len(inbuf),
                                 ob, ctypes.sizeof(ob) if ob is not None else 0, ctypes.byref(n), None)
        if not ok:
            return None, ctypes.get_last_error()
        return (ob.raw[:n.value] if ob is not None else b''), 0

    def pin_prop(self, pid, pin, outsize=1024, verb=GET, extra=b''):
        return self.ioctl(KSPROPSETID_Pin + struct.pack('<IIII', pid, verb, pin, 0) + extra, outsize)

    def pin_count(self):
        r, _ = self.pin_prop(PIN_CTYPES, 0, 4)
        return struct.unpack('<I', r)[0] if r else 0


def multiple_item_guids(r):
    cnt = struct.unpack_from('<I', r, 4)[0]
    return [r[8 + 16 * i: 24 + 16 * i] for i in range(cnt)]


# ----------------------------------------------------------------- formats
def waveformatext(ch, rate=48000, bits=16, mask=None, float_=False):
    mask = mask if mask is not None else {1: 0x4, 2: 0x3}.get(ch, 0)
    align = ch * bits // 8
    sub = KSDATAFORMAT_SUBTYPE_IEEE_FLOAT if float_ else KSDATAFORMAT_SUBTYPE_PCM
    return struct.pack('<HHIIHHHHI16s', 0xFFFE, ch, rate, rate * align, align, bits, 22, bits, mask, sub)


def ksdataformat(ch, rate=48000, bits=16, mask=None, mode=None):
    """KSDATAFORMAT + WAVEFORMATEXTENSIBLE, optionally followed by a processing-mode attribute list
    (what the audio engine sends when it opens a stream on a pin that advertises modes)."""
    wfx = waveformatext(ch, rate, bits, mask)
    fmt = struct.pack('<IIII16s16s16s', 64 + len(wfx), 2 if mode else 0, 0, 0,
                      KSDATAFORMAT_TYPE_AUDIO, KSDATAFORMAT_SUBTYPE_PCM, KSDATAFORMAT_SPECIFIER_WAVEFORMATEX) + wfx
    if mode:
        attr = struct.pack('<II16s16s', 40, 0, KSATTRIBUTEID_AUDIOSIGNALPROCESSING_MODE, guid(MODES[mode]))
        fmt += b'\0' * ((8 - len(fmt) % 8) % 8) + struct.pack('<II', 8 + len(attr), 1) + attr
    return fmt


def describe_format(fmt):
    if not fmt or len(fmt) < 64 + 16:
        return f'{len(fmt) if fmt else 0} bytes'
    size, flags = struct.unpack_from('<II', fmt)
    tag, ch, sr, avg, align, bits, cb = struct.unpack_from('<HHIIHHH', fmt, 64)
    s = f'tag=0x{tag:X} ch={ch} sr={sr} align={align} bits={bits}'
    if tag == 0xFFFE and len(fmt) >= 64 + 40:
        valid, mask = struct.unpack_from('<HI', fmt, 82)
        s += f' valid={valid} mask=0x{mask:X} sub={name_of(fmt[88:104])}'
    return s + (' +attributes' if flags & 2 else '')


# ----------------------------------------------------------------- pins
ksuser = ctypes.WinDLL('ksuser')
ksuser.KsCreatePin2.argtypes = [wt.HANDLE, ctypes.c_void_p, wt.DWORD, ctypes.POINTER(wt.HANDLE)]
ksuser.KsCreatePin2.restype = wt.DWORD
_com_ready = False


def create_pin(flt, pin, fmt):
    """KsCreatePin2 with a looped-streaming (WaveRT) connection. Returns (pin handle or None, HRESULT/err)."""
    global _com_ready
    if not _com_ready:
        ctypes.WinDLL('ole32').CoInitializeEx(None, 0)   # KsCreatePin2 needs COM (else 0x800401F0)
        _com_ready = True
    conn = struct.pack('<16sII16sIIIIQII', KSINTERFACESETID_Standard, 1, 0, KSMEDIUMSETID_Standard, 0, 0,
                       pin, 0, 0, 0x40000000, 1)
    hp = wt.HANDLE()
    err = ksuser.KsCreatePin2(flt.h, ctypes.create_string_buffer(conn + fmt), 0xC0000000, ctypes.byref(hp))
    return (hp.value if err == 0 else None), err


def pin_ioctl(hpin, set_guid, pid, verb, extra=b'', outsize=0, inbuf_value=None):
    n = wt.DWORD()
    ib = ctypes.create_string_buffer(set_guid + struct.pack('<II', pid, verb) + extra)
    ob = ctypes.create_string_buffer(inbuf_value) if inbuf_value is not None else (ctypes.create_string_buffer(outsize) if outsize else None)
    ok = k32.DeviceIoControl(hpin, IOCTL_KS_PROPERTY, ib, ctypes.sizeof(ib), ob, ctypes.sizeof(ob) if ob is not None else 0,
                             ctypes.byref(n), None)
    return (ob.raw[:n.value] if (ok and ob is not None) else (b'' if ok else None)), (0 if ok else ctypes.get_last_error())
