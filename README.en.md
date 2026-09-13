<div align="center">

# 聲成文 VoxProse

**Local-first AI voice typing for Windows: speak → transcribe → optionally polish or translate → type into the focused app.**

**Speak naturally. Write clearly.**

[![Release](https://img.shields.io/github/v/release/SanHsien/voxprose?sort=semver)](https://github.com/SanHsien/voxprose/releases/latest)
[![CI](https://github.com/SanHsien/voxprose/actions/workflows/ci.yml/badge.svg)](https://github.com/SanHsien/voxprose/actions/workflows/ci.yml)
[![CodeQL](https://github.com/SanHsien/voxprose/actions/workflows/codeql.yml/badge.svg)](https://github.com/SanHsien/voxprose/actions/workflows/codeql.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![Python 3.10–3.14](https://img.shields.io/badge/Python-3.10--3.14-3776AB.svg?logo=python&logoColor=white)](pyproject.toml)
[![Platform: Windows 10/11](https://img.shields.io/badge/Platform-Windows%2010%2F11-0078D4.svg?logo=windows11&logoColor=white)](https://www.microsoft.com/windows/)

[Download latest release](https://github.com/SanHsien/voxprose/releases/latest) · [Traditional Chinese](README.md)

</div>

![VoxProse Dashboard](assets/screenshot-pc-01.jpg)

VoxProse is a Windows 10/11 voice-typing tool. Hold or toggle a global hotkey, speak naturally, transcribe with local Faster-Whisper or an optional cloud STT engine, optionally polish or translate the text with an LLM, and send the result back to the application that currently has input focus.

It is built for people who want to type less by speaking, while keeping control over whether speech recognition and text processing stay local or use cloud providers.

## Highlights

- **Voice typing in any focused Windows app**: LINE, browsers, Office, chat tools, editors, and other input fields.
- **Local Whisper first**: Faster-Whisper can run on CPU or NVIDIA CUDA.
- **Optional cloud STT**: bring your own API key for Groq, Gemini, or OpenRouter speech recognition.
- **Optional AI rewriting and translation**: use local Ollama or cloud LLM providers such as OpenAI, Claude, Gemini, and OpenRouter.
- **Three-layer writing system**: Base + Scenario + Format lets the same spoken input produce different styles for different contexts.
- **Foreground-app scenario switching**: optionally map apps such as Outlook or LINE to different Scenario templates; off by default.
- **PTT, Toggle, and always-on modes**: push-to-talk, one-click toggle, or RMS/Silero VAD speech detection.
- **Vocabulary memory and diagnostics**: remember proper nouns and export a diagnostic bundle with API keys removed.

## Download

Go to [Latest Release](https://github.com/SanHsien/voxprose/releases/latest). The published Windows release currently provides two portable ZIP variants:

| Package | Best for |
|---|---|
| `ShengChengWen-Windows-Lite-*.zip` | CPU users or anyone who wants a smaller initial download; excludes CUDA and Whisper model files |
| `ShengChengWen-Windows-NoModel-*.zip` | NVIDIA GPU users; includes the CUDA runtime but not a Whisper model |

First run:

1. Download the appropriate ZIP and extract it to a simple path such as `D:\VoxProse`.
2. Run `VoxProse.exe`.
3. Choose or download a speech model when prompted.
4. Configure a hotkey, focus the target input field, and start speaking.

Release assets include matching `.sha256` checksum files. Current binaries are not Authenticode-signed, so Windows SmartScreen may show an unknown-publisher warning. Download only from this repository's Releases and verify SHA-256 when appropriate.

### Setup from source

If you do not want to use a Release ZIP, clone the repository and run the Windows setup script. It builds the local Python environment, installs dependencies, and handles CUDA conditionally when an NVIDIA GPU is present.

```bat
git clone https://github.com/SanHsien/voxprose.git
cd voxprose
setup_win.bat
```

Avoid protected paths such as `C:\Program Files`.

## Workflow

```text
Global hotkey / VAD
      ↓
Recording
      ↓
Local Faster-Whisper or optional cloud STT
      ↓
(optional) LLM rewriting / scenario / formatting / translation
      ↓
Paste into the currently focused Windows application
```

![Floating recording status window](assets/screenshot-miclevel.jpg)

## AI and privacy boundary

“Local-first” does not mean every configuration is always offline. The actual data flow depends on the engines you select:

| Choice | Data flow |
|---|---|
| Local Faster-Whisper | Audio is transcribed locally |
| Groq / Gemini / OpenRouter STT | Audio is sent to the selected cloud recognition provider |
| AI rewriting disabled | Recognized text is not sent to an LLM |
| Ollama rewriting | LLM processing can stay local |
| OpenAI / Claude / Gemini / OpenRouter and other cloud LLMs | Recognized text and required prompt context are sent to the selected provider |

Cloud features require the user to configure the corresponding service and API key. For sensitive material, use local STT and either disable cloud LLM processing or use local Ollama.

## Core screens

### Recognition and AI settings

![Recognition and AI settings](assets/screenshot-pc-02.jpg)

Choose the speech engine, Whisper model, and optional text-polishing engine.

### Three-layer writing system

![Three-layer writing system](assets/screenshot-pc-03.jpg)

- **Base**: persistent writing rules.
- **Scenario**: business, social, transcript, and other contexts.
- **Format**: email, formal document, bullets, social post, and other output shapes.

### Vocabulary memory

![Vocabulary memory](assets/screenshot-pc-04.jpg)

Add proper nouns manually or let frequently used terms accumulate for future recognition prompts.

## System requirements

- Windows 10 / 11
- Python 3.10–3.14 when running from source
- NVIDIA GPU optional for CUDA acceleration; CPU mode is supported
- 16 GB+ RAM recommended
- Several GB of disk space for runtime files and speech models

## Development and verification

Development setup, Windows compatibility notes, tests, packaging, and release validation are documented in [`docs/DEVELOPMENT.md`](docs/DEVELOPMENT.md).

Basic test command:

```powershell
python -m pytest tests/ -v
```

CI runs on Windows across Python 3.10, 3.11, 3.12, 3.13, and 3.14, compiling Python files and running pytest. Real microphone, hotkey, CUDA, model, and focused-input behavior still require Windows hardware validation.

## Documentation

- [README.md](README.md): primary Traditional Chinese introduction
- [Install and model download guide](安裝下載教學.md): installation and model-download troubleshooting
- [CHANGELOG.md](CHANGELOG.md): version history
- [docs/DEVELOPMENT.md](docs/DEVELOPMENT.md): development, tests, packaging, and Windows validation
- [docs/DECISIONS.md](docs/DECISIONS.md): design and maintenance decisions
- [docs/UPSTREAM.md](docs/UPSTREAM.md): upstream synchronization history
- [NOTICE.md](NOTICE.md): provenance, attribution, and third-party notices

## Provenance

VoxProse is a Windows-only fork of [`jfamily4tw/voicetype4tw-mac`](https://github.com/jfamily4tw/voicetype4tw-mac), derived from the VoiceType4TW / 嘴炮輸入法 `win-stable` Windows line. The original authors are **Jimmy Chiou** and **CC58TW**; the upstream Windows edition was previously maintained by **go-mask**. This fork is maintained independently by **SanHsien** under the product name 聲成文 VoxProse.

See [NOTICE.md](NOTICE.md) and [docs/UPSTREAM.md](docs/UPSTREAM.md) for complete provenance. This fork does not represent the upstream project's views.

## License

VoxProse is licensed under the [MIT License](LICENSE). Keep the license and required attribution when using, modifying, or redistributing the project; see [NOTICE.md](NOTICE.md) for provenance details.
