#!/usr/bin/env python3
"""Conservative pre-publication audit for forbidden blobs and identifiers."""

from __future__ import annotations

import argparse
import pathlib
import re
import sys

FORBIDDEN_SUFFIXES = {".rom", ".bin", ".fd", ".cap", ".ffs", ".zip", ".7z", ".rar", ".bak"}
FORBIDDEN_PARTS = {"dumps", "private", "efivars", ".git"}
IGNORED_PARTS = {"__pycache__", ".pytest_cache", ".venv", "build", "dist"}
KNOWN_GUIDS = {
    "5BE3BDF4-53CF-46A3-A6A9-73C34A6E5EE3",  # firmware module identity
}
PATTERNS = {
    "private key": re.compile(r"-----BEGIN (?:RSA |OPENSSH |EC )?PRIVATE KEY-----"),
    "Windows absolute path": re.compile(r"[A-Za-z]:\\(?:Users|Documents and Settings)\\[^\s/`]+", re.I),
    "Unix home path": re.compile(r"/(?:home|Users)/[^\s/`]+"),
    "MAC address": re.compile(r"(?<![0-9A-Fa-f])(?:[0-9A-Fa-f]{2}[:-]){5}[0-9A-Fa-f]{2}(?![0-9A-Fa-f])"),
    "IP address": re.compile(r"(?<![\d.])(?:\d{1,3}\.){3}\d{1,3}(?![\d.])"),
    "UUID": re.compile(r"\b[0-9A-Fa-f]{8}-[0-9A-Fa-f]{4}-[0-9A-Fa-f]{4}-[0-9A-Fa-f]{4}-[0-9A-Fa-f]{12}\b"),
    "credential assignment": re.compile(r"(?i)\b(?:password|passwd|secret|api[_-]?key|token)\s*[:=]\s*[\"']?[^\s\"']+"),
}


def audit(root: pathlib.Path) -> list[str]:
    findings: list[str] = []
    for path in sorted(root.rglob("*")):
        rel = path.relative_to(root)
        if any(part.casefold() in IGNORED_PARTS for part in rel.parts):
            continue
        if any(part.casefold() in FORBIDDEN_PARTS for part in rel.parts):
            if path.is_file():
                findings.append(f"forbidden directory: {rel}")
            continue
        if not path.is_file():
            continue
        if path.suffix.casefold() in FORBIDDEN_SUFFIXES:
            findings.append(f"forbidden binary/archive: {rel}")
            continue
        raw = path.read_bytes()
        if b"\0" in raw:
            findings.append(f"binary-looking file: {rel}")
            continue
        try:
            text = raw.decode("utf-8")
        except UnicodeDecodeError:
            findings.append(f"non-UTF-8 file: {rel}")
            continue
        if rel.as_posix() == "tools/audit_repo.py":
            continue  # pattern definitions and allow-list live here
        for label, pattern in PATTERNS.items():
            for match in pattern.finditer(text):
                value = match.group(0)
                if label == "UUID" and value.upper() in KNOWN_GUIDS:
                    continue
                line = text.count("\n", 0, match.start()) + 1
                findings.append(f"{label}: {rel}:{line}: {value[:80]}")
    return findings


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("root", nargs="?", type=pathlib.Path,
                        default=pathlib.Path(__file__).resolve().parents[1])
    args = parser.parse_args()
    findings = audit(args.root.resolve())
    if findings:
        print("AUDIT FAILED")
        print("\n".join(f"- {item}" for item in findings))
        return 1
    print("AUDIT PASS: forbidden blobs, archives, secrets and unapproved identifiers not found")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
