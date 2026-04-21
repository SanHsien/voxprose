"""v2.9.11: 診斷包匯出工具。

一鍵打包 debug.log / keystrike.log / macOS crash reports / 系統資訊 /
config (脫敏) 到桌面 zip，方便使用者回報問題。
"""
from __future__ import annotations

import datetime
import json
import os
import platform
import shutil
import subprocess
import sys
import tempfile
import zipfile
from pathlib import Path
from typing import Optional


def _sanitize_config(raw: dict) -> dict:
    """抹掉所有看起來像 API key / secret 的值。"""
    SECRET_HINTS = ("api_key", "apikey", "secret", "token", "password")
    out = {}
    for k, v in raw.items():
        lk = k.lower()
        if any(h in lk for h in SECRET_HINTS):
            if isinstance(v, str) and v:
                out[k] = f"<redacted:{len(v)}chars>"
            else:
                out[k] = "<redacted>"
        else:
            out[k] = v
    return out


def collect_env_info() -> str:
    """收集系統環境資訊，回傳多行字串。"""
    lines = []
    lines.append("=== VoiceType4TW 診斷環境資訊 ===")
    lines.append(f"產生時間: {datetime.datetime.now().isoformat()}")
    lines.append("")
    lines.append("[系統]")
    lines.append(f"  macOS: {platform.mac_ver()[0]}")
    lines.append(f"  Machine: {platform.machine()}")
    lines.append(f"  Processor: {platform.processor()}")
    lines.append(f"  Platform: {platform.platform()}")

    # chip 詳細資訊（sysctl）
    try:
        cpu_brand = subprocess.check_output(
            ["sysctl", "-n", "machdep.cpu.brand_string"],
            stderr=subprocess.DEVNULL, timeout=2
        ).decode().strip()
        lines.append(f"  CPU Brand: {cpu_brand}")
    except Exception:
        pass
    try:
        mem_bytes = int(subprocess.check_output(
            ["sysctl", "-n", "hw.memsize"],
            stderr=subprocess.DEVNULL, timeout=2
        ).decode().strip())
        lines.append(f"  RAM: {mem_bytes // (1024**3)} GB")
    except Exception:
        pass
    try:
        gpu = subprocess.check_output(
            ["system_profiler", "SPDisplaysDataType"],
            stderr=subprocess.DEVNULL, timeout=5
        ).decode()
        for ln in gpu.split("\n"):
            if "Chipset Model" in ln or "Metal" in ln:
                lines.append(f"  {ln.strip()}")
    except Exception:
        pass

    lines.append("")
    lines.append("[Python]")
    lines.append(f"  Version: {sys.version}")
    lines.append(f"  Executable: {sys.executable}")
    lines.append(f"  Prefix: {sys.prefix}")

    lines.append("")
    lines.append("[關鍵套件]")
    for pkg in ("mlx", "mlx_whisper", "PyQt6", "Quartz", "sounddevice", "objc", "rumps"):
        try:
            mod = __import__(pkg)
            ver = getattr(mod, "__version__", "unknown")
            path = getattr(mod, "__file__", "?")
            lines.append(f"  {pkg}: {ver}  ({path})")
        except Exception as e:
            lines.append(f"  {pkg}: <import failed: {e}>")

    lines.append("")
    lines.append("[環境變數]")
    for k in ("SSL_CERT_FILE", "RESOURCEPATH", "PATH", "PYTHONPATH", "DYLD_LIBRARY_PATH"):
        v = os.environ.get(k, "")
        if v:
            # PATH 太長會塞爆 log
            if len(v) > 500:
                v = v[:500] + "...(truncated)"
            lines.append(f"  {k}={v}")

    return "\n".join(lines) + "\n"


def _tail_file(path: Path, max_lines: int = 2000) -> bytes:
    """讀檔最後 N 行，bytes 形式。"""
    if not path.exists():
        return b""
    try:
        with open(path, "rb") as f:
            # 簡單做法：讀尾端 512KB
            try:
                f.seek(0, os.SEEK_END)
                size = f.tell()
                read_bytes = min(size, 512 * 1024)
                f.seek(size - read_bytes)
                data = f.read()
            except Exception:
                f.seek(0)
                data = f.read()
        # 取最後 N 行
        lines = data.splitlines(keepends=True)
        if len(lines) > max_lines:
            lines = lines[-max_lines:]
        return b"".join(lines)
    except Exception as e:
        return f"<failed to read {path}: {e}>".encode()


