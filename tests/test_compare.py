"""Testes da comparação entre APK original e reconstruído (ZIPs temporários)."""

import sys
import tempfile
import unittest
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from readroid import compare


def make_zip(path: Path, entries: dict[str, bytes]) -> Path:
    with zipfile.ZipFile(path, "w", zipfile.ZIP_DEFLATED) as archive:
        for name, data in entries.items():
            archive.writestr(name, data)
    return path


class CompareTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)

    def tearDown(self):
        self.tmp.cleanup()

    def test_apks_identicos(self):
        entries = {"AndroidManifest.xml": b"<manifest/>", "classes.dex": b"abc"}
        a = make_zip(self.root / "a.apk", entries)
        b = make_zip(self.root / "b.apk", entries)
        result = compare.compare_apks(a, b)
        self.assertEqual(result["size_delta"], 0)
        self.assertEqual(result["added_count"], 0)
        self.assertEqual(result["removed_count"], 0)
        self.assertEqual(result["changed_count"], 0)
        self.assertFalse(result["manifest_changed"])

    def test_detecta_alterado_adicionado_e_removido(self):
        a = make_zip(self.root / "a.apk",
                     {"AndroidManifest.xml": b"<manifest a='1'/>", "res/x.xml": b"um", "velho.txt": b"x"})
        b = make_zip(self.root / "b.apk",
                     {"AndroidManifest.xml": b"<manifest a='2'/>", "res/x.xml": b"um", "novo.txt": b"y"})
        result = compare.compare_apks(a, b)
        self.assertEqual(result["added"], ["novo.txt"])
        self.assertEqual(result["removed"], ["velho.txt"])
        self.assertEqual(result["changed"], ["AndroidManifest.xml"])
        self.assertTrue(result["manifest_changed"])

    def test_tamanho_relativo(self):
        a = make_zip(self.root / "a.apk", {"a.txt": b"x" * 1000})
        b = make_zip(self.root / "b.apk", {"a.txt": b"x" * 2000, "b.txt": b"y" * 1000})
        result = compare.compare_apks(a, b)
        self.assertGreater(result["size_delta"], 0)
        self.assertEqual(result["entries_after"], 2)

    def test_formatacao_mostra_leitura(self):
        a = make_zip(self.root / "a.apk", {"AndroidManifest.xml": b"<a/>"})
        b = make_zip(self.root / "b.apk", {"AndroidManifest.xml": b"<b/>"})
        lines = compare.format_comparison(compare.compare_apks(a, b))
        text = "\n".join(lines)
        self.assertIn("Tamanho:", text)
        self.assertIn("Arquivos:", text)
        self.assertIn("AndroidManifest.xml foi alterado", text)

    def test_arquivo_invalido_levanta_erro_claro(self):
        bad = self.root / "bad.apk"
        bad.write_bytes(b"nao e um zip")
        with self.assertRaises(zipfile.BadZipFile):
            compare.compare_apks(bad, bad)


if __name__ == "__main__":
    unittest.main()
