"""Interface de terminal do ReaDroid. Mantemos o menu simples para telas pequenas."""
from __future__ import annotations

import builtins as _builtins
import os
import re
import shutil
import subprocess
import sys
from collections.abc import Callable
from datetime import datetime
from pathlib import Path

from . import __version__
from .banner import render as render_banner
from .i18n import LANGUAGES, get_language, set_language, tr


# Translate static and known UI phrases consistently, including messages that
# include ANSI colors or interpolated paths/counts.
def print(*args, **kwargs):
    _builtins.print(*(tr(arg) if isinstance(arg, str) else arg for arg in args), **kwargs)
from . import cache, checks, compare, history, obfuscation, outputs, report, updater
from .analyzer import (
    analyze_manifest,
    decompile_with_jadx,
    extension_warning,
    extract_smali_with_apktool,
    inspect_apk,
    scan_strings,
    sha256_file,
    write_report,
)
from .builder import (
    DEFAULT_ALIAS,
    DEFAULT_STOREPASS,
    QUICK_EDITS,
    apply_quick_edits,
    build_pipeline,
    rename_package,
    valid_package_name,
)

# Usa a pasta desta cópia do projeto, não uma pasta fixa em ~/ReaDroid.
# Isso evita salvar os resultados em outro lugar quando o projeto foi extraído
# em Downloads ou executado a partir de um clone do GitHub.
BASE = Path(__file__).resolve().parents[1]
REPORTS = BASE / "reports"
OUTPUTS = BASE / "output"
BUILDS = BASE / "builds"
KEYSTORE = BASE / ".readroid-keystore.jks"

from . import ui as _ui

# Aliases de cor mantidos para todo o codigo existente (agora com a paleta Cyber oficial).
GREEN, CYAN, YELLOW, RED, DIM, RESET, BOLD = _ui.GREEN, _ui.CYAN, _ui.YELLOW, _ui.RED, _ui.DIM, _ui.RESET, _ui.BOLD
GOLD = _ui.YELLOW

# Remove sequências de escape ANSI e caracteres de controle antes de imprimir qualquer
# dado que veio de dentro de um APK (strings, nomes de arquivo, saída de ferramentas).
# Sem isso, um APK malicioso poderia manipular as cores/o cursor do seu terminal.
_CTRL_RE = re.compile(r"\x1b\[[0-9;]*[a-zA-Z]|[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]")


def sanitize(text: str) -> str:
    return _CTRL_RE.sub("", str(text))


def clear() -> None:
    os.system("clear" if os.environ.get("TERM") else "")


def width() -> int:
    return max(32, min(shutil.get_terminal_size((44, 24)).columns, 78))


# Largura visual de uma linha: ignora sequências ANSI (cores) e conta o resto
# por célula de terminal (wcwidth), para o layout não vazar em telas estreitas.
_ANSI_RE = re.compile(r"\x1b\[[0-9;?]*[a-zA-Z]|\x1b\][^\x07]*\x07")


def vwidth(line: str) -> int:
    return wcswidth(_ANSI_RE.sub("", str(line)))


def detect_platform() -> str:
    if sys.platform.startswith("win"):
        return "Windows"
    if sys.platform == "darwin":
        return "macOS"
    if os.path.isdir("/data/data/com.termux"):
        return "Termux"
    if sys.platform.startswith("linux"):
        return "Linux"
    return sys.platform


_NETWORK_CACHE: tuple[float, bool] = (0.0, False)


def network_state() -> str:
    """Estado da rede com cache de 60s: 'Online' ou 'Offline'."""
    global _NETWORK_CACHE
    import time
    import urllib.request
    now = time.monotonic()
    cached_at, cached_state = _NETWORK_CACHE
    if now - cached_at < 60:
        return "Online" if cached_state else "Offline"
    state = False
    try:
        urllib.request.urlopen("https://github.com", timeout=3).close()
        state = True
    except OSError:
        state = False
    _NETWORK_CACHE = (now, state)
    return "Online" if state else "Offline"


def tools_state() -> str:
    return "OK" if shutil.which("apktool") else "--"


def banner() -> None:
    clear()
    cols = width()
    for line in render_banner(cols, (GOLD, CYAN, RESET)):
        print(line)
    print(_ui.header_line(__version__, detect_platform(),
                          "OK" if ai_available() else "--", tools_state()))
    print(DIM + tr("IA opcional · Sem root · Offline por padrão")
          + " · " + network_state() + RESET)


_PASTE_RE = re.compile(r"\x1b\[[0-9;?]*[~a-zA-Z]|\[20[01]~|[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]"
                       r"|[\u200b-\u200f\u202a-\u202e\u2060\ufeff]")


def clean_path(raw: str) -> str:
    """Limpa o caminho digitado/colado: remove sequências de 'colar' do terminal (ESC[200~),
    caracteres invisíveis, espaços e aspas nas pontas. Colar no Termux às vezes traz lixo invisível."""
    return _PASTE_RE.sub("", raw).strip().strip('"').strip("'").strip()


def safe_input(prompt: str = "") -> str:
    """input() que não derruba o menu com traceback se o terminal fechar (Ctrl+D/Ctrl+C)."""
    try:
        return input(tr(prompt))
    except (EOFError, KeyboardInterrupt):
        print()
        return ""


def pause() -> None:
    safe_input("\nENTER para voltar ao menu...")


