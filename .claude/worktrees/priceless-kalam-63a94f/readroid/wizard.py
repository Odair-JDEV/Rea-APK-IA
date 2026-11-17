"""Assistente guiado para iniciantes: descompilar → editar → reconstruir → instalar.

Regras deste módulo:
- Backup é obrigatório antes de qualquer edição feita por IA.
- Nada é chamado de "pronto para instalar" se alinhamento/verificação foram pulados.
- Abrir o instalador do Android não é o mesmo que instalar: a mensagem diz o que aconteceu.
"""

from __future__ import annotations

import datetime
import re
import shutil
import subprocess
from pathlib import Path
from typing import Any

from .analyzer import extract_smali_with_apktool, validate_apk
from .builder import (DEFAULT_ALIAS, DEFAULT_STOREPASS, QUICK_EDITS, apply_quick_edits,
                      build_pipeline, rename_package, valid_package_name)
from .i18n import tr

_CTRL_RE = re.compile(r"\x1b\[[0-9;]*[a-zA-Z]|[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]")


def _sanitize(text: Any) -> str:
    return _CTRL_RE.sub("", str(text))


def _ask(prompt: str) -> str:
    return __import__("builtins").input(_sanitize(prompt))


def _pause() -> None:
    _ask(tr("\nENTER para continuar..."))


def _confirm(prompt: str) -> bool:
    return _ask(prompt + " (s/N): ").strip().lower() == "s"


def _print_step(label: str, ok: bool | None = True, detail: str | None = None) -> None:
    from .app import GREEN, YELLOW, RED, DIM, RESET
    mark = GREEN + "✓" + RESET if ok is True else YELLOW + "?" + RESET if ok is None else RED + "✗" + RESET
    print(f"  [{mark}] {label}")
    if detail:
        print(f"       {DIM}{_sanitize(detail)}{RESET}")


# -------------------------------------------------------------------------- pré-verificação

def _check_tools() -> dict[str, bool]:
    return {name: shutil.which(name) is not None
            for name in ("apktool", "zipalign", "apksigner", "java", "keytool", "adb")}


def _show_preflight(tools: dict[str, bool]) -> bool:
    from .app import CYAN, YELLOW, DIM, RESET
    print(CYAN + "\n" + tr("Verificando ferramentas...") + RESET)

    required = [("apktool", tr("Reconstruir APK (obrigatório)")),
                ("java", tr("Keytool/assinatura (obrigatório)"))]
    recommended = [("zipalign", tr("Alinhar APK (recomendado para instalação)")),
                   ("apksigner", tr("Assinatura v1+v2+v3 (recomendado)"))]
    optional = [("keytool", tr("Gerar chave de assinatura (se não existir)")),
                ("adb", tr("Instalar via ADB (opcional)"))]

    all_ok = True
    for name, desc in required:
        status = tools.get(name, False)
        _print_step(f"{name}: {desc}", status, None if status else tr("Instale: pkg install ") + name)
        all_ok = all_ok and status
    for name, desc in recommended:
        status = tools.get(name, False)
        _print_step(f"{name}: {desc}", status)
        if not status:
            print(f"       {YELLOW}→{RESET} {tr('Pode funcionar sem, mas o APK pode não instalar em Android 7+')}")
    for name, desc in optional:
        status = tools.get(name, False)
        _print_step(f"{name}: {desc}", status)
        if not status:
            print(f"       {DIM}→{RESET} {tr('Instale se quiser usar esta funcionalidade')}")

    if not all_ok:
        print(YELLOW + "\n" + tr("Algumas ferramentas obrigatórias faltando. Instale antes de continuar.") + RESET)
    return all_ok


# -------------------------------------------------------------------------- extração

def _select_apk() -> Path | None:
    from .app import ask_apk
    apk = ask_apk()
    if not apk:
        print(tr("Nenhum APK selecionado."))
    return apk


def _folder_matches_apk(folder: Path, apk: Path) -> bool:
    """Confere, pelo apktool.yml, se a pasta decodificada veio deste APK."""
    try:
        text = (folder / "apktool.yml").read_text(encoding="utf-8", errors="replace")
    except OSError:
        return False
    match = re.search(r"^\s*apkFileName:\s*['\"]?([^'\"\n]+)", text, re.MULTILINE)
    return bool(match) and match.group(1).strip() == apk.name


