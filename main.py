import os
import sys

# Ensure app directory is on sys.path — required for embedded Python (.runtime)
# which does not automatically add the script's directory.
_app_dir = os.path.dirname(os.path.abspath(__file__))
if _app_dir not in sys.path:
    sys.path.insert(0, _app_dir)

import multiprocessing
import platform
import time
import traceback
import logging
import certifi

# v2.8.27_V66: The Ultimate C++ Windowed Crash Fix (Access Violation 0xC0000005)
# PyInstaller --windowed destroys the C Runtime console handles.
# Any C++ library (like ctranslate2) trying to write to std::cout/std::cerr will ACCESS VIOLATE.
# We MUST map file descriptors 1 and 2 to NUL at the very beginning of the process.
if sys.platform == "win32" and getattr(sys, 'frozen', False):
    try:
        null_fd = os.open(os.devnull, os.O_RDWR)
        os.dup2(null_fd, 1)
        os.dup2(null_fd, 2)
    except OSError as e:
        # 2026-07-23（broad except 清查）：這段本身是「防止 ctranslate2 Access
        # Violation」的關鍵前置步驟（見上方 docstring）——若失敗又完全靜默，
        # 之後真的撞見無訊息崩潰時會完全查不到源頭。這裡 fd 1/2 尚未被導向
        # NUL，print 仍會到達原本的 stdout/stderr。
        print(f"[main] WARNING: Failed to redirect fd 1/2 to NUL: {e}", file=sys.stderr)

# v2.8.27_V70: THE ULTIMATE DEFENSE - threading.Thread.start Hook
import threading
try:
    _orig_thread_start = threading.Thread.start
    def _hooked_thread_start(self, *args, **kwargs):
        cls_name = str(self.__class__)
        thread_name = str(getattr(self, "name", ""))
        if "tqdm" in cls_name.lower() or "tqdm" in thread_name.lower():
            return
        return _orig_thread_start(self, *args, **kwargs)
    threading.Thread.start = _hooked_thread_start
except Exception as e:
    print(f"[main] WARNING: tqdm thread-hook install failed: {e}", file=sys.stderr)

# This MUST be set before any module loads libiomp5md.dll
os.environ["KMP_DUPLICATE_LIB_OK"] = "TRUE"

# v2.8.27_V68: Fatal Conflict Prevention between PyQt6 and CTranslate2
# When CTranslate2 loads in the same process as PyQt, Intel OpenMP tries to 
# initialize its thread pool and violently clashes with Qt's event loop, 
# resulting in Access Violation 0xC0000005. 
# We MUST force OpenMP to be sequential or strictly limited BEFORE importing faster_whisper.
os.environ["MKL_THREADING_LAYER"] = "SEQUENTIAL"
os.environ["OMP_NUM_THREADS"] = "1"
os.environ["CT2_USE_EXPERIMENTAL_PACKED_GEMM"] = "0"

# v2.8.27_V68: The ultimate bullet against Subprocess + PyInstaller crashes.
# faster_whisper uses tqdm. tqdm spawns a background monitor thread (_monitor.py)
# that violently crashes with Access Violation in Windows PyInstaller environments.
os.environ["TQDM_DISABLE"] = "1"
os.environ["TQDM_DISABLE_MONITOR"] = "1"

# V52: Ultra-Robust Main Process Detection
is_main_process = (
    getattr(multiprocessing.current_process(), 'name', '') == 'MainProcess' and
    os.environ.get("VOICETYPE_STT_WORKER") != "1" and
    "--multiprocessing-fork" not in sys.argv
)

if __name__ == "__main__":
    if platform.system() == "Windows":
        multiprocessing.freeze_support()
        
        # v2.8.27_V87: Modular Branding Initialization
        try:
            from utils.branding import init_windows_id
            init_windows_id()
        except Exception as e:
            logging.getLogger("voicetype").warning(f"[main] Branding init failed: {e}")
        
    # v2.8.27_V53: Force use certifi for SSL robustness in bundled environment
    try:
        os.environ['SSL_CERT_FILE'] = certifi.where()
    except Exception as e:
        print(f"[main] WARNING: Failed to set SSL_CERT_FILE via certifi: {e}", file=sys.stderr)
    
    if is_main_process:
        try:
            from paths import initialize_paths, APP_DATA_DIR, VERSION_NAME
            initialize_paths()

            # Enable faulthandler for main process crash logging
            # 2026-07-21: was a hardcoded os.environ['APPDATA']/'VoiceType4TW' literal
            # duplicating paths.APP_DATA_DIR; now references it directly. Pure
            # refactor — the actual on-disk path is unchanged (see docs/DECISIONS.md).
            import faulthandler
            app_data_dir = str(APP_DATA_DIR)
            if app_data_dir:
                os.makedirs(app_data_dir, exist_ok=True)
                crash_log = open(os.path.join(app_data_dir, "main_crash.log"), 'w', encoding='utf-8')
                faulthandler.enable(file=crash_log)

            # v2.8.27_V61: Fix logging not recording after V50
            # 2026-07-23：debug.log 原本用 FileHandler 附加寫入，沒有大小上限，
            # 長期執行會無限增長；改用共用的 RotatingFileHandler（見
            # utils/log_rotation.py，5MB×2 備份）。
            from utils.log_rotation import make_rotating_file_handler
            log_path = APP_DATA_DIR / "debug.log"
            logging.basicConfig(
                level=logging.INFO,
                format='%(asctime)s [%(levelname)s] %(name)s: %(message)s',
                handlers=[
                    make_rotating_file_handler(log_path),
                    logging.StreamHandler()
                ]
            )
            # v2.8.27_V73: Restore the "Flagship Banner" log style per user request
            from datetime import datetime
            banner_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            log_header = f"\n{'='*50}\n[START] {banner_time} {VERSION_NAME}\n{'='*50}"
            logging.getLogger("voicetype").info(log_header)
            logging.getLogger("voicetype").info(f"=== VoxProse Starting === Log: {log_path} (Level: INFO)")

            from ui.app import VoiceTypeApp
            app = VoiceTypeApp()
            app.run()
        except Exception as e:
            # Final attempt to log before death
            try:
                msg = f"[main] FATAL CRASH: {e}\n{traceback.format_exc()}"
                print(msg)
                with open("crash_emergency.log", "a", encoding="utf-8") as f:
                    f.write(msg + "\n")
            except Exception:
                # 緊急 crash log 本身也可能因權限或磁碟問題失敗；此時只能
                # 保留原始退出行為，但不要吞掉 KeyboardInterrupt/SystemExit。
                pass
            os._exit(1)
    else:
        # Child processes are handled by multiprocessing/freeze_support
        pass
