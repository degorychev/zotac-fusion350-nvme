#!/usr/bin/env python3
"""Build the verified clean-NVAR experiment without mutating inputs."""

import argparse
import pathlib
import sys

from firmware import (HASHES, NVAR_END, NVME_OFFSET, NVME_SIZE, ROM_SIZE,
                      ValidationError, read_exact, require_hash, sha256,
                      validate_fv, validate_nvme_ffs, write_new)


def build(working: bytes, official: bytes) -> bytes:
    require_hash(working, HASHES["nvme-working"], "working NVMe ROM")
    require_hash(official, HASHES["official-2K111114"], "official ROM")
    validate_fv(official, 0)
    if official[0x10000:NVAR_END] != b"\xFF" * 0x10000:
        raise ValidationError("второй официальный NVAR bank не является erased FF")
    result = official[:NVAR_END] + working[NVAR_END:]
    if result[NVAR_END:] != working[NVAR_END:]:
        raise ValidationError("firmware body изменён")
    validate_nvme_ffs(result[NVME_OFFSET:NVME_OFFSET + NVME_SIZE])
    require_hash(result, HASHES["nvme-clean-nvar"], "clean-NVAR result")
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--working", required=True, type=pathlib.Path)
    parser.add_argument("--official", required=True, type=pathlib.Path)
    parser.add_argument("--output", required=True, type=pathlib.Path)
    args = parser.parse_args()
    try:
        result = build(read_exact(args.working, ROM_SIZE), read_exact(args.official, ROM_SIZE))
        write_new(args.output, result)
    except (OSError, ValidationError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2
    print(f"created: {args.output}")
    print(f"SHA-256: {sha256(result)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
