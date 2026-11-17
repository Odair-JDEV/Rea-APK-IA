"""Minimal, persistent interface translations for ReaDroid (standard library only)."""
from __future__ import annotations

import json
import os
from pathlib import Path

LANGUAGES = {
    "pt": "Português",
    "en": "English",
    "ar": "العربية",
    "hi": "हिन्दी",
}
CONFIG_DIR = Path(os.environ.get("XDG_CONFIG_HOME", Path.home() / ".config")) / "readroid"
CONFIG_FILE = CONFIG_DIR / "settings.json"

# Keys are Portuguese source strings; unknown strings safely remain in Portuguese.
TRANSLATIONS = {
"en": {
"IA opcional · Sem root · Offline por padrão":"Optional AI · No root · Offline by default", "opcional":"optional", "Cancelar":"Cancel",
"Inspecionar estrutura do APK":"Inspect APK structure", "Analisar manifesto e permissões":"Analyze manifest and permissions",
"Buscar URLs, domínios e IPs":"Find URLs, domains and IPs", "Decompilar para Java com JADX":"Decompile to Java with JADX",
"Extrair smali e recursos com Apktool":"Extract smali and resources with Apktool", "Verificar dependências":"Check dependencies",
"Abrir pasta de relatórios":"Open reports folder", "Abrir pasta de resultados":"Open output folder",
"Explorar e abrir arquivos gerados":"Browse and open generated files", "Edições rápidas e renomear pacote (pré-build)":"Quick edits and rename package (pre-build)",
"Reconstruir, alinhar e assinar APK":"Rebuild, align and sign APK", "Gerenciar chave de assinatura":"Manage signing key",
"Idioma / Language / اللغة / भाषा":"Language / Idioma / اللغة / भाषा", "Sair":"Exit", "Assistente IA":"AI assistant",
"Escolha o idioma:":"Choose language:", "Idioma salvo:":"Language saved:", "Opção não reconhecida.":"Unknown option.",
"Até a próxima. ReaDroid encerrado.":"See you next time. ReaDroid closed.", "ReaDroid > ":"ReaDroid > ",
"APKs encontrados nas pastas comuns:":"APKs found in common folders:", "Escolha um APK: ":"Choose an APK: ",
"[P] Informar outro caminho":"[P] Enter another path", "Caminho completo do APK: ":"Full APK path: ",
"Nenhum arquivo informado.":"No file provided.", "Arquivo não encontrado.":"File not found.",
"Seleção não reconhecida; informe o caminho manualmente.":"Selection not recognized; enter the path manually.",
"ENTER para voltar ao menu...":"Press ENTER to return to menu...", "VERIFICAÇÃO DE DEPENDÊNCIAS":"DEPENDENCY CHECK",
"não encontrado":"not found", "APK pronto:":"APK ready:", "Cópia em:":"Copy saved to:",
"A reconstrução não terminou. Veja os passos acima.":"Rebuild did not finish. See the steps above.",
"A assinatura não foi validada; não instale este APK.":"Signature verification failed; do not install this APK.",
"Assistente guiado (iniciantes)":"Guided assistant (beginners)", "Assistente":"Assistant",
"=== Assistente ReaDroid: APK do início ao fim ===":"=== ReaDroid Assistant: APK from start to finish ===",
"Verificando ferramentas...":"Checking tools...", "Pode funcionar sem, mas o APK pode não instalar em Android 7+":"May work without, but APK may not install on Android 7+",
"Instale se quiser usar esta funcionalidade":"Install if you want to use this feature",
"Algumas ferramentas obrigatórias faltando. Instale antes de continuar.":"Some required tools are missing. Install them before continuing.",
"Extraindo com Apktool...":"Extracting with Apktool...",
"Falha na extração:":"Extraction failed:",
"Extraído em:":"Extracted to:",
"Edições rápidas disponíveis:":"Available quick edits:",
"Números (ex: 1,3) ou ENTER para pular:":"Numbers (e.g. 1,3) or ENTER to skip:",
"Aplicado:":"Applied:",
"Renomear pacote (applicationId)?":"Rename package (applicationId)?",
"Cancelado.":"Cancelled.",
"Novo nome do pacote (ex: com.exemplo.app):":"New package name (e.g. com.example.app):",
"Nome inválido. Use formato com.exemplo.app":"Invalid name. Use format like com.example.app",
"Pacote renomeado:":"Package renamed:",
"Usar IA para editar/corrigir arquivos?":"Use AI to edit/fix files?",
"Módulo de IA não disponível (readroid/ai.py).":"AI module not available (readroid/ai.py).",
"IA não configurada. Configure no menu principal (opção 13).":"AI not configured. Set up in main menu (option 15).",
"A IA vai editar arquivos na pasta decodificada. Backup será criado.":"AI will edit files in decoded folder. Backup will be created.",
"Backup:":"Backup:",
"Não foi possível criar backup. Continuar sem?":"Could not create backup. Continue without?",
"IA não conseguiu reconstruir:":"AI could not rebuild:",
"Iniciando reconstrução...":"Starting rebuild...",
"Reconstrução (apktool b)":"Rebuild (apktool b)", "Alinhamento (zipalign)":"Alignment (zipalign)",
"Assinatura":"Signature", "Verificação":"Verification",
"Falha na reconstrução.":"Rebuild failed.",
"Instalação":"Installation",
"O APK reconstruído é reassinado — NÃO substitui a versão da loja.":"The rebuilt APK is re-signed — it does NOT replace the store version.",
"Deseja tentar instalar no dispositivo?":"Try installing on device?",
"Tentando via ADB...":"Trying via ADB...",
"ADB falhou:":"ADB failed:",
"Tentando abridor do sistema...":"Trying system opener...",
"Abrindo instalador do Android...":"Opening Android installer...",
"Verifique o instalador do Android na tela.":"Check the Android installer on your screen.",
"Nenhum instalador disponível (adb/termux-open).":"No installer available (adb/termux-open).",
"APK salvo em:":"APK saved to:",
"Continuar para reconstrução?":"Continue to rebuild?",
"Pasta decodificada mantida em:":"Decoded folder kept at:",
},
"ar": {
"IA opcional · Sem root · Offline por padrão":"ذكاء اصطناعي اختياري · دون صلاحيات root · يعمل دون اتصال افتراضيًا", "opcional":"اختياري", "Cancelar":"إلغاء",
"Inspecionar estrutura do APK":"فحص بنية APK", "Analisar manifesto e permissões":"تحليل البيان والأذونات",
"Buscar URLs, domínios e IPs":"البحث عن الروابط والنطاقات وعناوين IP", "Decompilar para Java com JADX":"فك التحويل إلى Java باستخدام JADX",
"Extrair smali e recursos com Apktool":"استخراج smali والموارد باستخدام Apktool", "Verificar dependências":"فحص المتطلبات",
"Abrir pasta de relatórios":"فتح مجلد التقارير", "Abrir pasta de resultados":"فتح مجلد النتائج",
"Explorar e abrir arquivos gerados":"استعراض الملفات الناتجة وفتحها", "Edições rápidas e renomear pacote (pré-build)":"تعديلات سريعة وإعادة تسمية الحزمة",
"Reconstruir, alinhar e assinar APK":"إعادة بناء APK ومحاذاته وتوقيعه", "Gerenciar chave de assinatura":"إدارة مفتاح التوقيع",
"Idioma / Language / اللغة / भाषा":"اللغة / Language / Idioma / भाषा", "Sair":"خروج", "Assistente IA":"مساعد الذكاء الاصطناعي",
"Escolha o idioma:":"اختر اللغة:", "Idioma salvo:":"تم حفظ اللغة:", "Opção não reconhecida.":"خيار غير معروف.",
"Até a próxima. ReaDroid encerrado.":"إلى اللقاء. تم إغلاق ReaDroid.", "ReaDroid > ":"ReaDroid > ",
"APKs encontrados nas pastas comuns:":"ملفات APK الموجودة في المجلدات الشائعة:", "Escolha um APK: ":"اختر ملف APK: ",
"[P] Informar outro caminho":"[P] إدخال مسار آخر", "Caminho completo do APK: ":"المسار الكامل لملف APK: ",
"Nenhum arquivo informado.":"لم يتم إدخال ملف.", "Arquivo não encontrado.":"الملف غير موجود.",
"Seleção não reconhecida; informe o caminho manualmente.":"اختيار غير معروف؛ أدخل المسار يدويًا.",
"ENTER para voltar ao menu...":"اضغط ENTER للعودة إلى القائمة...", "VERIFICAÇÃO DE DEPENDÊNCIAS":"فحص المتطلبات",
"não encontrado":"غير موجود", "APK pronto:":"ملف APK جاهز:", "Cópia em:":"تم حفظ نسخة في:",
"A reconstrução não terminou. Veja os passos acima.":"لم تكتمل إعادة البناء. راجع الخطوات أعلاه.",
"A assinatura não foi validada; não instale este APK.":"فشل التحقق من التوقيع؛ لا تثبّت ملف APK هذا.",
},
"hi": {
"IA opcional · Sem root · Offline por padrão":"वैकल्पिक AI · root के बिना · डिफ़ॉल्ट रूप से ऑफ़लाइन", "opcional":"वैकल्पिक", "Cancelar":"रद्द करें",
"Inspecionar estrutura do APK":"APK संरचना जाँचें", "Analisar manifesto e permissões":"मैनिफेस्ट और अनुमतियाँ जाँचें",
"Buscar URLs, domínios e IPs":"URL, डोमेन और IP खोजें", "Decompilar para Java com JADX":"JADX से Java में डीकंपाइल करें",
"Extrair smali e recursos com Apktool":"Apktool से smali और संसाधन निकालें", "Verificar dependências":"निर्भरताएँ जाँचें",
"Abrir pasta de relatórios":"रिपोर्ट फ़ोल्डर खोलें", "Abrir pasta de resultados":"आउटपुट फ़ोल्डर खोलें",
"Explorar e abrir arquivos gerados":"बनाई गई फ़ाइलें देखें और खोलें", "Edições rápidas e renomear pacote (pré-build)":"त्वरित संपादन और पैकेज का नाम बदलें",
"Reconstruir, alinhar e assinar APK":"APK पुनर्निर्माण, संरेखण और हस्ताक्षर", "Gerenciar chave de assinatura":"हस्ताक्षर कुंजी प्रबंधित करें",
"Idioma / Language / اللغة / भाषा":"भाषा / Language / Idioma / اللغة", "Sair":"बाहर निकलें", "Assistente IA":"AI सहायक",
"Escolha o idioma:":"भाषा चुनें:", "Idioma salvo:":"भाषा सहेजी गई:", "Opção não reconhecida.":"अज्ञात विकल्प।",
"Até a próxima. ReaDroid encerrado.":"फिर मिलेंगे। ReaDroid बंद हो गया।", "ReaDroid > ":"ReaDroid > ",
"APKs encontrados nas pastas comuns:":"सामान्य फ़ोल्डरों में APK मिले:", "Escolha um APK: ":"APK चुनें: ",
"[P] Informar outro caminho":"[P] दूसरा पथ दर्ज करें", "Caminho completo do APK: ":"APK का पूरा पथ: ",
"Nenhum arquivo informado.":"कोई फ़ाइल नहीं दी गई।", "Arquivo não encontrado.":"फ़ाइल नहीं मिली।",
"Seleção não reconhecida; informe o caminho manualmente.":"चयन समझ नहीं आया; पथ स्वयं दर्ज करें।",
"ENTER para voltar ao menu...":"मेनू पर लौटने के लिए ENTER दबाएँ...", "VERIFICAÇÃO DE DEPENDÊNCIAS":"निर्भरता जाँच",
"não encontrado":"नहीं मिला", "APK pronto:":"APK तैयार:", "Cópia em:":"कॉपी यहाँ सहेजी गई:",
"A reconstrução não terminou. Veja os passos acima.":"पुनर्निर्माण पूरा नहीं हुआ। ऊपर दिए गए चरण देखें।",
"A assinatura não foi validada; não instale este APK.":"हस्ताक्षर सत्यापन विफल; इस APK को इंस्टॉल न करें।",
}}