def ask_apk() -> Path | None:
    # Para deixar o fluxo mais rápido no celular, tentamos encontrar APKs nas pastas comuns.
    candidates: list[Path] = []
    search_dirs = [Path.cwd(), Path.home() / "storage" / "downloads",
                   Path.home() / "storage" / "shared" / "Download",
                   Path.home() / "storage" / "shared" / "Documents",
                   Path("/storage/emulated/0/Download")]
    seen: set[str] = set()
    for folder in search_dirs:
        if not folder.is_dir():
            continue
        try:
            for item in sorted(folder.iterdir(), key=lambda p: p.stat().st_mtime, reverse=True):
                if (item.is_file() and item.suffix.lower() in (".apk", ".apks", ".xapk")
                        and str(item) not in seen):
                    candidates.append(item)
                    seen.add(str(item))
        except OSError:
            # Uma pasta sem permissão não deve impedir o uso das demais.
            continue
    candidates = candidates[:20]
    if candidates:
        print(CYAN + tr("APKs encontrados nas pastas comuns:") + RESET)
        for index, item in enumerate(candidates, 1):
            try:
                size_mb = item.stat().st_size / (1024 * 1024)
                print(f" [{index}] {sanitize(item.name)} ({size_mb:.1f} MB)")
            except OSError:
                print(f" [{index}] {sanitize(item.name)}")
        print(" [P] Informar outro caminho")
        choice = safe_input(tr("Escolha um APK: ")).strip()
        if choice.lower() != "p":
            try:
                return candidates[int(choice) - 1]
            except (ValueError, IndexError):
                print(YELLOW + tr("Seleção não reconhecida; informe o caminho manualmente.") + RESET)
    raw = clean_path(safe_input(tr("Caminho completo do APK: ")))
    if not raw:
        print(YELLOW + tr("Nenhum arquivo informado.") + RESET)
        return None
    path = Path(raw).expanduser()
    if not path.is_absolute():
        path = Path.cwd() / path
    if not path.exists() or not path.is_file():
        print(RED + tr("Arquivo não encontrado.") + " Dica: execute termux-setup-storage e use ~/storage/shared/Download/app.apk" + RESET)
        print(DIM + f"Caminho lido pelo ReaDroid: {str(path)!r}" + RESET)
        return None
    warning = extension_warning(path)
    if warning:
        print(YELLOW + warning + RESET)
    return path


def ask_decoded_dir() -> Path | None:
    """Lista pastas já decodificadas pelo Apktool (opção 5) e deixa escolher ou digitar outra."""
    OUTPUTS.mkdir(parents=True, exist_ok=True)
    candidates = sorted((p for p in OUTPUTS.glob("*_apktool") if p.is_dir()),
                        key=lambda p: p.stat().st_mtime, reverse=True)[:15]
    if candidates:
        print(CYAN + "Pastas decodificadas com Apktool:" + RESET)
        for index, item in enumerate(candidates, 1):
            print(f" [{index}] {sanitize(item.name)}")
        print(" [P] Informar outro caminho")
        choice = safe_input("Escolha a pasta: ").strip()
        if choice.lower() != "p":
            try:
                return candidates[int(choice) - 1]
            except (ValueError, IndexError):
                print(YELLOW + tr("Seleção não reconhecida; informe o caminho manualmente.") + RESET)
    raw = clean_path(safe_input("Caminho da pasta decodificada (saída do Apktool): "))
    if not raw:
        return None
    path = Path(raw).expanduser()
    if not path.is_dir():
        print(RED + "Pasta não encontrada." + RESET)
        print(DIM + f"Caminho lido pelo ReaDroid: {str(path)!r}" + RESET)
        return None
    return path


def save_and_show(report: dict, prefix: str, apk: Path) -> None:
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    target = REPORTS / f"{apk.stem}_{prefix}_{stamp}.json"
    write_report(report, target)
    print(GREEN + f"\nRelatório salvo: {target}" + RESET)


def cached_report(kind: str, apk: Path, compute: Callable[[], dict]) -> dict:
    """Reaproveita o resultado de uma análise já feita para o mesmo conteúdo (SHA-256)."""
    try:
        digest = sha256_file(apk)
    except OSError:
        return compute()
    data, hit = cache.cached(REPORTS, kind, digest, compute)
    if hit:
        print(DIM + "Resultado reaproveitado do cache (mesmo SHA-256 do APK)." + RESET)
    return data


def write_summary_for(apk: Path) -> Path | None:
    """Gera reports/<app>_resumo.md com uma explicação em linguagem simples."""
    try:
        inspection = cached_report("inspect", apk, lambda: inspect_apk(apk))
        manifest = cached_report("manifest", apk, lambda: analyze_manifest(apk, OUTPUTS / (apk.stem + "_manifest_work")))
        strings = cached_report("strings", apk, lambda: scan_strings(apk))
    except Exception as exc:  # um APK estranho não deve derrubar o menu
        print(RED + f"Não foi possível montar o resumo: {exc}" + RESET)
        return None
    text = report.build_summary(manifest, strings, inspection, app_name=apk.stem)
    target = REPORTS / f"{apk.stem}_resumo.md"
    try:
        report.write_summary(target, text)
    except OSError as exc:
        print(RED + f"Não foi possível gravar o resumo: {exc}" + RESET)
        return None
    return target


def run_action(title: str, action: Callable[[Path], dict]) -> None:
    print(CYAN + f"\n{title}" + RESET)
    apk = ask_apk()
    if apk is None:
        return
    try:
        report = action(apk)
        save_and_show(report, title.lower().replace(" ", "_"), apk)
        for warning in report.get("warnings", []):
            print(YELLOW + warning + RESET)
        if "permissions" in report:
            print(f"Permissões encontradas: {len(report.get('permissions', []))}")
            for item in report.get("permissions", [])[:25]:
                print(" •", sanitize(item.get("name", "")))
            if not report.get("decoded"):
                print(YELLOW + "Manifesto não decodificado. Veja a mensagem no relatório." + RESET)
        if "urls" in report:
            print(f"URLs: {len(report['urls'])} | Domínios: {len(report['domains'])} | IPs candidatos: {len(report['ipv4_candidates'])}")
            if report.get("truncated_categories"):
                print(YELLOW + f"Atenção: categorias truncadas (limite atingido): {', '.join(report['truncated_categories'])}" + RESET)
        if "zip_entry_count" in report:
            print(f"Arquivos: {report['zip_entry_count']} | DEX: {len(report['dex_files'])} | Bibliotecas nativas: {len(report['native_libraries'])}")
            hint = obfuscation.detect(apk)
            if hint.get("message"):
                color = YELLOW if hint.get("obfuscated") else DIM
                print(color + hint["message"] + RESET)
    except Exception as exc:  # O menu não deve fechar por um erro inesperado de um arquivo.
        print(RED + f"A análise falhou: {exc}" + RESET)
        print("O arquivo original não foi modificado.")


