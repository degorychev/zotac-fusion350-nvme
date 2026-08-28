#!/usr/bin/env python3
"""Read-only UEFI QueryVariableInfo() diagnostic via Linux efi_test."""
import ctypes
import os

NV, BS, RT = 1, 2, 4


class QueryVariableInfo(ctypes.Structure):
    _pack_ = 1
    _fields_ = [
        ("attributes", ctypes.c_uint32),
        ("maximum_variable_storage_size", ctypes.POINTER(ctypes.c_uint64)),
        ("remaining_variable_storage_size", ctypes.POINTER(ctypes.c_uint64)),
        ("maximum_variable_size", ctypes.POINTER(ctypes.c_uint64)),
        ("status", ctypes.POINTER(ctypes.c_ulong)),
    ]


def ioc(direction, kind, number, size):
    return (direction << 30) | (size << 16) | (ord(kind) << 8) | number


request = ioc(2, "p", 0x08, ctypes.sizeof(QueryVariableInfo))
libc = ctypes.CDLL(None, use_errno=True)
fd = os.open("/dev/efi_test", os.O_RDONLY | os.O_CLOEXEC)
try:
    print("attrs ioctl EFI_STATUS maximum_storage remaining maximum_variable")
    for attributes in range(1, 8):
        maximum, remaining, variable = (ctypes.c_uint64() for _ in range(3))
        status = ctypes.c_ulong(-1)
        query = QueryVariableInfo(attributes, ctypes.pointer(maximum),
                                  ctypes.pointer(remaining), ctypes.pointer(variable),
                                  ctypes.pointer(status))
        ctypes.set_errno(0)
        rc = libc.ioctl(fd, request, ctypes.byref(query))
        names = "|".join(name for bit, name in ((NV, "NV"), (BS, "BS"), (RT, "RT"))
                         if attributes & bit)
        print(f"{names:<8} {rc:5d} 0x{status.value:016x} "
              f"{maximum.value} {remaining.value} {variable.value}")
finally:
    os.close(fd)