TRANSLATIONS["en"].update({
    "A análise falhou:": "Analysis failed:", "O arquivo original não foi modificado.": "The original file was not modified.",
    "Inspeção APK": "APK inspection", "Manifesto": "Manifest", "Scanner strings": "String scanner",
    "Pastas decodificadas com Apktool:": "Decoded folders from Apktool:", "Escolha a pasta: ": "Choose a folder: ",
    "Pasta não encontrada.": "Folder not found.", "Chave de assinatura": "Signing key", "Verificação": "Verification",
    "Reconstrução (apktool b)": "Rebuild (apktool b)", "Alinhamento (zipalign)": "Alignment (zipalign)", "Assinatura": "Signature",
    "Edições": "Edits", "Nenhuma edição válida selecionada.": "No valid edits selected.",
    "Quando terminar de editar, use a opção 11 para reconstruir, alinhar e assinar.": "When editing is complete, use option 11 to rebuild, align and sign.",
    "Use só em APKs seus ou que você tem autorização para modificar.": "Only use this on APKs you own or are authorized to modify.",
    "A extração pode levar alguns minutos. O APK original não será alterado.": "Extraction may take a few minutes. The original APK will not be modified.",
    "Destino:": "Destination:", "Conteúdo:": "Contents:", "Pasta:": "Folder:",
    "Manifesto não decodificado. Veja a mensagem no relatório.": "Manifest not decoded. See the report message.",
})
TRANSLATIONS["ar"].update({
    "A análise falhou:": "فشل التحليل:", "O arquivo original não foi modificado.": "لم يتم تعديل الملف الأصلي.",
    "Inspeção APK": "فحص APK", "Manifesto": "البيان", "Scanner strings": "فاحص النصوص",
    "Pastas decodificadas com Apktool:": "المجلدات المفكوكة باستخدام Apktool:", "Escolha a pasta: ": "اختر مجلدًا: ",
    "Pasta não encontrada.": "المجلد غير موجود.", "Chave de assinatura": "مفتاح التوقيع", "Verificação": "التحقق",
    "Reconstrução (apktool b)": "إعادة البناء (apktool b)", "Alinhamento (zipalign)": "المحاذاة (zipalign)", "Assinatura": "التوقيع",
    "Edições": "التعديلات", "Nenhuma edição válida selecionada.": "لم يتم اختيار تعديلات صالحة.",
    "Quando terminar de editar, use a opção 11 para reconstruir, alinhar e assinar.": "بعد الانتهاء من التعديل، استخدم الخيار 11 لإعادة البناء والمحاذاة والتوقيع.",
    "Use só em APKs seus ou que você tem autorização para modificar.": "استخدم هذا فقط مع ملفات APK التي تملكها أو لديك إذن بتعديلها.",
    "A extração pode levar alguns minutos. O APK original não será alterado.": "قد يستغرق الاستخراج بضع دقائق. لن يتم تعديل ملف APK الأصلي.",
    "Destino:": "الوجهة:", "Conteúdo:": "المحتويات:", "Pasta:": "المجلد:",
    "Manifesto não decodificado. Veja a mensagem no relatório.": "تعذر فك البيان. راجع الرسالة في التقرير.",
})
TRANSLATIONS["hi"].update({
    "A análise falhou:": "विश्लेषण विफल:", "O arquivo original não foi modificado.": "मूल फ़ाइल में बदलाव नहीं किया गया।",
    "Inspeção APK": "APK निरीक्षण", "Manifesto": "मैनिफ़ेस्ट", "Scanner strings": "स्ट्रिंग स्कैनर",
    "Pastas decodificadas com Apktool:": "Apktool से डिकोड किए गए फ़ोल्डर:", "Escolha a pasta: ": "फ़ोल्डर चुनें: ",
    "Pasta não encontrada.": "फ़ोल्डर नहीं मिला।", "Chave de assinatura": "हस्ताक्षर कुंजी", "Verificação": "सत्यापन",
    "Reconstrução (apktool b)": "पुनर्निर्माण (apktool b)", "Alinhamento (zipalign)": "संरेखण (zipalign)", "Assinatura": "हस्ताक्षर",
    "Edições": "संपादन", "Nenhuma edição válida selecionada.": "कोई मान्य संपादन नहीं चुना गया।",
    "Quando terminar de editar, use a opção 11 para reconstruir, alinhar e assinar.": "संपादन के बाद पुनर्निर्माण, संरेखण और हस्ताक्षर के लिए विकल्प 11 चुनें।",
    "Use só em APKs seus ou que você tem autorização para modificar.": "केवल अपने या अनुमति प्राप्त APK पर उपयोग करें।",
    "A extração pode levar alguns minutos. O APK original não será alterado.": "निकालने में कुछ मिनट लग सकते हैं। मूल APK नहीं बदलेगा।",
    "Destino:": "गंतव्य:", "Conteúdo:": "सामग्री:", "Pasta:": "फ़ोल्डर:",
    "Manifesto não decodificado. Veja a mensagem no relatório.": "मैनिफ़ेस्ट डिकोड नहीं हुआ। रिपोर्ट में संदेश देखें।",
})


