"""Testes da biblioteca de prompts prontos."""
from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from readroid import prompts


class PromptLibraryTests(unittest.TestCase):
    def test_ids_unicos_e_campos_obrigatorios(self):
        ids = [item["id"] for item in prompts.PROMPTS]
        self.assertEqual(len(ids), len(set(ids)))
        for item in prompts.PROMPTS:
            self.assertTrue(item["titulo"].strip())
            self.assertTrue(item["descricao"].strip())
            self.assertGreater(len(item["prompt"]), 40)

    def test_todas_as_categorias_existem(self):
        for item in prompts.PROMPTS:
            self.assertIn(prompts.category_of(item["id"]), prompts.CATEGORIES)

    def test_agrupamento_cobre_todos_os_prompts(self):
        grouped = prompts.grouped()
        total = sum(len(items) for items in grouped.values())
        self.assertEqual(total, len(prompts.PROMPTS))

    def test_prompts_de_risco_tem_aviso(self):
        for prompt_id in ("desbloquear_vip", "remover_anuncios", "remover_verificacao_licenca",
                          "certificate_pinning"):
            item = prompts.by_id(prompt_id)
            self.assertIsNotNone(item)
            self.assertTrue(item.get("aviso"), prompt_id)

    def test_prompts_de_edicao_protegem_apktool(self):
        for item in prompts.PROMPTS:
            if prompts.category_of(item["id"]) in ("recursos", "rede", "interface"):
                self.assertIn("apktool", item["prompt"].lower() + " apktool.yml", item["id"])

    def test_by_id_desconhecido(self):
        self.assertIsNone(prompts.by_id("nao_existe"))

    def test_needs_input(self):
        self.assertTrue(prompts.needs_input("explicar_crash"))
        self.assertFalse(prompts.needs_input("traduzir_interface"))

    def test_prompts_de_diagnostico_sao_somente_leitura(self):
        for prompt_id in ("explicar_crash", "revisar_permissoes", "mapear_fluxo"):
            self.assertTrue(prompts.is_read_only(prompt_id), prompt_id)

    def test_prompts_de_edicao_nao_sao_somente_leitura(self):
        for prompt_id in ("traduzir_interface", "tema_escuro", "desbloquear_vip"):
            self.assertFalse(prompts.is_read_only(prompt_id), prompt_id)

    def test_read_only_desconhecido_e_falso(self):
        self.assertFalse(prompts.is_read_only("nao_existe"))


if __name__ == "__main__":
    unittest.main()
