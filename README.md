# ReaDroid

**Android Reverse Engineering Toolkit** — static analysis and APK rebuilding for Android 12–16, designed to run on Termux without root. The AI assistant is **optional**: ReaDroid works fully without it.

Repository: <https://github.com/Odair-JDEV/Rea-APK-IA>

> **OffensiveTec** is a subtle watermark in the terminal interface.

## Features

- Inspection of APK ZIP structure, SHA-256 hashes, DEX files, and native libraries.
- **Native binary AndroidManifest.xml (AXML) parser**, in pure Python — decodes the manifest of
  any real-world APK without requiring JADX, Apktool, or aapt2. These tools remain available
  as fallbacks for the rare cases where the built-in parser cannot handle the structure.
- Static extraction of URLs, domains (validated against a list of real TLDs to avoid mistaking class names for domains),
  and IPv4 address candidates.
- Optional JADX integration to decompile DEX into approximate Java code.
- Optional Apktool integration to extract resources and smali.
- **Automated rebuilding, alignment, and signing**: after editing extracted smali/resources,
  a single workflow (`apktool b` + `zipalign` + `apksigner`/`jarsigner`) outputs an install-ready APK.
- **Quick edits** to the decoded manifest (debuggable, allowBackup, cleartext traffic, INTERNET permission)
  before rebuilding.
- **Package renaming (applicationId)**: moves smali folders and updates class references as well as the manifest —
  best-effort, intended for repackaging your own app under a different package name.
- Local JSON reports, without external services or telemetry.
- Terminal menu designed for mobile screens, with sanitized output (preventing malicious APKs
  from injecting ANSI escape sequences into your terminal).
- Interactive file explorer to browse and view Java, Kotlin, Smali, XML, JSON files, reports, and rebuilt APKs
  directly from the menu.
- JADX results classified as success, partial, or failure based on the exit code and generated files.
- Outputs saved in the active project directory, avoiding confusion with another `~/ReaDroid` path.
- **Guided assistant for beginners** (option 13): decode → edit → rebuild → install, step by step, with honest reporting of skipped steps.
- **Build history and before/after comparison** (option 16): every rebuild is recorded with date, duration, steps and
  SHA-256, and the rebuilt APK can be compared with the original (files added, removed, changed, size delta).
- **Plain-language summary** (option 17): writes `reports/<app>_resumo.md` explaining permissions, exposed components
  and addresses found in the code, for people who do not know Android terminology.
- **Analysis cache by SHA-256**: inspecting, reading the manifest and scanning strings for the same APK reuses the
  previous result instead of redoing the work.
- **Obfuscation hint**: warns when the APK has many very short file names, which usually means obfuscated code.
- **Review before applying**: with the gateway provider, the AI can propose changes and show a diff; nothing is written
  until you approve. Diagnostic prompts (crash, permissions, flow) run read-only.
- **Optional AI editing with your own OpenAI-compatible gateway**: keep using OpenRouter/Codex, or point
  opencode at your own model server with a static API key.
- Interface in Portuguese (default), English, Arabic, and Hindi.

## Compatibility

ReaDroid relies on Python and the standard library for its core functionality (including manifest parsing). It was written targeting Termux ARM64 and Android 12–16, though it could not be tested across every device/version combination. Optional external tools depend on the packages and architecture available in the user's Termux repository. Compatible with Python 3.9 or newer.

JADX requires a compatible Java runtime; upstream documentation specifies Java 11 or later. The Termux JADX package typically depends on Termux's packaged OpenJDK. Apktool on Android has known official incompatibilities in certain configurations, so this feature is optional and should be validated on your device.

## Installation on Termux

Update packages:

```bash
pkg update && pkg upgrade
pkg install python openjdk-21 jadx apktool aapt unzip git
pkg install apksigner   # optional, but recommended - see "Rebuilding" below
```

