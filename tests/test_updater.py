"""Testes da atualização do repositório e da pasta de saída dos APKs.

Tudo é simulado: nenhuma chamada real de git, rede ou cópia para o celular.
"""

import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from readroid import outputs, updater


def _git_out(returncode=0, stdout="", stderr=""):
    result = subprocess.CompletedProcess(args=[], returncode=returncode, stdout=stdout, stderr=stderr)
    return result


class UpdaterTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.repo = Path(self.tmp.name)
        (self.repo / ".git").mkdir()

    def tearDown(self):
        self.tmp.cleanup()

    def _patch_git(self, responses):
        """responses: lista de (args_tupla, resultado); chamadas fora da lista recebem sucesso vazio."""
        def fake_git(repo, *args):
            key = tuple(args)
            if key in responses:
                return responses[key]
            return 0, ""
        return patch.object(updater, "_git", fake_git)

    def test_nao_e_repositorio(self):
        plain = Path(self.tmp.name) / "vazio"
        plain.mkdir()
        result = updater.check_update(plain)
        self.assertFalse(result["ok"])
        self.assertIn("repositório", result["message"])

    def test_sem_remote_recusa(self):
        with self._patch_git({("remote", "get-url", "origin"): (1, "")}):
            result = updater.check_update(self.repo)
        self.assertFalse(result["ok"])
        self.assertIn("origin", result["message"])

    def test_fetch_falhando_recusa(self):
        responses = {
            ("remote", "get-url", "origin"): (0, "https://github.com/x/y.git"),
            ("rev-parse", "--abbrev-ref", "HEAD"): (0, "main"),
            ("fetch", "origin", "main"): (1, "Could not resolve host"),
        }
        with self._patch_git(responses):
            result = updater.check_update(self.repo)
        self.assertFalse(result["ok"])
        self.assertIn("servidor", result["message"])

    def test_arquivos_alterados_bloqueiam(self):
        responses = {
            ("remote", "get-url", "origin"): (0, "https://github.com/x/y.git"),
            ("rev-parse", "--abbrev-ref", "HEAD"): (0, "main"),
            ("status", "--porcelain"): (0, " M readroid/app.py\n?? novo.txt\n"),
        }
        with self._patch_git(responses):
            result = updater.check_update(self.repo)
        self.assertFalse(result["ok"])
        self.assertTrue(result["dirty"])
        self.assertIn("alterados", result["message"])
        self.assertIn("readroid/app.py", result["message"])

    def test_commits_proprios_bloqueiam(self):
        responses = {
            ("remote", "get-url", "origin"): (0, "https://github.com/x/y.git"),
            ("rev-parse", "--abbrev-ref", "HEAD"): (0, "main"),
            ("rev-list", "--count", "HEAD..origin/main"): (0, "3"),
            ("rev-list", "--count", "origin/main..HEAD"): (0, "2"),
        }
        with self._patch_git(responses):
            result = updater.check_update(self.repo)
        self.assertFalse(result["ok"])
        self.assertTrue(result["diverged"])
        self.assertIn("não estão no remoto", result["message"])

    def test_em_dia_nao_propoe_nada(self):
        responses = {
            ("remote", "get-url", "origin"): (0, "https://github.com/x/y.git"),
            ("rev-parse", "--abbrev-ref", "HEAD"): (0, "main"),
            ("rev-list", "--count", "HEAD..origin/main"): (0, "0"),
            ("rev-list", "--count", "origin/main..HEAD"): (0, "0"),
        }
        with self._patch_git(responses):
            result = updater.check_update(self.repo)
        self.assertTrue(result["ok"])
        self.assertFalse(result["updated"])
        self.assertIn("mais recente", result["message"])

    def test_atualizacao_disponivel_lista_commits(self):
        responses = {
            ("remote", "get-url", "origin"): (0, "https://github.com/x/y.git"),
            ("rev-parse", "--abbrev-ref", "HEAD"): (0, "main"),
            ("rev-list", "--count", "HEAD..origin/main"): (0, "2"),
            ("rev-list", "--count", "origin/main..HEAD"): (0, "0"),
            ("log", "--oneline", "HEAD..origin/main"): (0, "abc1234 corrige build\ndef5678 novo menu\n"),
        }
        with self._patch_git(responses):
            result = updater.check_update(self.repo)
        self.assertTrue(result["ok"])
        self.assertTrue(result["updated"])
        self.assertEqual(result["behind"], 2)
        self.assertEqual(result["commits"], ["abc1234 corrige build", "def5678 novo menu"])

    def test_apply_usa_ff_only(self):
        seen = []

        def fake_git(repo, *args):
            seen.append(args)
            if args == ("merge", "--ff-only", "origin/main"):
                return 0, ""
            if args == ("log", "--oneline", "-1"):
                return 0, "abc1234 corrige build"
            return 0, ""

        with patch.object(updater, "_git", fake_git):
            result = updater.apply_update(self.repo, "main")
        self.assertTrue(result["ok"])
        self.assertIn(("merge", "--ff-only", "origin/main"), seen)
        self.assertIn("abc1234", result["message"])

    def test_apply_falhando_devolve_erro(self):
        def fake_git(repo, *args):
            if args and args[0] == "merge":
                return 1, "error: could not fast-forward"
            return 0, ""

        with patch.object(updater, "_git", fake_git):
            result = updater.apply_update(self.repo, "main")
        self.assertFalse(result["ok"])
        self.assertIn("fast-forward", result["message"])


class OutputDirTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.home = Path(self.tmp.name) / "home"
        self.home.mkdir()
        self.settings = self.home / ".readroid" / "settings.json"
        self._patchers = [
            patch.object(outputs, "SETTINGS_FILE", self.settings),
            patch.object(Path, "home", lambda: self.home),
        ]
        for item in self._patchers:
            item.start()

    def tearDown(self):
        for item in self._patchers:
            item.stop()
        self.tmp.cleanup()

    def test_padrao_sem_config(self):
        (self.home / "storage" / "downloads").mkdir(parents=True)
        result = outputs.resolve_output_dir()
        self.assertEqual(result, self.home / "storage" / "downloads" / "ReaDroid")

    def test_fora_do_termux_cai_no_builds(self):
        result = outputs.resolve_output_dir()
        self.assertEqual(result, Path.cwd() / "builds")

    def test_config_salva_e_relida(self):
        outputs.save_output_dir("Download/Meus APKs")
        self.assertEqual(outputs.load_output_dir(), "Download/Meus APKs")
        result = outputs.resolve_output_dir()
        self.assertTrue(str(result).endswith("Download\\Meus APKs") or str(result).endswith("Download/Meus APKs"))
        self.assertTrue(result.is_dir())

    def test_limpar_volta_ao_padrao(self):
        outputs.save_output_dir("/tmp/alguma")
        outputs.save_output_dir(None)
        self.assertEqual(outputs.load_output_dir(), "")

    def test_caminho_relativo_vira_storage_shared(self):
        result = outputs.resolve_output_dir("MinhasPastas/APKs")
        # No Windows o Path junta com a unidade atual; o que importa é o sufixo e a pasta criada.
        self.assertTrue(str(result).replace("\\", "/").endswith("MinhasPastas/APKs"))
        self.assertTrue(result.is_dir())

    def test_copy_nao_sobrescreve(self):
        src_dir = Path(self.tmp.name) / "src"
        src_dir.mkdir()
        apk = src_dir / "app.apk"
        apk.write_bytes(b"um")
        dest_dir = Path(self.tmp.name) / "dest"
        first = outputs.copy_to_output(apk, dest_dir)
        second = outputs.copy_to_output(apk, dest_dir)
        self.assertIsNotNone(first)
        self.assertIsNotNone(second)
        self.assertNotEqual(first, second)
        self.assertEqual(first.read_bytes(), b"um")

    def test_copy_falha_devolve_none(self):
        apk = Path(self.tmp.name) / "x.apk"
        apk.write_bytes(b"x")
        # Um caminho "ocupado" por um arquivo existente não pode virar pasta.
        blocker = Path(self.tmp.name) / "bloqueio"
        blocker.write_bytes("não sou pasta".encode())
        self.assertIsNone(outputs.copy_to_output(apk, blocker))


if __name__ == "__main__":
    unittest.main()
