
import os
import sys
import platform
import faulthandler
import multiprocessing

# Simulate main.py top-level environment
if platform.system() == "Windows":
    multiprocessing.freeze_support()
    os.environ["KMP_DUPLICATE_LIB_OK"] = "TRUE"
    os.environ["MKL_THREADING_LAYER"] = "GNU"
    os.environ["MKL_SERVICE_FORCE_INTEL"] = "1"
    os.environ["CT2_CUDA_ALLOW_FALLBACK"] = "1"
    os.environ["OMP_NUM_THREADS"] = "1"
    os.environ["KMP_BLOCKTIME"] = "0"
    os.environ["MKL_DEBUG_CPU_TYPE"] = "5"
    os.environ["MKL_CBWR"] = "COMPATIBLE"
    
    _fault_path = "test_fault.log"
    _fault_file = open(_fault_path, "w", encoding="utf-8")
    faulthandler.enable(file=_fault_file)

print("--- [SIMULATION START] ---")
print(f"Python: {sys.version}")
print(f"Platform: {platform.platform()}")

try:
    print("(1/3) Importing faster_whisper...")
    import faster_whisper
    from faster_whisper import WhisperModel
    print("      OK.")
    
    print("(2/3) Initializing WhisperModel (Device: cpu, Model: tiny)...")
    # Use 'tiny' for fast test
    model = WhisperModel("tiny", device="cpu", compute_type="int8")
    print("      OK.")
    
    print("(3/3) Running a dummy transcription...")
    # Just check if methods are callable
    print(f"      Model loaded: {model}")
    print("--- [SIMULATION SUCCESS] ---")
except Exception as e:
    print(f"!!! [SIMULATION FAILED]: {e}")
    import traceback
    traceback.print_exc()
finally:
    if platform.system() == "Windows":
        _fault_file.close()