def dependencies() -> None:
    print(CYAN + "\nVERIFICAÇÃO DE DEPENDÊNCIAS" + RESET)
    for name in ("python", "java", "jadx", "apktool", "aapt", "aapt2", "zipalign", "apksigner", "keytool", "unzip", "git", "opencode"):
        path = shutil.which(name)
        print(f"[{GREEN + 'OK' + RESET if path else YELLOW + '--' + RESET}] {name}: {path or 'não encontrado'}")
    if shutil.which("java"):
        try:
            result = subprocess.run(["java", "-version"], capture_output=True, text=True, timeout=5)
            print(sanitize((result.stderr or result.stdout).splitlines()[0]))
        except (OSError, subprocess.TimeoutExpired, IndexError):
            print("Java encontrado, mas não foi possível consultar a versão.")
    if shutil.which("jadx"):
        try:
            result = subprocess.run(["jadx", "--version"], capture_output=True, text=True, timeout=8)
            print("JADX:", sanitize((result.stdout or result.stderr).strip().splitlines()[0]))
        except (OSError, subprocess.TimeoutExpired, IndexError):
            print("JADX localizado; versão não confirmada.")
    print(CYAN + "\nPara reconstruir e assinar APKs (opção 11):" + RESET)
    print(" pkg install apktool aapt apksigner openjdk-21")
    print(" (aapt já inclui o zipalign; apksigner dá assinatura v1+v2+v3;")
    print("  sem ele, cai para jarsigner, que só assina v1.)")


def open_folder(path: Path) -> None:
    path.mkdir(parents=True, exist_ok=True)
    print("Pasta:", path)
    print("Conteúdo:")
    items = list(path.iterdir())
    if not items:
        print(" (vazia por enquanto)")
    for item in sorted(items, key=lambda p: p.name.lower())[:60]:
        print(" [DIR]" if item.is_dir() else " [FILE]", sanitize(item.name))


TEXT_EXTENSIONS = {
    ".java", ".kt", ".smali", ".xml", ".json", ".txt", ".md", ".html",
    ".js", ".css", ".properties", ".yml", ".yaml", ".gradle", ".pro",
    ".cfg", ".ini", ".log", ".sh", ".py", ".manifest"
}


def view_text_file(path: Path) -> None:
    """Abre arquivos de texto no próprio terminal, com paginação quando disponível."""
    try:
        if path.stat().st_size > 5 * 1024 * 1024:
            print(YELLOW + "Arquivo grande (>5 MB); não será carregado inteiro na tela." + RESET)
            print("Caminho:", path)
            return
        content = path.read_text(encoding="utf-8", errors="replace")
        clean = sanitize(content)
        less = shutil.which("less")
        if less:
            # Sem -R: não interpretamos códigos de escape do arquivo, só mostramos como texto.
            # Um arquivo decompilado/extraído é conteúdo não confiável.
            subprocess.run([less], input=clean, text=True, check=False)
            return
        lines = clean.splitlines()
        page_size = 120
        for start in range(0, max(1, len(lines)), page_size):
            print("\n".join(lines[start:start + page_size]))
            if start + page_size < len(lines):
                answer = safe_input("\nENTER para próxima página, q para sair: ").strip().lower()
                if answer == "q":
                    break
        if not lines:
            print("(arquivo vazio)")
    except (OSError, UnicodeError) as exc:
        print(RED + f"Não foi possível abrir o arquivo: {exc}" + RESET)


def browse_directory(path: Path, allowed_roots: tuple[Path, ...]) -> None:
    """Navegador simples: seleciona diretórios e abre arquivos pelo número."""
    current = path.resolve()
    roots = tuple(root.resolve() for root in allowed_roots)
    while True:
        print(CYAN + f"\nExplorador ReaDroid: {current}" + RESET)
        try:
            entries = sorted(current.iterdir(), key=lambda p: (not p.is_dir(), p.name.lower()))
        except OSError as exc:
            print(RED + f"Não foi possível listar a pasta: {exc}" + RESET)
            return
        if not entries:
            print(" (pasta vazia)")
        for index, item in enumerate(entries, 1):
            kind = "[DIR] " if item.is_dir() else "[ARQ] "
            try:
                size = f" ({item.stat().st_size / 1024:.1f} KB)" if item.is_file() else "/"
            except OSError:
                size = ""
            print(f" [{index}] {kind}{sanitize(item.name)}{size}")
        print(" [..] Voltar uma pasta | [0] Sair do explorador")
        choice = safe_input("Abrir > ").strip().lower()
        if choice in {"0", "q", "sair", ""}:
            return
        if choice in {"..", "p", "voltar"}:
            if current in roots:
                return
            parent = current.parent.resolve()
            if not any(parent == root or root in parent.parents for root in roots):
                return
            current = parent
            continue
        try:
            selected = entries[int(choice) - 1].resolve()
        except (ValueError, IndexError):
            print(YELLOW + "Seleção inválida." + RESET)
            continue
        if not any(selected == root or root in selected.parents for root in roots):
            print(RED + "Caminho fora das pastas de resultados bloqueado." + RESET)
            continue
        if selected.is_dir():
            current = selected
        elif selected.is_file():
            if selected.suffix.lower() in TEXT_EXTENSIONS or selected.suffix == "":
                view_text_file(selected)
            elif shutil.which("termux-open"):
                print("Abrindo com o aplicativo Android associado...")
                result = subprocess.run([shutil.which("termux-open"), str(selected)], check=False)
                if result.returncode:
                    print("Não foi possível abrir externamente. Caminho:", selected)
            else:
                print("Não há termux-open instalado. Caminho do arquivo:", selected)
                print("Instale o pacote termux-tools para abrir arquivos no Android.")
            safe_input("\nENTER para voltar ao explorador...")


