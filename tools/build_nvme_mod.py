#!/usr/bin/env python3
"""Fail-closed builder for the verified 2K110919 board-image profile."""

import argparse
import pathlib
import sys

from firmware import (HASHES, NVME_OFFSET, NVME_SIZE, ROM_SIZE, ValidationError,
                      read_exact, require_hash, scan_fvs, sha256,
                      validate_nvme_ffs, write_new)


def build(base: bytes, nvme: bytes) -> bytes:
    require_hash(base, HASHES["board-2K110919"], "base ROM")
    validate_nvme_ffs(nvme)
    target = base[NVME_OFFSET:NVME_OFFSET + NVME_SIZE]
    if target != b"\xFF" * NVME_SIZE:
        raise ValidationError("ожидаемый диапазон вставки не является полностью свободным")
    result = base[:NVME_OFFSET] + nvme + base[NVME_OFFSET + NVME_SIZE:]
    if result[:NVME_OFFSET] != base[:NVME_OFFSET] or result[NVME_OFFSET + NVME_SIZE:] != base[NVME_OFFSET + NVME_SIZE:]:
        raise ValidationError("изменены байты вне разрешённого диапазона")
    validate_nvme_ffs(result[NVME_OFFSET:NVME_OFFSET + NVME_SIZE])
    require_hash(result, HASHES["nvme-working"], "result ROM")
    if not scan_fvs(result):
        raise ValidationError("не найдены валидные FV")
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base", required=True, type=pathlib.Path,
                        help="локальный verified dump 2K110919; не официальный 2K111114")
    parser.add_argument("--nvme", required=True, type=pathlib.Path)
    parser.add_argument("--output", required=True, type=pathlib.Path)
    args = parser.parse_args()
    try:
        result = build(read_exact(args.base, ROM_SIZE), read_exact(args.nvme, NVME_SIZE))
        write_new(args.output, result)
    except (OSError, ValidationError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2
    print(f"created: {args.output}")
    print(f"SHA-256: {sha256(result)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

