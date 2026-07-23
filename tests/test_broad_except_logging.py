"""2026-07-23（隱私與加固任務第 3 項：broad except 靜默吞噬掃描）。

本專案歷史上三個「引擎自始壞掉」bug 全是被 `except Exception` 吞掉才長期
未被發現（見 CLAUDE.md 派工說明／REVIEW.md 問題總帳）。這次全 repo 掃描後，
對「真的該補 log」的靜默 except 補了一筆 log/print，但刻意不改變原本的
fallback 行為語義。

這裡只驗證兩個純邏輯模組（memory.manager／stats.tracker）—— 不需要
PyQt6/sounddevice 等重依賴，可在任何環境跑：損毀檔案時
(1) fallback 行為維持原樣（回空記憶/空統計），
(2) 現在會留下一筆可追蹤的 log，而不是完全靜默。

其餘檔案（audio/recorder.py、ui/app.py、config.py 等）的同類修正，因為
需要 PyQt6/sounddevice 等在本開發機未安裝的重依賴、或涉及即時錄音回呼，
於本檔不重複覆蓋；config.py 的對應覆蓋見 tests/test_config.py。
"""
import json
import logging

import memory.manager as memory_module
import stats.tracker as stats_module


def test_corrupted_memory_json_logs_warning_and_resets_to_empty(tmp_path, monkeypatch, caplog):
    memory_path = tmp_path / "memory.json"
    memory_path.write_text("{not valid json", encoding="utf-8")
    monkeypatch.setattr(memory_module, "MEMORY_PATH", memory_path)
    # _ensure_dirs() would otherwise try to mkdir the real DATA_DIR/ARCHIVE_DIR;
    # point them at tmp_path so this test never touches real AppData.
    monkeypatch.setattr(memory_module, "DATA_DIR", tmp_path)
    monkeypatch.setattr(memory_module, "ARCHIVE_DIR", tmp_path / "archive")

    with caplog.at_level(logging.WARNING, logger="voicetype.memory"):
        result = memory_module.load_memory()

    # Fallback 行為不變：損毀就回空記憶。
    assert result == {"entries": [], "summary": "", "last_archive": ""}
    # 但現在必須留下痕跡。
    assert any("memory.json" in r.message or str(memory_path) in r.message for r in caplog.records)


def test_corrupted_stats_json_logs_warning_and_resets_to_empty(tmp_path, monkeypatch, caplog):
    stats_path = tmp_path / "stats.json"
    stats_path.write_text("{not valid json", encoding="utf-8")
    monkeypatch.setattr(stats_module, "STATS_PATH", stats_path)
    monkeypatch.setattr(stats_module, "DATA_DIR", tmp_path)

    with caplog.at_level(logging.WARNING, logger="voicetype.stats"):
        result = stats_module.load_stats()

    assert result == {"sessions": []}
    assert any(str(stats_path) in r.message for r in caplog.records)


def test_malformed_session_entry_is_skipped_with_debug_log_not_silently(monkeypatch, caplog):
    """get_summary() 過去對格式錯誤的 session 記錄完全靜默 continue；現在
    要留一筆 debug log，且行為（略過該筆、其餘正常統計）不變。"""
    stats = {
        "sessions": [
            {"ts": "not-a-real-timestamp", "duration": 10, "chars": 5},
            {"ts": "2026-01-01T00:00:00", "duration": 3.0, "chars": 12},
        ]
    }
    monkeypatch.setattr(stats_module, "load_stats", lambda: stats)

    with caplog.at_level(logging.DEBUG, logger="voicetype.stats"):
        summary = stats_module.get_summary()

    # 壞掉那筆被跳過，好的那筆正常累加進 total。
    assert summary["total"]["sessions"] == 1
    assert summary["total"]["chars"] == 12
    assert any("malformed" in r.message.lower() or "not-a-real-timestamp" in r.message
               for r in caplog.records)
