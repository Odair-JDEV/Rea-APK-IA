"""Testes da retomada de sessão do agente (v0.6.0): tudo mockado, sem rede."""
from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from readroid import agent


class SessionTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.work = Path(self.tmp.name) / "app_apktool"
        self.work.mkdir()

    def tearDown(self):
        self.tmp.cleanup()

    def test_save_lista_e_carrega_sessao(self):
        messages = [{"role": "system", "content": "s"},
                    {"role": "user", "content": "edite o app"},
                    {"role": "assistant", "content": "", "tool_calls": []}]
        path = agent.save_session(self.work, messages, 60)
        self.assertIsNotNone(path)
        found = agent.list_sessions(self.work)
        self.assertEqual(len(found), 1)
        loaded = agent.load_session(self.work, found[0]["id"])
        self.assertEqual(loaded, messages)

    def test_carregar_sessao_inexistente_devolve_none(self):
        self.assertIsNone(agent.load_session(self.work, "20000101_000000"))

    def test_sessao_fora_da_pasta_e_bloqueada(self):
        # id com ".." não pode escapar da pasta de sessões
        self.assertIsNone(agent.load_session(self.work, "../../etc/passwd"))

    def test_limite_de_sessoes_guardadas(self):
        for _ in range(agent.SESSIONS_MAX + 3):
            agent.save_session(self.work, [{"role": "user", "content": "x"}], 5)
        found = agent.list_sessions(self.work)
        self.assertEqual(len(found), agent.SESSIONS_MAX)

    def test_limite_atinge_e_salva_sessao(self):
        # duas rodadas de tool_calls; na terceira o modelo responde texto => terminaria,
        # então simulamos um modelo que SEMPRE pede ferramenta e um max_steps pequeno.
        def always_tools(payload):
            return {"choices": [{"message": {"content": "", "tool_calls": [
                {"id": "c1", "function": {"name": "list_files", "arguments": "{}"}}]}}]}

        with patch.object(agent, "print", lambda *a, **k: None):
            res = agent.run(self.work, "edite", always_tools, emit=lambda m: None, max_steps=3)
        self.assertFalse(res["ok"])
        self.assertTrue(res.get("limit_reached"))
        self.assertTrue(res.get("session_id"))
        saved = agent.load_session(self.work, res["session_id"])
        self.assertTrue(saved)  # conversa inteira, com tool results
        roles = [m["role"] for m in saved]
        self.assertIn("tool", roles)

    def test_retomada_continua_da_conversa_salva(self):
        steps = {"n": 0}

        def chat_then_done(payload):
            steps["n"] += 1
            if steps["n"] == 1:
                return {"choices": [{"message": {"content": "", "tool_calls": [
                    {"id": "c1", "function": {"name": "list_files", "arguments": "{}"}}]}}]}
            return {"choices": [{"message": {"content": "terminei"}}]}

        res = agent.run(self.work, "edite", chat_then_done, emit=lambda m: None, max_steps=1)
        self.assertTrue(res.get("limit_reached"))
        session_id = res["session_id"]
        calls = []
        original_load = agent.load_session

        def fake_load(workdir, sid):
            calls.append(sid)
            return original_load(workdir, sid)

        with patch.object(agent, "load_session", fake_load):
            res2 = agent.run(self.work, "continue", chat_then_done,
                             emit=lambda m: None, max_steps=5, session_id=session_id)
        self.assertTrue(res2["ok"])
        self.assertEqual(calls, [session_id])
        self.assertEqual(steps["n"], 2)  # segunda chamada só acontece com a sessão retomada

    def test_retomada_com_sessao_invalida_falha_limpo(self):
        res = agent.run(self.work, "continue", lambda p: {}, emit=lambda m: None,
                        session_id="19000101_000000")
        self.assertFalse(res["ok"])
        self.assertIn("não encontrada", res["message"].lower())

    def test_sessoes_ficam_dentro_da_pasta_do_apk(self):
        def always_tools(payload):
            return {"choices": [{"message": {"content": "", "tool_calls": [
                {"id": "c", "function": {"name": "list_files", "arguments": "{}"}}]}}]}

        with patch.object(agent, "print", lambda *a, **k: None):
            agent.run(self.work, "edite", always_tools, emit=lambda m: None, max_steps=2)
        sess_dir = self.work / agent.SESSIONS_DIRNAME
        self.assertTrue(sess_dir.is_dir())
        # a listagem do agente nunca mostra a pasta de sessões como arquivo editável
        listing = agent.execute(self.work, "list_files", {"path": "."})
        self.assertNotIn(agent.SESSIONS_DIRNAME, listing)

    def test_json_da_sessao_e_legivel_e_completo(self):
        def always_tools(payload):
            return {"choices": [{"message": {"content": "", "tool_calls": [
                {"id": "c", "function": {"name": "read_file",
                                         "arguments": "{\"path\": \"a.txt\"}"}}]}}]}

        (self.work / "a.txt").write_text("conteudo", encoding="utf-8")
        with patch.object(agent, "print", lambda *a, **k: None):
            agent.run(self.work, "edite", always_tools, emit=lambda m: None, max_steps=1)
        session_path = sorted((self.work / agent.SESSIONS_DIRNAME).glob("session_*.json"))[0]
        data = json.loads(session_path.read_text(encoding="utf-8"))
        self.assertEqual(data["steps_used"], 1)
        content_blob = json.dumps(data, ensure_ascii=False)
        self.assertIn("conteudo", content_blob)