def browse_generated_files() -> None:
    """Permite localizar e abrir saídas do JADX/Apktool, builds e relatórios JSON."""
    OUTPUTS.mkdir(parents=True, exist_ok=True)
    REPORTS.mkdir(parents=True, exist_ok=True)
    BUILDS.mkdir(parents=True, exist_ok=True)
    while True:
        print(CYAN + "\nARQUIVOS GERADOS" + RESET)
        print(" [1] Código decompilado e recursos (output)")
        print(" [2] Relatórios JSON (reports)")
        print(" [3] APKs reconstruídos e assinados (builds)")
        print(" [0] Voltar ao menu principal")
        choice = safe_input("Explorar > ").strip()
        if choice == "0" or choice == "":
            return
        if choice == "1":
            browse_directory(OUTPUTS, (OUTPUTS, REPORTS, BUILDS))
        elif choice == "2":
            browse_directory(REPORTS, (OUTPUTS, REPORTS, BUILDS))
        elif choice == "3":
            browse_directory(BUILDS, (OUTPUTS, REPORTS, BUILDS))
        else:
            print(YELLOW + "Opção inválida." + RESET)


# ------------------------------------------------------------------ reconstrução e compilação

def prompt_rename_package(decoded: Path) -> None:
    """Pergunta o novo applicationId, valida e aplica. Usado nos dois fluxos
    (opção 10 isolada e dentro da opção 11, antes de reconstruir)."""
    print(DIM + "O pacote atual aparece no AndroidManifest.xml; isso move pastas smali" + RESET)
    print(DIM + "e troca as referências de classe - é melhor esforço, teste o resultado." + RESET)
    new_name = safe_input("Novo pacote (ex: com.exemplo.app) ou ENTER para pular: ").strip()
    if not new_name:
        return
    if not valid_package_name(new_name):
        print(RED + "Nome inválido. Use letras/números/'_' e pelo menos um ponto, ex: com.exemplo.app" + RESET)
        return
    result = rename_package(decoded, new_name)
    if result["ok"]:
        print(GREEN + result["message"] + RESET)
        if result["directories_moved"] or result["files_updated"]:
            print(f" {result['directories_moved']} pasta(s) de smali movida(s), "
                  f"{result['files_updated']} arquivo(s) atualizado(s).")
        if result.get("warning"):
            print(YELLOW + result["warning"] + RESET)
    else:
        print(RED + result["message"] + RESET)


def quick_edits_menu() -> None:
    decoded = ask_decoded_dir()
    if decoded is None:
        return
    keys = list(QUICK_EDITS)
    print(CYAN + "\nEdições rápidas disponíveis:" + RESET)
    for i, k in enumerate(keys, 1):
        print(f" [{i}] {QUICK_EDITS[k]}")
    choice = safe_input("Números separados por vírgula (ex: 1,3), ou ENTER para pular: ").strip()
    chosen = []
    for part in choice.split(","):
        part = part.strip()
        if part.isdigit() and 1 <= int(part) <= len(keys):
            chosen.append(keys[int(part) - 1])
    if chosen:
        result = apply_quick_edits(decoded, chosen)
        if result["ok"]:
            print(GREEN + "Aplicado: " + ", ".join(result["applied"]) + RESET)
            try:
                for item in result["applied"]:
                    history.add_edit(decoded, f"edição rápida: {item}")
            except OSError:
                pass  # o registro é conveniência; nunca deve impedir a edição
        else:
            print(RED + result["message"] + RESET)
    elif choice:
        print(YELLOW + "Nenhuma edição válida selecionada." + RESET)

    if safe_input("Renomear o pacote (applicationId) também? (s/N): ").strip().lower() == "s":
        prompt_rename_package(decoded)
    print("Quando terminar de editar, use a opção 11 para reconstruir, alinhar e assinar.")


def rebuild_and_sign() -> None:
    print(CYAN + "\nReconstrução e compilação automatizada" + RESET)
    print(YELLOW + "Use só em APKs seus ou que você tem autorização para modificar." + RESET)
    print(DIM + "Reassinar troca a identidade do desenvolvedor original; o resultado" + RESET)
    print(DIM + "não substitui o app da loja nem deve ser redistribuído sem permissão." + RESET)
    decoded = ask_decoded_dir()
    if decoded is None:
        return
    if not (decoded / "AndroidManifest.xml").is_file() or not (decoded / "apktool.yml").is_file():
        print(YELLOW + "Essa pasta não parece ser uma saída do Apktool (opção 5). Confira o caminho." + RESET)
        if safe_input("Continuar mesmo assim? (s/N): ").strip().lower() != "s":
            return

    edits: list[str] = []
    if safe_input("Aplicar alguma edição rápida antes de compilar? (s/N): ").strip().lower() == "s":
        keys = list(QUICK_EDITS)
        for i, k in enumerate(keys, 1):
            print(f" [{i}] {QUICK_EDITS[k]}")
        choice = safe_input("Números separados por vírgula: ").strip()
        for part in choice.split(","):
            part = part.strip()
            if part.isdigit() and 1 <= int(part) <= len(keys):
                edits.append(keys[int(part) - 1])

    if safe_input("Renomear o pacote (applicationId) antes de compilar? (s/N): ").strip().lower() == "s":
        prompt_rename_package(decoded)

    space = checks.check_disk_space(BUILDS, checks.estimate_build_space(decoded))
    if space.get("ok") is False:
        print(YELLOW + space["message"] + RESET)
        if safe_input("Continuar mesmo assim? (s/N): ").strip().lower() != "s":
            return
    elif space.get("ok"):
        print(DIM + space["message"] + RESET)

    sdk = checks.check_min_sdk(decoded)
    if sdk.get("message"):
        print((YELLOW if sdk.get("ok") is False else DIM) + sdk["message"] + RESET)

    name = decoded.name.replace("_apktool", "") or "app"
    work_dir = BUILDS / f"{name}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"

    def say(msg: str) -> None:
        print(CYAN + " · " + msg + RESET)

    result = build_pipeline(decoded, work_dir, KEYSTORE, DEFAULT_ALIAS, DEFAULT_STOREPASS, edits, say)
    steps = result["steps"]
    for name_step, label in (("quick_edits", "Edições"), ("rebuild", "Reconstrução (apktool b)"),
                             ("align", "Alinhamento (zipalign)"), ("keystore", "Chave de assinatura"),
                             ("sign", "Assinatura"), ("verify", "Verificação")):
        step = steps.get(name_step)
        if not step:
            continue
        ok = step.get("ok")
        mark = GREEN + "OK" + RESET if ok else (YELLOW + "pulado" + RESET if step.get("skipped") else RED + "falhou" + RESET)
        print(f" [{mark}] {label}")
        if step.get("message"):
            print("      " + step["message"])
        if step.get("warning"):
            print(YELLOW + "      " + step["warning"] + RESET)
        if not ok and step.get("stderr"):
            print(DIM + "      " + step["stderr"][-400:] + RESET)

    if result["ok"]:
        final = Path(result["final_apk"])
        print(GREEN + f"\nAPK pronto: {final}" + RESET)
        print("SHA256:", steps.get("sha256", "?"))
        show_comparison(decoded, final)
        # Cópia amigável para uma pasta fácil de achar no celular (escolhida por você).
        dest = choose_output_dir()
        if dest is not None:
            copied = outputs.copy_to_output(final, dest)
            if copied is not None:
                print(GREEN + f"{tr('Cópia em:')} {copied}" + RESET)
            else:
                print(YELLOW + f"Não foi possível copiar para {dest}; o APK continua em {final}." + RESET)
        if shutil.which("termux-open") and safe_input("Abrir o instalador do Android agora? (s/N): ").strip().lower() == "s":
            subprocess.run([shutil.which("termux-open"), str(final)], check=False)
    else:
        print(RED + "\nA reconstrução não terminou. Veja os passos acima." + RESET)


