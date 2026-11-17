"""Testes do layout do menu: nada estoura a largura nem perde uma opção."""
from __future__ import annotations

import io
import re
import sys
import unittest
from contextlib import redirect_stdout
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from readroid import app  # noqa: E402
from readroid import banner  # noqa: E402
from readroid import i18n  # noqa: E402

ANSI = re.compile(r"\x1b\[[0-9;]*[a-zA-Z]")


def render_all(cols: int) -> list[str]:
    original = app.width
    app.width = lambda: max(32, min(cols, 78))
    try:
        buf = io.StringIO()
        with redirect_stdout(buf):
            app.print_menu()
        return [ANSI.sub("", line) for line in buf.getvalue().splitlines()]
    finally:
        app.width = original


class MenuLayoutTests(unittest.TestCase):
    def setUp(self):
        # O idioma ativo é global; fixamos pt em memória e nunca gravamos a
        # configuração real do usuário durante o teste.
        self._lang = i18n._language
        i18n._language = "pt"

    def tearDown(self):
        i18n._language = self._lang

    def test_nenhuma_linha_estoura_a_largura(self):
        for cols in range(24, 121):
            width = max(32, min(cols, 78))
            for line in render_all(cols):
                # Largura visual: acentos e marcas combinantes não ocupam coluna.
                self.assertLessEqual(app.used_width(line), width,
                                     f"cols={cols}: {line!r}")

    def test_todas_as_opcoes_aparecem_sem_corte(self):
        for cols in (44, 60, 78):
            text = "\n".join(render_all(cols))
            for key, label in app._menu_entries().items():
                self.assertIn(label, text, f"cols={cols}: opção {key} ausente")

    def test_zero_sai_e_fica_fora_dos_grupos(self):
        text = "\n".join(render_all(60))
        self.assertIn(" 0  ", text)
        self.assertTrue(text.rstrip().endswith("┘"))

    def test_caixa_fecha_mesmo_em_tela_estreita(self):
        lines = [l for l in render_all(24) if l.strip()]
        self.assertTrue(lines[0].startswith("┌"))
        self.assertTrue(lines[-1].endswith("┘"))


class BannerLayoutTests(unittest.TestCase):
    def test_wordmark_cabe_em_tela_small(self):
        self.assertLessEqual(banner.big_width(), 40)

    def test_blocos_solidos_e_5_linhas(self):
        lines = banner.render(60, ("", "", ""))
        art = [ANSI.sub("", l).strip() for l in lines if ANSI.sub("", l).strip()]
        art = [l for l in art if l]
        self.assertEqual(len(art), 5)
        self.assertTrue(set("".join(art)) <= {"█", " "})

    def test_estreito_vira_uma_linha(self):
        lines = banner.render(30, ("", "", ""))
        self.assertEqual(len(lines), 1)
        self.assertIn("ReaDroid", lines[0])


if __name__ == "__main__":
    unittest.main()
