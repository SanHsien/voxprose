"""Windows 麥克風診斷腳本（手動執行，非 pytest 案例）。

用法：python diagnose_mic.py

做三件事：
1. 確認 sounddevice 已安裝（沒裝就給明確的安裝指令然後結束）。
2. 列出所有輸入裝置與系統預設輸入裝置。
3. 嘗試用與 audio/recorder.py 相同的參數（16kHz/mono/int16）開啟預設輸入
   串流並讀取約 0.5 秒，回報實際音量（RMS）——音量恆為 0 通常代表
   Windows 隱私權設定封鎖了麥克風，或選錯了裝置。

歷史：這支腳本原本是從 macOS 版複製過來的 tccutil/權限對話框導向內容，
在 Windows 上執行只會印出「Not macOS」直接返回，等於空殼（REVIEW.md 風險
排序表 #9）。2026-07-19 重寫為 Windows 實際可用的診斷（決策記錄見
docs/DECISIONS.md：release_win.ps1 的可攜版打包清單引用本檔案，刪除會斷
打包鏈，故選擇重寫而非刪除）。
"""
import sys

SAMPLERATE = 16000  # 與 audio/recorder.py 一致
CHANNELS = 1


def main() -> int:
    # 1. sounddevice 可用性
    try:
        import sounddevice as sd
        print("[OK] sounddevice imported")
    except ImportError:
        print("[FAIL] sounddevice NOT found.")
        print("       安裝方式：pip install sounddevice")
        print("       （正式安裝流程 setup_win.bat 會自動安裝，此情況通常代表")
        print("       目前用錯了 Python 環境，或還沒跑過 setup_win.bat。）")
        return 1

    # 2. 列出輸入裝置與預設裝置
    print("\n=== 輸入裝置列表 ===")
    try:
        devices = sd.query_devices()
        input_devices = [
            (i, d) for i, d in enumerate(devices) if d.get("max_input_channels", 0) > 0
        ]
        if not input_devices:
            print("[FAIL] 找不到任何輸入裝置。請確認麥克風已接上並在")
            print("       Windows「設定 → 系統 → 音效」中顯示為輸入裝置。")
            return 1
        default_input = None
        try:
            default_input = sd.default.device[0]  # (input, output)
        except Exception:
            pass
        for i, d in input_devices:
            marker = "  <-- 預設" if i == default_input else ""
            print(f"  [{i}] {d['name']} "
                  f"(輸入聲道 {d['max_input_channels']}, {int(d['default_samplerate'])} Hz){marker}")
        if default_input is None or default_input < 0:
            print("[WARN] 系統沒有預設輸入裝置；VoiceType 將無法錄音。")
    except Exception as e:
        print(f"[FAIL] 無法列舉音訊裝置：{e}")
        return 1

    # 3. 實際開啟串流讀 0.5 秒，回報音量
    print("\n=== 錄音測試（0.5 秒）===")
    print("請對著麥克風說話...")
    try:
        import numpy as np
        frames = int(SAMPLERATE * 0.5)
        recording = sd.rec(frames, samplerate=SAMPLERATE,
                           channels=CHANNELS, dtype="int16")
        sd.wait()
        rms = float(np.sqrt(np.mean(recording.astype(np.float32) ** 2))) / 32768.0
        level = min(rms * 10, 1.0)
        print(f"[OK] 成功開啟輸入串流並讀取音訊。音量指標：{level:.3f}（0~1）")
        if level < 0.005:
            print("[WARN] 音量幾乎為 0。可能原因：")
            print("       1. Windows「設定 → 隱私權與安全性 → 麥克風」封鎖了")
            print("          桌面應用程式（或 Python/終端機）的麥克風存取。")
            print("       2. 預設輸入裝置選錯（例如選到沒接的裝置）。")
            print("       3. 麥克風實體靜音或音量調到最低。")
        return 0
    except Exception as e:
        print(f"[FAIL] 無法開啟輸入串流：{e}")
        print("       請檢查 Windows「設定 → 隱私權與安全性 → 麥克風」，")
        print("       以及裝置是否被其他程式獨佔。")
        return 1


if __name__ == "__main__":
    sys.exit(main())
