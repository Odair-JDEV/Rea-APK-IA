"""Biblioteca de prompts prontos para a edição por IA.

Cada prompt é um texto curto, específico e verificável, pensado para o agente
editar a pasta decodificada pelo Apktool. Todos seguem as mesmas regras:

- mexer só dentro da pasta do APK;
- não alterar apktool.yml;
- fazer a menor mudança possível;
- listar os arquivos alterados e explicar o que mudou.

Uso autorizado: apenas APKs seus ou que você tem permissão explícita para
modificar. Desbloquear recursos pagos de um app de terceiros, remover anúncios
de um app que não é seu ou contornar licenças pode violar a lei e os termos do
desenvolvedor. Os prompts abaixo existem para testes, aprendizado e manutenção
do seu próprio app.
"""

from __future__ import annotations

from typing import Any

# id, título, descrição curta, texto do prompt, aviso (opcional)
PROMPTS: list[dict[str, Any]] = [
    # ---------------------------------------------------------------- interface
    {
        "id": "traduzir_interface",
        "titulo": "Traduzir a interface para português",
        "descricao": "Traduz os textos de res/values/strings.xml mantendo os nomes das chaves.",
        "prompt": (
            "Traduza para português do Brasil os textos visíveis ao usuário em res/values/strings.xml. "
            "Mantenha exatamente os mesmos nomes de chave e a mesma estrutura XML. "
            "Não traduza nomes de pacote, chaves de API, URLs, nomes de arquivo nem textos técnicos. "
            "Preserve os marcadores de formatação como %1$s, %d e \\n. "
            "Se existir res/values-pt ou res/values-pt-rBR, atualize essa pasta em vez de sobrescrever o padrão. "
            "Ao final, liste os arquivos alterados e quantas strings foram traduzidas."
        ),
    },
    {
        "id": "nome_do_app",
        "titulo": "Mudar o nome exibido do app",
        "descricao": "Altera apenas o rótulo mostrado no launcher.",
        "prompt": (
            "Altere o nome exibido do aplicativo para o valor que eu informar. "
            "Procure em res/values/strings.xml a string usada por android:label no AndroidManifest.xml "
            "e altere somente o texto dela. Não mude o nome do pacote, o applicationId nem nomes de classe. "
            "Se o rótulo estiver escrito direto no manifesto, altere apenas esse atributo. "
            "Informe o novo nome e liste o arquivo alterado."
        ),
    },
    {
        "id": "tema_escuro",
        "titulo": "Forçar tema escuro",
        "descricao": "Ajusta o tema base para escuro quando o app já tem um tema escuro definido.",
        "prompt": (
            "Verifique se o app já possui um tema escuro em res/values/styles.xml ou res/values-night. "
            "Se existir, faça o tema padrão usado no AndroidManifest.xml apontar para ele. "
            "Se não existir, não invente um tema novo: apenas explique o que seria necessário. "
            "Não altere cores individuais nem layouts. Liste o que mudou."
        ),
    },
    # ---------------------------------------------------------------- recursos do próprio app
    {
        "id": "desbloquear_vip",
        "titulo": "Desbloquear recursos VIP/premium (app seu)",
        "descricao": "Localiza a checagem de assinatura e explica como desativá-la no seu próprio app.",
        "aviso": "Use apenas em APK seu ou autorizado. Contornar cobrança de terceiros é ilegal.",
        "prompt": (
            "Este é um APK meu e tenho autorização para modificá-lo. "
            "Localize no código smali a verificação que decide se o usuário é VIP/premium "
            "(procure por nomes como isPremium, isVip, isPro, isSubscribed, hasSubscription, "
            "purchaseState, billing, BillingClient, e por constantes booleanas ligadas a essas checagens). "
            "Antes de alterar, mostre os arquivos e trechos encontrados e explique qual é o ponto de decisão. "
            "Depois, faça a menor mudança possível para que a checagem retorne verdadeiro, "
            "preferindo alterar o método que calcula o estado em vez de cada tela. "
            "Não remova a integração de cobrança, não apague classes e não quebre a inicialização. "
            "Liste os arquivos alterados e explique o efeito de cada mudança."
        ),
    },
    {
        "id": "remover_anuncios",
        "titulo": "Remover anúncios (app seu)",
        "descricao": "Desativa a exibição de anúncios sem remover as bibliotecas.",
        "aviso": "Use apenas em APK seu ou autorizado.",
        "prompt": (
            "Este é um APK meu e tenho autorização para modificá-lo. "
            "Localize onde os anúncios são carregados e exibidos (AdMob, AppLovin, Unity Ads, IronSource, "
            "Facebook Audience Network). Procure por classes como AdView, InterstitialAd, RewardedAd, "
            "loadAd, showAd e pelos IDs de bloco de anúncio. "
            "Faça a menor mudança possível para que os anúncios não sejam exibidos, "
            "preferindo desativar a chamada de exibição em vez de remover bibliotecas inteiras. "
            "Não quebre o fluxo do app: se o anúncio libera uma recompensa, mantenha a recompensa. "
            "Liste os arquivos alterados e explique cada mudança."
        ),
    },
    {
        "id": "remover_verificacao_licenca",
        "titulo": "Desativar verificação de licença (app seu)",
        "descricao": "Remove a checagem de licença do próprio app para testes internos.",
        "aviso": "Use apenas em APK seu. Isso não dá direito a usar apps de terceiros.",
        "prompt": (
            "Este é um APK meu e tenho autorização para modificá-lo. "
            "Localize a verificação de licença (LVL, LicenseChecker, LicenseValidator, "
            "ou checagens próprias de assinatura/recibo). "
            "Explique primeiro como a verificação funciona e onde está o ponto de decisão. "
            "Depois faça a menor mudança possível para que a verificação seja considerada válida em builds de teste. "
            "Não remova classes de cobrança nem altere o manifesto além do necessário. "
            "Liste os arquivos alterados."
        ),
    },
    # ---------------------------------------------------------------- rede e segurança
    {
        "id": "permitir_http",
        "titulo": "Permitir tráfego HTTP (cleartext)",
        "descricao": "Libera HTTP para depurar um servidor local.",
        "prompt": (
            "Permita tráfego HTTP sem TLS para depuração. "
            "No AndroidManifest.xml, adicione android:usesCleartextTraffic=\"true\" ao elemento <application> "
            "se ainda não existir. Se houver um network_security_config.xml, ajuste-o em vez de usar a flag global. "
            "Explique o risco de segurança dessa mudança e liste os arquivos alterados."
        ),
    },
    {
        "id": "remover_permissao",
        "titulo": "Remover uma permissão específica",
        "descricao": "Remove uma permissão do manifesto e explica o impacto.",
        "prompt": (
            "Remova do AndroidManifest.xml a permissão que eu informar. "
            "Antes, procure no código onde essa permissão é usada e liste os pontos encontrados. "
            "Se a remoção puder quebrar uma funcionalidade, avise e explique qual. "
            "Não remova outras permissões. Liste os arquivos alterados."
        ),
    },
    {
        "id": "certificate_pinning",
        "titulo": "Desativar certificate pinning (app seu)",
        "descricao": "Permite inspecionar o tráfego do seu próprio app em testes.",
        "aviso": "Use apenas em app seu ou em teste autorizado.",
        "prompt": (
            "Este é um APK meu e tenho autorização para modificá-lo. "
            "Localize a implementação de certificate pinning (CertificatePinner, TrustManager customizado, "
            "network_security_config.xml com <pin-set>, ou verificação manual de hash de certificado). "
            "Explique primeiro onde está e como funciona. "
            "Depois faça a menor mudança possível para desativar o pinning em builds de teste, "
            "mantendo a validação normal de TLS. Liste os arquivos alterados."
        ),
    },
    # ---------------------------------------------------------------- diagnóstico
    {
        "id": "explicar_crash",
        "titulo": "Explicar um crash",
        "descricao": "Analisa um stack trace e aponta a causa provável.",
        "prompt": (
            "Analise o stack trace abaixo e explique a causa provável em português. "
            "Aponte a classe e o método do app (não da biblioteca) mais próximos da origem, "
            "o arquivo smali correspondente e a correção mínima sugerida. "
            "Não modifique nenhum arquivo, apenas explique.\n\nSTACK TRACE:\n"
        ),
    },
    {
        "id": "revisar_permissoes",
        "titulo": "Revisar permissões e componentes expostos",
        "descricao": "Aponta riscos no manifesto do seu app.",
        "prompt": (
            "Leia o AndroidManifest.xml e liste, em português e de forma curta: "
            "permissões perigosas, componentes exportados (activity, service, receiver, provider) "
            "sem proteção, debuggable ligado, allowBackup ligado e qualquer intent-filter amplo. "
            "Para cada item, diga o risco e a correção recomendada. "
            "Não modifique nenhum arquivo, apenas analise."
        ),
    },
    {
        "id": "mapear_fluxo",
        "titulo": "Mapear o fluxo de uma tela",
        "descricao": "Explica como uma tela chega aos dados que mostra.",
        "prompt": (
            "Explique o fluxo da tela que eu informar: qual activity/fragment a abre, "
            "quais classes ela usa, de onde vêm os dados (rede, banco, preferências) e "
            "quais arquivos smali participam. Responda em português, de forma organizada. "
            "Não modifique nenhum arquivo."
        ),
    },
    # ---------------------------------------------------------------- build
    {
        "id": "corrigir_build",
        "titulo": "Corrigir erro de reconstrução",
        "descricao": "Recebe o erro do apktool e propõe a correção mínima.",
        "prompt": (
            "A reconstrução com apktool falhou com o erro abaixo. "
            "Explique a causa provável, aponte o arquivo e a linha e faça a correção mínima necessária. "
            "Não altere apktool.yml e não rode comandos de build. "
            "Liste os arquivos alterados.\n\nERRO:\n"
        ),
    },
    {
        "id": "corrigir_assinatura",
        "titulo": "Corrigir problema de assinatura",
        "descricao": "Investiga falhas de assinatura e alinhamento.",
        "prompt": (
            "A assinatura ou o alinhamento do APK falhou. Analise a mensagem abaixo, "
            "explique a causa e diga o que ajustar no projeto ou nas ferramentas. "
            "Não modifique arquivos do APK sem explicar antes. Mensagem:\n\n"
        ),
    },
    # ---------------------------------------------------------------- manutenção
    {
        "id": "atualizar_sdk",
        "titulo": "Ajustar targetSdkVersion",
        "descricao": "Explica o impacto de mudar o targetSdk no manifesto.",
        "prompt": (
            "Explique o que muda ao alterar o targetSdkVersion deste app para o valor que eu informar. "
            "Liste os pontos do manifesto e do código que podem precisar de ajuste "
            "(permissões em tempo de execução, exportação de componentes, armazenamento, notificações). "
            "Não altere nenhum arquivo ainda: apenas apresente o plano."
        ),
    },
    {
        "id": "limpar_logs",
        "titulo": "Remover logs de depuração",
        "descricao": "Remove chamadas de Log.d/Log.v do código.",
        "prompt": (
            "Remova as chamadas de log de depuração (Log.v, Log.d, Log.i) do código smali, "
            "mantendo Log.w e Log.e. Faça a menor mudança possível e não altere a lógica. "
            "Liste os arquivos alterados e quantas chamadas foram removidas."
        ),
    },
]

