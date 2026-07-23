"""前景視窗感知：純 ctypes Win32 API，取得目前前景視窗所屬程序的執行檔名稱。

2026-07-23：用於「情境模板自動切換」功能（見 `config.py` 的
`auto_scenario_enabled`/`auto_scenario_rules`、`ui/app.py._detect_auto_scenario()`、
`docs/REFERENCES.md` Wispr Flow 調研條目、`docs/DECISIONS.md` 對應決策）。

設計原則：
- **不加新依賴**：純 `ctypes.windll`，不用 `psutil`。
- **偵測時機由呼叫端決定**：本模組只負責單次查詢（`GetForegroundWindow` →
  `GetWindowThreadProcessId` → `OpenProcess` → `QueryFullProcessImageNameW`），
  不做輪詢或常駐監看——呼叫端應在熱鍵按下/VAD 段落開始那一刻呼叫一次。
- **絕不拋例外**：非 Windows 平台、抓不到前景視窗、或任何一步 Win32 呼叫失敗，
  一律回傳 `None`；呼叫端不需要自己包 try/except 就能安全使用，只需把
  `None` 視為「偵測不到，維持現行手動情境」。
- **可 mock 測試**：實際的 DLL 函式指標存在模組層級變數 `_user32`/`_kernel32`
  （而非函式內區域變數的 `ctypes.windll.user32`），測試可以直接
  `monkeypatch.setattr(foreground, "_user32", fake_user32)` 整個換掉，不需要
  真的碰 ctypes 底層物件。
"""
import ctypes
from ctypes import wintypes
import logging
import platform

log = logging.getLogger("voicetype")

IS_WINDOWS = platform.system() == "Windows"

# PROCESS_QUERY_LIMITED_INFORMATION：比 PROCESS_QUERY_INFORMATION 需要的權限更低，
# 足以呼叫 QueryFullProcessImageNameW，對受保護/提權的系統行程也較不容易被拒絕。
PROCESS_QUERY_LIMITED_INFORMATION = 0x1000

MAX_PATH_BUFFER_LEN = 512

_user32 = None
_kernel32 = None

if IS_WINDOWS:
    try:
        _user32 = ctypes.windll.user32
        _kernel32 = ctypes.windll.kernel32
    except Exception as e:
        # 理論上不該發生（IS_WINDOWS 已經是 platform.system()=="Windows"），
        # 但任何環境異常（如受限沙盒）都不該讓 import 這個模組整個炸掉。
        log.warning(f"[foreground] ctypes.windll unavailable despite Windows platform: {e}")
        _user32 = None
        _kernel32 = None


def get_foreground_process_name():
    """回傳目前前景視窗所屬程序的執行檔名稱（如 `"OUTLOOK.EXE"`，含副檔名，
    保留原始大小寫；大小寫比對交給呼叫端，見 `resolve_scenario_for_process()`）。

    非 Windows、`_user32`/`_kernel32` 不可用、抓不到前景視窗、或任何一步
    Win32 呼叫失敗，一律回傳 `None`。
    """
    if not IS_WINDOWS or _user32 is None or _kernel32 is None:
        return None

    try:
        hwnd = _user32.GetForegroundWindow()
        if not hwnd:
            return None

        pid = wintypes.DWORD(0)
        _user32.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
        if not pid.value:
            return None

        h_process = _kernel32.OpenProcess(PROCESS_QUERY_LIMITED_INFORMATION, False, pid.value)
        if not h_process:
            return None

        try:
            buf = ctypes.create_unicode_buffer(MAX_PATH_BUFFER_LEN)
            buf_len = wintypes.DWORD(MAX_PATH_BUFFER_LEN)
            ok = _kernel32.QueryFullProcessImageNameW(h_process, 0, buf, ctypes.byref(buf_len))
            if not ok:
                return None
            full_path = buf.value
            if not full_path:
                return None
            # basename：支援反斜線與正斜線（理論上 Windows 路徑一律反斜線，
            # 保留正斜線容錯不影響正確性）。
            return full_path.replace("/", "\\").rsplit("\\", 1)[-1]
        finally:
            _kernel32.CloseHandle(h_process)
    except Exception as e:
        log.warning(f"[foreground] Detection failed: {e}")
        return None


def resolve_scenario_for_process(proc_name, rules: dict):
    """依 `auto_scenario_rules` 規則字典，把「前景程式執行檔名稱」解析成對應
    的情境模板名稱；找不到規則回傳 `None`（呼叫端 fallback 回手動選擇的情境）。

    比對語義（2026-07-23 決定，見 docs/DECISIONS.md）：
    - **不分大小寫**：`"OUTLOOK.EXE"` 與 `"outlook.exe"` 視為相同。
    - **副檔名容錯**：規則鍵可以是 `"outlook.exe"` 也可以只寫 `"outlook"`
      （不含副檔名），兩者都能比對到 `proc_name="OUTLOOK.EXE"`——降低使用者
      手動輸入規則時漏打/打錯副檔名的挫折感。
    - 規則字典為空或 `proc_name` 為 `None`/空字串，直接回傳 `None`。
    - 多筆規則同時符合時，回傳字典疊代順序中第一筆命中的（Python 3.7+ dict
      保留插入順序，即設定頁列表由上到下的順序）。
    """
    if not proc_name or not rules:
        return None

    proc_lower = proc_name.strip().lower()
    proc_stem = proc_lower[:-4] if proc_lower.endswith(".exe") else proc_lower

    for raw_key, scenario in rules.items():
        if not raw_key:
            continue
        key_lower = str(raw_key).strip().lower()
        key_stem = key_lower[:-4] if key_lower.endswith(".exe") else key_lower
        if key_lower == proc_lower or key_stem == proc_stem:
            return scenario

    return None