def load_language() -> str:
    try:
        lang = json.loads(CONFIG_FILE.read_text(encoding="utf-8")).get("language", "pt")
        return lang if lang in LANGUAGES else "pt"
    except (OSError, ValueError, TypeError):
        return "pt"

_language = load_language()

# compact menu labels v1
TRANSLATIONS["en"].update({"Inspec. APK":"APK scan","Decompilar":"Decompile","Extrair smali":"Smali","Dependencias":"Deps","Relatorios":"Reports","Resultados":"Results","Ver arquivos":"Files","Edicoes":"Edits","Assinar APK":"Sign APK","Chave APK":"APK key","Assistente IA":"AI","Idioma":"Lang","Sair":"Exit"})

TRANSLATIONS.setdefault("ar", {}).update({"Inspec. APK":"APK","Decompilar":"تفكيك","Extrair smali":"Smali","Dependencias":"تبعيات","Relatorios":"تقارير","Resultados":"نتائج","Ver arquivos":"ملفات","Edicoes":"تعديل","Assinar APK":"توقيع","Chave APK":"مفتاح","Assistente IA":"AI","Idioma":"لغة","Sair":"خروج"})
TRANSLATIONS.setdefault("hi", {}).update({"Inspec. APK":"APK","Decompilar":"डिकंपाइल","Extrair smali":"Smali","Dependencias":"Deps","Relatorios":"रिपोर्ट","Resultados":"परिणाम","Ver arquivos":"फ़ाइलें","Edicoes":"संपादन","Assinar APK":"साइन APK","Chave APK":"APK कुंजी","Assistente IA":"AI","Idioma":"भाषा","Sair":"बाहर"})


