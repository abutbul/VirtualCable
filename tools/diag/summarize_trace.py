"""Summarize an audio-stack ETW trace decoded by tracerpt (see capture-trace.ps1).

Usage: python tools/diag/summarize_trace.py %TEMP%\\vc_audio_trace\\audio.xml [--endpoint GUID] [--all]

Prints, in order:
  * WIL failures (FallbackError / ...) with source file, line and HRESULT - these name the
    function inside audiosrv/audioses that failed, e.g. endpointcharacteristics.cpp
  * 'Errors' events (Func/LineNum/HResult) - the propagation chain up to the client API
  * the per-endpoint activity (format evaluation, device format, spatial settings, ...) for
    every endpoint id mentioned, or only --endpoint
--all also prints every other event of the audio service process.
"""
import argparse
import re
import sys
from collections import Counter

HRESULTS = {
    0x80070490: 'ERROR_NOT_FOUND', 0x88890008: 'AUDCLNT_E_UNSUPPORTED_FORMAT', 0x88890004: 'AUDCLNT_E_DEVICE_INVALIDATED',
    0x8889000A: 'AUDCLNT_E_DEVICE_IN_USE', 0x80070005: 'E_ACCESSDENIED', 0x80004001: 'E_NOTIMPL', 0x80070057: 'E_INVALIDARG',
    0x80004005: 'E_FAIL', 0x88890002: 'AUDCLNT_E_ALREADY_INITIALIZED', 0x88890019: 'AUDCLNT_E_BUFFER_SIZE_NOT_ALIGNED',
}


def hr_text(v):
    try:
        n = int(v, 0) if isinstance(v, str) else int(v)
    except ValueError:
        return v
    n &= 0xFFFFFFFF
    return f'0x{n:08X}' + (f' {HRESULTS[n]}' if n in HRESULTS else '')


def parse(path):
    x = open(path, encoding='utf-8', errors='replace').read()
    for e in re.findall(r'<Event .*?</Event>', x, re.S):
        e = re.sub(r'\s+', ' ', e)
        prov = re.search(r'<Provider Name="([^"]*)"', e)
        pid = re.search(r'ProcessID="(\d+)"', e)
        task = None
        if '<RenderingInfo' in e:
            m = re.search(r'<Task>([^<]*)</Task>', e.split('<RenderingInfo', 1)[1])
            task = m.group(1) if m else None
        data = dict(re.findall(r'<Data Name="([^"]*)">([^<]*)</Data>', e))
        yield {'provider': prov.group(1) if prov else '?', 'pid': pid.group(1) if pid else '?', 'task': task or '',
               'data': {k: v.strip() for k, v in data.items()}}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('xml')
    ap.add_argument('--endpoint', help='only show activity for this endpoint GUID (substring)')
    ap.add_argument('--all', action='store_true')
    args = ap.parse_args()
    events = list(parse(args.xml))
    print(f'{len(events)} events; providers: ' + ', '.join(f'{p} ({n})' for p, n in Counter(e["provider"] for e in events).most_common()))

    print('\n== WIL failures (first occurrence of each file:line)')
    seen = set()
    for e in events:
        d = e['data']
        if 'hresult' in d and 'fileName' in d:
            key = (d['fileName'], d.get('lineNumber'))
            if key in seen:
                continue
            seen.add(key)
            print(f'   {d.get("module", "?"):<14} {d["fileName"].rsplit(chr(92), 1)[-1]}:{d.get("lineNumber")} '
                  f'{hr_text(d["hresult"])}  [{e["task"]}]')

    print('\n== Error propagation (Func / HResult)')
    for e in events:
        d = e['data']
        if 'Func' in d and ('HResult' in d or 'originalHResult' in d):
            orig = f' (from {hr_text(d["originalHResult"])})' if 'originalHResult' in d else ''
            print(f'   pid {e["pid"]:<6} {d["Func"]:<40} line {d.get("LineNum", "?"):<6} {hr_text(d.get("HResult", "0"))}{orig}')

    print('\n== Endpoint activity')
    for e in events:
        d = e['data']
        ep = d.get('endpointId') or d.get('EndpointId') or d.get('Endpoint Id') or ''
        if not ep or (args.endpoint and args.endpoint.lower() not in ep.lower()):
            continue
        rest = ' '.join(f'{k}={v}' for k, v in d.items() if k not in ('endpointId', 'EndpointId', 'Endpoint Id'))
        print(f'   {e["task"] or e["provider"]:<48} {ep[-38:]} {rest[:160]}')

    if args.all:
        print('\n== All non-notification events')
        for e in events:
            if e['task'] == 'AudioCore_EVT_MMDevAPI':
                continue
            rest = ' '.join(f'{k}={v}' for k, v in e['data'].items())
            print(f'   pid {e["pid"]:<6} {e["provider"].split(".")[-1]:<24} {e["task"]:<44} {rest[:200]}')


if __name__ == '__main__':
    sys.exit(main())