`aapt` already includes `zipalign`. If `openjdk-21`, `jadx`, `apktool`, or `apksigner` are not available in your configured repository, install the available packages and consult the official Termux documentation/README. ReaDroid does not automatically download third-party executable binaries.

Clone the repository:

```bash
git clone https://github.com/Odair-JDEV/Rea-APK-IA.git
cd Rea-APK-IA
python readroid.py
```

Alternatively, if you have already downloaded the files, run `bash install.sh` followed by `python readroid.py`.

To select APKs from the Download folder, enable storage access when prompted by Termux:

```bash
termux-setup-storage
```

Example path: `~/storage/shared/Download/app.apk`.

### Desktop Linux (experimental)

On a Debian/Ubuntu, Fedora or Arch machine, `bash install-linux.sh`
prepares the same folders and installs only the base
(`python3`, Java, `unzip`, `git`; on Arch via full `pacman -Syu` to avoid a
partial upgrade). Optional tools (`jadx`, `apktool`, `aapt`/`zipalign`,
`apksigner`) are left to your distro's packages — the script ends by
reporting which are present, with versions, and which are missing.
Then run `python3 readroid.py`. Tested on Debian with system apktool/jadx.

## Usage

1. Run `python readroid.py`.
2. Select the desired analysis from the menu.
3. Paste the APK path when prompted (or choose one automatically discovered in the Download folder).
   If you are new to this, start with **option 13 (guided assistant)** instead of picking options by hand.
4. Review reports in `reports/` and exported files in `output/` within the running project directory. Use option **9 — Explore and open generated files** to browse directories and view files.

The APK path can be absolute or relative to the current working directory. For the JADX option, the tool uses at most four threads (default: two) to reduce memory pressure. Large APKs may still require significant RAM and storage.

## Rebuilding, Alignment, and Signing (options 5, 10, 11, 12)

This workflow provides an install-ready APK without needing to memorize `apktool`/`zipalign`/`apksigner` commands:

1. **Option 5** decodes the APK using Apktool (smali + human-readable resources).
2. Edit files inside the generated directory (`output/<app>_apktool/`) using any text editor on your device.
   For common tweaks without manual editing, use **option 10** (quick manifest edits).
3. Also in **option 10** (or directly in option 11 before compiling), you can **rename the package**
   (applicationId). This moves the `smali`/`smali_classesN` directories from the old package path to the new one and updates
   class references found in `.smali` files and the manifest. This is best-effort: code
   that constructs package names via reflection or at runtime might not be covered — always test the rebuilt APK
   before relying on it.
4. **Option 11** rebuilds (`apktool b`), aligns (`zipalign`), and signs (`apksigner`, falling back to
   `jarsigner` if apksigner is not installed) sequentially. The final APK is placed in `builds/` and,
   if storage access is granted, a copy is also sent to `Downloads/ReaDroid/`.
5. **Option 12** inspects or recreates the signing key used (automatically generated during the first
   rebuild).

Without `apksigner`, ReaDroid uses Java's built-in `jarsigner` (v1/JAR signing only). This usually
works, but apps targeting `targetSdkVersion` 24 or higher may be rejected by the package installer on Android 7+
without a v2 signature. Install `pkg install apksigner` for full signing support (v1+v2+v3).

**Important:** Only use this on your own APKs or applications you have explicit permission to modify. Re-signing an app
changes the original developer identity — the output will not replace the app store version, and redistributing
someone else's modified APK without permission may violate their license. See `SECURITY.md`.

## Guided assistant (option 13)

For beginners, option 13 walks through the whole flow in order:

1. **Check tools** — required (`apktool`, `java`) and recommended (`zipalign`, `apksigner`) are listed with what is missing.
2. **Pick an APK** — from the discovered list or a path you type.
3. **Decode with Apktool** — refuses to reuse a folder that belongs to a different APK unless you confirm.
4. **Edit** — quick manifest edits, optional package rename, a pause for manual editing in any editor, and an optional
   AI edit (which always requires a real instruction).
