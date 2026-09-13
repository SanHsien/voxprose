"""Tests for vocab/manager.py.

Two of these guard regressions ported from upstream jfamily4tw/voicetype4tw-mac
`main` branch commit 805b007 (v2.9.18):

1. Short ASCII acronyms (<=4 chars, alnum) must not be fuzzy-corrected via
   edit-distance-1 -- otherwise a vocab entry like "PTT" can hijack "STT" in
   the transcript just because they're one edit apart. This bug also existed
   in this fork's `apply_vocab_correction` (structurally identical code to
   upstream's pre-fix version) before the guard was ported.
2. `load_all_learned_words()` must sort deterministically -- ties on
   occurrence count used to fall back on dict insertion order, which made the
   UI list's order for equally-frequent words unstable across runs.

All tests monkeypatch the module's data-file constants into an isolated
tmp_path so no test ever touches the real %APPDATA% vocab data (same pattern
as tests/test_config.py's isolated_config_paths fixture).
"""
import json

import pytest

import vocab.manager as vocab_manager


@pytest.fixture
def isolated_vocab_paths(tmp_path, monkeypatch):
    vocab_dir = tmp_path / "vocab"
    custom_path = vocab_dir / "custom_vocab.json"
    auto_memory_path = vocab_dir / "auto_memory.json"
    monkeypatch.setattr(vocab_manager, "_VOCAB_DATA_DIR", vocab_dir)
    monkeypatch.setattr(vocab_manager, "CUSTOM_VOCAB_PATH", custom_path)
    monkeypatch.setattr(vocab_manager, "AUTO_MEMORY_PATH", auto_memory_path)
    return custom_path, auto_memory_path


def _write_custom_vocab(path, words):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps({"words": words, "updated_at": ""}, ensure_ascii=False),
        encoding="utf-8",
    )


def _write_auto_memory(path, memory):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps({"memory": memory, "updated_at": ""}, ensure_ascii=False),
        encoding="utf-8",
    )


class TestFuzzyAcronymGuard:
    def test_short_ascii_acronym_is_not_fuzzy_corrected_by_another_acronym(
        self, isolated_vocab_paths
    ):
        """Vocab contains PTT; STT (edit distance 1 from PTT) must survive
        untouched -- this is the exact regression upstream fixed."""
        custom_path, _ = isolated_vocab_paths
        _write_custom_vocab(custom_path, ["PTT"])

        result = vocab_manager.apply_vocab_correction("這是 STT 系統")

        assert "STT" in result
        assert "PTT" not in result

    def test_short_ascii_acronym_exact_match_still_corrects(self, isolated_vocab_paths):
        """Exact matches (not fuzzy) must keep working even for guarded words."""
        custom_path, _ = isolated_vocab_paths
        _write_custom_vocab(custom_path, ["PTT"])

        result = vocab_manager.apply_vocab_correction("這是 PTT 系統")

        assert "PTT" in result

    def test_long_word_fuzzy_correction_still_works(self, isolated_vocab_paths):
        """Regression guard: the acronym guard must not affect longer (>=3
        char, non-acronym) vocab words -- fuzzy correction behavior for these
        is unchanged."""
        custom_path, _ = isolated_vocab_paths
        _write_custom_vocab(custom_path, ["聲成文"])

        result = vocab_manager.apply_vocab_correction("這個工具叫做生成文")

        assert "聲成文" in result

    def test_long_ascii_word_above_four_chars_still_fuzzy_corrects(
        self, isolated_vocab_paths
    ):
        """The guard only applies to <=4 char ASCII acronyms; longer ASCII
        words (e.g. product names) keep the original fuzzy-correction
        behavior."""
        custom_path, _ = isolated_vocab_paths
        _write_custom_vocab(custom_path, ["Claude"])

        result = vocab_manager.apply_vocab_correction("我在用 Claade")

        assert "Claude" in result


class TestLearnedWordSortStability:
    def test_ties_break_by_word_not_insertion_order(self, isolated_vocab_paths):
        _, auto_memory_path = isolated_vocab_paths
        # Insertion order deliberately reversed relative to expected sort
        # order, so a naive "-count only" sort would happen to look correct
        # by accident if dict order matched; this ordering would not.
        _write_auto_memory(auto_memory_path, {"香蕉": 2, "蘋果": 2, "橘子": 5})

        result = vocab_manager.load_all_learned_words()

        # 橘子 (count 5) first; then the count-2 tie broken alphabetically.
        assert result == ["橘子", "蘋果", "香蕉"]

    def test_result_is_deterministic_across_repeated_calls(self, isolated_vocab_paths):
        _, auto_memory_path = isolated_vocab_paths
        _write_auto_memory(auto_memory_path, {"b": 1, "a": 1, "c": 3})

        first = vocab_manager.load_all_learned_words()
        second = vocab_manager.load_all_learned_words()

        assert first == second == ["c", "a", "b"]