def _collect_crash_reports(tmp_dir: Path, max_count: int = 5) -> list[Path]:
    """複製 macOS DiagnosticReports 裡 VoiceType 相關的 crash report。"""
    home = Path.home()
    candidates: list[Path] = []
    for base in (
        home / "Library" / "Logs" / "DiagnosticReports",
        Path("/Library/Logs/DiagnosticReports"),
    ):
        if not base.exists():
            continue
        for f in base.iterdir():
            name = f.name
            if any(hint in name for hint in ("嘴炮輸入法", "VoiceType", "voicetype", "python")):
                # python 也收進來，py2app 的 crash 可能掛在 python binary 名下
                if f.suffix.lower() in (".ips", ".crash", ".diag"):
                    candidates.append(f)

    # 按 mtime 新 → 舊排序
    candidates.sort(key=lambda p: p.stat().st_mtime, reverse=True)
    copied: list[Path] = []
    for f in candidates[:max_count]:
        try:
            dest = tmp_dir / f.name
            shutil.copy2(f, dest)
            copied.append(dest)
        except Exception:
            pass
    return copied


def export_diagnostic_bundle(
    app_data_dir: Path,
    config: dict,
    desktop_dir: Optional[Path] = None,
) -> Optional[Path]:
    """打包診斷 zip 到桌面。回傳 zip 路徑，失敗回傳 None。"""
    if desktop_dir is None:
        desktop_dir = Path.home() / "Desktop"
    desktop_dir.mkdir(parents=True, exist_ok=True)

    stamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    zip_path = desktop_dir / f"VoiceType4TW_診斷_{stamp}.zip"

    with tempfile.TemporaryDirectory() as td:
        tmp = Path(td)

        # 1. 環境資訊
        try:
            (tmp / "env_info.txt").write_text(collect_env_info(), encoding="utf-8")
        except Exception as e:
            (tmp / "env_info.txt").write_text(f"collect_env_info failed: {e}", encoding="utf-8")

        # 2. debug.log (最後 2000 行)
        debug_log = app_data_dir / "debug.log"
        try:
            data = _tail_file(debug_log, max_lines=2000)
            (tmp / "debug.log").write_bytes(data)
        except Exception:
            pass

        # 3. keystrike.log (最後 500 行)
        keystrike_log = app_data_dir / "keystrike.log"
        try:
            data = _tail_file(keystrike_log, max_lines=500)
            (tmp / "keystrike.log").write_bytes(data)
        except Exception:
            pass

        # 4. 脫敏 config
        try:
            safe = _sanitize_config(config)
            (tmp / "config_sanitized.json").write_text(
                json.dumps(safe, ensure_ascii=False, indent=2), encoding="utf-8"
            )
        except Exception as e:
            (tmp / "config_sanitized.json").write_text(f"sanitize failed: {e}", encoding="utf-8")

        # 5. Crash reports
        crash_dir = tmp / "crash_reports"
        crash_dir.mkdir(exist_ok=True)
        try:
            copied = _collect_crash_reports(crash_dir, max_count=5)
            (tmp / "crash_reports" / "_index.txt").write_text(
                f"收集到 {len(copied)} 份 crash report\n" + "\n".join(p.name for p in copied),
                encoding="utf-8",
            )
        except Exception as e:
            (tmp / "crash_reports" / "_error.txt").write_text(str(e), encoding="utf-8")

        # 6. 打 zip
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

    # 開啟 Finder 反白檔案
    try:
        subprocess.Popen(["open", "-R", str(zip_path)])
    except Exception:
        pass

    return zip_path


def install_faulthandler(log_file_path: Path) -> None:
    """啟用 faulthandler 寫 C-level crash trace 到 log file。
    必須在所有重 import 之前呼叫。"""
    try:
        import faulthandler
        # 打開一個常駐 file handle（必須全程保持開啟，不能 close）
        global _FAULT_FILE
        _FAULT_FILE = open(log_file_path, "a", buffering=1)
        _FAULT_FILE.write(
            f"\n=== faulthandler enabled at {datetime.datetime.now().isoformat()} ===\n"
        )
        _FAULT_FILE.flush()
        faulthandler.enable(file=_FAULT_FILE, all_threads=True)
    except Exception as e:
        print(f"[diagnostics] faulthandler init failed: {e}")


_FAULT_FILE = None  # 必須為 module 級 global，避免被 GC