def show_comparison(decoded: Path, rebuilt: Path) -> None:
    """Compara o APK reconstruído com o original, quando o original é conhecido."""
    state = history.load_state(decoded)
    source = state.get("source_path")
    if not source:
        print(DIM + "Comparação indisponível: o APK original não está registrado nesta pasta." + RESET)
        print(DIM + "Extraia com a opção 5 para registrar a origem automaticamente." + RESET)
        return
    original = Path(str(source))
    if not original.is_file():
        print(DIM + f"Comparação indisponível: o APK original não está mais em {original}." + RESET)
        return
    try:
        result = compare.compare_apks(original, rebuilt)
    except (OSError, ValueError) as exc:
        print(YELLOW + f"Não foi possível comparar: {exc}" + RESET)
        return
    print(CYAN + "\nO que mudou em relação ao original:" + RESET)
    for line in compare.format_comparison(result):
        print(" " + sanitize(line))


def history_menu() -> None:
    print(CYAN + "\nHistórico de builds" + RESET)
    entries = history.load_history(BUILDS)
    if not entries:
        print(" Nenhuma reconstrução registrada ainda.")
        print(DIM + " O histórico começa a ser gravado na próxima vez que você usar a opção 11." + RESET)
        return
    for line in history.format_history(entries):
        print(" " + sanitize(line))
    print(DIM + f"\n Arquivo: {history.history_path(BUILDS)}" + RESET)
    if safe_input("\nComparar um APK reconstruído com o original? (s/N): ").strip().lower() != "s":
        return
    apks = sorted((p for p in BUILDS.rglob("*.apk") if p.is_file()),
                  key=lambda p: p.stat().st_mtime, reverse=True)[:15]
    if not apks:
        print(YELLOW + "Nenhum APK encontrado em builds/." + RESET)
        return
    for index, item in enumerate(apks, 1):
        print(f" [{index}] {sanitize(item.name)}")
    choice = safe_input("Escolha o APK reconstruído: ").strip()
    try:
        rebuilt = apks[int(choice) - 1]
    except (ValueError, IndexError):
        print(YELLOW + "Seleção inválida." + RESET)
        return
    decoded = ask_decoded_dir()
    if decoded is None:
        return
    show_comparison(decoded, rebuilt)


def summary_menu() -> None:
    print(CYAN + "\nResumo legível do app" + RESET)
    print(DIM + "Gera um arquivo .md explicando permissões, componentes expostos e endereços." + RESET)
    apk = ask_apk()
    if apk is None:
        return
    target = write_summary_for(apk)
    if target is None:
        return
    print(GREEN + f"\nResumo salvo: {target}" + RESET)
    if safe_input("Mostrar agora? (s/N): ").strip().lower() == "s":
        view_text_file(target)


def help_menu() -> None:
    print(CYAN + "\nAjuda rápida" + RESET)
    print(" 1-3  Analisar um APK sem alterar nada (estrutura, manifesto, endereços).")
    print(" 4-5  Extrair código e recursos para uma pasta de trabalho.")
    print(" 6    Conferir se apktool, java, apksigner e afins estão instalados.")
    print(" 7-9  Abrir relatórios, resultados e navegar pelos arquivos gerados.")
    print(" 10   Edições rápidas e renomear pacote (altera a pasta decodificada).")
    print(" 11   Reconstruir, alinhar e assinar o APK final.")
    print(" 12   Ver ou apagar a chave de assinatura local.")
    print(" 13   Assistente guiado: faz o caminho completo para quem está começando.")
    print(" 14   Trocar o idioma da interface.")
    print(" 15   Assistente de IA (opcional): edita a pasta decodificada e reconstrói.")
    print(" 16   Histórico de builds e comparação antes/depois.")
    print(" 17   Resumo legível (resumo.md) para quem não conhece Android.")
    print(" 18   Atualizar o ReaDroid pelo repositório (seguro, com confirmação).")
    print(" 19   Configurar a pasta padrão para cópias dos APKs reconstruídos.")
    print(DIM + "\n Dica: use só APKs seus ou que você tem autorização para modificar." + RESET)


COMMON_OUTPUT_DIRS = (
    "~/storage/downloads",
    "~/storage/shared/Download",
    "~/storage/shared/Download/ReaDroid",
    "~/storage/shared/Documents",
    "/storage/emulated/0/Download",
)