5. **Rebuild, align, and sign** — each step is reported separately.
6. **Install (optional)** — via `adb install` when available, otherwise it opens the Android installer.

It is deliberately honest about what happened: if `zipalign` or `apksigner` is missing, the APK is still produced but
the assistant warns that it was not aligned or that the signature was not verified. Opening the Android installer
(`termux-open`) is reported as "installer opened", not as "installed" — only a successful `adb install` counts as
installed. The backup is its own optional step, offered right before the AI edit.

## History, comparison and summary (options 16 and 17)

**Option 16, build history.** Every rebuild through option 11 (and through the guided assistant) appends an entry to
`builds/history.json`: when it ran, how long it took, which steps succeeded or were skipped, the final APK and its
SHA-256. The menu shows the most recent entries and can compare a rebuilt APK with the original: size before and after,
files added, removed and changed, and whether `AndroidManifest.xml` changed. The comparison needs the original APK
path, recorded automatically when you decode with option 5; if the original moved or was deleted, ReaDroid says so
instead of guessing.

**Option 17, plain-language summary.** Produces `reports/<app>_resumo.md` with package, version, size, manifest
warnings (`debuggable`, `allowBackup`, cleartext traffic), permissions grouped with dangerous ones first and explained
in plain words, exported components, and the URLs, domains and IPs found in the code. It ends with an explicit
limitations section: this is static analysis, and permissions or addresses are leads for review, not a verdict.

Both options reuse the SHA-256 analysis cache, so running them on an APK you already analyzed is fast.

## Menu map

| Option | What it does |
| --- | --- |
| 1–3 | Inspect APK, analyze manifest/permissions, scan URLs/domains/IPs |
| 4–5 | Decompile with JADX / extract smali and resources with Apktool |
| 6–9 | Check dependencies, open reports/output folders, browse generated files |
| 10 | Quick manifest edits and package rename |
| 11 | Rebuild, align, and sign |
| 12 | Manage the signing key |
| **13** | **Guided assistant (beginners)** |
| 14 | Language |
| **15** | **Optional AI assistant** (hidden automatically if `readroid/ai.py` is removed) |
| 16 | Build history and before/after comparison |
| 17 | Plain-language summary (`resumo.md`) |
| 18 | Update ReaDroid from the repository (safe, confirmed fast-forward) |
| 19 | Choose the default folder for rebuilt APK copies |

Type `?` at the main prompt for a short explanation of each option.

## Updating ReaDroid (option 18) and choosing where APKs go

**Option 18, self-update.** Checks your copy against `origin` (the GitHub repository), shows the incoming commits,
and, only after you confirm, fast-forwards your branch. It refuses to run when:

- the folder is not a Git clone (no `.git` or no `origin` remote);
- you have modified files (`git status` not clean) — it lists them instead of overwriting your work;
- your branch has commits that are not on the remote — ReaDroid never overwrites your own commits;
- the server cannot be reached.

Only project files change. Your APKs, reports, decoded folders, builds and keys are untouched. After updating,
restart ReaDroid to run the new version. There is no automatic background update: updates happen only when you
choose option 18 and answer "s".

**Where rebuilt APKs are saved.** The signed APK always stays in `builds/<app>_<date>/`. After a rebuild, ReaDroid
also asks where to put an easy-to-find copy, listing the common Termux folders (`~/storage/downloads`,
`~/storage/shared/Download`, `/storage/emulated/0/Download`, ...), and you can type any folder on the phone.
You can save the folder as the default (stored in `~/.readroid/settings.json`, outside the project) and change it
later with option 19. Existing files are never overwritten: a second copy gets a numbered name.

## Quick start with AI editing

After the Termux installation above, install opencode if you want AI editing (Codex users can skip this):

```bash
pkg install nodejs-lts
npm install -g opencode-ai
```

Then, inside ReaDroid, open **option 15** and choose your provider with `[P]`:

