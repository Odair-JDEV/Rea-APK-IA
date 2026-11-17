"""Testes do resumo legível (resumo.md)."""

import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from readroid import report

MANIFEST = {
    "decoded": True,
    "package": "com.exemplo.app",
    "version_name": "1.2.3",
    "version_code": "45",
    "min_sdk": 24,
    "target_sdk": 34,
    "application": {"debuggable": "true", "allow_backup": "false", "uses_cleartext_traffic": "true"},
    "permissions": [
        {"name": "android.permission.INTERNET"},
        {"name": "android.permission.CAMERA"},
        {"name": "android.permission.READ_CONTACTS"},
    ],
    "components": [
        {"type": "activity", "name": ".MainActivity", "exported": "true"},
        {"type": "service", "name": ".Sync", "exported": "false"},
        {"type": "receiver", "name": ".Boot", "exported": None, "intent_filters": ["x"]},
    ],
}

STRINGS = {"urls": ["https://api.exemplo.com/v1"], "domains": ["api.exemplo.com"], "ipv4_candidates": ["10.0.0.1"]}
INSPECTION = {"file_size_bytes": 2 * 1024 * 1024, "dex_files": ["classes.dex"], "native_libraries": ["lib/x.so"]}


class ReportTests(unittest.TestCase):
    def test_resumo_tem_identidade(self):
        text = report.build_summary(MANIFEST, STRINGS, INSPECTION, "App Teste")
        self.assertIn("App Teste", text)
        self.assertIn("com.exemplo.app", text)
        self.assertIn("1.2.3", text)
        self.assertIn("2048 KB", text)

    def test_avisos_do_manifesto(self):
        text = report.build_summary(MANIFEST, None, None)
        self.assertIn("debuggable", text)
        self.assertIn("usesCleartextTraffic", text)
        self.assertNotIn("allowBackup", text)

    def test_permissoes_perigosas_primeiro(self):
        text = report.build_summary(MANIFEST, None, None)
        self.assertIn("Que merecem atenção", text)
        self.assertIn("usar a câmera", text)
        self.assertIn("ler contatos", text)
        # INTERNET não é considerada perigosa: fica na lista "Outras".
        self.assertLess(text.index("usar a câmera"), text.index("INTERNET", text.index("Outras")))

    def test_componentes_expostos(self):
        text = report.build_summary(MANIFEST, None, None)
        self.assertIn(".MainActivity", text)
        # receiver com intent-filter e sem exported explícito conta como exposto.
        self.assertIn(".Boot", text)

    def test_enderecos_e_aviso_de_limitacao(self):
        text = report.build_summary(MANIFEST, STRINGS, None)
        self.assertIn("api.exemplo.com", text)
        self.assertIn("10.0.0.1", text)
        self.assertIn("análise estática", text)

    def test_tudo_vazio_nao_quebra(self):
        text = report.build_summary(None, None, None, "vazio")
        self.assertIn("vazio", text)
        self.assertIn("Limitações", text)

    def test_write_summary_cria_arquivo(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = report.write_summary(Path(tmp) / "reports" / "r.md", "# oi")
            self.assertTrue(path.is_file())
            self.assertEqual(path.read_text(encoding="utf-8"), "# oi")


if __name__ == "__main__":
    unittest.main()
