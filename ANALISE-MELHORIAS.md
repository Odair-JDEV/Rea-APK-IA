# Análise completa: melhorias, reorganização e prompts prontos

Documento de trabalho do ReaDroid. Cobre o estado atual do código, o que reorganizar, o que
melhorar em cada área e a biblioteca de prompts prontos para edição por IA.

> **Uso responsável.** Os prompts de "desbloquear VIP", "remover anúncios" e "desativar licença"
> existem para APKs seus, testes internos e aprendizado. Contornar cobrança, licença ou anúncio de
> um app de terceiros pode violar a lei e os termos do desenvolvedor. O ReaDroid pede confirmação
> explícita antes de usar esses prompts.

---

## 1. Estado atual

| Módulo | Linhas | Papel |
| --- | --- | --- |
| `app.py` | 792 | Menu, cores, entrada segura, navegação de arquivos, ações de análise |
| `ai.py` | 1313 | Provedores (OpenRouter, Codex, gateway), menu de IA, ciclo editar→reconstruir |
| `wizard.py` | 405 | Assistente guiado para iniciantes |
| `analyzer.py` | 349 | Inspeção, manifesto AXML, varredura de strings, JADX/Apktool |
| `builder.py` | 302 | `apktool b`, zipalign, keystore, assinatura, verificação |
| `agent.py` | 252 | Agente interno do gateway (ferramentas de arquivo) |
| `i18n.py` | 335 | Traduções pt/en/ar/hi |
| `axml.py` | 161 | Parser nativo de manifesto binário |
| `prompts.py` | novo | Biblioteca de prompts prontos |

**Pontos fortes:** núcleo sem dependências externas, parser AXML próprio, saída sanitizada,
backup e restauração, agente com limites de caminho, testes offline.

**Pontos fracos:** `ai.py` concentra responsabilidades demais; o menu principal e o menu de IA
usam letras e números misturados; não há histórico de builds; a análise não compara o APK
reconstruído com o original; não há relatório legível para leigos.

---

## 2. Reorganização de funcionalidades

### 2.1 Dividir `ai.py` (1313 linhas)

O arquivo hoje faz configuração, provedores, menu, ciclo de build e backup. Proposta:

```
readroid/ai/
├── __init__.py        # reexporta a API pública (compatível com o código atual)
├── settings.py        # chaves, ai.json, gateway, limites
├── providers.py       # opencode, codex, gateway, comandos e ambiente
├── gateway.py         # chat, descoberta de modelos, agente interno
├── menu.py            # _menu_loop, _setup, _choose_provider, _change_model
├── edit.py            # fix_loop, _edit_and_rebuild, _recreate_with_ai
└── backup.py          # criar, listar, restaurar
```

Ganho: cada arquivo abaixo de ~250 linhas, testes por área, e o `__init__.py` mantém
`from readroid import ai` funcionando sem tocar em `app.py` e `wizard.py`.

### 2.2 Unificar os dois menus

Hoje o menu principal usa números (1–15) e o menu de IA mistura números com letras
(`[P]`, `[B]`, `[L]`, `[R]`). Proposta: um único esquema.

- Menu principal: 1–9 análise, 10–12 build, 13 assistente, 14 idioma, 15 IA.
- Menu de IA: 1–9 ações, 10 configuração, 11 desativar, e as letras só para ações
  globais (`P` provedor, `B` backup, `L` limite, `R` prompts).

Alternativa mais limpa: transformar o menu de IA em submenu numerado e deixar letras apenas
para "voltar" e "ajuda".

### 2.3 Separar "analisar" de "editar"

O fluxo atual mistura leitura e escrita no mesmo menu. Proposta de três blocos explícitos:

1. **Analisar** (somente leitura): inspeção, manifesto, strings, relatórios.
2. **Editar** (escreve na pasta decodificada): edições rápidas, renomear pacote, IA, prompts.
3. **Construir** (gera APK): rebuild, alinhamento, assinatura, instalação.

Isso reduz o risco de alguém achar que está só analisando quando na verdade altera arquivos.

### 2.4 Estado do projeto por APK

Criar `output/<app>_apktool/.readroid.json` com: APK de origem, SHA-256, data da extração,
edições aplicadas, backups, último build e resultado. Hoje esse contexto se perde entre sessões.

