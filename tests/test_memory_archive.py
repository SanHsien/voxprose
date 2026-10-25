"""記憶歸檔不能覆蓋先前的歸檔檔。

Regression: memory/manager.py 的歸檔檔名只有 `memory_<年>-W<週>.json`
（手動壓縮則是 `..._purge.json`），同一週內第二次歸檔／壓縮會直接覆蓋前一份，
而 clear_memory／purge_and_summarize 的說明都承諾「保留歸檔／備份」。
"""
import json

import pytest

import memory.manager as mm


@pytest.fixture
def isolated(tmp_path, monkeypatch):
    monkeypatch.setattr(mm, "DATA_DIR", tmp_path)
    monkeypatch.setattr(mm, "MEMORY_PATH", tmp_path / "memory.json")
    monkeypatch.setattr(mm, "ARCHIVE_DIR", tmp_path / "archive")
    return tmp_path


def _fill(prefix, n=3):
    for i in range(n):
        mm.add_entry(f"{prefix}-stt-{i}", f"{prefix}-llm-{i}")


def _archived_texts(archive_dir):
    texts = []
    for f in archive_dir.glob("*.json"):
        data = json.loads(f.read_text(encoding="utf-8"))
        texts.extend(e["stt"] for e in data["entries"])
    return texts


def test_two_purges_in_the_same_week_keep_both_backups(isolated):
    _fill("first")
    assert mm.purge_and_summarize() == 3
    _fill("second")
    assert mm.purge_and_summarize() == 3

    texts = _archived_texts(isolated / "archive")
    assert sorted(texts) == sorted(
        [f"first-stt-{i}" for i in range(3)] + [f"second-stt-{i}" for i in range(3)]
    )


def test_auto_archive_after_clear_memory_keeps_earlier_archive(isolated):
    _fill("old", n=10)  # 達 10 筆 -> maybe_archive 觸發歸檔
    assert any((isolated / "archive").glob("*.json"))
    mm.clear_memory()  # last_archive 被清空，下一次達標會在同一週再歸檔
    _fill("new", n=10)

    texts = _archived_texts(isolated / "archive")
    assert "old-stt-0" in texts
    assert "new-stt-0" in texts