# OFFTEC_FULL_UI_TRANSLATIONS
TRANSLATIONS["en"].update({
    "SISTEMA":"SYSTEM", "MENU":"MENU", "Sem root":"No root",
    "Ver:":"Version:", "Offline":"Offline", "Dependencias":"Deps",
    "Relatorios":"Reports", "Resultados":"Results", "Ver arquivos":"Files",
    "Edicoes":"Edits", "Chave APK":"APK key", "Inspec. APK":"APK scan",
    "Reconstrução e compilação automatizada":"Automated rebuild and compilation",
    "Essa pasta não parece ser uma saída do Apktool (opção 5). Confira o caminho.":"This folder does not look like Apktool output (option 5). Check the path.",
    "Continuar mesmo assim?":"Continue anyway?",
    "Aplicar alguma edição rápida antes de compilar?":"Apply quick edits before building?",
    "Números separados por vírgula:":"Comma-separated numbers:",
    "Renomear o pacote (applicationId) antes de compilar?":"Rename the package (applicationId) before building?",
    "pulado":"skipped", "falhou":"failed", "Edições":"Edits",
    "Reconstrução (apktool b)":"Rebuild (apktool b)",
    "Alinhamento (zipalign)":"Alignment (zipalign)",
    "Chave de assinatura":"Signing key", "Assinatura":"Signature",
    "Verificação":"Verification", "APK pronto:":"APK ready:",
    "Abrir o instalador do Android agora?":"Open the Android installer now?",
    "A reconstrução não terminou. Veja os passos acima.":"The rebuild did not finish. See the steps above.",
    "Em uso:":"In use:", "Alias padrão:":"Default alias:",
    "a senha padrão é":"the default password is",
    "troque editando builder.py se quiser outra":"change it in builder.py to use another",
    "Apagar esta chave e gerar outra no próximo build?":"Delete this key and generate another on the next build?",
    "Chave removida. Uma nova será criada na próxima reconstrução.":"Key removed. A new one will be created during the next rebuild.",
    "Nenhuma chave gerada ainda. Ela é criada automaticamente na primeira":"No key has been generated yet. It is created automatically during the first",
    "reconstrução (opção 11) e reaproveitada nas seguintes.":"rebuild (option 11) and reused for later builds.",
    "Local:":"Location:", "Dica: use a opção 11 para gerar um APK e depois 'readroid verify' nele.":"Tip: use option 11 to build an APK, then run 'readroid verify' on it.",
    "Reassinar troca a identidade do desenvolvedor original; o resultado":"Re-signing changes the original developer identity; the result",
    "não substitui o app da loja nem deve ser redistribuído sem permissão.":"does not replace the store app and must not be redistributed without permission.",
    "Essa pasta não parece ser uma saída do Apktool":"This folder does not appear to be Apktool output",
    "Abrir >":"Open >", "Explorar >":"Browse >",
    "ARQUIVOS GERADOS":"GENERATED FILES",
    "Código decompilado e recursos (output)":"Decompiled code and resources (output)",
    "Relatórios JSON (reports)":"JSON reports (reports)",
    "APKs reconstruídos e assinados (builds)":"Rebuilt and signed APKs (builds)",
    "Voltar ao menu principal":"Return to main menu",
    "Opção inválida.":"Invalid option.",
    "Seleção inválida.":"Invalid selection.",
    "Pasta não encontrada.":"Folder not found.",
    "Caminho fora das pastas de resultados bloqueado.":"Path outside the output folders is blocked.",
    "Abrindo com o aplicativo Android associado...":"Opening with the associated Android app...",
    "Não foi possível abrir externamente. Caminho:":"Could not open externally. Path:",
    "Não há termux-open instalado. Caminho do arquivo:":"termux-open is not installed. File path:",
    "Instale o pacote termux-tools para abrir arquivos no Android.":"Install the termux-tools package to open files on Android.",
    "Novo pacote (ex: com.exemplo.app) ou ENTER para pular:":"New package (e.g. com.example.app), or ENTER to skip:",
    "Nome inválido. Use letras/números/'_' e pelo menos um ponto, ex: com.exemplo.app":"Invalid name. Use letters, numbers, '_' and at least one dot, e.g. com.example.app",
    "Edições rápidas disponíveis:":"Available quick edits:",
    "Números separados por vírgula (ex: 1,3), ou ENTER para pular:":"Comma-separated numbers (e.g. 1,3), or ENTER to skip:",
    "Aplicado:":"Applied:", "Nenhuma edição válida selecionada.":"No valid edits selected.",
    "Quando terminar de editar, use a opção 11 para reconstruir, alinhar e assinar.":"When editing is complete, use option 11 to rebuild, align and sign.",
    "Use só em APKs seus ou que você tem autorização para modificar.":"Only use APKs you own or are authorized to modify.",
    "Aplicar alguma edição rápida antes de compilar? (s/N):":"Apply quick edits before building? (y/N):",
    "Renomear o pacote (applicationId) também? (s/N):":"Rename the package (applicationId) too? (y/N):",
    "Renomear o pacote (applicationId) antes de compilar? (s/N):":"Rename the package (applicationId) before building? (y/N):",
    "Salvar em":"Save to", "A extração pode levar alguns minutos. O APK original não será alterado.":"Extraction may take a few minutes. The original APK will not be changed.",
    "Edite os arquivos dentro dessa pasta e depois use as opções 10/11.":"Edit the files in this folder, then use options 10/11.",
    "Android":"Android", "Python":"Python", "Java":"Java", "JADX":"JADX",
    "APKtool":"APKtool", "Sign":"Sign",
})
TRANSLATIONS["ar"].update({
    "SISTEMA":"النظام", "MENU":"القائمة", "Sem root":"بدون صلاحيات root",
    "Ver:":"الإصدار:", "Offline":"دون اتصال",
    "Reconstrução e compilação automatizada":"إعادة البناء والتجميع تلقائيًا",
    "Continuar mesmo assim?":"هل تريد المتابعة رغم ذلك؟",
    "Aplicar alguma edição rápida antes de compilar?":"هل تريد تطبيق تعديلات سريعة قبل البناء؟",
    "Números separados por vírgula:":"أدخل الأرقام مفصولة بفواصل:",
    "Renomear o pacote (applicationId) antes de compilar?":"هل تريد تغيير اسم الحزمة قبل البناء؟",
    "pulado":"تم التخطي", "falhou":"فشل",
    "APK pronto:":"ملف APK جاهز:", "Abrir o instalador do Android agora?":"هل تريد فتح مثبت Android الآن؟",
    "A reconstrução não terminou. Veja os passos acima.":"لم تكتمل إعادة البناء. راجع الخطوات أعلاه.",
    "Em uso:":"قيد الاستخدام:", "Alias padrão:":"الاسم المستعار الافتراضي:",
    "Apagar esta chave e gerar outra no próximo build?":"هل تريد حذف هذا المفتاح وإنشاء آخر عند البناء التالي؟",
    "Chave removida. Uma nova será criada na próxima reconstrução.":"تم حذف المفتاح. سيتم إنشاء مفتاح جديد عند إعادة البناء.",
    "Local:":"الموقع:", "ARQUIVOS GERADOS":"الملفات المُنشأة",
    "Código decompilado e recursos (output)":"الكود المفكك والموارد (output)",
    "Relatórios JSON (reports)":"تقارير JSON (reports)",
    "APKs reconstruídos e assinados (builds)":"ملفات APK المعاد بناؤها والموقعة (builds)",
    "Voltar ao menu principal":"العودة إلى القائمة الرئيسية",
    "Opção inválida.":"خيار غير صالح.", "Seleção inválida.":"اختيار غير صالح.",
    "Pasta não encontrada.":"المجلد غير موجود.",
    "Caminho fora das pastas de resultados bloqueado.":"تم حظر المسار خارج مجلدات النتائج.",
    "Abrindo com o aplicativo Android associado...":"جارٍ الفتح باستخدام تطبيق Android المرتبط...",
    "Instale o pacote termux-tools para abrir arquivos no Android.":"ثبّت حزمة termux-tools لفتح الملفات على Android.",
    "Edições rápidas disponíveis:":"التعديلات السريعة المتاحة:",
    "Aplicado:":"تم التطبيق:", "Android":"Android", "Python":"Python",
    "Java":"Java", "JADX":"JADX", "APKtool":"APKtool", "Sign":"التوقيع",
})
TRANSLATIONS["hi"].update({
    "SISTEMA":"सिस्टम", "MENU":"मेनू", "Sem root":"बिना root",
    "Ver:":"संस्करण:", "Offline":"ऑफ़लाइन",
    "Reconstrução e compilação automatizada":"स्वचालित पुनर्निर्माण और संकलन",
    "Continuar mesmo assim?":"क्या फिर भी जारी रखें?",
    "Aplicar alguma edição rápida antes de compilar?":"बिल्ड से पहले त्वरित संपादन लागू करें?",
    "Números separados por vírgula:":"अल्पविराम से अलग किए गए नंबर:",
    "Renomear o pacote (applicationId) antes de compilar?":"बिल्ड से पहले पैकेज का नाम बदलें?",
    "pulado":"छोड़ा गया", "falhou":"विफल",
    "APK pronto:":"APK तैयार:", "Abrir o instalador do Android agora?":"Android इंस्टॉलर अभी खोलें?",
    "A reconstrução não terminou. Veja os passos acima.":"पुनर्निर्माण पूरा नहीं हुआ। ऊपर दिए गए चरण देखें।",
    "Em uso:":"उपयोग में:", "Alias padrão:":"डिफ़ॉल्ट उपनाम:",
    "Apagar esta chave e gerar outra no próximo build?":"क्या यह कुंजी हटाकर अगले बिल्ड में नई बनाएं?",
    "Chave removida. Uma nova será criada na próxima reconstrução.":"कुंजी हटा दी गई। अगले पुनर्निर्माण में नई बनेगी।",
    "Local:":"स्थान:", "ARQUIVOS GERADOS":"बनाई गई फ़ाइलें",
    "Código decompilado e recursos (output)":"डिकंपाइल कोड और संसाधन (output)",
    "Relatórios JSON (reports)":"JSON रिपोर्ट (reports)",
    "APKs reconstruídos e assinados (builds)":"पुनर्निर्मित और हस्ताक्षरित APK (builds)",
    "Voltar ao menu principal":"मुख्य मेनू पर लौटें",
    "Opção inválida.":"अमान्य विकल्प।", "Seleção inválida.":"अमान्य चयन।",
    "Pasta não encontrada.":"फ़ोल्डर नहीं मिला।",
    "Caminho fora das pastas de resultados bloqueado.":"आउटपुट फ़ोल्डर के बाहर का पथ ब्लॉक है।",
    "Abrindo com o aplicativo Android associado...":"संबंधित Android ऐप से खोला जा रहा है...",
    "Instale o pacote termux-tools para abrir arquivos no Android.":"Android पर फ़ाइलें खोलने के लिए termux-tools इंस्टॉल करें।",
    "Edições rápidas disponíveis:":"उपलब्ध त्वरित संपादन:",
    "Aplicado:":"लागू किया गया:", "Android":"Android", "Python":"Python",
    "Java":"Java", "JADX":"JADX", "APKtool":"APKtool", "Sign":"हस्ताक्षर",
})

