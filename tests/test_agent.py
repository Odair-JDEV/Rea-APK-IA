"""Testes do agente interno do gateway: sem rede, sem opencode e sem APK real."""
from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from readroid import agent


class AgentToolTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.work = Path(self.tmp.name)
        (self.work / "apktool.yml").write_text("apkFileName: app.apk\n", encoding="utf-8")
        (self.work / "AndroidManifest.xml").write_text('<manifest package="a"/>', encoding="utf-8")
        (self.work / "res").mkdir()
        (self.work / "res" / "strings.xml").write_text(
            '<resources><string name="x">Hi</string></resources>', encoding="utf-8")

    def tearDown(self):
        self.tmp.cleanup()

    def test_le_arquivo_dentro_da_pasta(self):
        self.assertIn("package", agent.execute(self.work, "read_file", {"path": "AndroidManifest.xml"}))

    def test_bloqueia_caminho_fora_da_pasta(self):
        result = agent.execute(self.work, "write_file", {"path": "../fora.txt", "content": "x"})
        self.assertIn("bloqueado", result)
        self.assertFalse((self.work.parent / "fora.txt").exists())

    def test_protege_apktool_yml(self):
        result = agent.execute(self.work, "write_file", {"path": "apktool.yml", "content": "x"})
        self.assertIn("protegido", result)
        self.assertIn("apkFileName", (self.work / "apktool.yml").read_text(encoding="utf-8"))

    def test_grava_arquivo_de_texto(self):
        result = agent.execute(self.work, "write_file",
                               {"path": "res/strings.xml", "content": "<resources/>"})
        self.assertIn("Gravado", result)
        self.assertEqual((self.work / "res" / "strings.xml").read_text(encoding="utf-8"), "<resources/>")

    def test_busca_texto(self):
        result = agent.execute(self.work, "search_text", {"query": "Hi"})
        self.assertIn("strings.xml", result)

    def test_lista_arquivos(self):
        result = agent.execute(self.work, "list_files", {"path": "."})
        self.assertIn("AndroidManifest.xml", result)


class AgentLoopTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.work = Path(self.tmp.name)
        (self.work / "AndroidManifest.xml").write_text('<manifest package="a"/>', encoding="utf-8")

    def tearDown(self):
        self.tmp.cleanup()

    def test_executa_ferramentas_e_termina(self):
        rounds = []

        def request(payload):
            rounds.append(payload)
            if len(rounds) == 1:
                return {"choices": [{"message": {"content": "", "tool_calls": [
                    {"id": "1", "function": {"name": "read_file",
                                             "arguments": '{"path": "AndroidManifest.xml"}'}}]}}]}
            return {"choices": [{"message": {"content": "Terminei."}}]}

        seen = []
        result = agent.run(self.work, "leia o manifesto", request, emit=seen.append)
        self.assertTrue(result["ok"])
        self.assertEqual(result["message"], "Terminei.")
        self.assertEqual(result["steps"], 2)
        self.assertTrue(any("read_file" in line for line in seen))
        self.assertEqual(rounds[0]["tools"][0]["function"]["name"], "list_files")

    def test_erro_do_gateway_nao_quebra(self):
        def request(payload):
            return {"error": {"message": "chave inválida"}}

        result = agent.run(self.work, "x", request, emit=lambda m: None)
        self.assertFalse(result["ok"])
        self.assertIn("chave inválida", result["message"])

    def test_excecao_de_rede_vira_mensagem(self):
        def request(payload):
            raise OSError("sem conexão")

        result = agent.run(self.work, "x", request, emit=lambda m: None)
        self.assertFalse(result["ok"])
        self.assertIn("sem conexão", result["message"])

    def test_limite_de_passos(self):
        def request(payload):
            return {"choices": [{"message": {"content": "", "tool_calls": [
                {"id": "1", "function": {"name": "list_files", "arguments": "{}"}}]}}]}

        result = agent.run(self.work, "x", request, emit=lambda m: None, max_steps=3)
        self.assertFalse(result["ok"])
        self.assertIn("limite", result["message"])


class AgentSafetyTests(unittest.TestCase):
    """Modo somente leitura e modo proposta (dry run)."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.work = Path(self.tmp.name)
        (self.work / "AndroidManifest.xml").write_text("<manifest/>", encoding="utf-8")

    def tearDown(self):
        self.tmp.cleanup()

    def _write_request(self, path="AndroidManifest.xml", content="<manifest novo/>"):
        import json as _json
        calls = {"n": 0}

        def request(payload):
            calls["n"] += 1
            if calls["n"] == 1:
                return {"choices": [{"message": {"content": "", "tool_calls": [
                    {"id": "1", "function": {"name": "write_file",
                                             "arguments": _json.dumps({"path": path, "content": content})}}]}}]}
            return {"choices": [{"message": {"content": "Pronto."}}]}

        return request

    def test_read_only_bloqueia_gravacao(self):
        result = agent.run(self.work, "x", self._write_request(), emit=lambda m: None, read_only=True)
        self.assertTrue(result["ok"])
        self.assertEqual((self.work / "AndroidManifest.xml").read_text(encoding="utf-8"), "<manifest/>")

    def test_read_only_avisa_o_modelo(self):
        seen = {}

        def request(payload):
            seen["system"] = payload["messages"][0]["content"]
            return {"choices": [{"message": {"content": "ok"}}]}

        agent.run(self.work, "x", request, emit=lambda m: None, read_only=True)
        self.assertIn("NÃO pode alterar", seen["system"])

    def test_dry_run_nao_grava_e_devolve_proposta(self):
        result = agent.run(self.work, "x", self._write_request(), emit=lambda m: None, dry_run=True)
        self.assertTrue(result["ok"])
        self.assertEqual((self.work / "AndroidManifest.xml").read_text(encoding="utf-8"), "<manifest/>")
        self.assertEqual(result["proposals"]["AndroidManifest.xml"], "<manifest novo/>")

    def test_apply_proposals_grava(self):
        applied = agent.apply_proposals(self.work, {"AndroidManifest.xml": "<manifest aplicado/>"})
        self.assertTrue(applied["ok"])
        self.assertEqual(applied["written"], ["AndroidManifest.xml"])
        self.assertEqual((self.work / "AndroidManifest.xml").read_text(encoding="utf-8"),
                         "<manifest aplicado/>")

    def test_apply_proposals_respeita_apktool_yml(self):
        (self.work / "apktool.yml").write_text("version: 2\n", encoding="utf-8")
        applied = agent.apply_proposals(self.work, {"apktool.yml": "hackeado"})
        self.assertFalse(applied["ok"])
        self.assertEqual((self.work / "apktool.yml").read_text(encoding="utf-8"), "version: 2\n")

    def test_diff_proposal_mostra_linhas(self):
        diff = agent.diff_proposal(self.work, "AndroidManifest.xml", "<manifest novo/>")
        text = "\n".join(diff)
        self.assertIn("-<manifest/>", text)
        self.assertIn("+<manifest novo/>", text)

    def test_diff_de_arquivo_novo(self):
        diff = agent.diff_proposal(self.work, "novo.txt", "linha")
        self.assertIn("/dev/null", "\n".join(diff))

    def test_summarize_proposals_conta_linhas(self):
        lines = agent.summarize_proposals(self.work, {"AndroidManifest.xml": "<manifest novo/>"})
        self.assertEqual(len(lines), 1)
        self.assertIn("+1", lines[0])
        self.assertIn("-1", lines[0])


if __name__ == "__main__":
    unittest.main()