- **OpenRouter** — press `[10]` and paste your key; ReaDroid manages the free model for you.
- **Own gateway** — press `[P]` → gateway, then `[10]` and enter the base URL, auth scheme (`Bearer` or `x-api-key`),
  key, and model ID (ReaDroid can list the models your gateway exposes).
- **Codex** — uses the `codex` binary you already configured in Termux.

Press `[8]` to test the provider, then use **option 13** for the guided flow, or **option 4** in the AI menu to edit
and rebuild in a loop.

## Optional AI Assistant (option 15)

ReaDroid never needs AI. The assistant lives in a separate module (`readroid/ai.py`); if you do not want it,
just ignore option 15 — or delete that file and the option disappears.

**Setup is one step:** open option 15, choose the provider with `[P]`, and paste your key with `[10]`. For OpenRouter,
ReaDroid then:

- stores the key in `~/.readroid/openrouter.key` (permission 600, **outside the project**, so it can't be committed);
- generates an `opencode.json` pointing to OpenRouter with a free NVIDIA Nemotron model
  (default `nvidia/nemotron-3.5-lightning:free`; if a free model goes away, ReaDroid switches to another `:free` one by itself, never to a paid one; you can also pick one in the menu);
- tests the key/model directly against the OpenRouter API, then tests opencode itself.

**Works from any folder.** ReaDroid always starts opencode inside the decoded APK folder
(`output/<app>_apktool`), passing the config (`OPENCODE_CONFIG`) and key (`OPENROUTER_API_KEY`) by environment
variable. You no longer need to `cd` into a specific folder first, and it refuses to open opencode in your home folder.

Menu: open the assistant interactively, summarize the app, **cross-check ReaDroid's JSON reports
(permissions, URLs, domains, IPs) against the code**, **edit with the AI and rebuild in a loop**, explain a rebuild
error, ask a free-form question, test/diagnose, **resume a task the agent couldn't finish (09)**, switch model/key,
or disable (deletes key and config).

**Edit → rebuild loop (option 4):** the AI edits only inside the decoded folder, ReaDroid rebuilds/aligns/signs, and
on failure (with your confirmation each time, up to 3 attempts) the build error is sent back to the AI. ReaDroid lists
which files the AI changed. This option no longer creates a backup by itself — use **`[B]` Backup** first when you want
a restore point.

**`[L]` / option 12 — Step limit:** the internal agent stops after a bounded number of steps (default 60, adjustable from 5 to
300). Each step is one round of tool calls (read, write, search) or the final answer. If a task is large, raise the
limit here or split it into smaller instructions.

**Resume after the step limit (option 09):** when the internal gateway agent reaches the step limit without
finishing, the whole conversation is saved inside the decoded folder (`.readroid_sessions/`, latest 10 kept) and
ReaDroid offers to continue right away — or you can come back later, choose **09 Retomar tarefa**, pick the folder
and the saved session, add an extra instruction (or none) and the agent picks up exactly where it stopped, keeping
everything it already learned about your APK. The sessions folder is hidden from the agent's own tools, so the AI
neither re-reads nor edits its past sessions.

**`[D] Review the diff before applying`:** with the gateway provider, the AI works in proposal mode: it reads the
files and returns the new content, ReaDroid shows a per-file summary (`+lines / -lines`) and, if you ask, the full
unified diff. Nothing is written until you approve, and after applying you can rebuild right away. With OpenRouter or
Codex the external tool writes directly, so ReaDroid says so instead of pretending to review.

**Read-only prompts:** the diagnostic prompts (explain a crash, review permissions, map a flow) are marked
`(só leitura)` in the prompt list and run with writes blocked, so asking the AI to explain something cannot change
your files.

**`[B] Backup`:** dedicated menu for the decoded folder — create a timestamped backup (`builds/_backup_<app>_<date>`),
list existing ones, or restore one. Restoring keeps the replaced state as `<app>_antes_de_restaurar` so the restore
itself is reversible.

**Own gateway (OpenAI-compatible, no opencode required):** in the AI menu, choose `[P]` and pick the gateway
provider, then `[10]` to configure it. You provide the base URL (e.g. `https://api.cosmospro.dev/v1`), the auth
scheme (`Bearer` or `x-api-key`), the key and the model ID (ReaDroid can list models from `GET /v1/models`).

With the gateway selected, ReaDroid does **not** need the `opencode` binary at all: it uses a built-in editing agent
(`readroid/agent.py`) that talks straight to your gateway, reads and writes files **only inside the decoded APK
folder**, refuses paths outside it, blocks writes to `apktool.yml`, and stops after a bounded number of steps. While
the model is working you see a spinner with the current step, and each file it reads or writes is listed.

The key is stored in `~/.readroid/gateway.key` (permission 600) and is never written into `opencode.json`; if you do
have opencode installed, the generated config references it as `{env:READROID_GATEWAY_API_KEY}` and points opencode
at your gateway. `[8]` tests the gateway directly and then the internal agent; option 11 switches models. OpenRouter and
Codex keep working exactly as before.

**Where credentials live:** everything stays in `~/.readroid/` (`openrouter.key`, `gateway.key`, `ai.json`,
`opencode.json`), permission 600 on the key files, never inside the repository. Running option **13** (disable)
deletes both keys and the generated config, turning AI back off.

**Privacy:** free models may log prompts, and everything the AI reads (code, strings, manifest) is sent over the
internet. Use only on your own APKs or ones you are authorized to analyze. AI output shown by ReaDroid is sanitized
against terminal escape sequences; the interactive opencode screen is drawn by opencode itself.

## Important Limitations

- ReaDroid performs static analysis. It does not execute the APK or monitor its runtime behavior.
- The native AXML parser covers what most analyses require (package, version, permissions,
  components, `<application>` flags); for manifests with unusual structures, the tool still
  attempts JADX/Apktool/aapt2 as fallbacks.
- JADX does not perfectly reconstruct all original code; identifiers may be obfuscated and original comments/variable names may be lost.
- URLs, domains, IPs, and permissions are leads for manual review, not definitive proof of malicious behavior.
- The string scanner enforces file size and item count limits per category to prevent excessive memory usage; the
  report notes in `truncated_categories` when a list might be incomplete.
- Rebuilding depends on `apktool`/`zipalign`/`apksigner` (or `jarsigner`) being installed; without
  them, each step details precisely what is missing.
- ReaDroid never modifies or signs the original APK — every rebuild generates a new file under `builds/`.

## Security and Responsible Use

Analyze only your own applications, test apps, or those you have explicit permission to inspect. APKs are untrusted files; avoid executing them. The tool invokes JADX/Apktool/zipalign/apksigner with separate arguments (without shell interpretation) and does not transmit APKs over the internet (the optional AI assistant sends the file contents you ask it to read to OpenRouter; it is off until you configure it). Tool outputs are saved locally. See `SECURITY.md` for specific guidelines regarding rebuilding and signing.

## Testing

Run:

```bash
python -m unittest discover -s tests -v
```

The suite does not need a device, a real APK, or network access: AI and gateway calls are mocked, and the newer
modules (history, checks, compare, report, cache, obfuscation, agent safety modes) are covered with temporary files
only. A few tests depend on POSIX file permissions and on the optional RTL packages (`arabic_reshaper`,
`python-bidi`, `wcwidth`), so on Windows or on a minimal Python they report failures unrelated to the code under test.
Those packages are optional at runtime too: without them the menu falls back to approximate width and left-to-right
text instead of failing to start.

## License

MIT. See `LICENSE`.

## Credits

ReaDroid is an original interface and automation tool that integrates optional third-party tools. JADX, Apktool, and apksigner maintain their own projects, licenses, and terms; see the links below.

- JADX: https://github.com/skylot/jadx
- Apktool: https://github.com/iBotPeaches/Apktool
- apksigner (Termux): https://github.com/termux/termux-packages
- Termux: https://github.com/termux/termux-app
