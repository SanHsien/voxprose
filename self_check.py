"""
VoiceType4TW Self-Check Utility (v2.7.32)
Diagnoses Windows environment issues, dependencies, and hardware status.
"""
import os
import sys
import platform
import subprocess
from pathlib import Path

# v2.7.32: Fix environment for standalone check
if platform.system() == "Windows":
    os.environ["KMP_DUPLICATE_LIB_OK"] = "TRUE"

def print_header(text):
    print(f"\n{'='*20} {text} {'='*20}")

def check_env_vars():
    print_header("Environment Variables")
    ok = os.environ.get("KMP_DUPLICATE_LIB_OK") == "TRUE"
    print(f"KMP_DUPLICATE_LIB_OK: {os.environ.get('KMP_DUPLICATE_LIB_OK')} {'[PASS]' if ok else '[FAIL - Critical for Windows]'}")
    return ok

def check_dependencies():
    print_header("Dependencies")
    deps = ["PyQt6", "faster_whisper", "pystray", "PIL", "pynput", "pyperclip", "certifi"]
    all_ok = True
    for dep in deps:
        try:
            if dep == "PIL":
                import PIL
            else:
                __import__(dep)
            print(f"{dep:<15}: [OK]")
        except ImportError:
            print(f"{dep:<15}: [MISSING]")
            all_ok = False
    return all_ok

def check_hardware():
    print_header("Hardware & Drivers")
    # 1. GPU / CUDA
    try:
        import ctranslate2
        cuda_count = ctranslate2.get_cuda_device_count()
        if cuda_count > 0:
            print(f"CUDA GPU found: {cuda_count} device(s) [PASS]")
        else:
            print("CUDA GPU: Not found [INFO - Running in CPU mode]")
    except Exception as e:
        print(f"CUDA check failed: {e}")

    # 2. Audio Device
    try:
        import sounddevice
        devices = sounddevice.query_devices()
        input_devs = [d for d in devices if d['max_input_channels'] > 0]
        if input_devs:
            print(f"Audio Input: {len(input_devs)} device(s) found [PASS]")
            default = sounddevice.query_devices(kind='input')
            print(f"Default Mic: {default.get('name')}")
        else:
            print("Audio Input: No microphones detected! [FAIL]")
    except Exception as e:
        print(f"Audio check failed: {e}")

def check_filesystem():
    print_header("File System")
    try:
        from paths import APP_DATA_DIR, get_data_dir
        data_dir = APP_DATA_DIR
    except ImportError:
        print("paths.py not found or invalid.")
        return

    print(f"Data Directory: {data_dir}")
    if data_dir.exists():
        try:
            # Test writing to a subfolder using get_data_dir
            test_dir = get_data_dir("diag_test")
            test_file = test_dir / "test_write.tmp"
            test_file.write_text("test")
            test_file.unlink()
            print("Write Permission: [OK]")
        except Exception as e:
            print(f"Write Permission: [FAIL] - {e}")
    else:
        print(f"Data Directory: [MISSING] - Path: {data_dir}")

def check_models():
    print_header("AI Models Status")
    cache_path = Path.home() / ".cache" / "huggingface" / "hub"
    if cache_path.exists():
        found = list(cache_path.glob("models--Systran--faster-whisper-*"))
        if found:
            print(f"Faster-Whisper Models: {len(found)} cached [PASS]")
            for m in found:
                print(f"  - {m.name}")
        else:
            print("Faster-Whisper Models: Not cached [INFO - Will download on first run]")
    else:
        print("HF Cache: Not found [INFO]")

if __name__ == "__main__":
    print("Starting VoiceType4TW Self-Check...")
    print(f"OS: {platform.system()} {platform.release()}")
    print(f"Python: {sys.version}")
    
    check_env_vars()
    check_dependencies()
    check_hardware()
    check_filesystem()
    check_models()
    
    print_header("Diagnostics Done")
    input("\nPress Enter to exit...")
