"""共用 CUDA 加速判定——Dashboard 與 STT worker 唯一真相源（2026-07-22）。

背景：`ui/settings/dashboard_page.py` 原本只用
`ctranslate2.get_cuda_device_count() > 0` 判斷「CUDA GPU 可用」，但這個
API 只是問 NVIDIA 驅動「有沒有 CUDA 裝置」，不代表 faster-whisper/
ctranslate2 實際載入模型時能不能用得到——真正需要的 cuBLAS/cuDNN 執行期
函式庫（`requirements-cuda-win.txt`，只有 `setup_win.bat` 偵測到
`nvidia-smi` 時才會安裝）如果沒裝，`WhisperModel(device="cuda", ...)`
仍會失敗，`stt/subprocess_whisper.py` 的 worker 會靜默降級回 CPU。因此
「偵測到裝置數 > 0」與「加速實際可用」是兩件事，Dashboard 過去把兩者混為
一談，在只裝了 `requirements-win.txt`（無 CUDA 函式庫）的機器上會顯示
「✅ CUDA GPU x1 (加速可用)」，但實際跑起來是 CPU——文案與行為矛盾。

`probe_cuda()` 補上 worker 真正用來決定要不要 fallback 的同一道測試
（`ctypes.WinDLL("cublas64_12.dll")` 硬載入驗證，含 worker 用的 NVIDIA DLL
路徑探索），讓 Dashboard 與 worker 永遠回報同一個結論。見
docs/DECISIONS.md「CUDA Dashboard 文案誠實化」。
"""
import logging
import os
import platform

log = logging.getLogger("voicetype.stt")


def probe_cuda() -> dict:
    """回傳 {"device_count": int, "accel_available": bool, "reason": str}。

    - device_count：`ctranslate2.get_cuda_device_count()` 回報的裝置數（驅動
      層級偵測，不保證能實際載入模型）。
    - accel_available：是否真的能載入 CUDA 執行期函式庫（cuBLAS）——這是
      `stt/subprocess_whisper.py` worker 決定要不要 fallback 回 CPU 的同一項
      測試，Windows 專用；非 Windows 平台此 fork 不支援，恆回 False。
    - reason：給 UI 顯示或 log 用的簡短說明。
    """
    result = {"device_count": 0, "accel_available": False, "reason": ""}

    try:
        import ctranslate2
    except Exception as e:
        result["reason"] = f"驅動組件遺失: {e}"
        return result

    try:
        result["device_count"] = ctranslate2.get_cuda_device_count()
    except Exception as e:
        result["reason"] = f"GPU 偵測組件異常: {e}"
        return result

    if result["device_count"] <= 0:
        result["reason"] = "未偵測到 CUDA GPU"
        return result

    if platform.system() != "Windows":
        # 本 fork 目前只支援 Windows；理論上不會走到這裡（get_stt() 在其他
        # 平台走 LocalWhisperSTT，非本模組適用範圍），保守回 False 而非假設
        # 可用，避免對未驗證平台做樂觀宣稱。
        result["reason"] = "非 Windows 平台，未驗證加速可用性"
        return result

    # Windows：比照 stt/subprocess_whisper.py 的 _stt_worker 硬驗證——先做
    # NVIDIA DLL 路徑探索，再實際嘗試載入 cuBLAS，兩處邏輯保持一致。
    import ctypes
    import site
    import sys
    from pathlib import Path

    try:
        for pdir in site.getsitepackages():
            nvidia_root = Path(pdir) / "nvidia"
            if nvidia_root.exists():
                for bin_dir in nvidia_root.glob("**/bin"):
                    if bin_dir.is_dir():
                        os.add_dll_directory(str(bin_dir))
        venv_bin = Path(sys.executable).parent
        if (venv_bin / "cublas64_12.dll").exists():
            os.add_dll_directory(str(venv_bin))
    except Exception as e:
        # 這段失敗不改變最終結論（下面的硬載入測試會自己得出對錯結論），
        # 但補一筆 debug log 方便診斷「為什麼找不到 DLL 路徑」。
        log.debug(f"[cuda_check] DLL directory discovery failed: {e}")

    try:
        test_load = ctypes.WinDLL("cublas64_12.dll")
        del test_load
        result["accel_available"] = True
        result["reason"] = "CUDA 加速可用"
    except Exception:
        result["accel_available"] = False
        result["reason"] = "偵測到 GPU，但缺少 CUDA 函式庫（requirements-cuda-win.txt 未安裝）"

    return result