def choose_output_dir() -> Path | None:
    """Pergunta onde salvar a cópia do APK reconstruído, para este build.

    A pasta de trabalho dentro do projeto continua sendo usada normalmente;
    isto é só a cópia amigável que fica fácil de achar no celular."""
    current = outputs.load_output_dir()
    print(CYAN + "\nOnde salvar o APK reconstruído?" + RESET)
    if current:
        print(DIM + f" Configurada nas preferências: {current}" + RESET)
    for index, item in enumerate(COMMON_OUTPUT_DIRS, 1):
        resolved = Path(item).expanduser()
        mark = "  (existe)" if resolved.is_dir() else ""
        print(f" [{index}] {item}{mark}")
    print(" [P] Informar outra pasta")
    print(" [N] Usar o padrão (~/storage/downloads/ReaDroid)")
    raw = clean_path(safe_input("Escolha: ").strip())
    if raw.lower() in ("n", ""):
        return outputs.resolve_output_dir(None)
    if raw.lower() == "p":
        typed = clean_path(safe_input("Caminho da pasta (absoluto ou ~/…): ").strip())
        if not typed:
            print(YELLOW + "Nada informado; usando o padrão." + RESET)
            return outputs.resolve_output_dir(None)
        raw = typed
    elif raw.isdigit() and 1 <= int(raw) <= len(COMMON_OUTPUT_DIRS):
        raw = COMMON_OUTPUT_DIRS[int(raw) - 1]
    try:
        candidate = Path(raw).expanduser()
        if not candidate.is_absolute():
            candidate = Path.home() / "storage" / "shared" / candidate
    except (OSError, RuntimeError):
        print(RED + "Caminho inválido; usando o padrão." + RESET)
        return outputs.resolve_output_dir(None)
    try:
        candidate.mkdir(parents=True, exist_ok=True)
    except OSError as exc:
        print(RED + f"Não foi possível criar a pasta ({exc}); usando o padrão." + RESET)
        return outputs.resolve_output_dir(None)
    if safe_input("Lembrar esta pasta para os próximos builds? (s/N): ").strip().lower() == "s":
        try:
            outputs.save_output_dir(str(candidate))
            print(GREEN + f"Pasta salva: {candidate}" + RESET)
        except OSError:
            print(YELLOW + "Não foi possível salvar a preferência; vale só para este build." + RESET)
    return candidate


def output_dir_menu() -> None:
    """Opção 19: define, limpa ou só mostra a pasta padrão das cópias de APK."""
    print(CYAN + "\nPasta de destino dos APKs reconstruídos" + RESET)
    current = outputs.load_output_dir()
    if current:
        print(f" Configurada: {current}")
    else:
        print(DIM + " Padrão atual: ~/storage/downloads/ReaDroid (Termux)" + RESET)
    print(DIM + " O APK original continua sempre em builds/; esta pasta recebe só uma cópia." + RESET)
    if safe_input("Escolher outra pasta agora? (s/N): ").strip().lower() != "s":
        return
    dest = choose_output_dir()
    if dest is not None:
        print(GREEN + f"Em uso neste momento: {dest}" + RESET)


def update_menu() -> None:
    """Opção 18: verifica e aplica atualizações do repositório (fast-forward)."""
    print(CYAN + "\nAtualizar o ReaDroid" + RESET)
    print(DIM + f" Projeto: {BASE}" + RESET)
    print(DIM + " Só arquivos do projeto são mexidos; seus APKs, relatórios e builds ficam." + RESET)
    result = updater.check_update(BASE)
    print(result.get("message", ""))
    commits = result.get("commits") or []
    for line in commits:
        print("  " + sanitize(line))
    if not result.get("ok") or not result.get("updated"):
        return
    if safe_input(f"\nAplicar {result.get('behind', '?')} atualização(ões) agora? (s/N): ").strip().lower() != "s":
        print(DIM + "Nada foi alterado." + RESET)
        return
    applied = updater.apply_update(BASE, result["branch"])
    print((GREEN if applied["ok"] else RED) + applied["message"] + RESET)
    if applied["ok"]:
        print(YELLOW + "Reinicie o ReaDroid para usar a versão nova." + RESET)


def keystore_menu() -> None:
    print(CYAN + "\nChave de assinatura" + RESET)
    if KEYSTORE.is_file():
        print(f" Em uso: {KEYSTORE}")
        print(f" Alias padrão: {DEFAULT_ALIAS}")
        print(" (a senha padrão é 'readroid123' - troque editando builder.py se quiser outra)")
        if safe_input("Apagar esta chave e gerar outra no próximo build? (s/N): ").strip().lower() == "s":
            KEYSTORE.unlink()
            print(GREEN + "Chave removida. Uma nova será criada na próxima reconstrução." + RESET)
    else:
        print(" Nenhuma chave gerada ainda. Ela é criada automaticamente na primeira")
        print(" reconstrução (opção 11) e reaproveitada nas seguintes.")
        print(f" Local: {KEYSTORE}")
    if shutil.which("apksigner") and KEYSTORE.is_file():
        print(DIM + " Dica: use a opção 11 para gerar um APK e depois 'readroid verify' nele." + RESET)


# ------------------------------------------------------------------ menu

MENU = [
    ("1", "Inspecionar estrutura do APK"),
    ("2", "Analisar manifesto e permissões"),
    ("3", "Buscar URLs, domínios e IPs"),
    ("4", "Decompilar para Java com JADX"),
    ("5", "Extrair smali e recursos com Apktool"),
    ("6", "Verificar dependências"),
    ("7", "Abrir pasta de relatórios"),
    ("8", "Abrir pasta de resultados"),
    ("9", "Explorar e abrir arquivos gerados"),
    ("10", "Edições rápidas e renomear pacote (pré-build)"),
    ("11", "Reconstruir, alinhar e assinar APK"),
    ("12", "Gerenciar chave de assinatura"),
    ("13", "Assistente guiado (iniciantes)"),
    ("14", "Idioma / Language / اللغة / भाषा"),
    ("15", "Assistente de IA (opcional, editar com IA)"),
    ("16", "Histórico de builds e comparação"),
    ("17", "Resumo legível do app (resumo.md)"),
    ("18", "Atualizar o ReaDroid (repositório)"),
    ("19", "Destino das cópias de APK"),
]


def ai_available() -> bool:
    """A IA é um módulo à parte: se readroid/ai.py for apagado, o menu 15 some e nada quebra."""
    try:
        from . import ai  # noqa: F401
        return True
    except ImportError:
        return False


