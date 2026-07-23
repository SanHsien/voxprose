"""測試 Mac 主線 11-3（`docs/mac-mainline-absorption-analysis.md`）移植 + Windows 化
改寫：utils/diagnostics.py 的診斷包匯出工具。

不觸碰真實桌面目錄：export_diagnostic_bundle 的 desktop_dir/app_data_dir 一律傳
tmp_path；不觸發真實檔案總管視窗：subprocess.Popen 全部 monkeypatch。
本檔在真實 Windows 開發機上執行（本次任務環境本身就是 Windows 11），因此
collect_env_info/collect_device_info/_get_windows_total_ram_gb 都是對著真實
系統呼叫，非 mock。
"""
import json
import tempfile
import zipfile
from pathlib import Path
from unittest.mock import patch

from utils.diagnostics import (
    _sanitize_config,
    _tail_file,
    collect_device_info,
    collect_env_info,
    export_diagnostic_bundle,
)


class TestSanitizeConfig:
    def test_redacts_api_key_fields(self):
        raw = {"openai_api_key": "sk-abcdef1234567890", "llm_engine": "openai"}
        out = _sanitize_config(raw)
        assert out["llm_engine"] == "openai"
        assert out["openai_api_key"] != raw["openai_api_key"]
        assert "sk-" not in out["openai_api_key"]

    def test_redacts_secret_token_password_hints_case_insensitive(self):
        raw = {"MY_SECRET": "x", "AuthToken": "y", "user_password": "z", "normal_field": "keep"}
        out = _sanitize_config(raw)
        assert out["MY_SECRET"] == "<redacted:1chars>"
        assert out["AuthToken"] == "<redacted:1chars>"
        assert out["user_password"] == "<redacted:1chars>"
        assert out["normal_field"] == "keep"

    def test_empty_or_falsy_secret_value_still_redacted_placeholder(self):
        out = _sanitize_config({"api_key": ""})
        assert out["api_key"] == "<redacted>"

    def test_none_input_returns_empty_dict(self):
        assert _sanitize_config(None) == {}


class TestCollectEnvInfo:
    def test_returns_non_empty_string_with_expected_sections(self):
        info = collect_env_info()
        assert isinstance(info, str)
        assert "[系統]" in info
        assert "[Python]" in info
        assert "[關鍵套件]" in info
        assert "[環境變數]" in info

    def test_never_raises_even_if_a_sub_collector_fails(self):
        # collect_env_info 逐段 try/except，個別失敗不該讓整體掛掉
        with patch("utils.diagnostics.platform.win32_ver", side_effect=RuntimeError("boom")):
            info = collect_env_info()
        assert "[系統]" in info


class TestCollectDeviceInfo:
    def test_reports_missing_sounddevice_gracefully(self):
        # 本次開發機沒裝 sounddevice，驗證明確訊息而非例外往外炸
        info = collect_device_info()
        assert "音訊輸入裝置清單" in info
        if "sounddevice 未安裝" not in info:
            # 若環境剛好有裝 sounddevice，至少格式合理
            assert "[" in info


class TestTailFile:
    def test_missing_file_returns_empty_bytes(self):
        assert _tail_file(Path("C:/definitely/not/exists/debug.log")) == b""

    def test_returns_only_last_n_lines(self):
        with tempfile.TemporaryDirectory() as td:
            p = Path(td) / "log.txt"
            p.write_text("\n".join(f"line{i}" for i in range(10)) + "\n", encoding="utf-8")
            data = _tail_file(p, max_lines=3)
            text = data.decode("utf-8")
            lines = [l for l in text.splitlines() if l]
            assert lines == ["line7", "line8", "line9"]


