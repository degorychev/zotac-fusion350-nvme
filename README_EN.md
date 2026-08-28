# NVMe boot and NVRAM recovery on ZOTAC FUSION350-B-E / E350ITX-B-E

This repository documents a verified experiment on one AMD E-350/Hudson-M1
board. An X64 NVMe DXE made an NVMe device connected through mini-PCIe visible
to UEFI, but native boot entries still failed because the 64 KiB AMI NVAR store
had only 1310 bytes remaining. Rebuilding from the official factory-clean NVAR
template restored 55124 bytes of available space; `efibootmgr` created the PBS
entry and a normal reboot loaded PBS from NVMe.

The tested firmware is AMI Aptio IV 4.6.4, board build `2K110919`; the official
`2K111114` update was confirmed as the same firmware family. The SPI device is a
removable 4 MiB Winbond W25Q32. A verified backup and a tested programmer-based
recovery path are mandatory.

No ZOTAC/AMI BIOS image, machine dump, extracted proprietary module, or third-
party `.ffs` binary is distributed here. Users must obtain their own inputs.
The scripts accept only the exact documented hashes, validate the FFS/FV
structure, create a new output, and fail closed on any mismatch.

```bash
python3 tools/verify_rom.py /path/to/local-image
python3 tools/build_nvme_mod.py --base /path/to/board-dump \
  --nvme /path/to/NvmExpressDxe_4.ffs --output /path/to/new-image
python3 tools/build_clean_nvar_mod.py --working /path/to/nvme-image \
  --official /path/to/official-update-image --output /path/to/clean-image
```

The exact community build of `NvmExpressDxe_4.ffs` is intentionally excluded
because its redistribution provenance is not documented clearly enough. The
repository license applies only to this project's own code and documentation.

See the [primary Russian README](README.md), [known hashes](hashes/known-images.txt)
and [disclaimer](DISCLAIMER.md).