def _extract_apk(apk: Path, outputs_dir: Path) -> Path | None:
    target = outputs_dir / (apk.stem + "_apktool")
    if target.exists():
        if _folder_matches_apk(target, apk):
            print(tr("Pasta já existe para este APK; reutilizando: ") + str(target))
            return target
        print(tr("A pasta já existe, mas não corresponde a este APK: ") + str(target))
        if not _confirm(tr("Apagar essa pasta e extrair de novo?")):
            print(tr("Extração cancelada. Escolha outro APK ou remova a pasta manualmente."))
            return None
        try:
            shutil.rmtree(target)
        except OSError as exc:
            print(tr("Não foi possível apagar a pasta: ") + _sanitize(exc))
            return None

    print(tr("Extraindo com Apktool..."))
    result = extract_smali_with_apktool(apk, target)
    if not result.get("ok"):
        print(tr("Falha na extração: ") + _sanitize(result.get("message", "Erro desconhecido")))
        if result.get("stderr"):
            print(_sanitize(result["stderr"][-2000:]))
        return None
    print(tr("Extraído em: ") + str(target))
    return target


# -------------------------------------------------------------------------- edição

def _apply_quick_edits(decoded: Path) -> None:
    from .app import CYAN, GREEN, RED, RESET
    print(CYAN + "\n" + tr("Edições rápidas disponíveis:") + RESET)
    keys = list(QUICK_EDITS.keys())
    for i, key in enumerate(keys, 1):
        print(f"  [{i}] {QUICK_EDITS[key]}")
    choice = _ask(tr("Números (ex: 1,3) ou ENTER para pular: ")).strip()
    if not choice:
        return
    edits = [keys[int(part) - 1] for part in (p.strip() for p in choice.split(","))
             if part.isdigit() and 1 <= int(part) <= len(keys)]
    if not edits:
        return
    result = apply_quick_edits(decoded, edits)
    if result.get("ok"):
        print(GREEN + tr("Aplicado: ") + ", ".join(result["applied"]) + RESET)
    else:
        print(RED + tr("Falha: ") + _sanitize(result.get("message", "Erro")) + RESET)


def _rename_package_prompt(decoded: Path) -> None:
    from .app import GREEN, YELLOW, RED, RESET
    if not _confirm(tr("Renomear pacote (applicationId)?")):
        return
    while True:
        new_pkg = _ask(tr("Novo nome do pacote (ex: com.exemplo.app): ")).strip()
        if not new_pkg:
            print(tr("Cancelado."))
            return
        if valid_package_name(new_pkg):
            break
        print(RED + tr("Nome inválido. Use formato com.exemplo.app") + RESET)
    result = rename_package(decoded, new_pkg)
    if result.get("ok"):
        print(GREEN + tr("Pacote renomeado: ") + f"{result['old_package']} → {new_pkg}" + RESET)
        if result.get("warning"):
            print(YELLOW + result["warning"] + RESET)
    else:
        print(RED + tr("Falha: ") + _sanitize(result.get("message", "Erro")) + RESET)


def _manual_edit_pause(decoded: Path) -> None:
    from .app import CYAN, DIM, RESET
    print(CYAN + "\n" + tr("Edição manual") + RESET)
    print(tr("Arquivos em: ") + str(decoded))
    print(DIM + tr("Edite com o editor que preferir. Quando terminar, volte a esta janela.") + RESET)
    _ask(tr("ENTER quando terminar de editar (ou ENTER para pular): "))


def _backup(decoded: Path, builds_dir: Path) -> Path | None:
    dest = builds_dir / f"_backup_{decoded.name}_{datetime.datetime.now():%Y%m%d_%H%M%S}"
    try:
        shutil.copytree(decoded, dest)
        return dest
    except (OSError, shutil.Error):
        return None


