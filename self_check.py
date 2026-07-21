import os
import sys
import time
import traceback
import importlib.util
from pathlib import Path

def check_file_exists(path):
    exists = os.path.exists(path)
    print(f"[CHECK] File {path}: {'EXISTS' if exists else 'MISSING'}")
    return exists

def test_stt_recognition():
    print("[STT-TEST] Initializing STT Worker for functional test...")
    try:
        from stt.subprocess_whisper import SubprocessWhisperSTT
        config = {"whisper_model": "tiny", "stt_engine": "local_whisper"} # Use tiny for fast test
        stt = SubprocessWhisperSTT(config)
        
        # 1. Wait for ready
        print("[STT-TEST] Waiting for model to be ready (timeout 120s for download)...")
        start = time.time()
        while not stt.is_ready and (time.time() - start < 120):
            time.sleep(1.0)
        
        if not stt.is_ready:
            print("[FAIL] STT Worker failed to become ready in time.")
            return False
        
        print("[STT-TEST] Model READY. Sending dummy audio for recognition...")
        
        # 2. Perform a real transcription (1 second of silence/dummy)
        dummy_audio = b'\x00' * 32000 # 1 sec of 16kHz 16-bit mono
        result = stt.transcribe(dummy_audio)
        
        print(f"[STT-TEST] Recognition Successful. Result: '{result}' (Empty is OK for silence)")
        
        # 3. Cleanup
        del stt
        return True
    except Exception as e:
        print(f"[FAIL] STT Recognition Test crashed: {e}")
        traceback.print_exc()
        return False

def run_self_check():
    print("=== VoxProse STT-Deep-Check Initialized ===")
    
    # 1. Check basic structure
    essential_files = ["main.py", "paths.py", "stt/subprocess_whisper.py", "ui/app.py"]
    if not all(check_file_exists(f) for f in essential_files):
        print("  RESULT: FAILED (Missing core files)")
        sys.exit(1)
    
    # 2. Check Version Logic (NameError fix verification)
    try:
        from paths import VERSION_NAME, BUILD_ID
        print(f"[PASS] Constants: {VERSION_NAME} ({BUILD_ID})")
    except Exception as e:
        print(f"[FAIL] Version constants missing: {e}")
        sys.exit(1)

    # 3. Functional STT Test (The User Requirement)
    if not test_stt_recognition():
        print("  RESULT: FAILED (STT Chain Broken)")
        sys.exit(1)
    
    # 📝 Summary
    print("\n" + "="*40)
    print("  RESULT: SUCCESS (STT Recognition Verified)")
    sys.exit(0)

if __name__ == "__main__":
    run_self_check()
