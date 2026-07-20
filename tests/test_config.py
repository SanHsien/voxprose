"""Tests for config.py's load_config()/save_config() round trip and the
LOCAL_KEYS split (local, machine-specific settings vs. globally-synced
settings — see paths.py's SYNC_BASE_DIR and AGENTS.md's 開發約定).

Adapted from the old (pre-Windows-purification) manual script `test_save.py`
(recovered from commit 51094bf via `git show`). The original script mutated
the developer's *real* %APPDATA%\\VoiceType4TW\\config_local.json in place,
which is not something an automated test suite should ever do — this version
monkeypatches config.APP_DATA_DIR / LOCAL_CONFIG_PATH / GLOBAL_CONFIG_PATH to
an isolated tmp_path for every test so the real user config is never touched.
"""
import json

import pytest

import config as config_module


@pytest.fixture
def isolated_config_paths(tmp_path, monkeypatch):
    """Redirect config.py's file-system targets into a throwaway tmp_path.

    Patching APP_DATA_DIR too (not just the two config file paths) matters:
    load_config() checks `APP_DATA_DIR / "config.json"` for a legacy-format
    migration and, if found, deletes it after merging — we must not let that
    resolve to the developer's real AppData directory.
    """
    local_path = tmp_path / "config_local.json"
    global_path = tmp_path / "config_global.json"
    monkeypatch.setattr(config_module, "APP_DATA_DIR", tmp_path)
    monkeypatch.setattr(config_module, "LOCAL_CONFIG_PATH", local_path)
    monkeypatch.setattr(config_module, "GLOBAL_CONFIG_PATH", global_path)
    return local_path, global_path


def test_load_config_returns_defaults_when_no_files_exist(isolated_config_paths):
    cfg = config_module.load_config()

    assert cfg["hotkey_ptt"] == config_module.DEFAULT_CONFIG["hotkey_ptt"]
    assert cfg["stt_engine"] == config_module.DEFAULT_CONFIG["stt_engine"]


def test_save_then_load_round_trips_a_local_key(isolated_config_paths):
    local_path, _ = isolated_config_paths

    cfg = config_module.load_config()
    cfg["hotkey_ptt"] = "page_up (code:116)"
    config_module.save_config(cfg)

    assert local_path.exists()
    saved_local = json.loads(local_path.read_text(encoding="utf-8"))
    assert saved_local["hotkey_ptt"] == "page_up (code:116)"

    reloaded = config_module.load_config()
    assert reloaded["hotkey_ptt"] == "page_up (code:116)"


def test_save_config_splits_local_and_global_keys(isolated_config_paths):
    local_path, global_path = isolated_config_paths

    cfg = config_module.DEFAULT_CONFIG.copy()
    cfg["hotkey_ptt"] = "f13"          # in LOCAL_KEYS -> must land in the local file only
    cfg["llm_prompt"] = "custom!"      # not in LOCAL_KEYS -> must land in the global file only
    config_module.save_config(cfg)

    local_data = json.loads(local_path.read_text(encoding="utf-8"))
    global_data = json.loads(global_path.read_text(encoding="utf-8"))

    assert "hotkey_ptt" in local_data
    assert "hotkey_ptt" not in global_data
    assert "llm_prompt" in global_data
    assert "llm_prompt" not in local_data


def test_api_key_fields_are_all_local_only():
    """Every *_api_key field in DEFAULT_CONFIG must be local-only (never
    written to the cloud-syncable global config) — see 風險表 #4 in
    REVIEW.md and the migration decision in docs/DECISIONS.md."""
    api_key_fields = {k for k in config_module.DEFAULT_CONFIG if k.endswith("_api_key")}
    assert api_key_fields, "expected at least one *_api_key field to exist"
    assert api_key_fields <= config_module.LOCAL_KEYS


def test_save_config_never_writes_api_keys_to_global(isolated_config_paths):
    local_path, global_path = isolated_config_paths

    cfg = config_module.DEFAULT_CONFIG.copy()
    cfg["openai_api_key"] = "sk-test"
    cfg["anthropic_api_key"] = "sk-ant-test"
    config_module.save_config(cfg)

    local_data = json.loads(local_path.read_text(encoding="utf-8"))
    global_data = json.loads(global_path.read_text(encoding="utf-8"))

    assert local_data["openai_api_key"] == "sk-test"
    assert local_data["anthropic_api_key"] == "sk-ant-test"
    assert "openai_api_key" not in global_data
    assert "anthropic_api_key" not in global_data


def test_load_config_migrates_leaked_api_key_from_global_to_local(isolated_config_paths):
    """Simulates a pre-existing user whose synced config_global.json (e.g. in
    an iCloud/Google Drive/NAS folder) still has an API key from before the
    LOCAL_KEYS fix. load_config() must, as a one-time migration, move it into
    the local file and strip it from the global file on disk — not just in
    the in-memory merged dict — so a later save_config() doesn't write it
    back to the sync folder and the secret stops leaking on every load."""
    local_path, global_path = isolated_config_paths

    global_path.write_text(
        json.dumps({
            "openai_api_key": "sk-leaked",
            "llm_prompt": "keep me",
        }),
        encoding="utf-8",
    )

    cfg = config_module.load_config()

    # In-memory merged config has the migrated value.
    assert cfg["openai_api_key"] == "sk-leaked"
    assert cfg["llm_prompt"] == "keep me"

    # On-disk global file no longer contains the key...
    global_data = json.loads(global_path.read_text(encoding="utf-8"))
    assert "openai_api_key" not in global_data
    assert global_data["llm_prompt"] == "keep me"

    # ...and it has landed in the local file instead.
    assert local_path.exists()
    local_data = json.loads(local_path.read_text(encoding="utf-8"))
    assert local_data["openai_api_key"] == "sk-leaked"

    # A subsequent reload must not resurrect the key in global (i.e. the
    # migration is truly one-time and stable, not re-leaking on every load).
    cfg2 = config_module.load_config()
    assert cfg2["openai_api_key"] == "sk-leaked"
    global_data_after_reload = json.loads(global_path.read_text(encoding="utf-8"))
    assert "openai_api_key" not in global_data_after_reload


def test_global_config_is_not_polluted_by_local_keys(isolated_config_paths):
    """Every key in LOCAL_KEYS that is also in DEFAULT_CONFIG must never be
    written to the global (cloud-syncable) file — that would leak
    machine-specific settings (hotkeys, mic sensitivity) across machines."""
    _, global_path = isolated_config_paths

    cfg = config_module.DEFAULT_CONFIG.copy()
    config_module.save_config(cfg)

    global_data = json.loads(global_path.read_text(encoding="utf-8"))
    leaked = config_module.LOCAL_KEYS & global_data.keys()
    assert not leaked, f"LOCAL_KEYS leaked into the global config file: {leaked}"
