"""Compact, bold ReaDroid terminal banner (solid blocks, Termux-friendly)."""

# Wordmark READROID em blocos sólidos: 5 linhas, 39 colunas.
_LETTERS = {
    "R": ["████", "█ ██", "████", "█ ██", "█ ██"],
    "E": ["████", "█   ", "███ ", "█   ", "████"],
    "A": [" ██ ", "█ ██", "████", "█ ██", "█ ██"],
    "D": ["███ ", "█ ██", "█ ██", "█ ██", "███ "],
    "O": [" ██ ", "█ ██", "█ ██", "█ ██", " ██ "],
    "I": ["████", " ██ ", " ██ ", " ██ ", "████"],
}


def _wordmark(word: str = "READROID") -> list[str]:
    return [" ".join(_LETTERS[ch][row] for ch in word) for row in range(5)]


ART = _wordmark()
GOLD = "\033[38;5;220m"


def big_width() -> int:
    """Largura do wordmark em blocos, usada para decidir o layout."""
    return max(len(line) for line in ART)


def render(columns: int, colors: tuple[str, str, str]) -> list[str]:
    """Desenha o banner conforme a largura do terminal.

    Telas largas recebem o wordmark em blocos; telas estreitas do Termux
    recebem uma única linha, para não quebrar o desenho.
    """
    color, _cyan, reset = colors
    width = max(24, min(int(columns), 78))

    if width < big_width() + 6:
        return [f"{color}{'ReaDroid'.center(width)}{reset}"]

    lines = [""]
    for art_line in ART:
        lines.append(f"{color}{art_line.center(width)}{reset}")
    lines.append("")
    return lines
