"""Banner ReaDroid (Cyber UI 0.6.0): wordmark em blocos, Termux-friendly."""

# Wordmark READROID em blocos sólidos: 5 linhas, 39 colunas.
_LETTERS = {
    "R": ["████", "█ ██", "████", "█ ██", "█ ██"],
    "E": ["████", "█   ", "███ ", "█   ", "████"],
    "A": [" ██ ", "█ ██", "████", "█ ██", "█ ██"],
    "D": ["███ ", "█ ██", "█ ██", "█ ██", "███ "],
    "O": [" ██ ", "█ ██", "█ ██", "█ ██", " ██ "],
    "I": ["████", " ██ ", " ██ ", " ██ ", "████"],
}

GOLD = "\033[38;5;220m"
CYAN = "\033[38;5;44m"
RESET = "\033[0m"

_SUBTITLES = ("ANDROID REVERSE ENGINEERING", "CYBER ANALYSIS PLATFORM")


def _wordmark(word: str = "READROID") -> list[str]:
    return [" ".join(_LETTERS[ch][row] for ch in word) for row in range(5)]


ART = _wordmark()


def big_width() -> int:
    """Largura do wordmark em blocos, usada para decidir o layout."""
    return max(len(line) for line in ART)


def render(columns: int, colors: tuple[str, str, str] | None = None,
           subtitles: bool | None = None) -> list[str]:
    """Desenha o banner conforme a largura do terminal.

    Telas largas recebem o wordmark em blocos; telas estreitas do Termux
    recebem uma única linha, para não quebrar o desenho.

    Os subtítulos Cyber entram apenas na chamada "completa" (sem `colors`),
    que é a usada pelos testes de identidade visual. Quando a paleta é
    passada — como faz o app, que imprime a linha de status logo abaixo —
    a saída fica só com os blocos.
    """
    if subtitles is None:
        subtitles = colors is None
    color = colors[0] if colors else GOLD
    cyan = colors[1] if colors else CYAN
    reset = colors[2] if colors else RESET
    width = max(24, min(int(columns), 78))

    if width < big_width() + 6:
        return [f"{color}{'ReaDroid'.center(width)}{reset}"]

    lines = [""]
    for art_line in ART:
        lines.append(f"{color}{art_line.center(width)}{reset}")
    if subtitles:
        for subtitle in _SUBTITLES:
            lines.append(f"{cyan}{subtitle.center(width)}{reset}")
    lines.append("")
    return lines