def _maybe_ai_edit(decoded: Path, app_module) -> dict[str, Any] | None:
    """Edição por IA com backup obrigatório. Devolve o resultado do build feito pela IA."""
    from .app import GREEN, YELLOW, RED, DIM, RESET
    if not _confirm(tr("Usar IA para editar/corrigir arquivos?")):
        return None
    try:
        from . import ai
    except ImportError:
        print(RED + tr("Módulo de IA não disponível (readroid/ai.py).") + RESET)
        return None

    ready, why, _binary = ai.ready()
    if not ready:
        print(YELLOW + tr("IA não configurada. Configure no menu de IA (opção 15).") + RESET)
        print(DIM + _sanitize(why) + RESET)
        return None

    instruction = _ask(tr("O que a IA deve fazer? (ex: traduzir a interface para português): ")).strip()
    if not instruction:
        print(YELLOW + tr("Nada informado; edição por IA cancelada.") + RESET)
        return None

    print(tr("A IA vai editar arquivos na pasta decodificada. Backup será criado."))
    if not _confirm(tr("Continuar?")):
        return None

    backup = _backup(decoded, app_module.BUILDS)
    if backup is None:
        print(RED + tr("Não foi possível criar o backup. A edição por IA foi cancelada.") + RESET)
        return None
    print(GREEN + tr("Backup: ") + str(backup) + RESET)

    def build_fn() -> dict[str, Any]:
        name = decoded.name.replace("_apktool", "") or "app"
        work = app_module.BUILDS / f"{name}_{datetime.datetime.now():%Y%m%d_%H%M%S}"
        return build_pipeline(decoded, work, app_module.KEYSTORE, DEFAULT_ALIAS, DEFAULT_STOREPASS, [])

    out = ai.fix_loop(decoded, instruction, build_fn,
                      lambda prompt: ai.ask_with_fallback(app_module, decoded, prompt),
                      lambda q: _ask(q + " (s/N): ").strip().lower() == "s",
                      print, max_rounds=3)
    if out.get("ok"):
        print(GREEN + tr("A IA terminou e o APK foi reconstruído.") + RESET)
        return out.get("result")
    print(RED + tr("IA não conseguiu reconstruir: ") + _sanitize(out.get("message", "Erro")) + RESET)
    print(tr("Para desfazer as mudanças da IA, restaure o backup: ") + str(backup))
    return None


# -------------------------------------------------------------------------- build e instalação

def _report_build(result: dict[str, Any]) -> Path | None:
    """Mostra cada etapa e só devolve o APK quando ele está realmente pronto."""
    from .app import GREEN, YELLOW, RED, DIM, RESET
    steps = result.get("steps", {})
    for step_name, label in (("quick_edits", tr("Edições rápidas")),
                             ("rebuild", tr("Reconstrução (apktool b)")),
                             ("align", tr("Alinhamento (zipalign)")),
                             ("keystore", tr("Chave de assinatura")),
                             ("sign", tr("Assinatura")),
                             ("verify", tr("Verificação"))):
        step = steps.get(step_name)
        if not step:
            continue
        skipped = step.get("skipped")
        detail = None
        if skipped:
            detail = step.get("message")
        elif not step.get("ok"):
            detail = step.get("message") or str(step.get("stderr", ""))[-500:]
        _print_step(label, None if skipped else step.get("ok"), detail)

    if not result.get("ok"):
        print(RED + "\n" + tr("Falha na reconstrução.") + RESET)
        sign = steps.get("sign", {})
        if sign.get("stderr"):
            print(DIM + _sanitize(str(sign["stderr"])[-500:]) + RESET)
        return None

    final_apk = Path(result["final_apk"])
    print(GREEN + "\n" + tr("APK reconstruído: ") + str(final_apk) + RESET)
    print(tr("SHA256: ") + str(result.get("sha256", "?")))

    if steps.get("align", {}).get("skipped"):
        print(YELLOW + tr("Atenção: o APK NÃO foi alinhado (zipalign ausente). "
                          "Pode falhar ao instalar em Android 7+.") + RESET)
    if steps.get("verify", {}).get("ok") is None:
        print(YELLOW + tr("Atenção: a assinatura NÃO foi verificada (apksigner ausente). "
                          "Instale o apksigner antes de confiar neste APK.") + RESET)
    return final_apk


