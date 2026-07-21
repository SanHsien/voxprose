"""Mac 主線 v2.9.11（11-3，`51094bf:utils/diagnostics.py`，259 行）移植 + Windows 化改寫：
診斷包匯出工具。

一鍵打包 Windows 環境資訊／麥克風裝置清單／debug.log／keystrike.log／
main_crash.log／設定摘要（脫敏）到桌面 zip，方便使用者回報問題。

與 Mac 原版的差異（收集邏輯全部改寫成 Windows 對應版，概念相同）：
- `collect_env_info()`：Mac 版用 `sysctl`/`system_profiler` 取 CPU brand／RAM／GPU；
  這裡改用 `platform.win32_ver()` + ctypes `GlobalMemoryStatusEx` 取 Windows 版本與
  總實體記憶體，不含 GPU 型號查詢（現樹無對應需求，CUDA 由
  `requirements-cuda-win.txt` 另行處理，非本檔範圍）。
- 無 macOS `~/Library/Logs/DiagnosticReports` crash report 目錄；改收
  `main.py` 的 `main_crash.log`（`faulthandler.enable()` 輸出，見 main.py:89-94，
  現樹本來就已存在，只是從未被打包匯出過）。
- 新增 `collect_device_info()`（Mac 版沒有獨立函式，裝置資訊混在 env info 裡）：
  比照 `diagnose_mic.py` 的 `sd.query_devices()` 邏輯，沒裝 sounddevice 時給明確
  訊息而非讓整個匯出失敗。
- 開啟檔案總管定位輸出檔用 `explorer /select,`，取代 macOS 的 `open -R`。

接線點：`ui/settings_window.py` 原本「🎤 麥克風測試與診斷」按鈕內有一段
`if platform.system() != "Darwin": QMessageBox("此診斷功能目前專為 macOS 設計")`
的假擋板——該擋板之後的實際測試程式碼（`sd.rec()` + numpy RMS）本來就是跨平台
邏輯、從未呼叫任何 macOS 專屬 API，擋板本身才是誤植的死碼（Windows 使用者連
按鈕都被 `if platform.system() == "Windows": self.btn_mic_test.hide()` 藏起來，
是兩層「假功能」疊在一起）。本次一併移除擋板、恢復按鈕，並新增獨立的
「📦 匯出診斷包」按鈕呼叫本檔案的 `export_diagnostic_bundle()`。詳見
docs/DECISIONS.md 2026-07-20 條目。
"""
from __future__ import annotations

import ctypes
import datetime
import json
import os
import platform
import subprocess
import sys
import tempfile
import zipfile
from pathlib import Path
from typing import Optional


def _sanitize_config(raw: dict) -> dict:
    """抹掉所有看起來像 API key / secret 的值，比照 config.py 的
    `*_api_key` 本地化決策同一套「看起來像密鑰就抹」邏輯，只是用途是輸出
    診斷檔而非決定本地/雲端儲存。"""
    SECRET_HINTS = ("api_key", "apikey", "secret", "token", "password")
    out = {}
    for k, v in (raw or {}).items():
        lk = k.lower()
        if any(h in lk for h in SECRET_HINTS):
            if isinstance(v, str) and v:
                out[k] = f"<redacted:{len(v)}chars>"
            else:
                out[k] = "<redacted>"
        else:
            out[k] = v
    return out


