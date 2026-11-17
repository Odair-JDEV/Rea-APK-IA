"""Testes do assistente guiado: sem APK real, sem dispositivo e sem IA de verdade."""
from __future__ import annotations

import io
import os
import shutil
import sys
import tempfile
import types
import unittest
from contextlib import redirect_stdout
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import readroid  # noqa: E402
from readroid import wizard  # noqa: E402


def _patch_ai(fake_ai):
    """`from . import ai` resolve o atributo do pacote, não apenas sys.modules."""
    return patch.multiple(readroid, ai=fake_ai, create=True)


def _fake_app_module(base: Path) -> types.ModuleType:
    """Substitui readroid.app: o import real exigiria dependências opcionais (RTL)."""
    module = types.ModuleType("readroid.app")
    for name, value in (("GREEN", ""), ("CYAN", ""), ("YELLOW", ""), ("RED", ""),
                        ("DIM", ""), ("RESET", ""), ("BOLD", "")):
        setattr(module, name, value)
    module.OUTPUTS = base / "output"
    module.BUILDS = base / "builds"
    module.KEYSTORE = base / "keystore.jks"
    for path in (module.OUTPUTS, module.BUILDS):
        path.mkdir(parents=True, exist_ok=True)
    module.safe_input = input
    module.sanitize = lambda text: str(text)
    return module