CATEGORIES = {
    "interface": "Interface e textos",
    "recursos": "Recursos do próprio app",
    "rede": "Rede e segurança",
    "diagnostico": "Diagnóstico",
    "build": "Build e assinatura",
    "manutencao": "Manutenção",
}

_CATEGORY_OF = {
    "traduzir_interface": "interface",
    "nome_do_app": "interface",
    "tema_escuro": "interface",
    "desbloquear_vip": "recursos",
    "remover_anuncios": "recursos",
    "remover_verificacao_licenca": "recursos",
    "permitir_http": "rede",
    "remover_permissao": "rede",
    "certificate_pinning": "rede",
    "explicar_crash": "diagnostico",
    "revisar_permissoes": "diagnostico",
    "mapear_fluxo": "diagnostico",
    "corrigir_build": "build",
    "corrigir_assinatura": "build",
    "atualizar_sdk": "manutencao",
    "limpar_logs": "manutencao",
}


def by_id(prompt_id: str) -> dict[str, Any] | None:
    return next((item for item in PROMPTS if item["id"] == prompt_id), None)


def category_of(prompt_id: str) -> str:
    return _CATEGORY_OF.get(prompt_id, "manutencao")


def grouped() -> dict[str, list[dict[str, Any]]]:
    """Prompts agrupados por categoria, na ordem de CATEGORIES."""
    result: dict[str, list[dict[str, Any]]] = {key: [] for key in CATEGORIES}
    for item in PROMPTS:
        result[category_of(item["id"])].append(item)
    return result


def needs_input(prompt_id: str) -> bool:
    """Prompts que terminam pedindo um dado do usuário (nome, permissão, stack trace)."""
    return prompt_id in {"nome_do_app", "remover_permissao", "explicar_crash",
                         "mapear_fluxo", "corrigir_build", "corrigir_assinatura",
                         "atualizar_sdk"}


# Prompts de diagnóstico: a resposta é uma explicação, não uma edição. Rodá-los em modo
# somente leitura evita que a IA "conserte" algo que você só queria entender.
READ_ONLY_PROMPTS = {"explicar_crash", "revisar_permissoes", "mapear_fluxo"}


def is_read_only(prompt_id: str) -> bool:
    """True quando o prompt só pede análise e não deve alterar arquivos."""
    return prompt_id in READ_ONLY_PROMPTS