def get_language() -> str:
    return _language

def set_language(lang: str) -> None:
    global _language
    if lang not in LANGUAGES:
        raise ValueError("Idioma inválido")
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    temp = CONFIG_FILE.with_suffix(".tmp")
    temp.write_text(json.dumps({"language": lang}, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    temp.replace(CONFIG_FILE)
    _language = lang

def tr(text: str) -> str:
    table = TRANSLATIONS.get(_language, {})
    if text in table:
        return table[text]
    # Translate known phrases inside coloured/interpolated UI strings too.
    for source in sorted(table, key=len, reverse=True):
        if source and source in text:
            text = text.replace(source, table[source])
    return text

# ------------------------------------------------------------------ assistente guiado
_WIZARD_EN = {'\nENTER para continuar...': '\nPress ENTER to continue...', 'Verificando ferramentas...': 'Checking tools...', 'Reconstruir APK (obrigatório)': 'Rebuild APK (required)', 'Keytool/assinatura (obrigatório)': 'Keytool/signing (required)', 'Alinhar APK (recomendado para instalação)': 'Align APK (recommended for install)', 'Assinatura v1+v2+v3 (recomendado)': 'v1+v2+v3 signing (recommended)', 'Gerar chave de assinatura (se não existir)': 'Generate signing key (if missing)', 'Instalar via ADB (opcional)': 'Install via ADB (optional)', 'Instale: pkg install ': 'Install with: pkg install ', 'Algumas ferramentas obrigatórias faltando. Instale antes de continuar.': 'Some required tools are missing. Install them before continuing.', 'Nenhum APK selecionado.': 'No APK selected.', 'Pasta já existe para este APK; reutilizando: ': 'Folder already exists for this APK; reusing: ', 'A pasta já existe, mas não corresponde a este APK: ': 'The folder exists but does not match this APK: ', 'Apagar essa pasta e extrair de novo?': 'Delete that folder and extract again?', 'Extração cancelada. Escolha outro APK ou remova a pasta manualmente.': 'Extraction cancelled. Choose another APK or remove the folder manually.', 'Não foi possível apagar a pasta: ': 'Could not delete the folder: ', 'Extraindo com Apktool...': 'Extracting with Apktool...', 'Falha na extração: ': 'Extraction failed: ', 'Extraído em: ': 'Extracted to: ', 'Edições rápidas disponíveis:': 'Available quick edits:', 'Números (ex: 1,3) ou ENTER para pular: ': 'Numbers (e.g. 1,3) or ENTER to skip: ', 'Aplicado: ': 'Applied: ', 'Falha: ': 'Failed: ', 'Renomear pacote (applicationId)?': 'Rename package (applicationId)?', 'Novo nome do pacote (ex: com.exemplo.app): ': 'New package name (e.g. com.example.app): ', 'Cancelado.': 'Cancelled.', 'Nome inválido. Use formato com.exemplo.app': 'Invalid name. Use a format like com.example.app', 'Pacote renomeado: ': 'Package renamed: ', 'Edição manual': 'Manual editing', 'Arquivos em: ': 'Files in: ', 'Edite com o editor que preferir. Quando terminar, volte a esta janela.': 'Edit with your preferred editor. When done, return to this window.', 'ENTER quando terminar de editar (ou ENTER para pular): ': 'Press ENTER when done editing (or ENTER to skip): ', 'Usar IA para editar/corrigir arquivos?': 'Use AI to edit/fix files?', 'Módulo de IA não disponível (readroid/ai.py).': 'AI module not available (readroid/ai.py).', 'IA não configurada. Configure no menu de IA (opção 13).': 'AI not configured. Set it up in the AI menu.', 'O que a IA deve fazer? (ex: traduzir a interface para português): ': 'What should the AI do? (e.g. translate the UI to English): ', 'Nada informado; edição por IA cancelada.': 'Nothing provided; AI edit cancelled.', 'A IA vai editar arquivos na pasta decodificada. Backup será criado.': 'The AI will edit files in the decoded folder. A backup will be created.', 'Continuar?': 'Continue?', 'Não foi possível criar o backup. A edição por IA foi cancelada.': 'Could not create the backup. The AI edit was cancelled.', 'Backup: ': 'Backup: ', 'A IA terminou e o APK foi reconstruído.': 'The AI finished and the APK was rebuilt.', 'IA não conseguiu reconstruir: ': 'The AI could not rebuild: ', 'Para desfazer as mudanças da IA, restaure o backup: ': 'To undo the AI changes, restore the backup: ', 'Edições rápidas': 'Quick edits', 'Reconstrução (apktool b)': 'Rebuild (apktool b)', 'Alinhamento (zipalign)': 'Alignment (zipalign)', 'Chave de assinatura': 'Signing key', 'Assinatura': 'Signature', 'Verificação': 'Verification', 'Falha na reconstrução.': 'Rebuild failed.', 'APK reconstruído: ': 'APK rebuilt: ', 'SHA256: ': 'SHA256: ', 'Atenção: o APK NÃO foi alinhado (zipalign ausente). ': 'Warning: the APK was NOT aligned (zipalign missing). ', 'Pode falhar ao instalar em Android 7+.': 'It may fail to install on Android 7+.', 'Atenção: a assinatura NÃO foi verificada (apksigner ausente). ': 'Warning: the signature was NOT verified (apksigner missing). ', 'Instale o apksigner antes de confiar neste APK.': 'Install apksigner before trusting this APK.', 'Iniciando reconstrução...': 'Starting rebuild...', 'Instalação': 'Installation', 'O APK reconstruído é reassinado — NÃO substitui a versão da loja.': 'The rebuilt APK is re-signed — it does NOT replace the store version.', 'Deseja tentar instalar no dispositivo?': 'Try installing on the device?', 'APK salvo em: ': 'APK saved to: ', 'Tentando via ADB...': 'Trying via ADB...', 'ADB falhou: ': 'ADB failed: ', 'Instalado via ADB.': 'Installed via ADB.', 'Tentando abridor do sistema...': 'Trying the system opener...', 'Abrindo instalador do Android...': 'Opening the Android installer...', 'Não foi possível abrir o instalador: ': 'Could not open the installer: ', 'O instalador do Android foi aberto. Confirme a instalação na tela.': 'The Android installer was opened. Confirm the install on screen.', 'Nenhum instalador disponível (adb/termux-open).': 'No installer available (adb/termux-open).', '=== Assistente ReaDroid: APK do início ao fim ===': '=== ReaDroid Assistant: APK from start to finish ===', 'APK inválido: ': 'Invalid APK: ', 'Etapa de edição — arquivos em: ': 'Editing stage — files in: ', 'Continuar para reconstrução?': 'Continue to rebuild?', 'Pasta decodificada mantida em: ': 'Decoded folder kept at: ', 'Pronto: APK instalado no dispositivo.': 'Done: APK installed on the device.', 'Instalador aberto; a instalação ainda depende de você confirmar na tela.': 'Installer opened; the install still depends on you confirming on screen.', 'Assistente de IA (opcional, editar com IA)': 'AI assistant (optional, edit with AI)', 'Assistente guiado (iniciantes)': 'Guided assistant (beginners)', 'Assistente': 'Assistant', 'IA': 'AI'}

_WIZARD_AR = {'\nENTER para continuar...': '\nاضغط ENTER للمتابعة...', 'Verificando ferramentas...': 'جارٍ التحقق من الأدوات...', 'Reconstruir APK (obrigatório)': 'إعادة بناء APK (إلزامي)', 'Keytool/assinatura (obrigatório)': 'Keytool/التوقيع (إلزامي)', 'Alinhar APK (recomendado para instalação)': 'محاذاة APK (موصى بها للتثبيت)', 'Assinatura v1+v2+v3 (recomendado)': 'توقيع v1+v2+v3 (موصى به)', 'Gerar chave de assinatura (se não existir)': 'إنشاء مفتاح التوقيع (إن لم يوجد)', 'Instalar via ADB (opcional)': 'التثبيت عبر ADB (اختياري)', 'Algumas ferramentas obrigatórias faltando. Instale antes de continuar.': 'بعض الأدوات الإلزامية ناقصة. ثبّتها قبل المتابعة.', 'Nenhum APK selecionado.': 'لم يتم اختيار APK.', 'Extraindo com Apktool...': 'جارٍ الاستخراج بواسطة Apktool...', 'Falha na extração: ': 'فشل الاستخراج: ', 'Extraído em: ': 'تم الاستخراج إلى: ', 'Edições rápidas disponíveis:': 'تعديلات سريعة متاحة:', 'Aplicado: ': 'تم التطبيق: ', 'Falha: ': 'فشل: ', 'Renomear pacote (applicationId)?': 'إعادة تسمية الحزمة (applicationId)؟', 'Cancelado.': 'تم الإلغاء.', 'Edição manual': 'التعديل اليدوي', 'Arquivos em: ': 'الملفات في: ', 'Edite com o editor que preferir. Quando terminar, volte a esta janela.': 'عدّل بالمحرر المفضل لديك. عندما تنتهي، ارجع إلى هذه النافذة.', 'Usar IA para editar/corrigir arquivos?': 'استخدام الذكاء الاصطناعي لتعديل/إصلاح الملفات؟', 'Continuar?': 'متابعة؟', 'A IA vai editar arquivos na pasta decodificada. Backup será criado.': 'سيقوم الذكاء الاصطناعي بتعديل الملفات في المجلد المفكوك. سيتم إنشاء نسخة احتياطية.', 'Falha na reconstrução.': 'فشلت إعادة البناء.', 'Iniciando reconstrução...': 'بدء إعادة البناء...', 'Instalação': 'التثبيت', 'Deseja tentar instalar no dispositivo?': 'هل تريد محاولة التثبيت على الجهاز؟', 'APK salvo em: ': 'تم حفظ APK في: ', 'Tentando via ADB...': 'المحاولة عبر ADB...', 'Instalado via ADB.': 'تم التثبيت عبر ADB.', 'Abrindo instalador do Android...': 'جارٍ فتح مثبّت Android...', 'Assistente guiado (iniciantes)': 'المساعد الموجّه (للمبتدئين)', 'Assistente': 'المساعد', 'IA': 'الذكاء الاصطناعي', 'Assistente de IA (opcional, editar com IA)': 'مساعد الذكاء الاصطناعي (اختياري)'}

_WIZARD_HI = {'\nENTER para continuar...': '\nजारी रखने के लिए ENTER दबाएँ...', 'Verificando ferramentas...': 'औज़ार जाँचे जा रहे हैं...', 'Reconstruir APK (obrigatório)': 'APK पुनर्निर्माण (आवश्यक)', 'Keytool/assinatura (obrigatório)': 'Keytool/हस्ताक्षर (आवश्यक)', 'Alinhar APK (recomendado para instalação)': 'APK संरेखित करें (इंस्टॉल के लिए सुझाया गया)', 'Assinatura v1+v2+v3 (recomendado)': 'v1+v2+v3 हस्ताक्षर (सुझाया गया)', 'Gerar chave de assinatura (se não existir)': 'हस्ताक्षर कुंजी बनाएँ (अगर न हो)', 'Instalar via ADB (opcional)': 'ADB से इंस्टॉल (वैकल्पिक)', 'Algumas ferramentas obrigatórias faltando. Instale antes de continuar.': 'कुछ आवश्यक औज़ार गायब हैं। जारी रखने से पहले इंस्टॉल करें।', 'Nenhum APK selecionado.': 'कोई APK चयनित नहीं।', 'Extraindo com Apktool...': 'Apktool से निकाला जा रहा है...', 'Falha na extração: ': 'निकालने में विफल: ', 'Extraído em: ': 'यहाँ निकाला गया: ', 'Edições rápidas disponíveis:': 'उपलब्ध त्वरित संपादन:', 'Aplicado: ': 'लागू किया गया: ', 'Falha: ': 'विफल: ', 'Renomear pacote (applicationId)?': 'पैकेज का नाम बदलें (applicationId)?', 'Cancelado.': 'रद्द किया गया।', 'Edição manual': 'मैनुअल संपादन', 'Arquivos em: ': 'फ़ाइलें यहाँ: ', 'Edite com o editor que preferir. Quando terminar, volte a esta janela.': 'अपने पसंदीदा एडिटर से संपादित करें। पूरा होने पर इस विंडो में लौटें।', 'Usar IA para editar/corrigir arquivos?': 'फ़ाइलें संपादित/ठीक करने के लिए AI का उपयोग करें?', 'Continuar?': 'जारी रखें?', 'A IA vai editar arquivos na pasta decodificada. Backup será criado.': 'AI डिकोड किए गए फ़ोल्डर में फ़ाइलें संपादित करेगा। बैकअप बनाया जाएगा।', 'Falha na reconstrução.': 'पुनर्निर्माण विफल।', 'Iniciando reconstrução...': 'पुनर्निर्माण शुरू हो रहा है...', 'Instalação': 'इंस्टॉलेशन', 'Deseja tentar instalar no dispositivo?': 'डिवाइस पर इंस्टॉल करने का प्रयास करें?', 'APK salvo em: ': 'APK यहाँ सहेजा गया: ', 'Tentando via ADB...': 'ADB से प्रयास हो रहा है...', 'Instalado via ADB.': 'ADB से इंस्टॉल हुआ।', 'Abrindo instalador do Android...': 'Android इंस्टॉलर खोला जा रहा है...', 'Assistente guiado (iniciantes)': 'निर्देशित सहायक (शुरुआती लोगों के लिए)', 'Assistente': 'सहायक', 'IA': 'AI', 'Assistente de IA (opcional, editar com IA)': 'AI सहायक (वैकल्पिक)'}

TRANSLATIONS.setdefault("en", {}).update(_WIZARD_EN)
TRANSLATIONS.setdefault("ar", {}).update(_WIZARD_AR)
TRANSLATIONS.setdefault("hi", {}).update(_WIZARD_HI)

# ------------------------------------------------------------------ backup separado
_BACKUP_EN = {'O backup é uma etapa separada, oferecida antes da edição.': 'The backup is a separate step, offered before editing.', 'Criar um backup da pasta decodificada agora?': 'Create a backup of the decoded folder now?', 'Backup opcional: permite desfazer edições depois.': 'Optional backup: lets you undo edits later.', 'Não foi possível criar o backup (espaço em disco?).': 'Could not create the backup (disk space?).', 'Para desfazer, restaure um backup anterior em builds/_backup_*.': 'To undo, restore an earlier backup from builds/_backup_*.', 'Para desfazer, use [B] Backup e restaure um backup anterior.': 'To undo, use [B] Backup and restore an earlier backup.', 'O backup é feito na opção [B] Backup, separadamente.': 'The backup is done separately in option [B] Backup.'}

_BACKUP_AR = {'O backup é uma etapa separada, oferecida antes da edição.': 'النسخ الاحتياطي خطوة منفصلة، تُعرض قبل التعديل.', 'Criar um backup da pasta decodificada agora?': 'إنشاء نسخة احتياطية للمجلد المفكوك الآن؟', 'Backup opcional: permite desfazer edições depois.': 'نسخة احتياطية اختيارية: تتيح التراجع عن التعديلات لاحقًا.', 'Não foi possível criar o backup (espaço em disco?).': 'تعذّر إنشاء النسخة الاحتياطية (مساحة القرص؟).', 'Para desfazer, restaure um backup anterior em builds/_backup_*.': 'للتراجع، استعد نسخة احتياطية سابقة من builds/_backup_*.', 'Para desfazer, use [B] Backup e restaure um backup anterior.': 'للتراجع، استخدم [B] النسخ الاحتياطي واستعد نسخة سابقة.', 'O backup é feito na opção [B] Backup, separadamente.': 'يتم النسخ الاحتياطي بشكل منفصل في الخيار [B].'}

_BACKUP_HI = {'O backup é uma etapa separada, oferecida antes da edição.': 'बैकअप एक अलग चरण है, संपादन से पहले पेश किया जाता है।', 'Criar um backup da pasta decodificada agora?': 'अभी डिकोड किए गए फ़ोल्डर का बैकअप बनाएँ?', 'Backup opcional: permite desfazer edições depois.': 'वैकल्पिक बैकअप: बाद में संपादन पूर्ववत करने देता है।', 'Não foi possível criar o backup (espaço em disco?).': 'बैकअप नहीं बन सका (डिस्क स्थान?)।', 'Para desfazer, restaure um backup anterior em builds/_backup_*.': 'पूर्ववत करने के लिए builds/_backup_* से पुराना बैकअप पुनर्स्थापित करें।', 'Para desfazer, use [B] Backup e restaure um backup anterior.': 'पूर्ववत करने के लिए [B] बैकअप से पुराना बैकअप पुनर्स्थापित करें।', 'O backup é feito na opção [B] Backup, separadamente.': 'बैकअप अलग से विकल्प [B] में किया जाता है।'}

TRANSLATIONS.setdefault("en", {}).update(_BACKUP_EN)
TRANSLATIONS.setdefault("ar", {}).update(_BACKUP_AR)
TRANSLATIONS.setdefault("hi", {}).update(_BACKUP_HI)
