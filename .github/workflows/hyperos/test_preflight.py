#!/usr/bin/env python3
"""Offline tests for the isolated HyperOS 1 stock-image preflight."""
import io
import json
from pathlib import Path
import struct
import tarfile
import tempfile
import unittest
from types import SimpleNamespace
from unittest.mock import patch

import preflight


class HyperOSPreflightTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="yunluo-hyperos-tests-")
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.archive = self.root / preflight.ROM["archive_name"]
        self.work = self.root / "stock"
        self.reports = self.root / "reports"

    def archive_with(self, entries):
        with tarfile.open(self.archive, "w:gz") as arc:
            for name, content in entries:
                info = tarfile.TarInfo(name=name)
                info.size = len(content)
                arc.addfile(info, io.BytesIO(content))

    def extract_with_test_checksum(self):
        with patch.dict(preflight.ROM, {"archive_md5": preflight.digest(self.archive, "md5")}):
            preflight.extract(SimpleNamespace(archive=str(self.archive), work=str(self.work), reports=str(self.reports)))

    def test_firmware_pinned_to_correct_device(self):
        cfg = preflight.ROM
        self.assertEqual(cfg["codename"], "yunluo")
        self.assertEqual(cfg["android"], 14)
        self.assertTrue(cfg["archive_name"].startswith("yunluo_global_images_OS1.0.9.0.ULYMIXM"))
        self.assertEqual(len(cfg["archive_md5"]), 32)
        self.assertFalse(cfg["allow_modifications"])

    def test_sparse_header_validation(self):
        valid = struct.pack("<I4H4I", 0xED26FF3A, 1, 0, 28, 12, 4096, 524288, 123, 0)
        info = preflight.parse_sparse_header(valid)
        self.assertEqual(info["raw_size"], 2147483648)
        self.assertEqual(info["chunks"], 123)
        with self.assertRaises(ValueError):
            preflight.parse_sparse_header(valid[:-1])
        with self.assertRaises(ValueError):
            preflight.parse_sparse_header(b"FAIL" + valid[4:])

    def test_vbmeta_header_offsets(self):
        vb = bytearray(8192)
        vb[:4] = b"AVB0"
        struct.pack_into(">I", vb, 28, 1)
        struct.pack_into(">I", vb, 120, 3)
        result = preflight.parse_vbmeta_header(vb)
        self.assertEqual(result, {"flags": 3, "algorithm": 1})
        with self.assertRaises(ValueError):
            preflight.parse_vbmeta_header(b"NOT-AVB0")

    def test_extract_stock_super_and_vbmeta_only(self):
        folder = "yunluo_global_images_OS1.0.9.0.ULYMIXM_14.0"
        self.archive_with([
            (folder + "/images/super.img", b"stock-super"),
            (folder + "/images/vbmeta.img", b"stock-vbmeta"),
            (folder + "/images/boot.img", b"not-extracted"),
            (folder + "/flash_all.sh", b"stock-script"),
        ])
        self.extract_with_test_checksum()
        self.assertEqual((self.work / "images/super.img").read_bytes(), b"stock-super")
        self.assertEqual((self.work / "images/vbmeta.img").read_bytes(), b"stock-vbmeta")
        self.assertFalse((self.work / "images/boot.img").exists())
        result = json.loads((self.reports / "01-source.json").read_text())
        self.assertEqual(result["modified_images"], 0)
        self.assertFalse(result["firmware_zip_built"])

    def test_reject_wrong_archive_checksum(self):
        folder = "yunluo_global_images_OS1.0.9.0.ULYMIXM_14.0"
        self.archive_with([(folder + "/images/super.img", b"data")])
        with self.assertRaisesRegex(ValueError, "MD5"):
            preflight.extract(SimpleNamespace(archive=str(self.archive), work=str(self.work), reports=str(self.reports)))

    def test_reject_archive_path_traversal(self):
        self.archive_with([("../outside/images/super.img", b"unsafe")])
        with self.assertRaisesRegex(ValueError, "Unsafe"):
            self.extract_with_test_checksum()

    def test_reject_duplicate_stock_image(self):
        folder = "yunluo_global_images_OS1.0.9.0.ULYMIXM_14.0"
        self.archive_with([
            (folder + "/images/super.img", b"abc"),
            (folder + "/images/super.img", b"def"),
            (folder + "/images/vbmeta.img", b"avb"),
        ])
        with self.assertRaisesRegex(ValueError, "Duplicate"):
            self.extract_with_test_checksum()


if __name__ == "__main__":
    unittest.main()