def ai_assistant() -> None:
    import sys

    from . import ai
    ai.run_menu(sys.modules[__name__])




# As bibliotecas de árabe/hindi são opcionais: sem elas, o menu usa a largura
# aproximada e mostra o texto no sentido normal em vez de derrubar o programa.
try:
    from wcwidth import wcswidth, wcwidth
except ImportError:  # pragma: no cover - depende do ambiente
    def wcwidth(ch):
        import unicodedata
        if unicodedata.combining(ch) or unicodedata.category(ch) in ("Cf", "Mn", "Me"):
            return 0
        return 2 if unicodedata.east_asian_width(ch) in ("W", "F") else 1

    def wcswidth(text):
        return sum(wcwidth(ch) for ch in str(text))

try:
    import arabic_reshaper
    from bidi.algorithm import get_display
except ImportError:  # pragma: no cover - depende do ambiente
    arabic_reshaper = None

    def get_display(text):
        return text


def has_rtl(s):
    return any("\u0600" <= c <= "\u06ff" or "\u0750" <= c <= "\u077f"
               or "\u08a0" <= c <= "\u08ff" for c in s)


def rtl(s):
    if arabic_reshaper is None:
        return s
    return get_display(arabic_reshaper.reshape(s))


def fit(text, size):
    # Sequências ANSI (cores) não ocupam células: são repassadas intactas e
    # ignoradas na medição, senão itens coloridos são truncados e o painel vaza.
    out, used = [], 0
    esc = False
    for ch in str(text):
        if esc:
            out.append(ch)
            if ch.isalpha():
                esc = False
            continue
        if ch == "\x1b":
            out.append(ch)
            esc = True
            continue
        w = max(0, wcwidth(ch))
        if used + w > size:
            break
        out.append(ch)
        used += w
    t = "".join(out)
    if has_rtl(t):
        t = rtl(t)
    # Mede o texto sem ANSI: wcswidth devolve -1 para escapes de controle.
    visible = max(0, wcswidth(_ANSI_RE.sub("", t)))
    return t + " " * max(0, size - visible)


def _panel(title: str, items: list[str], panel_width: int,
           color: str) -> list[str]:
    """Desenha um painel de terminal sem dependências externas."""
    inner = max(10, panel_width - 2)
    top = "┌" + "─" * inner + "┐"
    bottom = "└" + "─" * inner + "┘"
    out = [color + top + RESET]

    heading = (" " + title + " ")[:inner]
    out.append(color + "│" + RESET + BOLD +
               fit(heading, inner) + RESET + color + "│" + RESET)
    out.append(color + "├" + "─" * inner + "┤" + RESET)

    for item in items:
        # Evita linhas longas quebrando o desenho em telas estreitas.
        out.append(color + "│" + RESET +
                   fit(item, inner) + color + "│" + RESET)

    out.append(color + bottom + RESET)
    return out



def _system_items() -> list[str]:
    checks = [
        ("Python", shutil.which("python") is not None),
        ("Java", shutil.which("java") is not None),
        ("JADX", shutil.which("jadx") is not None),
        ("APKtool", shutil.which("apktool") is not None),
        ("Sign", shutil.which("apksigner") is not None),
    ]
    items = [
        f"Ver: {__version__}",
        detect_platform(),
        "Sem root",
        network_state(),
        "",
    ]
    items.extend(f"{n}: {_ui.status(ok, '[OK]', '[OFF]')}" for n, ok in checks)
    items.append(f"IA: {_ui.status(ai_available(), '[OK]', '[OFF]')}")
    online = network_state() == "Online"
    items.append(f"Rede: {_ui.status(online, 'Online', 'Offline')}")
    return items


# Grupos do menu Cyber: seções em caixa alta, opções embaixo de cada uma.
_MENU_SECTIONS: list[tuple[str, tuple[str, ...]]] = [
    ("ANÁLISE APK", ("1", "2", "3")),
    ("ENGENHARIA REVERSA", ("4", "5")),
    ("SEGURANÇA E BUILD", ("10", "11", "12")),
    ("RELATÓRIOS", ("6", "7", "8", "9", "16", "17")),
    ("INTELIGÊNCIA ARTIFICIAL", ("13", "15")),
    ("CONFIGURAÇÕES", ("14", "18", "19", "0")),
]

_MENU_LABELS = {
    "1": "Inspec. APK",
    "2": "Manifesto",
    "3": "URLs/IPs",
    "4": "Decompilar",
    "5": "Extrair smali",
    "6": "Dependencias",
    "7": "Relatorios",
    "8": "Resultados",
    "9": "Ver arquivos",
    "10": "Edicoes",
    "11": "Assinar APK",
    "12": "Chave APK",
    "13": "Assistente",
    "14": "Idioma",
    "15": "IA",
    "16": "Historico",
    "17": "Resumo",
    "18": "Atualizar",
    "19": "Destino APK",
    "0": "Sair",
}


def _menu_items(compact: bool = False) -> list[str]:
    items: list[str] = []
    for section, keys in _MENU_SECTIONS:
        items.append(section)
        for key in keys:
            if key == "15" and not ai_available():
                continue
            if key == "0":
                items.append(f"0 — {tr(_MENU_LABELS[key])}")
            else:
                items.append(f"{key} — {tr(_MENU_LABELS[key])}")
    return items


_BORDERLESS = False


def _set_borderless(texts):
    """Árabe/hindi: sem bordas laterais e painéis empilhados."""
    global _BORDERLESS
    _BORDERLESS = any(
        "\u0600" <= c <= "\u08ff" or "\u0900" <= c <= "\u097f"
        or "\ufb50" <= c <= "\ufeff"
        for t in texts for c in str(t))


def _ed(ch):
    if not _BORDERLESS:
        return ch
    return " " if ch == "│" else "─"


