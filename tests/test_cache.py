"""Testes do cache de análise por SHA-256 e da pista de ofuscação."""

import sys
import tempfile
import unittest
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from readroid import cache, obfuscation


class CacheTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.reports = Path(self.tmp.name) / "reports"

    def tearDown(self):
        self.tmp.cleanup()

    def test_guarda_e_le(self):
        cache.store(self.reports, "inspect", "a" * 64, {"x": 1})
        self.assertEqual(cache.load(self.reports, "inspect", "a" * 64), {"x": 1})

    def test_hash_diferente_nao_reaproveita(self):
        cache.store(self.reports, "inspect", "a" * 64, {"x": 1})
        self.assertIsNone(cache.load(self.reports, "inspect", "b" * 64))

    def test_tipo_diferente_nao_colide(self):
        cache.store(self.reports, "inspect", "a" * 64, {"x": 1})
        self.assertIsNone(cache.load(self.reports, "strings", "a" * 64))

    def test_cached_calcula_uma_vez(self):
        calls = []

        def compute():
            calls.append(1)
            return {"valor": 42}

        first, hit1 = cache.cached(self.reports, "manifest", "c" * 64, compute)
        second, hit2 = cache.cached(self.reports, "manifest", "c" * 64, compute)
        self.assertEqual(first, second)
        self.assertFalse(hit1)
        self.assertTrue(hit2)
        self.assertEqual(len(calls), 1)

    def test_entrada_corrompida_e_ignorada(self):
        cache.store(self.reports, "inspect", "d" * 64, {"x": 1})
        path = cache._path_for(self.reports, "inspect", "d" * 64)
        path.write_text("{ quebrado", encoding="utf-8")
        self.assertIsNone(cache.load(self.reports, "inspect", "d" * 64))

    def test_hash_com_caracteres_estranhos_nao_escapa_da_pasta(self):
        path = cache._path_for(self.reports, "inspect", "../../etc/passwd")
        self.assertEqual(path.parent, cache.cache_dir(self.reports))

    def test_poda_mantem_limite(self):
        original = cache.MAX_CACHE_FILES
        cache.MAX_CACHE_FILES = 3
        try:
            for index in range(6):
                cache.store(self.reports, "inspect", f"{index:064d}", {"i": index})
            files = list(cache.cache_dir(self.reports).glob("*.json"))
            self.assertLessEqual(len(files), 3)
        finally:
            cache.MAX_CACHE_FILES = original


class ObfuscationTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)

    def tearDown(self):
        self.tmp.cleanup()

    def _apk(self, names):
        path = self.root / "app.apk"
        with zipfile.ZipFile(path, "w") as archive:
            for name in names:
                archive.writestr(name, b"x")
        return path

    def test_nomes_normais_nao_marcam(self):
        apk = self._apk([f"res/layout/tela_{i}.xml" for i in range(60)])
        result = obfuscation.detect(apk)
        self.assertFalse(result["obfuscated"])
        self.assertIn("Sem indício", result["message"])

    def test_muitos_nomes_curtos_marcam(self):
        letters = "abcdefghijklmnopqrstuvwxyz"
        names = [f"res/{letters[i]}/{letters[i]}.xml" for i in range(26)]
        names += [f"smali/{letters[i]}/{letters[i]}.smali" for i in range(26)]
        names += [f"assets/{letters[i]}/{letters[i]}.json" for i in range(26)]
        result = obfuscation.detect(self._apk(names))
        self.assertTrue(result["obfuscated"])
        self.assertIn("ofuscado", result["message"])

    def test_arquivo_invalido_nao_quebra(self):
        bad = self.root / "bad.apk"
        bad.write_bytes(b"nao e zip")
        result = obfuscation.detect(bad)
        self.assertIsNone(result["obfuscated"])
        self.assertIn("Não foi possível", result["message"])


if __name__ == "__main__":
    unittest.main()
