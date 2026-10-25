"""設定／記憶／統計／詞彙檔的寫入必須是原子的。

Regression: 這些模組都用 `open(path, "w")` 再 json.dump。寫到一半程序被結束
（斷電、被工作管理員砍掉、磁碟滿了）就留下被截斷的 JSON；下次載入失敗後各模組
一律退回預設值——config_local.json 壞掉會讓熱鍵與所有 API key 無聲重置，
memory.json／stats.json 壞掉則整份歷史歸零。先寫暫存檔再 os.replace 就不會
有「只寫了一半」的狀態。
"""
import json

import pytest

import config as config_module
import memory.manager as memory_module
import stats.tracker as stats_module
import vocab.manager as vocab_module
from utils.atomic_io import write_json_atomic


class _Crash(Exception):
    pass


@pytest.fixture
def crash_mid_write(monkeypatch):
    """json.dump 寫出一半就中斷，模擬寫入途中程序消失。"""
    real_dump = json.dump

    def broken_dump(obj, fp, *args, **kwargs):
        fp.write('{"truncated": ')
        fp.flush()
        raise _Crash("process died mid-write")

    monkeypatch.setattr(json, "dump", broken_dump)
    return real_dump


def test_helper_keeps_old_file_when_write_crashes(tmp_path, crash_mid_write):
    target = tmp_path / "data.json"
    target.write_text('{"ok": 1}', encoding="utf-8")

    with pytest.raises(_Crash):
        write_json_atomic(target, {"ok": 2})

    assert json.loads(target.read_text(encoding="utf-8")) == {"ok": 1}
    assert [p.name for p in tmp_path.iterdir()] == ["data.json"]  # 暫存檔已清掉


def test_helper_writes_utf8_non_ascii(tmp_path):
    target = tmp_path / "data.json"
    write_json_atomic(target, {"字": "聲成文"})
    assert "聲成文" in target.read_text(encoding="utf-8")


def test_save_config_does_not_corrupt_existing_local_file(tmp_path, monkeypatch, crash_mid_write):
    local, glob = tmp_path / "config_local.json", tmp_path / "config_global.json"
    monkeypatch.setattr(config_module, "LOCAL_CONFIG_PATH", local)
    monkeypatch.setattr(config_module, "GLOBAL_CONFIG_PATH", glob)
    local.write_text(json.dumps({"hotkey_ptt": "f9", "openai_api_key": "sk-keep"}), encoding="utf-8")

    config_module.save_config({"hotkey_ptt": "f1", "openai_api_key": "sk-new", "language": "zh"})

    assert json.loads(local.read_text(encoding="utf-8"))["openai_api_key"] == "sk-keep"


def test_save_memory_and_stats_do_not_corrupt_existing_files(tmp_path, monkeypatch, crash_mid_write):
    monkeypatch.setattr(memory_module, "DATA_DIR", tmp_path)
    monkeypatch.setattr(memory_module, "ARCHIVE_DIR", tmp_path / "archive")
    monkeypatch.setattr(memory_module, "MEMORY_PATH", tmp_path / "memory.json")
    monkeypatch.setattr(stats_module, "DATA_DIR", tmp_path)
    monkeypatch.setattr(stats_module, "STATS_PATH", tmp_path / "stats.json")
    (tmp_path / "memory.json").write_text('{"entries": [{"ts": "t", "stt": "a", "llm": "a"}]}', encoding="utf-8")
    (tmp_path / "stats.json").write_text('{"sessions": [{"ts": "t"}]}', encoding="utf-8")

    with pytest.raises(_Crash):
        memory_module.save_memory({"entries": []})
    with pytest.raises(_Crash):
        stats_module.save_stats({"sessions": []})

    assert json.loads((tmp_path / "memory.json").read_text(encoding="utf-8"))["entries"]
    assert json.loads((tmp_path / "stats.json").read_text(encoding="utf-8"))["sessions"]


def test_vocab_saves_do_not_corrupt_existing_files(tmp_path, monkeypatch, crash_mid_write):
    vdir = tmp_path / "vocab"
    vdir.mkdir()
    monkeypatch.setattr(vocab_module, "_VOCAB_DATA_DIR", vdir)
    monkeypatch.setattr(vocab_module, "CUSTOM_VOCAB_PATH", vdir / "custom_vocab.json")
    monkeypatch.setattr(vocab_module, "AUTO_MEMORY_PATH", vdir / "auto_memory.json")
    (vdir / "custom_vocab.json").write_text('{"words": ["保留"]}', encoding="utf-8")
    (vdir / "auto_memory.json").write_text('{"memory": {"詞彙": 5}}', encoding="utf-8")

    with pytest.raises(_Crash):
        vocab_module._save_custom_vocab(["新"])
    with pytest.raises(_Crash):
        vocab_module._save_auto_memory({})

    assert json.loads((vdir / "custom_vocab.json").read_text(encoding="utf-8"))["words"] == ["保留"]
    assert json.loads((vdir / "auto_memory.json").read_text(encoding="utf-8"))["memory"] == {"詞彙": 5}


def test_legacy_config_is_kept_when_migration_cannot_be_saved(tmp_path, monkeypatch):
    """舊版 config.json 搬不進新檔時不能照樣刪掉（save_config 會吞例外）。"""
    app_dir = tmp_path / "app"
    app_dir.mkdir()
    legacy = app_dir / "config.json"
    legacy.write_text(json.dumps({"openai_api_key": "sk-legacy"}), encoding="utf-8")
    monkeypatch.setattr(config_module, "APP_DATA_DIR", app_dir)
    monkeypatch.setattr(config_module, "LOCAL_CONFIG_PATH", tmp_path / "missing_dir" / "config_local.json")
    monkeypatch.setattr(config_module, "GLOBAL_CONFIG_PATH", tmp_path / "missing_dir2" / "config_global.json")
    # 讓全域寫入也失敗：把父目錄位置佔成一般檔案
    (tmp_path / "missing_dir2").write_text("not a dir", encoding="utf-8")

    config_module.load_config()

    assert legacy.exists()
