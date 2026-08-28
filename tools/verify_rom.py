#!/usr/bin/env python3
"""Read-only identification of known 4 MiB images and valid FV headers."""

import argparse
import pathlib
import sys

from firmware import HASHES, ROM_SIZE, ValidationError, read_exact, scan_fvs, sha256


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("rom", type=pathlib.Path)
    args = parser.parse_args()
    try:
        data = read_exact(args.rom, ROM_SIZE)
    except (OSError, ValidationError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2
    digest = sha256(data)
    names = [name for name, known in HASHES.items() if known == digest]
    print(f"size: {len(data)} (0x{len(data):X})")
    print(f"SHA-256: {digest}")
    print(f"known image: {', '.join(names) if names else 'no'}")
    volumes = scan_fvs(data)
    print(f"valid FV headers: {len(volumes)}")
    for offset, length, header in volumes:
        print(f"  0x{offset:06X} length=0x{length:X} header=0x{header:X}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

