import os
import sys
import multiprocessing

def _worker_process():
    # 在子進程才載入 CTranslate2
    import faulthandler
    faulthandler.enable()
    
    print("[Worker] Loading faster_whisper...")
    from faster_whisper import WhisperModel
    model_size = "medium"

    print("[Worker] Initializing model (device=auto)...")
    try:
        model = WhisperModel(model_size, device="auto", compute_type="int8", cpu_threads=2)
        print("[Worker] SUCCESS: Model loaded with GPU!")
    except Exception as e:
        print(f"[Worker] Failed GPU, trying CPU... ({e})")
        model = WhisperModel(model_size, device="cpu", compute_type="float32", cpu_threads=4)
        print("[Worker] SUCCESS: Model loaded with CPU!")
        
    print("[Worker] Done. Waiting...")
    import time
    time.sleep(10)

if __name__ == '__main__':
    multiprocessing.freeze_support()
    
    # 這裡載入 PyQt6
    import PyQt6.QtCore as QtCore
    import PyQt6.QtWidgets as QtWidgets
    from PyQt6.QtWidgets import QApplication

    os.environ["KMP_DUPLICATE_LIB_OK"] = "TRUE"
    os.environ["TQDM_DISABLE"] = "1"

    print("[Main] Starting QApplication...")
    app = QApplication(sys.argv)
    
    print("[Main] Spawning Worker...")
    ctx = multiprocessing.get_context('spawn')
    p = ctx.Process(target=_worker_process)
    p.start()
    
    # PyQt 訊息迴圈 (我們這裡不阻塞，只等幾秒看子進程有沒有死)
    import time
    time.sleep(5)
    
    print(f"[Main] Worker alive? {p.is_alive()}")
    if p.is_alive():
        print("[Main] SUCCESS: Subprocess isolation works!")
        p.terminate()
        sys.exit(0)
    else:
        print(f"[Main] FAIL: Worker died with exit code {p.exitcode}")
        sys.exit(1)