def _get_windows_total_ram_gb() -> Optional[float]:
    """用 ctypes 呼叫 Win32 `GlobalMemoryStatusEx` 取總實體記憶體（GB）。
    非 Windows 或呼叫失敗一律回傳 None（呼叫端自行決定要不要顯示這行）。"""
    if sys.platform != "win32":
        return None
    try:
        class MEMORYSTATUSEX(ctypes.Structure):
            _fields_ = [
                ("dwLength", ctypes.c_uint32),
                ("dwMemoryLoad", ctypes.c_uint32),
                ("ullTotalPhys", ctypes.c_uint64),
                ("ullAvailPhys", ctypes.c_uint64),
                ("ullTotalPageFile", ctypes.c_uint64),
                ("ullAvailPageFile", ctypes.c_uint64),
                ("ullTotalVirtual", ctypes.c_uint64),
                ("ullAvailVirtual", ctypes.c_uint64),
                ("ullAvailExtendedVirtual", ctypes.c_uint64),
            ]

        stat = MEMORYSTATUSEX()
        stat.dwLength = ctypes.sizeof(MEMORYSTATUSEX)
        if ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(stat)):
            return round(stat.ullTotalPhys / (1024 ** 3), 1)
    except Exception:
        pass
    return None


def collect_env_info() -> str:
    """收集 Windows 系統環境資訊，回傳多行字串。"""
    lines = []
    lines.append("=== VoxProse 診斷環境資訊 (Windows) ===")
    lines.append(f"產生時間: {datetime.datetime.now().isoformat()}")
    lines.append("")
    lines.append("[系統]")
    lines.append(f"  Platform: {platform.platform()}")
    try:
        win_ver = platform.win32_ver()  # (release, version, csd, ptype)
        lines.append(
            f"  Windows: release={win_ver[0]} version={win_ver[1]} "
            f"servicepack={win_ver[2]} type={win_ver[3]}"
        )
    except Exception:
        pass
    lines.append(f"  Machine: {platform.machine()}")
    lines.append(f"  Processor: {platform.processor()}")

    ram_gb = _get_windows_total_ram_gb()
    if ram_gb is not None:
        lines.append(f"  RAM: {ram_gb} GB")

    lines.append("")
    lines.append("[Python]")
    lines.append(f"  Version: {sys.version}")
    lines.append(f"  Executable: {sys.executable}")
    lines.append(f"  Prefix: {sys.prefix}")

    lines.append("")
    lines.append("[關鍵套件]")
    for pkg in ("PyQt6", "sounddevice", "faster_whisper", "httpx", "numpy", "win32api"):
        try:
            mod = __import__(pkg)
            ver = getattr(mod, "__version__", "unknown")
            path = getattr(mod, "__file__", "?")
            lines.append(f"  {pkg}: {ver}  ({path})")
        except Exception as e:
            lines.append(f"  {pkg}: <import failed: {e}>")

    lines.append("")
    lines.append("[環境變數]")
    for k in ("APPDATA", "SSL_CERT_FILE", "PATH", "PYTHONPATH"):
        v = os.environ.get(k, "")
        if v:
            # PATH 太長會塞爆 log
            if len(v) > 500:
                v = v[:500] + "...(truncated)"
            lines.append(f"  {k}={v}")

    return "\n".join(lines) + "\n"


def collect_device_info() -> str:
    """收集音訊輸入裝置清單（比照 diagnose_mic.py 的邏輯：sounddevice 沒裝時
    給明確訊息而非讓整包匯出失敗）。"""
    lines = ["=== 音訊輸入裝置清單 ==="]
    try:
        import sounddevice as sd
    except ImportError:
        lines.append("[FAIL] sounddevice 未安裝，無法列舉裝置。")
        return "\n".join(lines) + "\n"

    try:
        devices = sd.query_devices()
        default_input = None
        try:
            default_input = sd.default.device[0]
        except Exception:
            pass
        input_devices = [
            (i, d) for i, d in enumerate(devices) if d.get("max_input_channels", 0) > 0
        ]
        if not input_devices:
            lines.append("[FAIL] 找不到任何輸入裝置。")
        for i, d in input_devices:
            marker = "  <-- 預設" if i == default_input else ""
            lines.append(
                f"  [{i}] {d['name']} "
                f"(輸入聲道 {d['max_input_channels']}, {int(d['default_samplerate'])} Hz){marker}"
            )
    except Exception as e:
        lines.append(f"[FAIL] 無法列舉音訊裝置：{e}")

    return "\n".join(lines) + "\n"


