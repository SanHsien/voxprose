#!/usr/bin/env python3
"""
VoiceType4TW macOS Microphone Diagnostic Tool
Systmatically checks permissions and actual audio input energy.
"""
import os
import sys
import platform
import time
import numpy as np
import sounddevice as sd

def print_header(text):
    print(f"\n{'='*20} {text} {'='*20}")

def check_permission_status():
    print_header("1. OS Permission Check (AVFoundation)")
    if platform.system() != "Darwin":
        print("This diagnostic is for macOS only.")
        return False
        
    try:
        import objc
        # Dynamically load AVFoundation
        objc.loadBundle('AVFoundation', 
                        bundle_path='/System/Library/Frameworks/AVFoundation.framework', 
                        module_globals=globals())
        from Foundation import NSBundle
        
        # Check authorization status
        # AVMediaTypeAudio = 'soun'
        status = AVCaptureDevice.authorizationStatusForMediaType_('soun')
        
        mapping = {
            0: "Not Determined (尚未決定)",
            1: "Restricted (受限)",
            2: "Denied (拒絕)",
            3: "Authorized (已授權)"
        }
        
        print(f"Current Status: {mapping.get(status, f'Unknown {status}')}")
        
        if status == 3:
            print("[PASS] macOS reports that Microphone access is AUTHORIZED.")
            return True
        elif status == 0:
            print("[INFO] Permission not requested yet. Trying to trigger...")
            # We don't want to hang here with a handler, just inform.
            return False
        else:
            print("[FAIL] Microphone access is NOT AUTHORIZED by the system.")
            return False
            
    except Exception as e:
        print(f"[ERROR] Could not check AVFoundation status: {e}")
        return False

def check_audio_devices():
    print_header("2. SoundDevice / PortAudio Device Check")
    try:
        devices = sd.query_devices()
        print(f"Total devices found: {len(devices)}")
        
        input_devs = [d for d in devices if d['max_input_channels'] > 0]
        if not input_devs:
            print("[FAIL] No input devices (microphones) detected by PortAudio!")
            return False
            
        default = sd.query_devices(kind='input')
        print(f"Default Input Device: {default.get('name')}")
        return True
    except Exception as e:
        print(f"[FAIL] PortAudio Error: {e}")
        return False

def test_recording_energy():
    print_header("3. Real-time Audio Energy Test (The 'Silicon Silence' Check)")
    print("Preparing to record 3 seconds of audio...")
    print(">>> PLEASE SPEAK INTO YOUR MICROPHONE NOW <<<")
    
    fs = 16000
    duration = 3.0 # seconds
    
    try:
        recording = sd.rec(int(duration * fs), samplerate=fs, channels=1, dtype='float32')
        
        # Countdown
        for i in range(3, 0, -1):
            print(f"{i}...")
            time.sleep(1)
            
        sd.wait() # Wait for recording to finish
        
        # Analyze energy
        energy = np.sqrt(np.mean(recording**2))
        max_val = np.max(np.abs(recording))
        
        print(f"\nResults:")
        print(f"RMS Energy: {energy:.6f}")
        print(f"Peak Value: {max_val:.6f}")
        
        if energy < 1e-7:
            print("\n[CRITICAL FAIL] SILENCE DETECTED (能源趨近於零)")
            print("這通常代表 TCC 雖然顯示授權，但 macOS 核心 (CoreAudio) 卻攔截了資料串流。")
            return False
        elif energy < 1e-3:
            print("\n[WARNING] VERY LOW VOLUME DETECTED.")
            print("請檢查系統輸入音量設定或確保您有對著麥克風說話。")
            return True
        else:
            print("\n[SUCCESS] AUDIO DATA RECEIVED! (收到音訊資料)")
            return True
            
    except Exception as e:
        print(f"[ERROR] Recording test failed: {e}")
        return False

def suggest_fixes(has_perm, has_energy):
    print_header("🔍 Recommended Actions / 建議方案")
    
    if not has_perm:
        print("1. [修復權限] 請前往『系統設定』->『隱私權與安全性』->『麥克風』。")
        print("   確保您啟動 VoiceType 的程式（如 Terminal, VSCode 或 .app）開關已開啟。")
    
    if has_perm and not has_energy:
        print("1. [重置 TCC 紀錄] 這是最有效的解法，執行以下指令並重新啟動：")
        print("   tccutil reset Microphone")
        print("\n2. [重啟音訊服務] 有時 CoreAudio 會卡死，執行：")
        print("   sudo killall coreaudiod")
        print("\n3. [檢查輸入裝置] 進入『系統設定』->『聲音』，確認輸入裝置選擇正確且有跳動量表。")
        print("\n4. [如果是 .app 版] 這通常涉及 Code Signing 損壞。建議重新執行安裝腳本。")

if __name__ == "__main__":
    print("VoiceType4TW macOS Mic Diagnostic Start")
    perm_ok = check_permission_status()
    dev_ok = False
    if perm_ok:
        dev_ok = check_audio_devices()
        
    energy_ok = False
    if dev_ok:
        energy_ok = test_recording_energy()
        
    suggest_fixes(perm_ok, energy_ok)
    
    print("\n" + "="*50)
    print("Diagnostic Complete.")
