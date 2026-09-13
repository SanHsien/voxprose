"""Windows 權限檢查。

2026-07-23（隱私與加固任務第 4 項，Windows 化清查）：讀檔確認過，本檔早在
`b4094b7`（v2.9.6 Windows Stable — Mac cleanup）就已經把 macOS 專屬邏輯
（AXIsProcessTrusted 等 TCC 權限檢查）全部移除，內容已經是純 Windows no-op
——AGENTS.md 模組表原本寫「內容仍偏 macOS 導向」是舊描述沒跟著更新，已一併
修正（見 AGENTS.md 對應條目）。

清查時發現的實際問題：4 個函式裡只有 `ensure_all_permissions()` 被
`ui/app.py` import，但從未被呼叫過——也就是說這個模組完全是死碼，
`check_microphone()` 永遠回傳 `True`、`request_microphone_permission()`
永遠 no-op，即使使用者真的在 Windows「設定 → 隱私權 → 麥克風」關閉了本程式
的麥克風存取權，這裡也不會有任何反應。

處置：保留最小介面、不動 `check_accessibility()`（Windows 沒有對應概念），
但把 `check_microphone()` 換成真正讀取 Windows 隱私權同意狀態的實作
（`CapabilityAccessManager\\ConsentStore\\microphone` 登錄機碼），並在
`ui/app.py` 啟動時實際呼叫 `ensure_all_permissions()`（修正「import 了但
沒人呼叫」的死碼）。`ensure_all_permissions()` 只記一筆警告 log、不主動彈出
系統設定視窗——啟動流程不應該有意外的跳窗副作用；使用者要手動開啟設定頁時
呼叫端可自行呼叫 `request_microphone_permission()`（尚未接到任何 UI 按鈕，
之後有需要再接線）。

讀不到登錄機碼（舊版 Windows、企業原則管理、機碼路徑改變等）一律視為
「已授權」，避免對本來能正常錄音的使用者誤報——這裡的判斷只是「額外提示」，
不是麥克風能否運作的唯一依據（實際能不能用仍以
`ui/settings/general_page.py` 的錄音測試「完全靜音」偵測為準）。
"""
import logging
import sys

log = logging.getLogger("voicetype")

IS_WINDOWS = sys.platform == "win32"

_MIC_CONSENT_KEY = r"Software\Microsoft\Windows\CurrentVersion\CapabilityAccessManager\ConsentStore\microphone"


def check_accessibility() -> bool:
    """Windows: 無對應的輔助使用權限概念，永遠視為已授權。"""
    return True


def check_microphone() -> bool:
    """讀取 Windows「設定 → 隱私權 → 麥克風」的同意狀態。

    回傳 False 只代表登錄檔明確記錄「Deny」；讀不到機碼、非 Windows、
    或讀取過程任何例外，一律視為已授權（見本檔 docstring 的理由）。
    """
    if not IS_WINDOWS:
        return True
    try:
        import winreg
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, _MIC_CONSENT_KEY) as key:
            value, _ = winreg.QueryValueEx(key, "Value")
            return value != "Deny"
    except FileNotFoundError:
        # 機碼不存在（舊版 Windows、企業原則管理等）：視為已授權。
        return True
    except Exception as e:
        log.debug(f"[permissions] check_microphone registry read failed: {e}")
        return True


def request_microphone_permission():
    """開啟 Windows 系統設定的麥克風隱私頁面，讓使用者自行授權。

    Windows 沒有像 macOS 那樣的程式化請求 API，只能引導使用者手動開啟。
    目前尚未接到任何 UI 按鈕，供之後需要時呼叫。
    """
    if not IS_WINDOWS:
        return
    try:
        import os
        os.startfile("ms-settings:privacy-microphone")
    except Exception as e:
        log.warning(f"[permissions] Failed to open microphone privacy settings: {e}")


def ensure_all_permissions():
    """啟動時呼叫一次：若麥克風權限被拒，記一筆警告 log 供事後排查。

    刻意不自動彈出系統設定視窗——啟動流程不該有意外的跳窗副作用。
    """
    if not check_microphone():
        log.warning(
            "[permissions] 麥克風權限可能被 Windows 隱私設定拒絕，"
            "請至「設定 → 隱私權與安全性 → 麥克風」確認已授權本程式。"
        )
