"""Testes da identidade visual Cyber UI (v0.5.0): layout adaptativo e componentes."""

import io
import os
import re
import sys
import unittest
from contextlib import redirect_stdout
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from readroid import banner, ui

_ANSI = re.compile("\x1b" + re.escape("[") + "[0-9;]*m")


def plain(text: str) -> str:
    return _ANSI.sub("", text)


class PaletteTests(unittest.TestCase):
    def test_paleta_oficial_em_256_cores(self):
        self.assertEqual(ui.YELLOW, "\033[38;5;220m")
        self.assertEqual(ui.CYAN, "\033[38;5;44m")
        self.assertEqual(ui.GREEN, "\033[38;5;35m")
        self.assertEqual(ui.RED, "\033[38;5;196m")
        self.assertEqual(ui.GRAY, "\033[38;5;245m")

    def test_simbolos_padronizados(self):
        self.assertEqual(ui.OK, "[OK]")
        self.assertEqual(ui.OFF, "[OFF]")
        self.assertEqual(ui.WARN, "[!]")
        self.assertEqual(ui.ERROR, "[ERROR]")

    def test_status_verde_vermelho_e_atencao(self):
        self.assertIn("[OK]", plain(ui.status(True)))
        self.assertIn("[ERROR]", plain(ui.status(False)))
        self.assertIn("[!]", plain(ui.status(None)))

    def test_message_kinds(self):
        self.assertIn("[OK]", plain(ui.message("tudo certo", "ok")))
        self.assertIn("[!]", plain(ui.message("cuidado", "warn")))
        self.assertIn("[ERROR]", plain(ui.message("falhou", "error")))
        self.assertIn("info", plain(ui.message("info")))


class BannerTests(unittest.TestCase):
    def test_cyber_subtitle_present(self):
        text = plain("\n".join(banner.render(70)))
        self.assertIn("ANDROID REVERSE ENGINEERING", text)
        self.assertIn("CYBER ANALYSIS PLATFORM", text)

    def test_compacto_em_36_colunas(self):
        lines = banner.render(36)
        self.assertEqual(len(lines), 1)
        self.assertIn("ReaDroid", plain(lines[0]))


class AppMenuTests(unittest.TestCase):
    def setUp(self):
        import readroid.app as app
        self.app = app
        self.out = io.StringIO()

    def test_layout_expandido_78_colunas(self):
        with patch.object(self.app.shutil, "get_terminal_size", lambda fallback=None: os.terminal_size((78, 24))):
            with redirect_stdout(self.out):
                self.app.print_menu()
        text = self.out.getvalue()
        self.assertIn("SYSTEM", text)
        self.assertIn("MENU", text)
        # as duas bordas ficam na mesma linha (lado a lado)
        first_row = text.splitlines()[0]
        self.assertIn("┌", first_row)
        self.assertEqual(first_row.count("┌"), 2)

    def test_layout_compacto_36_colunas(self):
        with patch.object(self.app.shutil, "get_terminal_size", lambda fallback=None: os.terminal_size((36, 24))):
            with redirect_stdout(self.out):
                self.app.print_menu()
        text = self.out.getvalue()
        self.assertIn("SYSTEM", text)
        self.assertIn("MENU", text)
        # no compacto, cada painel vem inteiro numa coluna: SYSTEM primeiro
        self.assertLess(text.index("SYSTEM"), text.index("MENU"))

    def test_nenhuma_linha_passa_da_largura(self):
        for cols in (32, 36, 50, 64, 78):
            with self.subTest(cols=cols):
                buffer = io.StringIO()
                with patch.object(self.app.shutil, "get_terminal_size", lambda fallback=None: os.terminal_size((cols, 24))):
                    with redirect_stdout(buffer):
                        self.app.print_menu()
                for line in buffer.getvalue().splitlines():
                    self.assertLessEqual(self.app.vwidth(line), cols, line)

    def test_menu_mostra_secoes_e_todas_as_opcoes(self):
        items = plain("\n".join(self.app._menu_items()))
        for section in ("ANÁLISE APK", "ENGENHARIA REVERSA", "SEGURANÇA E BUILD",
                        "RELATÓRIOS", "INTELIGÊNCIA ARTIFICIAL", "CONFIGURAÇÕES"):
            self.assertIn(section, items)
        for key in ("1", "2", "3", "4", "5", "6", "7", "8", "9", "10",
                    "11", "12", "13", "14", "15", "16", "17", "18", "19", "0"):
            self.assertRegex(items, rf"(?m)^\s*{key}\s+—")

    def test_system_items_so_estados_reais(self):
        items = plain("\n".join(self.app._system_items()))
        self.assertIn("[OK]", items)
        self.assertIn("[OFF]", items)
        self.assertIn("IA", items)

    def test_banner_header_tem_plataforma_e_rede(self):
        buffer = io.StringIO()
        with patch.object(self.app, "clear", lambda: None), redirect_stdout(buffer):
            self.app.banner()
        text = plain(buffer.getvalue())
        from readroid import __version__
        self.assertIn("v" + __version__, text)
        self.assertIn(self.app.detect_platform(), text)
        self.assertTrue("Online" in text or "Offline" in text, text)
        self.assertIn("IA:", text)


class AiMenuTests(unittest.TestCase):
    def test_menu_de_ia_tem_todas_as_acoes(self):
        import tempfile
        os.environ["READROID_HOME"] = tempfile.mkdtemp()
        import readroid.ai as ai
        import readroid.app as app
        app.safe_input = lambda prompt="": "0"
        buffer = io.StringIO()
        with redirect_stdout(buffer):
            ai._menu_loop(app)
        text = plain(buffer.getvalue())
        for expected in ("Abrir o assistente", "Resumir o app", "Cruzar relatórios",
                         "Editar com a IA", "Recriar um trecho", "Explicar um erro",
                         "Pergunta livre", "Testar / diagnosticar", "Prompts prontos",
                         "Backup", "Trocar modelo", "Limite de passos",
                         "Configurar provedor/chave", "Trocar provedor", "Desativar IA",
                         "Voltar"):
            self.assertIn(expected, text)


if __name__ == "__main__":
    unittest.main()