---

## 3. Melhorias por área

### 3.1 Análise

- **Comparação antes/depois**: comparar o APK reconstruído com o original (tamanho, arquivos
  adicionados/removidos, manifesto alterado). É a verificação mais útil para quem edita.
- **Relatório legível**: gerar um `resumo.md` com o que o app faz, permissões perigosas,
  domínios e componentes exportados, em linguagem simples.
- **Heurísticas explicáveis**: cada alerta deve citar o arquivo e a linha que o gerou.
- **Cache por SHA-256**: não reanalisar o mesmo APK duas vezes.
- **Detecção de ofuscação**: indicar quando nomes de classe são curtos e sem sentido, para
  avisar que a edição por IA será mais difícil.

### 3.2 Build

- **Histórico de builds** em JSON: data, duração, etapas, resultado, SHA-256 do APK final.
- **Validação de instalação**: comparar `minSdkVersion` com a versão do dispositivo via `adb`.
- **Assinatura v4** quando o `apksigner` suportar.
- **Checagem de espaço em disco** antes de reconstruir.
- **Mensagens de erro traduzidas**: hoje o erro do apktool aparece cru.

### 3.3 IA

- **Prompts prontos** (implementado nesta rodada): biblioteca em `readroid/prompts.py`,
  acessível por `[R]` no menu de IA e por `P` na pergunta da opção 4.
- **Diff antes de aplicar**: mostrar o que a IA mudou e pedir confirmação antes de reconstruir.
- **Modo somente leitura**: prompts de diagnóstico não devem poder gravar arquivos.
- **Custo estimado**: contar tokens aproximados por chamada e mostrar no fim.
- **Retomada**: se o agente estourar o limite, permitir continuar de onde parou.

### 3.4 Interface

- **Ajuda contextual** (`?`) em cada menu.
- **Confirmação dupla** para ações destrutivas (apagar pasta, restaurar backup).
- **Barra de progresso** nas etapas longas (apktool, jadx).
- **Modo compacto** já existe; falta um modo "explicar cada opção" para iniciantes.

### 3.5 Qualidade

- **Testes de integração** com um APK mínimo gerado no próprio teste.
- **Cobertura** dos caminhos de erro (ferramenta ausente, disco cheio, permissão negada).
- **Lint** (`ruff`) e verificação de tipos (`mypy`) no CI.
- **CI multiplataforma**: hoje os testes de permissão falham no Windows.

---

## 4. Prompts prontos

Implementados em `readroid/prompts.py`. Todos seguem as regras: mexer só na pasta do APK,
não alterar `apktool.yml`, fazer a menor mudança possível e listar os arquivos alterados.

### Interface e textos

| Prompt | O que faz |
| --- | --- |
| Traduzir a interface | Traduz `strings.xml` mantendo chaves e marcadores |
| Mudar o nome do app | Altera só o rótulo do launcher |
| Forçar tema escuro | Aponta o tema padrão para o tema escuro existente |

### Recursos do próprio app

| Prompt | O que faz | Aviso |
| --- | --- | --- |
| Desbloquear VIP/premium | Localiza `isPremium`/billing e explica o ponto de decisão antes de mudar | Sim |
| Remover anúncios | Desativa a exibição sem remover bibliotecas | Sim |
| Desativar verificação de licença | Desativa LVL/checagem própria em builds de teste | Sim |

### Rede e segurança

| Prompt | O que faz | Aviso |
| --- | --- | --- |
| Permitir HTTP | Adiciona `usesCleartextTraffic` ou ajusta o network config | — |
| Remover permissão | Remove uma permissão e lista onde ela é usada | — |
| Desativar certificate pinning | Remove o pinning mantendo a validação TLS | Sim |

### Diagnóstico

| Prompt | O que faz |
| --- | --- |
| Explicar um crash | Analisa stack trace e aponta a causa provável |
| Revisar permissões | Lista riscos do manifesto com correção sugerida |
| Mapear o fluxo de uma tela | Explica activity, classes e origem dos dados |

### Build e assinatura

| Prompt | O que faz |
| --- | --- |
| Corrigir erro de reconstrução | Recebe o erro do apktool e propõe a correção mínima |
| Corrigir problema de assinatura | Investiga falha de assinatura ou alinhamento |

