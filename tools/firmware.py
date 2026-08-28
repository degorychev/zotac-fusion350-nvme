#!/usr/bin/env python3
"""Small, dependency-free validators for the known firmware profile."""

from __future__ import annotations

import hashlib
import pathlib
import struct
import uuid

ROM_SIZE = 0x400000
NVAR_END = 0x020000
FV_SIGNATURE = b"_FVH"

HASHES = {
    "board-2K110919": "833EFD7CB5A1D77C1F8B6E5D5B2701BDD75F08D806A20E762BB40A2FE61F5BE5",
    "official-2K111114": "C14AC80DF372EBFC97B91E553DFE8FD67DFE66EA76378B289DACF1FA7522E48F",
    "nvme-working": "40E425C1D0597C1D5BE42DFB82E2790E1BE9FC833C2FF7EC02167DA35783CB72",
    "nvme-clean-nvar": "4678C13C79EFB5715B1D0A47787FCDCE52D4FA7D6B4849AA19DF5CFE7BDB4F28",
}

NVME_GUID = "5BE3BDF4-53CF-46A3-A6A9-73C34A6E5EE3"
NVME_SIZE = 0x5160
NVME_SHA256 = "0D77ACA7597795AB8C70A70770740DF4D6BFCF95464983E4AEF63ACDD2F64072"
NVME_OFFSET = 0x132F48


class ValidationError(ValueError):
    pass


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest().upper()


def read_exact(path: pathlib.Path, size: int | None = None) -> bytes:
    data = path.read_bytes()
    if size is not None and len(data) != size:
        raise ValidationError(f"{path}: размер 0x{len(data):X}, ожидался 0x{size:X}")
    return data


def require_hash(data: bytes, expected: str, label: str) -> None:
    actual = sha256(data)
    if actual != expected:
        raise ValidationError(f"{label}: SHA-256 {actual}, ожидался {expected}")


def checksum16(data: bytes) -> int:
    if len(data) % 2:
        raise ValidationError("16-bit checksum requires an even byte count")
    return sum(struct.unpack(f"<{len(data) // 2}H", data)) & 0xFFFF


def validate_fv(data: bytes, offset: int) -> tuple[int, int]:
    if data[offset + 0x28:offset + 0x2C] != FV_SIGNATURE:
        raise ValidationError(f"нет сигнатуры FV по адресу 0x{offset:X}")
    length = struct.unpack_from("<Q", data, offset + 0x20)[0]
    header_length = struct.unpack_from("<H", data, offset + 0x30)[0]
    if not header_length or offset + length > len(data):
        raise ValidationError(f"некорректный FV по адресу 0x{offset:X}")
    if checksum16(data[offset:offset + header_length]) != 0:
        raise ValidationError(f"ошибка checksum заголовка FV по адресу 0x{offset:X}")
    return length, header_length


def scan_fvs(data: bytes) -> list[tuple[int, int, int]]:
    found = []
    start = 0
    while True:
        sig = data.find(FV_SIGNATURE, start)
        if sig < 0:
            return found
        offset = sig - 0x28
        try:
            length, header = validate_fv(data, offset)
        except (ValidationError, struct.error):
            start = sig + 1
            continue
        found.append((offset, length, header))
        start = sig + 4


def validate_nvme_ffs(data: bytes) -> None:
    require_hash(data, NVME_SHA256, "NvmExpressDxe_4.ffs")
    if len(data) != NVME_SIZE:
        raise ValidationError("неверный размер NVMe FFS")
    guid = str(uuid.UUID(bytes_le=data[:16])).upper()
    if guid != NVME_GUID:
        raise ValidationError(f"неверный GUID NVMe FFS: {guid}")
    declared = int.from_bytes(data[20:23], "little")
    if declared != len(data) or data[18] != 0x07:
        raise ValidationError("некорректный тип или размер FFS")
    header = bytearray(data[:24])
    header[17] = header[23] = 0
    if sum(header) & 0xFF or (sum(data[24:]) + data[17]) & 0xFF:
        raise ValidationError("неверная checksum FFS")
    if data[0x5C:0x60] != b"PE\0\0":
        raise ValidationError("PE signature NVMe driver not found")
    if struct.unpack_from("<H", data, 0x60)[0] != 0x8664:
        raise ValidationError("NVMe driver is not X64")
    if struct.unpack_from("<H", data, 0x74)[0] != 0x20B:
        raise ValidationError("NVMe driver is not PE32+")


def write_new(path: pathlib.Path, data: bytes) -> None:
    if path.exists():
        raise ValidationError(f"output уже существует: {path}")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(data)