def _tail_file(path: Path, max_lines: int = 2000) -> bytes:
    """讀檔最後 N 行，bytes 形式（避免大檔全讀爆記憶體，只 seek 尾端 512KB）。"""
    if not path or not Path(path).exists():
        return b""
    try:
        with open(path, "rb") as f:
            try:
                f.seek(0, os.SEEK_END)
                size = f.tell()
                read_bytes = min(size, 512 * 1024)
                f.seek(size - read_bytes)
                data = f.read()
            except Exception:
                f.seek(0)
                data = f.read()
        lines = data.splitlines(keepends=True)
        if len(lines) > max_lines:
            lines = lines[-max_lines:]
        return b"".join(lines)
    except Exception as e:
        return f"<failed to read {path}: {e}>".encode()


def export_diagnostic_bundle(
    app_data_dir: Path,
    config: dict,
    desktop_dir: Optional[Path] = None,
) -> Optional[Path]:
    """打包診斷 zip。預設放桌面，回傳 zip 路徑；失敗回傳 None。

    Args:
        app_data_dir: `paths.APP_DATA_DIR`，debug.log/keystrike.log/main_crash.log
            都在這個目錄下。
        config: 目前設定 dict（會先脫敏才寫入 zip）。
        desktop_dir: 輸出目錄，預設 `~/Desktop`；測試時可傳 tmp_path 覆蓋。
    """
    if desktop_dir is None:
        desktop_dir = Path.home() / "Desktop"
    try:
        desktop_dir.mkdir(parents=True, exist_ok=True)
    except Exception:
        # 桌面路徑異常（權限受限帳號等）時退回 app_data_dir，確保仍能匯出成功
        desktop_dir = Path(app_data_dir)
        desktop_dir.mkdir(parents=True, exist_ok=True)

    stamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    zip_path = desktop_dir / f"VoxProse_診斷_{stamp}.zip"

    with tempfile.TemporaryDirectory() as td:
        tmp = Path(td)

        # 1. 環境資訊
        try:
            (tmp / "env_info.txt").write_text(collect_env_info(), encoding="utf-8")
        except Exception as e:
            (tmp / "env_info.txt").write_text(f"collect_env_info failed: {e}", encoding="utf-8")

        # 2. 音訊裝置清單
        try:
            (tmp / "device_info.txt").write_text(collect_device_info(), encoding="utf-8")
        except Exception as e:
            (tmp / "device_info.txt").write_text(f"collect_device_info failed: {e}", encoding="utf-8")

        # 3. 各類 log（存在才收，沒有就跳過，不製造空檔）
        for log_name, max_lines in (
            ("debug.log", 2000),
            ("keystrike.log", 500),
            ("main_crash.log", 2000),
        ):
            try:
                data = _tail_file(Path(app_data_dir) / log_name, max_lines=max_lines)
                if data:
                    (tmp / log_name).write_bytes(data)
            except Exception:
                pass

        # 4. 脫敏設定摘要
        try:
            safe = _sanitize_config(config)
            (tmp / "config_sanitized.json").write_text(
                json.dumps(safe, ensure_ascii=False, indent=2), encoding="utf-8"
            )
        except Exception as e:
            (tmp / "config_sanitized.json").write_text(f"sanitize failed: {e}", encoding="utf-8")

        # 5. 打 zip
        try:
            with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
                for root, _, files in os.walk(tmp):
                    for name in files:
                        full = Path(root) / name
                        arc = full.relative_to(tmp)
                        zf.write(full, arc)
        except Exception as e:
            print(f"[diagnostics] Failed to create zip: {e}")
            return None

    # 開啟檔案總管反白檔案（Windows 對應 macOS 的 `open -R`）
    if sys.platform == "win32":
        try:
            subprocess.Popen(["explorer", "/select,", str(zip_path)])
        except Exception:
            pass

    return zip_path
