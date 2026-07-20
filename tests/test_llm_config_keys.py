"""Regression guard: every config key an LLM provider reads must exist in
config.DEFAULT_CONFIG.

Background: llm/claude.py used to read `claude_api_key` / `claude_model`,
but DEFAULT_CONFIG and the settings UI store `anthropic_api_key` /
`anthropic_model` — so the Claude engine always got an empty key and
silently returned the raw text without ever calling the API. This test
makes that whole class of "engine reads key X, UI writes key Y" typos fail
loudly for every provider, present and future.

Implementation: static AST scan of each llm/*.py source file for
`config.get("...")` / `self.config.get("...")` calls in string-literal
form, so no optional provider SDK (anthropic/openai/...) needs to be
importable — this runs unconditionally in any environment.
"""
import ast
from pathlib import Path

import pytest

from config import DEFAULT_CONFIG

REPO_ROOT = Path(__file__).resolve().parent.parent
LLM_DIR = REPO_ROOT / "llm"

# 這些是 provider 讀取、但刻意不放 DEFAULT_CONFIG 的鍵（目前沒有）。
ALLOWED_EXTRA_KEYS: set = set()

LLM_PROVIDER_FILES = sorted(
    p for p in LLM_DIR.glob("*.py")
    # base.py: 抽象基底類別，不讀 config。prompts.py（13-1 集中化 system prompt，
    # 2026-07-20 移植）：純 SYSTEM_PROMPTS 字典 + get_default_system_prompt()，
    # 不含任何 provider 的 config.get(...) 呼叫，兩者都不是「provider 讀 config」
    # 這個檢查的對象。
    if p.name not in ("__init__.py", "base.py", "prompts.py")
)


def _config_keys_read_by(source: str) -> set:
    """Collect first-argument string literals of every `*.get("...")` call
    whose receiver is `config` or `self.config`."""
    keys = set()
    tree = ast.parse(source)
    for node in ast.walk(tree):
        if not (isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute)):
            continue
        if node.func.attr != "get":
            continue
        receiver = node.func.value
        is_config = (isinstance(receiver, ast.Name) and receiver.id == "config") or (
            isinstance(receiver, ast.Attribute)
            and receiver.attr == "config"
            and isinstance(receiver.value, ast.Name)
            and receiver.value.id == "self"
        )
        if not is_config:
            continue
        if node.args and isinstance(node.args[0], ast.Constant) and isinstance(node.args[0].value, str):
            keys.add(node.args[0].value)
    return keys


def test_found_llm_provider_files():
    assert len(LLM_PROVIDER_FILES) >= 7, (
        f"Expected at least 7 LLM provider files under llm/, found "
        f"{[p.name for p in LLM_PROVIDER_FILES]}"
    )


@pytest.mark.parametrize("provider_file", LLM_PROVIDER_FILES, ids=lambda p: p.name)
def test_llm_provider_reads_only_known_config_keys(provider_file: Path):
    source = provider_file.read_text(encoding="utf-8")
    keys = _config_keys_read_by(source)
    assert keys, f"{provider_file.name} reads no config keys — scan is broken?"

    unknown = keys - set(DEFAULT_CONFIG) - ALLOWED_EXTRA_KEYS
    assert not unknown, (
        f"{provider_file.name} reads config key(s) {sorted(unknown)} that do not "
        f"exist in config.DEFAULT_CONFIG — the settings UI will never store them, "
        f"so the provider silently gets defaults (e.g. an empty API key)."
    )


def test_claude_reads_anthropic_named_fields():
    """明確固定 Claude 引擎使用 anthropic_* 欄位名（歷史上就是這裡踩雷）。"""
    source = (LLM_DIR / "claude.py").read_text(encoding="utf-8")
    keys = _config_keys_read_by(source)
    assert "anthropic_api_key" in keys
    assert "anthropic_model" in keys
    assert "claude_api_key" not in keys
    assert "claude_model" not in keys
