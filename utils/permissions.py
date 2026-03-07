import os
import sys
import platform
import subprocess
import ctypes
import logging

log = logging.getLogger("voicetype")

def is_macos():
    return platform.system() == "Darwin"

def check_accessibility():
    """檢查補助功能 (Accessibility) 權限"""
    if not is_macos():
        return True
    try:
        lib = ctypes.cdll.LoadLibrary(
            '/System/Library/Frameworks/ApplicationServices.framework/ApplicationServices')
        lib.AXIsProcessTrusted.restype = ctypes.c_bool
        return lib.AXIsProcessTrusted()
    except Exception as e:
        log.error(f"[PERM] Accessibility check FAILED: {e}")
        return False

def check_microphone():
    """檢查麥克風權限 (不會觸發彈窗)"""
    if not is_macos():
        return True
    try:
        import objc
        objc.loadBundle('AVFoundation', bundle_path='/System/Library/Frameworks/AVFoundation.framework', module_globals=globals())
        # 'soun' is the type for 'audio' in AVFoundation (AVMediaTypeAudio)
        status = AVCaptureDevice.authorizationStatusForMediaType_('soun')
        return status == 3 # 3 == AVAuthorizationStatusAuthorized
    except Exception as e:
        log.error(f"[PERM] Microphone check FAILED: {e}")
        return False

def request_microphone_permission():
    """主動觸發麥克風權限彈窗"""
    if not is_macos():
        return
    log.info("[PERM] Triggering Microphone permission dialog...")
    try:
        import sounddevice as sd
        # 開啟一個極短的流來觸發系統彈窗
        def callback(indata, frames, time, status):
            pass
        with sd.InputStream(callback=callback, channels=1, samplerate=16000):
            pass
    except Exception as e:
        log.error(f"[PERM] Failed to trigger Mic dialog: {e}")

def request_apple_events_permission():
    """主動觸發 System Events (AppleEvents) 權限彈窗"""
    if not is_macos():
        return
    log.info("[PERM] Triggering System Events permission dialog...")
    try:
        # 執行一個無害的 AppleScript 來觸發權限要求
        script = 'tell application "System Events" to get name of contents'
        subprocess.run(["osascript", "-e", script], capture_output=True, timeout=2)
    except Exception as e:
        log.error(f"[PERM] Failed to trigger AppleEvents dialog: {e}")

def ensure_all_permissions():
    """檢查並在必要時主動觸發權限要求"""
    if not is_macos():
        return
        
    # 麥克風：如果沒權限，觸發一下
    if not check_microphone():
        request_microphone_permission()
        
    # AppleEvents：我們無法直接偵測權限，但可以在啟動時「戳」一下讓彈窗出現
    # 否則使用者第一次貼上時才會跳彈窗，會造成斷點
    request_apple_events_permission()
    
    # 註：Accessibility 無法透過代碼觸發「允許」彈窗（只能帶使用者去設定頁面）
    # pynput 在啟動時如果沒權限會自動跳提示