def print_menu() -> None:
    import unicodedata

    cols = width()
    gold = "\033[38;5;220m"
    cyan = CYAN
    reset = RESET
    gap = 2

    def char_width(ch):
        if unicodedata.combining(ch):
            return 0
        if unicodedata.category(ch) in ("Cf", "Mn", "Me"):
            return 0
        return 2 if unicodedata.east_asian_width(ch) in ("W", "F") else 1


    left_items = _system_items()
    right_items = _menu_items(True)
    _set_borderless(left_items + right_items)

    if cols >= 40:
        lw = (cols - gap) // 2
        rw = cols - gap - lw

        def compact_panel(title, items, panel_width, color):
            inner = max(1, panel_width - 2)
            lines = [
                _ed("┌") + "─" * inner + _ed("┐"),
                _ed("│") + fit(title, inner) + _ed("│"),
                _ed("├") + "─" * inner + _ed("┤"),
            ]
            lines.extend(_ed("│") + fit(item, inner) + _ed("│") for item in items)
            lines.append(_ed("└") + "─" * inner + _ed("┘"))
            return [color + line + reset for line in lines]

        left = compact_panel("SYSTEM", left_items, lw, gold)
        right = compact_panel("MENU", right_items, rw, cyan)
        height = max(len(left), len(right))

        for i in range(height):
            a = left[i] if i < len(left) else gold + _ed("│") + " " * (lw - 2) + _ed("│") + reset
            b = right[i] if i < len(right) else cyan + _ed("│") + " " * (rw - 2) + _ed("│") + reset
            print(a + (f"\x1b[{lw + gap + 1}G" if _BORDERLESS else " " * gap) + b)
    else:
        panel_width = max(32, cols - 2)
        for title, items, color in (
            ("SYSTEM", left_items, gold),
            ("MENU", right_items, cyan),
        ):
            inner = max(10, panel_width - 2)
            lines = [
                _ed("┌") + "─" * inner + _ed("┐"),
                _ed("│") + fit(title, inner) + _ed("│"),
                _ed("├") + "─" * inner + _ed("┤"),
            ]
            lines.extend(_ed("│") + fit(item, inner) + _ed("│") for item in items)
            lines.append(_ed("└") + "─" * inner + _ed("┘"))
            for line in lines:
                print(color + line + reset)
            print()

    print()

def language_menu() -> None:
    print(CYAN + "\n" + tr("Escolha o idioma:") + RESET)
    codes = list(LANGUAGES)
    for index, code in enumerate(codes, 1):
        current = "  ✓" if code == get_language() else ""
        print(f" [{index}] {LANGUAGES[code]} ({code}){current}")
    print(" [0] " + tr("Cancelar"))
    choice = safe_input("> ").strip()
    if choice == "0" or not choice:
        return
    if choice.isdigit() and 1 <= int(choice) <= len(codes):
        code = codes[int(choice) - 1]
        set_language(code)
        print(f"{GREEN}{tr('Idioma salvo:')} {LANGUAGES[code]}{RESET}")
    else:
        print(YELLOW + tr("Opção não reconhecida.") + RESET)


def main() -> None:
    REPORTS.mkdir(parents=True, exist_ok=True)
    OUTPUTS.mkdir(parents=True, exist_ok=True)
    BUILDS.mkdir(parents=True, exist_ok=True)
    while True:
        banner()
        print_menu()
        choice = safe_input(CYAN + "\n" + tr("ReaDroid > ") + RESET).strip()

        if choice == "1":
            run_action("Inspeção APK", inspect_apk)
        elif choice == "2":
            run_action("Manifesto", lambda apk: analyze_manifest(apk, OUTPUTS / (apk.stem + "_manifest_work")))
        elif choice == "3":
            run_action("Scanner strings", scan_strings)
        elif choice == "4":
            apk = ask_apk()
            if apk:
                target = OUTPUTS / (apk.stem + "_jadx")
                print(YELLOW + "A decompilação pode demorar e consumir RAM. Use APKs confiáveis e que você tem autorização para analisar." + RESET)
                if safe_input(f"Salvar em {target}? [s/N]: ").strip().lower() == "s":
                    result = decompile_with_jadx(apk, target)
                    print((GREEN if result.get("ok") else YELLOW) + result.get("message", "Processo concluído.") + RESET)
                    print("Destino:", result.get("output_dir", target))
                    if result.get("stderr"):
                        print(sanitize(result["stderr"][-2500:]))
                    save_and_show(result, "jadx", apk)
        elif choice == "5":
            apk = ask_apk()
            if apk:
                target = OUTPUTS / (apk.stem + "_apktool")
                print(YELLOW + "A extração pode levar alguns minutos. O APK original não será alterado." + RESET)
                if safe_input(f"Salvar em {target}? [s/N]: ").strip().lower() == "s":
                    result = extract_smali_with_apktool(apk, target)
                    print((GREEN if result.get("ok") else YELLOW) + result.get("message", "Processo concluído.") + RESET)
                    print("Destino:", result.get("output_dir", target))
                    if result.get("stderr"):
                        print(sanitize(result["stderr"][-2500:]))
                    save_and_show(result, "apktool", apk)
                    if result.get("ok"):
                        try:
                            history.mark_extracted(target, apk, sha256_file(apk))
                        except OSError:
                            pass
                        print(DIM + "Edite os arquivos dentro dessa pasta e depois use as opções 10/11." + RESET)
        elif choice == "6":
            dependencies()
        elif choice == "7":
            open_folder(REPORTS)
        elif choice == "8":
            open_folder(OUTPUTS)
        elif choice == "9":
            browse_generated_files()
        elif choice == "10":
            quick_edits_menu()
        elif choice == "11":
            rebuild_and_sign()
        elif choice == "12":
            keystore_menu()
        elif choice == "13":
            from .wizard import run_wizard
            run_wizard(sys.modules[__name__])
        elif choice == "14":
            language_menu()
        elif choice == "15" and ai_available():
            ai_assistant()
        elif choice == "16":
            history_menu()
        elif choice == "17":
            summary_menu()
        elif choice == "18":
            update_menu()
        elif choice == "19":
            output_dir_menu()
        elif choice == "?":
            help_menu()
        elif choice in ("0", ""):
            print(GREEN + tr("Até a próxima. ReaDroid encerrado.") + RESET)
            break
        else:
            print(YELLOW + tr("Opção não reconhecida.") + RESET)
        if choice not in ("0", "14"):
            pause()
