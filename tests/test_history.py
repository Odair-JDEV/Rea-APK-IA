"""Testes do histórico de builds e do estado por APK (só arquivos temporários)."""

import json
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from readroid import history


class HistoryTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.builds = self.root / "builds"
        self.decoded = self.root / "app_apktool"
        self.decoded.mkdir()

    def tearDown(self):
        self.tmp.cleanup()

    def _result(self, ok=True, sha="a" * 64):
        return {
            "ok": ok,
            "final_apk": str(self.builds / "out" / "app.apk") if ok else None,
            "steps": {
                "rebuild": {"ok": ok},
                "align": {"ok": True, "skipped": False},
                "verify": {"ok": False, "skipped": True},
                "sha256": sha,
            },
        }

    def test_historico_comeca_vazio(self):
        self.assertEqual(history.load_history(self.builds), [])

    def test_registra_e_le_entrada(self):
        entry = history.record_build(self.builds, self._result(), self.decoded, duration_s=3.14)
        self.assertTrue(entry["ok"])
        self.assertEqual(entry["duration_s"], 3.1)
        self.assertEqual(entry["sha256"], "a" * 64)
        self.assertTrue(entry["steps"]["verify"]["skipped"])

        stored = history.load_history(self.builds)
        self.assertEqual(len(stored), 1)
        self.assertEqual(stored[0]["decoded"], "app_apktool")

    def test_registra_falha_sem_apk(self):
        entry = history.record_build(self.builds, self._result(ok=False), self.decoded)
        self.assertFalse(entry["ok"])
        self.assertIsNone(entry["final_apk"])

    def test_documento_corrompido_nao_derruba(self):
        history.history_path(self.builds).parent.mkdir(parents=True, exist_ok=True)
        history.history_path(self.builds).write_text("{ nao é json", encoding="utf-8")
        self.assertEqual(history.load_history(self.builds), [])
        self.assertTrue(history.record_build(self.builds, self._result(), self.decoded)["ok"])

    def test_historico_respeita_limite(self):
        original = history.MAX_HISTORY_ENTRIES
        history.MAX_HISTORY_ENTRIES = 3
        try:
            for _ in range(6):
                history.record_build(self.builds, self._result(), self.decoded)
            self.assertEqual(len(history.load_history(self.builds)), 3)
        finally:
            history.MAX_HISTORY_ENTRIES = original

    def test_format_history_mais_recente_primeiro(self):
        history.record_build(self.builds, self._result(), self.decoded)
        history.record_build(self.builds, self._result(ok=False), self.decoded)
        lines = history.format_history(history.load_history(self.builds))
        self.assertEqual(len(lines), 2)
        self.assertIn("falhou", lines[0])
        self.assertIn("OK", lines[1])

    def test_estado_por_apk(self):
        apk = self.root / "orig.apk"
        apk.write_bytes(b"x")
        history.mark_extracted(self.decoded, apk, "b" * 64)
        state = history.load_state(self.decoded)
        self.assertEqual(state["source_apk"], "orig.apk")
        self.assertEqual(state["source_sha256"], "b" * 64)
        self.assertEqual(state["edits"], [])

        history.add_edit(self.decoded, "edição rápida: debuggable")
        state = history.load_state(self.decoded)
        self.assertEqual(len(state["edits"]), 1)
        self.assertEqual(state["edits"][0]["what"], "edição rápida: debuggable")

    def test_mark_build_guarda_ultimo(self):
        entry = history.record_build(self.builds, self._result(), self.decoded)
        history.mark_build(self.decoded, entry)
        self.assertEqual(history.load_state(self.decoded)["last_build"]["sha256"], "a" * 64)

    def test_estado_ausente_devolve_vazio(self):
        self.assertEqual(history.load_state(self.decoded), {})

    def test_arquivo_de_estado_e_json(self):
        history.mark_extracted(self.decoded, self.root / "a.apk")
        raw = json.loads((self.decoded / history.STATE_FILE).read_text(encoding="utf-8"))
        self.assertIn("updated_at", raw)


class BuilderHistoryTests(unittest.TestCase):
    """O build real registra histórico; com record_history=False não grava nada."""

    def test_build_pipeline_pode_nao_registrar(self):
        from readroid import builder
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            decoded = root / "app_apktool"
            decoded.mkdir()
            (decoded / "apktool.yml").write_text("version: 2.9.0\n", encoding="utf-8")
            result = builder.build_pipeline(decoded, root / "builds" / "x", root / "k.jks",
                                            quick_edits=[], progress=None, record_history=False)
            self.assertIn("steps", result)
            self.assertFalse((root / "builds" / "history.json").exists())
            self.assertFalse((decoded / ".readroid.json").exists())


if __name__ == "__main__":
    unittest.main()