def _build_apk(decoded: Path, builds_dir: Path, keystore: Path) -> Path | None:
    from .app import CYAN, RESET
    name = decoded.name.replace("_apktool", "") or "app"
    work = builds_dir / f"{name}_{datetime.datetime.now():%Y%m%d_%H%M%S}"
    print(CYAN + "\n" + tr("Iniciando reconstrução...") + RESET)
    result = build_pipeline(decoded, work, keystore, DEFAULT_ALIAS, DEFAULT_STOREPASS, [],
                            lambda m: print("  · " + _sanitize(m)))
    return _report_build(result)


def _install_apk(apk: Path, has_adb: bool) -> str:
    """Devolve 'installed', 'opened' (instalador aberto, instalação não confirmada) ou 'saved'."""
    from .app import CYAN, YELLOW, RED, GREEN, RESET
    print(CYAN + "\n" + tr("Instalação") + RESET)
    print(tr("O APK reconstruído é reassinado — NÃO substitui a versão da loja."))

    if not _confirm(tr("Deseja tentar instalar no dispositivo?")):
        print(tr("APK salvo em: ") + str(apk))
        return "saved"

    if has_adb:
        print(tr("Tentando via ADB..."))
        try:
            result = subprocess.run(["adb", "install", "-r", str(apk)], capture_output=True,
                                    text=True, timeout=180)
        except (OSError, subprocess.TimeoutExpired) as exc:
            print(YELLOW + tr("ADB falhou: ") + _sanitize(exc) + RESET)
        else:
            if result.returncode == 0 and "Success" in (result.stdout or ""):
                print(GREEN + tr("Instalado via ADB.") + RESET)
                return "installed"
            print(YELLOW + tr("ADB falhou: ") + _sanitize((result.stderr or result.stdout)[-300:]) + RESET)
        print(tr("Tentando abridor do sistema..."))

    opener = shutil.which("termux-open")
    if opener:
        print(tr("Abrindo instalador do Android..."))
        try:
            subprocess.run([opener, str(apk)], check=False, timeout=60)
        except (OSError, subprocess.TimeoutExpired) as exc:
            print(RED + tr("Não foi possível abrir o instalador: ") + _sanitize(exc) + RESET)
        else:
            print(tr("O instalador do Android foi aberto. Confirme a instalação na tela."))
            print(tr("APK salvo em: ") + str(apk))
            return "opened"

    print(RED + tr("Nenhum instalador disponível (adb/termux-open).") + RESET)
    print(tr("APK salvo em: ") + str(apk))
    return "saved"


# -------------------------------------------------------------------------- fluxo principal

def run_wizard(app_module) -> None:
    """Ponto de entrada do assistente guiado."""
    from .app import CYAN, GREEN, YELLOW, RED, BOLD, RESET

    print(CYAN + BOLD + "\n" + tr("=== Assistente ReaDroid: APK do início ao fim ===") + RESET)

    tools = _check_tools()
    if not _show_preflight(tools):
        _pause()
        return

    apk = _select_apk()
    if not apk:
        _pause()
        return
    try:
        validate_apk(apk)
    except ValueError as exc:
        print(RED + tr("APK inválido: ") + _sanitize(exc) + RESET)
        _pause()
        return

    decoded = _extract_apk(apk, app_module.OUTPUTS)
    if not decoded:
        _pause()
        return

    print(CYAN + "\n" + tr("Etapa de edição — arquivos em: ") + str(decoded) + RESET)
    _apply_quick_edits(decoded)
    _rename_package_prompt(decoded)
    _manual_edit_pause(decoded)

    ai_result = _maybe_ai_edit(decoded, app_module)

    if ai_result is not None:
        # A IA já reconstruiu no ciclo dela; só reportamos o resultado.
        final_apk = _report_build(ai_result)
    else:
        if not _confirm(tr("Continuar para reconstrução?")):
            print(tr("Pasta decodificada mantida em: ") + str(decoded))
            _pause()
            return
        final_apk = _build_apk(decoded, app_module.BUILDS, app_module.KEYSTORE)
    if not final_apk:
        _pause()
        return

    status = _install_apk(final_apk, tools.get("adb", False))
    if status == "installed":
        print(GREEN + tr("Pronto: APK instalado no dispositivo.") + RESET)
    elif status == "opened":
        print(YELLOW + tr("Instalador aberto; a instalação ainda depende de você confirmar na tela.") + RESET)
    else:
        print(tr("APK salvo em: ") + str(final_apk))
    _pause()
