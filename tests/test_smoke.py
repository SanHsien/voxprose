"""Smoke tests: syntax-compile the whole repo, and import the modules that
have no heavy/optional runtime dependency (PyQt6, sounddevice, faster-whisper,
provider SDKs...). This is the zero-cost safety net described in AGENTS.md —
it will not catch behavioral regressions, only "somebody pushed a syntax
error / broken import" mistakes.

Modules that need optional third-party packages are imported defensively:
if the package is missing in the current environment we skip instead of
failing, per AGENTS.md/DEVELOPMENT.md ("不要為了測試去裝大型相依").
"""
import importlib
import py_compile
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent

# Directories that must never be walked into: VCS internals, virtualenvs,
# build/dist output, embedded runtimes, and large ignored data dirs (see
# .gitignore). Keeping this list in sync with .gitignore avoids wasting time
# compiling third-party/vendored code that isn't part of this project.
EXCLUDED_DIR_NAMES = {
    ".git", ".venv", "venv", "env", "__pycache__",
    "build", "dist", ".runtime", "bundled_models", "archive",
    ".eggs", ".agents", ".codex", "node_modules",
}


def _iter_repo_python_files():
    for path in REPO_ROOT.rglob("*.py"):
        if any(part in EXCLUDED_DIR_NAMES for part in path.relative_to(REPO_ROOT).parts):
            continue
        # Skip anything under a VoiceType4TW_Win_*_V* release staging folder.
        if any(part.startswith("VoiceType4TW_Win_") for part in path.relative_to(REPO_ROOT).parts):
            continue
        yield path


ALL_PY_FILES = sorted(_iter_repo_python_files(), key=lambda p: str(p))


@pytest.mark.parametrize("py_file", ALL_PY_FILES, ids=lambda p: str(p.relative_to(REPO_ROOT)))
def test_py_compile(py_file: Path):
    """Every tracked .py file must at least be syntactically valid."""
    py_compile.compile(str(py_file), doraise=True)


def test_found_expected_python_files():
    """Guard against the glob silently matching nothing (e.g. wrong cwd)."""
    assert len(ALL_PY_FILES) > 20, (
        f"Expected the repo to contain more than 20 .py files, found {len(ALL_PY_FILES)}. "
        "Check that tests are being run from the repo root."
    )


# --- Pure-logic modules: no PyQt6/sounddevice/faster-whisper/provider SDKs ---
# These MUST import cleanly in any environment that has Python itself.
PURE_LOGIC_MODULES = [
    "config",
    "paths",
    "net_config",
    "stt.base",
    "stt.hallucination_filter",
    "llm.base",
    "vocab.manager",
    "memory.manager",
    "stats.tracker",
    "utils.resources",
    "audio.mutex",
    "audio.gain",
]


@pytest.mark.parametrize("module_name", PURE_LOGIC_MODULES)
def test_import_pure_logic_module(module_name: str):
    module = importlib.import_module(module_name)
    assert module is not None


# --- Modules that depend on an optional/heavy third-party package. ---
# (module_name, package_used_for_the_skip_reason)
OPTIONAL_DEPENDENCY_MODULES = [
    ("stt.local_whisper", "faster_whisper"),
    ("stt.groq_whisper", "groq"),
    ("stt.gemini_stt", "httpx"),
    ("stt.openrouter_stt", "httpx"),
    ("llm.openrouter", "httpx"),
    ("llm.gemini", "httpx"),
    ("llm.ollama", "requests"),
    ("llm.qwen", "httpx"),
    ("llm.deepseek", "httpx"),
    ("llm.claude", "anthropic"),
    ("llm.openai_llm", "openai"),
    ("actions.builtins", "httpx"),
    ("hotkey.listener", None),
    ("output.injector", "pyperclip"),
    ("audio.recorder", "sounddevice"),
    ("audio.auto_trigger", "sounddevice"),
    ("ui.positions", "PyQt6"),  # imports the ui package, whose __init__ needs PyQt6
]


@pytest.mark.parametrize(
    "module_name,dep_hint", OPTIONAL_DEPENDENCY_MODULES, ids=[m for m, _ in OPTIONAL_DEPENDENCY_MODULES]
)
def test_import_optional_module_or_skip(module_name: str, dep_hint):
    try:
        importlib.import_module(module_name)
    except ImportError as exc:
        pytest.skip(f"optional dependency not installed for {module_name} ({dep_hint}): {exc}")


if __name__ == "__main__":
    sys.exit(pytest.main([__file__, "-v"]))