### Manutenção

| Prompt | O que faz |
| --- | --- |
| Ajustar targetSdkVersion | Explica o impacto antes de mudar |
| Remover logs de depuração | Remove `Log.v`/`Log.d`/`Log.i`, mantém `w` e `e` |

### Como usar

1. Menu principal → **15** (IA).
2. **`[R]`** → escolha a pasta do APK → escolha o prompt.
3. Prompts com aviso pedem confirmação de que o APK é seu.
4. Prompts que precisam de dado (nome, permissão, stack trace) pedem o texto antes de rodar.

Também é possível usar dentro da opção 4: quando ela pergunta a tarefa, digite `P`.

### Exemplo de prompt de VIP (texto completo)

```
Este é um APK meu e tenho autorização para modificá-lo.
Localize no código smali a verificação que decide se o usuário é VIP/premium
(procure por nomes como isPremium, isVip, isPro, isSubscribed, hasSubscription,
purchaseState, billing, BillingClient, e por constantes booleanas ligadas a essas checagens).
Antes de alterar, mostre os arquivos e trechos encontrados e explique qual é o ponto de decisão.
Depois, faça a menor mudança possível para que a checagem retorne verdadeiro,
preferindo alterar o método que calcula o estado em vez de cada tela.
Não remova a integração de cobrança, não apague classes e não quebre a inicialização.
Liste os arquivos alterados e explique o efeito de cada mudança.
```

O pedido de "mostre antes de alterar" é intencional: reduz o risco de a IA apagar código de
cobrança e quebrar o app, e deixa claro para você onde a decisão acontece.

---

## 5. Ordem sugerida de implementação

1. **Curto prazo** (baixo risco, alto ganho): prompts prontos (feito), histórico de builds,
   comparação antes/depois, ajuda contextual.
2. **Médio prazo**: dividir `ai.py`, unificar menus, estado por APK, relatório legível.
3. **Longo prazo**: diff antes de aplicar, modo somente leitura, retomada do agente,
   CI multiplataforma com lint e tipos.

Cada item deve vir com teste offline, sem rede e sem dispositivo, como o restante do projeto.

---

## 6. Estado da implementação

| Item | Situação | Onde |
| --- | --- | --- |
| Biblioteca de prompts prontos | feito | `readroid/prompts.py`, menu de IA `[R]` |
| Histórico de builds | feito | `readroid/history.py`, opção 16 |
| Comparação antes/depois | feito | `readroid/compare.py`, opção 16 e pós-build |
| Ajuda contextual | feito | `?` no menu principal |
| Estado por APK | feito | `output/<app>_apktool/.readroid.json` |
| Relatório legível | feito | `readroid/report.py`, opção 17 |
| Cache de análise por SHA-256 | feito | `readroid/cache.py` |
| Detecção de ofuscação | feito | `readroid/obfuscation.py` |
| Checagem de espaço e minSdk | feito | `readroid/checks.py`, antes do build |
| Diff antes de aplicar | feito (gateway) | `agent.run(dry_run=True)`, menu de IA `[D]` |
| Modo somente leitura | feito (gateway) | `agent.run(read_only=True)`, prompts de diagnóstico |
| Retomada do agente | feito | `agent.save_session/load_session`, menu de IA 09; sessões em `.readroid_sessions/` |
| CI multiplataforma | feito | `.github/workflows/ci.yml`: Ubuntu+Windows, Python 3.10/3.12, ruff |
| Dividir `ai.py` em pacote | **não feito, de propósito** | ver nota abaixo |
| Unificar menus | feito (na prática) | IA inteiramente numerada (01–13); letras `[R]/[D]/[B]/[P]/[L]` continuam como atalhos |

**Por que `ai.py` não foi dividido.** A divisão em pacote quebraria os testes e a API interna que
fazem `patch.object(ai, "gateway_chat", ...)` e `patch.object(ai, "find_opencode", ...)`: com
submódulos, as chamadas internas deixariam de passar pelo namespace do pacote e o patch não teria
efeito. O ganho seria organizacional, o custo seria reescrever a suíte inteira de IA. Fica como
trabalho futuro, junto com a unificação completa dos menus.
