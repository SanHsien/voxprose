import os
import sys
# 啟用 faulthandler 捕捉 C++ 崩潰
import faulthandler
faulthandler.enable()

print("1. Loading PyQt6...")
import PyQt6.QtCore as QtCore
import PyQt6.QtWidgets as QtWidgets
from PyQt6.QtWidgets import QApplication

os.environ["KMP_DUPLICATE_LIB_OK"] = "TRUE"

# 致命致命！tqdm._monitor.py 的背景執行緒會和 PyQt 發生 Access Violation
os.environ["TQDM_DISABLE"] = "1"
# 對某些版本的 tqdm 也試試這個
import os
os.environ["TQDM_DISABLE_MONITOR"] = "1"

print("2. Starting QApplication...")
app = QApplication(sys.argv)

print("3. Loading faster_whisper...")
from faster_whisper import WhisperModel
model_size = "medium"

print("4. Initializing model (device=auto)...")
try:
    model = WhisperModel(model_size, device="auto", compute_type="int8", cpu_threads=2)
    print("SUCCESS: Model loaded with GPU!")
except Exception as e:
    print(f"Failed GPU, trying CPU... ({e})")
    model = WhisperModel(model_size, device="cpu", compute_type="float32", cpu_threads=4)
    print("SUCCESS: Model loaded with CPU!")

print("5. Done.")
sys.exit(0)