class TestExportDiagnosticBundle:
    def test_creates_zip_with_expected_members(self, tmp_path):
        app_data_dir = tmp_path / "appdata"
        app_data_dir.mkdir()
        (app_data_dir / "debug.log").write_text("some log line\n", encoding="utf-8")
        desktop_dir = tmp_path / "desktop"

        config = {"openai_api_key": "sk-secret", "llm_engine": "openai"}

        with patch("utils.diagnostics.subprocess.Popen"):
            zip_path = export_diagnostic_bundle(app_data_dir, config, desktop_dir=desktop_dir)

        assert zip_path is not None
        assert zip_path.exists()
        assert zip_path.parent == desktop_dir

        with zipfile.ZipFile(zip_path) as zf:
            names = set(zf.namelist())
            assert "env_info.txt" in names
            assert "device_info.txt" in names
            assert "config_sanitized.json" in names
            assert "debug.log" in names  # 有內容的 log 應該被收進去

            sanitized = json.loads(zf.read("config_sanitized.json"))
            assert sanitized["openai_api_key"] != "sk-secret"
            assert sanitized["llm_engine"] == "openai"

    def test_skips_missing_logs_without_creating_empty_entries(self, tmp_path):
        app_data_dir = tmp_path / "appdata_empty"
        app_data_dir.mkdir()
        desktop_dir = tmp_path / "desktop2"

        with patch("utils.diagnostics.subprocess.Popen"):
            zip_path = export_diagnostic_bundle(app_data_dir, {}, desktop_dir=desktop_dir)

        assert zip_path is not None
        with zipfile.ZipFile(zip_path) as zf:
            names = set(zf.namelist())
            # 沒有任何 log 檔存在時，不應該生出空的 debug.log/main_crash.log 條目
            assert "debug.log" not in names
            assert "main_crash.log" not in names

    def test_opens_explorer_to_highlight_zip_on_windows(self, tmp_path):
        """驗證有嘗試呼叫 explorer /select,（Windows 對應 macOS open -R），
        且引數帶著正確的 zip 路徑。

        2026-07-22 修正：原本斷言 `mock_popen.assert_called_once()`，但這裡
        patch 的是 `utils.diagnostics.subprocess.Popen`——即整個行程共用的
        `subprocess` module 物件，不是 diagnostics 專屬的一份拷貝。在某些
        Python 建置（例如本次驗證用的 uv 安裝 cpython 3.11.15）上，
        `collect_env_info()` 呼叫的 `platform.platform()`/`platform.uname()`/
        `platform.win32_ver()` 內部會各自呼叫 `platform._syscmd_ver()`，
        該函式為了取得完整版本號會 shell 出 `subprocess.check_output("ver",
        shell=True, ...)`——因為同一顆 mock 攔截了整個行程的 Popen，這些跟本
        測試無關的呼叫也被算進了呼叫次數，讓 `assert_called_once()` 在這類
        建置上必然失敗（已用 `git stash` 驗證：在完全未改動的 HEAD 上重現
        一樣的失敗，與本次任務改動無關）。測試真正該驗證的是「有且僅有一次
        以 'explorer' 開頭的呼叫，且帶正確 zip 路徑」，因此改為在
        `call_args_list` 裡篩選 explorer 呼叫，不再對呼叫總數做斷言。
        """
        app_data_dir = tmp_path / "appdata_explorer"
        app_data_dir.mkdir()
        desktop_dir = tmp_path / "desktop3"

        with patch("utils.diagnostics.subprocess.Popen") as mock_popen:
            zip_path = export_diagnostic_bundle(app_data_dir, {}, desktop_dir=desktop_dir)

        assert zip_path is not None
        explorer_calls = [
            c for c in mock_popen.call_args_list
            if c.args and isinstance(c.args[0], (list, tuple)) and c.args[0]
            and c.args[0][0] == "explorer"
        ]
        assert len(explorer_calls) == 1, (
            "預期恰好一次 explorer Popen 呼叫，實際："
            f"{len(explorer_calls)}（全部呼叫：{mock_popen.call_args_list}）"
        )
        called_args = explorer_calls[0].args[0]
        assert called_args[0] == "explorer"
        assert str(zip_path) in called_args

    def test_falls_back_to_app_data_dir_when_desktop_unwritable(self, tmp_path, monkeypatch):
        app_data_dir = tmp_path / "appdata3"
        app_data_dir.mkdir()

        from pathlib import Path as RealPath

        orig_mkdir = RealPath.mkdir
        call_count = {"n": 0}

        def fake_mkdir(self, *args, **kwargs):
            call_count["n"] += 1
            if call_count["n"] == 1:
                raise PermissionError("no access")
            return orig_mkdir(self, *args, **kwargs)

        monkeypatch.setattr(RealPath, "mkdir", fake_mkdir)

        with patch("utils.diagnostics.subprocess.Popen"):
            zip_path = export_diagnostic_bundle(
                app_data_dir, {}, desktop_dir=tmp_path / "unwritable_desktop"
            )

        assert zip_path is not None
        assert zip_path.parent == app_data_dir
