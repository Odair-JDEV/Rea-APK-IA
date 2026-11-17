"""Testes das checagens de espaço em disco e minSdk (sem rede e sem dispositivo)."""

import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from readroid import checks


class DiskTests(unittest.TestCase):
    def test_espaco_suficiente(self):
        with tempfile.TemporaryDirectory() as tmp:
            result = checks.check_disk_space(Path(tmp), required=1)
            self.assertTrue(result["ok"])
            self.assertIn("Espaço livre", result["message"])

    def test_espaco_insuficiente(self):
        with tempfile.TemporaryDirectory() as tmp:
            result = checks.check_disk_space(Path(tmp), required=10 ** 15)
            self.assertFalse(result["ok"])
            self.assertIn("Pouco espaço", result["message"])

    def test_medicao_impossivel_nao_mente(self):
        with patch.object(checks.shutil, "disk_usage", side_effect=OSError("sem acesso")):
            result = checks.check_disk_space(Path("."), required=1)
        self.assertIsNone(result["ok"])
        self.assertIn("Não foi possível", result["message"])

    def test_estimativa_tem_piso(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "a.txt").write_text("x" * 100, encoding="utf-8")
            self.assertGreaterEqual(checks.estimate_build_space(root), checks.MIN_FREE_BYTES)

    def test_estimativa_cresce_com_a_pasta(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "big.bin").write_bytes(b"0" * 4_000_000)
            original = checks.MIN_FREE_BYTES
            checks.MIN_FREE_BYTES = 1000
            try:
                self.assertGreater(checks.estimate_build_space(root), 1000)
            finally:
                checks.MIN_FREE_BYTES = original


class MinSdkTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.decoded = Path(self.tmp.name)

    def tearDown(self):
        self.tmp.cleanup()

    def test_le_do_apktool_yml(self):
        (self.decoded / "apktool.yml").write_text(
            "sdkInfo:\n  minSdkVersion: '21'\n  targetSdkVersion: '34'\n", encoding="utf-8")
        self.assertEqual(checks.manifest_min_sdk(self.decoded), 21)

    def test_le_do_manifesto(self):
        (self.decoded / "AndroidManifest.xml").write_text(
            '<manifest android:minSdkVersion="24"></manifest>', encoding="utf-8")
        self.assertEqual(checks.manifest_min_sdk(self.decoded), 24)

    def test_sem_informacao_devolve_none(self):
        self.assertIsNone(checks.manifest_min_sdk(self.decoded))

    def test_dispositivo_antigo_falha(self):
        (self.decoded / "apktool.yml").write_text("minSdkVersion: 30\n", encoding="utf-8")
        result = checks.check_min_sdk(self.decoded, sdk=26)
        self.assertFalse(result["ok"])
        self.assertIn("mais antigo", result["message"])

    def test_dispositivo_compativel(self):
        (self.decoded / "apktool.yml").write_text("minSdkVersion: 21\n", encoding="utf-8")
        result = checks.check_min_sdk(self.decoded, sdk=34)
        self.assertTrue(result["ok"])

    def test_sem_adb_nao_afirma_nada(self):
        (self.decoded / "apktool.yml").write_text("minSdkVersion: 21\n", encoding="utf-8")
        with patch.object(checks, "device_sdk", return_value=None):
            result = checks.check_min_sdk(self.decoded)
        self.assertIsNone(result["ok"])
        self.assertEqual(result["min_sdk"], 21)

    def test_device_sdk_sem_adb(self):
        with patch.object(checks.shutil, "which", return_value=None):
            self.assertIsNone(checks.device_sdk())


if __name__ == "__main__":
    unittest.main()