class WizardTestCase(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.base = Path(self.tmp.name)
        self.app = _fake_app_module(self.base)
        self._saved_app = sys.modules.get("readroid.app")
        sys.modules["readroid.app"] = self.app
        self.out = io.StringIO()

    def tearDown(self):
        if self._saved_app is None:
            sys.modules.pop("readroid.app", None)
        else:
            sys.modules["readroid.app"] = self._saved_app
        self.tmp.cleanup()

    def say(self, *args):
        return None

    def confirm(self, answer: bool):
        return lambda prompt="": answer


class ExtractionTests(WizardTestCase):
    def test_reconhece_pasta_do_mesmo_apk(self):
        folder = self.base / "app_apktool"
        folder.mkdir()
        (folder / "apktool.yml").write_text("apkFileName: app.apk\n", encoding="utf-8")
        self.assertTrue(wizard._folder_matches_apk(folder, Path("app.apk")))
        self.assertFalse(wizard._folder_matches_apk(folder, Path("outro.apk")))

    def test_pasta_de_outro_apk_nao_e_reutilizada_sem_confirmacao(self):
        outputs = self.app.OUTPUTS
        stale = outputs / "app_apktool"
        stale.mkdir()
        (stale / "apktool.yml").write_text("apkFileName: outro.apk\n", encoding="utf-8")
        apk = self.base / "app.apk"
        apk.write_bytes(b"PK\x03\x04")
        with patch.object(wizard, "_confirm", self.confirm(False)), \
                patch.object(wizard, "extract_smali_with_apktool") as extract, \
                redirect_stdout(self.out):
            result = wizard._extract_apk(apk, outputs)
        self.assertIsNone(result)
        extract.assert_not_called()

    def test_pasta_do_mesmo_apk_e_reutilizada_sem_reextrair(self):
        outputs = self.app.OUTPUTS
        same = outputs / "app_apktool"
        same.mkdir()
        (same / "apktool.yml").write_text("apkFileName: app.apk\n", encoding="utf-8")
        apk = self.base / "app.apk"
        apk.write_bytes(b"PK\x03\x04")
        with patch.object(wizard, "extract_smali_with_apktool") as extract, redirect_stdout(self.out):
            result = wizard._extract_apk(apk, outputs)
        self.assertEqual(result, same)
        extract.assert_not_called()


class BuildReportTests(WizardTestCase):
    def _steps(self, **overrides):
        steps = {
            "rebuild": {"ok": True},
            "align": {"ok": True},
            "keystore": {"ok": True},
            "sign": {"ok": True},
            "verify": {"ok": True},
        }
        steps.update(overrides)
        return steps

    def test_falha_de_assinatura_nao_devolve_apk(self):
        result = {"ok": False, "final_apk": None,
                  "steps": self._steps(sign={"ok": False, "stderr": "boom"})}
        with redirect_stdout(self.out):
            self.assertIsNone(wizard._report_build(result))

    def test_avisa_quando_alinhamento_foi_pulado(self):
        apk = self.base / "final.apk"
        apk.write_bytes(b"x")
        result = {"ok": True, "final_apk": str(apk), "sha256": "abc",
                  "steps": self._steps(align={"ok": None, "skipped": True,
                                              "message": "zipalign não instalado"})}
        with redirect_stdout(self.out):
            self.assertEqual(wizard._report_build(result), apk)
        text = self.out.getvalue()
        self.assertIn("NÃO foi alinhado", text)

    def test_avisa_quando_verificacao_foi_pulada(self):
        apk = self.base / "final.apk"
        apk.write_bytes(b"x")
        result = {"ok": True, "final_apk": str(apk), "sha256": "abc",
                  "steps": self._steps(verify={"ok": None})}
        with redirect_stdout(self.out):
            wizard._report_build(result)
        self.assertIn("NÃO foi verificada", self.out.getvalue())


class AiEditTests(WizardTestCase):
    def test_sem_backup_a_ia_nao_edita(self):
        decoded = self.app.OUTPUTS / "app_apktool"
        decoded.mkdir()
        fake_ai = types.ModuleType("readroid.ai")
        fake_ai.ready = lambda: (True, "", "opencode")
        fake_ai.fix_loop = lambda *a, **k: self.fail("fix_loop não deveria rodar sem backup")
        answers = iter(["s", "traduzir", "s"])
        with patch.dict(sys.modules, {"readroid.ai": fake_ai}), _patch_ai(fake_ai), \
                patch.object(wizard, "_backup", lambda *a: None), \
                patch("builtins.input", lambda prompt="": next(answers)), \
                redirect_stdout(self.out):
            self.assertIsNone(wizard._maybe_ai_edit(decoded, self.app))
        self.assertIn("cancelada", self.out.getvalue())

    def test_pede_instrucao_em_vez_de_rebuild_com_prompt_vazio(self):
        decoded = self.app.OUTPUTS / "app_apktool"
        decoded.mkdir()
        calls = {}

        def fake_loop(decoded_dir, instruction, *args, **kwargs):
            calls["instruction"] = instruction
            return {"ok": False, "message": "parado"}

        fake_ai = types.ModuleType("readroid.ai")
        fake_ai.ready = lambda: (True, "", "opencode")
        fake_ai.fix_loop = fake_loop
        answers = iter(["s", "", ])
        backup = self.base / "backup"
        with patch.dict(sys.modules, {"readroid.ai": fake_ai}), _patch_ai(fake_ai), \
                patch.object(wizard, "_backup", lambda *a: backup), \
                patch("builtins.input", lambda prompt="": next(answers)), \
                redirect_stdout(self.out):
            self.assertIsNone(wizard._maybe_ai_edit(decoded, self.app))
        self.assertNotIn("instruction", calls)

    def test_ia_não_configurada_nao_pede_backup(self):
        decoded = self.app.OUTPUTS / "app_apktool"
        decoded.mkdir()
        fake_ai = types.ModuleType("readroid.ai")
        fake_ai.ready = lambda: (False, "sem chave", None)
        with patch.dict(sys.modules, {"readroid.ai": fake_ai}), _patch_ai(fake_ai), \
                patch.object(wizard, "_backup", lambda *a: self.fail("não deveria pedir backup")), \
                patch("builtins.input", lambda prompt="": "s"), \
                redirect_stdout(self.out):
            self.assertIsNone(wizard._maybe_ai_edit(decoded, self.app))
        self.assertIn("não configurada", self.out.getvalue())


class InstallTests(WizardTestCase):
    def test_abrir_instalador_nao_conta_como_instalado(self):
        apk = self.base / "final.apk"
        apk.write_bytes(b"x")

        def which(name):
            return "/usr/bin/termux-open" if name == "termux-open" else None

        with patch.object(shutil, "which", which), \
                patch.object(wizard.subprocess, "run", lambda *a, **k: None), \
                patch.object(wizard, "_confirm", self.confirm(True)), \
                redirect_stdout(self.out):
            status = wizard._install_apk(apk, has_adb=False)
        self.assertEqual(status, "opened")

    def test_adb_sem_success_nao_conta_como_instalado(self):
        apk = self.base / "final.apk"
        apk.write_bytes(b"x")

        class Proc:
            returncode = 0
            stdout = "Performing Streamed Install\n"
            stderr = ""

        with patch.object(wizard.subprocess, "run", lambda *a, **k: Proc()), \
                patch.object(shutil, "which", lambda name: None), \
                patch.object(wizard, "_confirm", self.confirm(True)), \
                redirect_stdout(self.out):
            status = wizard._install_apk(apk, has_adb=True)
        self.assertEqual(status, "saved")


if __name__ == "__main__":
    unittest.main()
