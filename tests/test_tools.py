import pathlib
import sys
import tempfile
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))

import audit_repo
import firmware


class FirmwareTests(unittest.TestCase):
    def test_known_hashes_are_sha256(self):
        for digest in firmware.HASHES.values():
            self.assertEqual(len(digest), 64)
            int(digest, 16)

    def test_write_new_never_overwrites(self):
        with tempfile.TemporaryDirectory() as directory:
            path = pathlib.Path(directory) / "out"
            firmware.write_new(path, b"first")
            with self.assertRaises(firmware.ValidationError):
                firmware.write_new(path, b"second")
            self.assertEqual(path.read_bytes(), b"first")

    def test_audit_detects_forbidden_extension(self):
        with tempfile.TemporaryDirectory() as directory:
            root = pathlib.Path(directory)
            (root / "image.rom").write_bytes(b"test")
            self.assertTrue(audit_repo.audit(root))

    def test_repository_audit(self):
        self.assertEqual(audit_repo.audit(ROOT), [])


if __name__ == "__main__":
    unittest.main()
