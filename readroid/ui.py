"""Identidade visual do ReaDroid (Cyber UI v0.5.0).

Centraliza cores, símbolos de estado e desenho de componentes reutilizáveis.
Nada aqui depende de bibliotecas externas; tudo é ANSI puro compatível com Termux.

Regras da paleta oficial:
- amarelo (#FFD21F) para marca, títulos e destaques;
- ciano (#20D9E8) para menus, navegação e informação técnica;
- verde (#22C55E) para sucesso;
- vermelho (#EF4444) para erro;
- cinza (#A1A1AA) para informação secundária;
- texto principal (#E5E7EB).
"""

from __future__ import annotations

# Cores ANSI: 256-color approximations das cores hex da identidade.
YELLOW = "\033[38;5;220m"      # marca/títulos (#FFD21F)
CYAN = "\033[38;5;44m"         # menus/técnico (#20D9E8)
GREEN = "\033[38;5;35m"        # sucesso (#22C55E)
RED = "\033[38;5;196m"         # erro (#EF4444)
GRAY = "\033[38;5;245m"        # secundário (#A1A1AA)
TEXT = "\033[38;5;253m"        # texto principal (#E5E7EB)
RESET = "\033[0m"
BOLD = "\033[1m"
DIM = "\033[2m"

# Símbolos padronizados de estado (texto puro, sem emoji).
OK = "[OK]"
OFF = "[OFF]"
WARN = "[!]"
ERROR = "[ERROR]"


def status(ok: bool | None, label_ok: str | None = None, label_off: str | None = None) -> str:
    """Símbolo de estado colorido para uma checagem.

    `True` fica verde (ou label_ok), `False` vermelho (ou label_off) e
    `None` (desconhecido) usa label_off em amarelo quando informado —
    assim "Rede: Offline" aparece como estado, não como erro.
    """
    if ok is True:
        return GREEN + (label_ok or OK) + RESET
    if label_off:
        return (RED if ok is False else YELLOW) + label_off + RESET
    if ok is False:
        return RED + ERROR + RESET
    return YELLOW + WARN + RESET


def rule(width: int, color: str = GRAY) -> str:
    """Linha horizontal discreta."""
    return color + "─" * max(10, width) + RESET


def header_line(version: str, platform: str, ai_state: str, tools_state: str) -> str:
    """Linha única de status sob o título: versão, plataforma, IA e ferramentas."""
    parts = [f"v{version}", platform, f"IA:{ai_state}", f"Ferram:{tools_state}"]
    return GRAY + " · ".join(parts) + RESET


def section(title: str) -> str:
    """Título de seção em amarelo com marca de seta."""
    return BOLD + YELLOW + "▸ " + str(title).upper() + RESET


def message(text: str, kind: str = "info") -> str:
    """Mensagem padronizada: info, ok, warn, error."""
    if kind == "ok":
        return GREEN + OK + RESET + " " + text
    if kind == "warn":
        return YELLOW + WARN + RESET + " " + text
    if kind == "error":
        return RED + ERROR + RESET + " " + text
    return CYAN + "·" + RESET + " " + text
