"""Check that a driver binary only imports kernel functions this Windows installation exports.

Usage: python tools/diag/check_driver_imports.py <path\\to\\TabletAudioSample.sys>   (needs `pip install pefile`)

Catches the class of bug where a driver built with a new WDK silently links against exports that
only exist on newer Windows (e.g. ExAllocateFromNPagedLookasideList, Windows 11 only), which makes
the driver fail to load (Code 39) on older systems even though it installs. CI runs a dumpbin-based
version of the same check for the known offenders; this script checks every import against the
kernel of the machine it runs on.
"""
import os
import sys

import pefile

SYS32 = os.path.join(os.environ.get('SystemRoot', r'C:\Windows'), 'System32')
SEARCH = [SYS32, os.path.join(SYS32, 'drivers')]


def exports(dll):
    for d in SEARCH:
        p = os.path.join(d, dll)
        if os.path.exists(p):
            pe = pefile.PE(p, fast_load=True)
            pe.parse_data_directories(directories=[pefile.DIRECTORY_ENTRY['IMAGE_DIRECTORY_ENTRY_EXPORT']])
            return {s.name.decode() for s in pe.DIRECTORY_ENTRY_EXPORT.symbols if s.name}
    return None


def main():
    if len(sys.argv) != 2:
        print(__doc__)
        return 2
    pe = pefile.PE(sys.argv[1])
    bad = 0
    for entry in pe.DIRECTORY_ENTRY_IMPORT:
        dll = entry.dll.decode()
        ex = exports(dll)
        if ex is None:
            print(f'{dll}: not found on this system')
            bad += 1
            continue
        missing = [i.name.decode() for i in entry.imports if i.name and i.name.decode() not in ex]
        print(f'{dll}: {len(entry.imports)} imports, missing on this system: {missing or "none"}')
        bad += len(missing)
    return 1 if bad else 0


if __name__ == '__main__':
    sys.exit(main())
