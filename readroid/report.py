"""Relatório legível (`resumo.md`) a partir dos relatórios JSON do ReaDroid.

Pensado para quem não conhece terminologia Android: explica em linguagem simples o
que o app parece fazer, o que pede de permissão, quais componentes ficam expostos e
quais endereços aparecem no código. Nada é executado.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

DANGEROUS_PERMISSIONS = {
    "android.permission.READ_SMS": "ler mensagens SMS",
    "android.permission.SEND_SMS": "enviar SMS",
    "android.permission.RECEIVE_SMS": "receber SMS",
    "android.permission.READ_CONTACTS": "ler contatos",
    "android.permission.WRITE_CONTACTS": "alterar contatos",
    "android.permission.CALL_PHONE": "fazer ligações",
    "android.permission.READ_CALL_LOG": "ler histórico de chamadas",
    "android.permission.ACCESS_FINE_LOCATION": "localização precisa(GPS)",
    "android.permission.ACCESS_COARSE_LOCATION": "localização aproximada",
    "android.permission.ACCESS_BACKGROUND_LOCATION": "localização em segundo plano",
    "android.permission.CAMERA": "usar a câmera",
    "android.permission.RECORD_AUDIO": "gravar áudio",
    "android.permission.READ_EXTERNAL_STORAGE": "ler arquivos do aparelho",
    "android.permission.WRITE_EXTERNAL_STORAGE": "gravar arquivos no aparelho",
    "android.permission.MANAGE_EXTERNAL_STORAGE": "acesso amplo a arquivos",
    "android.permission.READ_PHONE_STATE": "ler dados do telefone",
    "android.permission.REQUEST_INSTALL_PACKAGES": "instalar outros APKs",
    "android.permission.SYSTEM_ALERT_WINDOW": "desenhar sobre outros apps",
    "android.permission.QUERY_ALL_PACKAGES": "listar todos os apps instalados",
    "android.permission.POST_NOTIFICATIONS": "enviar notificações",
    "android.permission.BODY_SENSORS": "ler sensores do corpo",
    "android.permission.GET_ACCOUNTS": "ver contas do aparelho",
}

COMPONENT_KINDS = {"activity", "activity-alias", "service", "receiver", "provider"}


def _perm_label(name: str) -> str:
    friendly = DANGEROUS_PERMISSIONS.get(name)
    return f"{name} ({friendly})" if friendly else name


def _short(name: str, limit: int = 8) -> list[str]:
    return [str(item) for item in (name or [])[:limit]]


def build_summary(manifest: dict[str, Any] | None, strings: dict[str, Any] | None,
                  inspection: dict[str, Any] | None, app_name: str = "app") -> str:
    """Monta o Markdown a partir dos relatórios disponíveis (todos opcionais)."""
    lines = [f"# Resumo do app: {app_name}", ""]
    manifest = manifest or {}
    strings = strings or {}
    inspection = inspection or {}

    package = manifest.get("package") or manifest.get("package_name")
    if package:
        lines.append(f"- **Pacote:** `{package}`")
    if manifest.get("version_name") or manifest.get("version_code"):
        lines.append(f"- **Versão:** {manifest.get('version_name') or '?'} "
                     f"({manifest.get('version_code') or '?'})")
    if manifest.get("min_sdk") or manifest.get("target_sdk"):
        lines.append(f"- **Android mínimo / alvo:** {manifest.get('min_sdk') or '?'} / "
                     f"{manifest.get('target_sdk') or '?'}")
    if inspection.get("file_size_bytes"):
        lines.append(f"- **Tamanho:** {inspection['file_size_bytes'] // 1024} KB")
    if inspection.get("dex_files"):
        lines.append(f"- **Arquivos de código (DEX):** {len(inspection['dex_files'])}")
    if inspection.get("native_libraries"):
        lines.append(f"- **Bibliotecas nativas:** {len(inspection['native_libraries'])}")
    lines.append("")

    application = manifest.get("application") or {}
    flags = []
    if str(application.get("debuggable", "")).lower() == "true":
        flags.append("`debuggable` ligado: permite depuração pelo adb (não recomendado em produção).")
    if str(application.get("allow_backup", "")).lower() == "true":
        flags.append("`allowBackup` ligado: o sistema pode copiar dados do app em backup.")
    if str(application.get("uses_cleartext_traffic", "")).lower() == "true":
        flags.append("Tráfego HTTP sem TLS permitido (`usesCleartextTraffic`).")
    if flags:
        lines += ["## Avisos do manifesto", ""] + [f"- {item}" for item in flags] + [""]

    permissions = [p.get("name", "") for p in (manifest.get("permissions") or []) if isinstance(p, dict)]
    if permissions:
        dangerous = [name for name in permissions if name in DANGEROUS_PERMISSIONS]
        lines += [f"## Permissões ({len(permissions)})", ""]
        if dangerous:
            lines.append("**Que merecem atenção:**")
            lines += [f"- {_perm_label(name)}" for name in dangerous]
            lines.append("")
        others = [name for name in permissions if name not in DANGEROUS_PERMISSIONS]
        if others:
            lines.append("Outras:")
            lines += [f"- `{name}`" for name in others[:20]]
            if len(others) > 20:
                lines.append(f"- ... (+{len(others) - 20})")
            lines.append("")

    components = [c for c in (manifest.get("components") or []) if isinstance(c, dict)]
    exported = [c for c in components
                if str(c.get("exported", "")).lower() == "true"
                or (c.get("intent_filters") and c.get("exported") is None)]
    if exported:
        lines += ["## Componentes expostos", ""]
        for item in exported[:25]:
            kind = str(item.get("type") or item.get("kind") or "?")
            name = str(item.get("name") or "?")
            lines.append(f"- **{kind}:** `{name}`")
        lines.append("")

    urls = _short(strings.get("urls", []))
    domains = _short(strings.get("domains", []))
    ips = _short(strings.get("ipv4_candidates", []))
    if urls or domains or ips:
        lines += ["## Endereços encontrados no código", ""]
        if domains:
            lines.append(f"**Domínios ({len(strings.get('domains', []))}):** " + ", ".join(f"`{d}`" for d in domains))
        if urls:
            lines.append(f"**URLs ({len(strings.get('urls', []))}):** " + ", ".join(f"`{u}`" for u in urls))
        if ips:
            lines.append(f"**IPs ({len(strings.get('ipv4_candidates', []))}):** " + ", ".join(f"`{i}`" for i in ips))
        lines.append("")
        lines.append("_São textos encontrados no APK; não confirmam conexões nem comportamento malicioso._")
        lines.append("")

    lines += ["## Limitações", "",
              "- Esta é uma análise estática: o app não é executado.",
              "- Permissões e endereços são pistas para revisão, não um veredito de segurança.",
              ""]
    return "\n".join(lines)


def write_summary(path: Path, text: str) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    return path