class AiResumeTests(unittest.TestCase):
    """A camada de menu (ai.py) oferece retomada quando o limite é atingido."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        import os
        os.environ["READROID_HOME"] = str(Path(self.tmp.name) / "rd")
        import importlib

        import readroid.ai as ai
        self.ai = importlib.reload(ai)
        self.work = Path(self.tmp.name) / "app_apktool"
        self.work.mkdir()

    def tearDown(self):
        import os
        os.environ.pop("READROID_HOME", None)
        self.tmp.cleanup()

    def test_oferta_de_retomada_apos_limite(self):
        def fake_agent(*args, **kwargs):
            return {"ok": False, "limit_reached": True, "steps": 60,
                    "session_id": "20260101_000000", "message": "limite"}

        def fake_resume(ui, decoded, res):
            fake_resume.called = True

        fake_resume.called = False
        with patch.object(self.ai, "run_gateway_agent", fake_agent), \
                patch.object(self.ai, "_offer_resume", fake_resume):
            res = self.ai.run_gateway_agent(self.work, "edite")
        self.assertFalse(res["ok"])
        self.assertTrue(res.get("session_id"))

    def test_run_gateway_agent_passa_session_id(self):
        self.ai.configure("gw-" + "k" * 30, "m", self.ai.PROVIDER_GATEWAY, "https://g.dev")
        seen = {}

        def fake_run(workdir, instruction, request, emit=print, animate=None, max_steps=0,
                     read_only=False, dry_run=False, session_id=None):
            seen["session_id"] = session_id
            return {"ok": True, "message": "ok"}

        import readroid.agent as agent_module
        with patch.object(agent_module, "run", fake_run):
            self.ai.run_gateway_agent(self.work, "edite", session_id="20260101_000000")
        self.assertEqual(seen["session_id"], "20260101_000000")

    def test_menu_ia_tem_opcao_de_retomada(self):
        import io
        from contextlib import redirect_stdout

        import readroid.app as app
        app.safe_input = lambda prompt="": "0"
        buffer = io.StringIO()
        with redirect_stdout(buffer):
            self.ai._menu_loop(app)
        text = buffer.getvalue()
        self.assertIn("Retomar tarefa", text)


if __name__ == "__main__":
    unittest.main()
