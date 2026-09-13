"""stt/cuda_check.py:probe_cuda() 單元測試（2026-07-22）。

背景：`ui/settings/dashboard_page.py` 過去只用
`ctranslate2.get_cuda_device_count() > 0` 判斷「CUDA 加速可用」，但這只是問
NVIDIA 驅動有沒有裝置，不代表 faster-whisper/ctranslate2 實際載入模型時能
用得到——真正需要的 cuBLAS 執行期函式庫（`requirements-cuda-win.txt`）沒裝
時，Dashboard 仍會顯示「加速可用」，但 `stt/subprocess_whisper.py` 的 worker
其實已經靜默降級回 CPU。`probe_cuda()` 補上與 worker 相同的
`ctypes.WinDLL("cublas64_12.dll")` 硬驗證，讓兩處回報一致。

全部用 mock（`ctranslate2` 模組、`ctypes.WinDLL`），不依賴真實硬體/驅動，
CI（無 GPU 的 windows-latest runner）也能穩定跑。涵蓋四種情境：
1. 完全沒裝 ctranslate2（驅動組件遺失）。
2. 裝了但裝置數為 0（沒有 CUDA GPU）。
3. 有裝置但 cuBLAS 載入失敗（缺 CUDA 函式庫，這是本次 Dashboard 誤導 bug
   的真實重現案例：`ctranslate2.get_cuda_device_count()` 回 1，但機器只裝了
   `requirements-win.txt`，沒裝 `requirements-cuda-win.txt`）。
4. 有裝置且 cuBLAS 可正常載入（加速真的可用）。
"""
import sys
import types

import pytest

from stt.cuda_check import probe_cuda


def _fake_ctranslate2(device_count=None, raise_on_call=False):
    """建立一個假的 ctranslate2 module 物件，塞進 sys.modules。"""
    mod = types.ModuleType("ctranslate2")

    def _get_cuda_device_count():
        if raise_on_call:
            raise RuntimeError("boom")
        return device_count

    mod.get_cuda_device_count = _get_cuda_device_count
    return mod


def test_probe_cuda_no_ctranslate2_installed(monkeypatch):
    """情境 1：ctranslate2 完全沒裝（import 失敗）。"""
    monkeypatch.setitem(sys.modules, "ctranslate2", None)

    result = probe_cuda()

    assert result["device_count"] == 0
    assert result["accel_available"] is False
    assert "驅動組件遺失" in result["reason"]


def test_probe_cuda_device_count_zero(monkeypatch):
    """情境 2：ctranslate2 裝了，但機器上沒有 CUDA GPU（count=0）。"""
    monkeypatch.setitem(sys.modules, "ctranslate2", _fake_ctranslate2(device_count=0))

    result = probe_cuda()

    assert result["device_count"] == 0
    assert result["accel_available"] is False
    assert "未偵測到 CUDA GPU" in result["reason"]


def test_probe_cuda_device_count_call_raises(monkeypatch):
    """額外情境：get_cuda_device_count() 本身丟例外（GPU 偵測組件異常）。"""
    monkeypatch.setitem(sys.modules, "ctranslate2", _fake_ctranslate2(raise_on_call=True))

    result = probe_cuda()

    assert result["device_count"] == 0
    assert result["accel_available"] is False
    assert "GPU 偵測組件異常" in result["reason"]


def test_probe_cuda_device_found_but_cublas_missing(monkeypatch):
    """情境 3（本次 bug 的真實重現）：ctranslate2 回報有 1 張 GPU，但機器只裝
    了 requirements-win.txt、沒裝 requirements-cuda-win.txt 的 CUDA 函式庫，
    cuBLAS DLL 載入失敗——worker 會強制降級 CPU，Dashboard 也該誠實反映。"""
    monkeypatch.setitem(sys.modules, "ctranslate2", _fake_ctranslate2(device_count=1))

    import platform as platform_module
    monkeypatch.setattr(platform_module, "system", lambda: "Windows")

    import ctypes

    def _raise_winerror(name):
        raise OSError(f"Could not find module '{name}'")

    monkeypatch.setattr(ctypes, "WinDLL", _raise_winerror, raising=False)

    result = probe_cuda()

    assert result["device_count"] == 1
    assert result["accel_available"] is False
    assert "缺少 CUDA 函式庫" in result["reason"]


def test_probe_cuda_fully_available(monkeypatch):
    """情境 4：有裝置，且 cuBLAS 可正常載入——加速真的可用。"""
    monkeypatch.setitem(sys.modules, "ctranslate2", _fake_ctranslate2(device_count=1))

    import platform as platform_module
    monkeypatch.setattr(platform_module, "system", lambda: "Windows")

    import ctypes

    class _FakeWinDLL:
        def __init__(self, name):
            self.name = name

    monkeypatch.setattr(ctypes, "WinDLL", _FakeWinDLL, raising=False)

    result = probe_cuda()

    assert result["device_count"] == 1
    assert result["accel_available"] is True
    assert result["reason"] == "CUDA 加速可用"


def test_probe_cuda_non_windows_platform_is_conservative(monkeypatch):
    """非 Windows 平台：本 fork 目前只支援 Windows，get_stt() 在其他平台走
    LocalWhisperSTT（不經過本模組），但 probe_cuda() 若被誤用也不該樂觀宣稱
    可用——保守回 False。"""
    monkeypatch.setitem(sys.modules, "ctranslate2", _fake_ctranslate2(device_count=1))

    import platform as platform_module
    monkeypatch.setattr(platform_module, "system", lambda: "Darwin")

    result = probe_cuda()

    assert result["device_count"] == 1
    assert result["accel_available"] is False


if __name__ == "__main__":
    sys.exit(pytest.main([__file__, "-v"]))
