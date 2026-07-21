import os
import sys
import threading
import platform
import multiprocessing
import multiprocessing.connection
import time
import io
import traceback

# v2.8.27_V73: Explicit model pre-download with progress (Clean Surgery)
def _download_progress_callback(n, total, pipe, model_alias):
    if total > 0:
        pct = int((n / total) * 100)
        pipe.send({"type": "progress", "value": pct, "detail": f"Downloading {model_alias}: {pct}%"})

from .base import BaseSTT


# Mac 主線 13-2（51094bf:stt/mlx_whisper.py）移植：抗幻覺轉錄參數。
# no_speech_threshold 拉高 → Whisper 對「這段沒人聲」更敏感；
# condition_on_previous_text=False → 不讓前一段的幻覺污染下一段。
# 抽成獨立函式方便單元測試 mock 驗證參數（_stt_worker 本體需要真實子程序環境無法直接測）。
DEFAULT_INITIAL_PROMPT = "以下是繁體中文的語音內容："


# Bug fix（2026-07-20）：client 端 transcribe() 把 vocab.manager.build_vocab_prompt()
# 的結果放進 IPC 訊息的 "prompt" 欄位送給 worker，但 worker 過去從未讀取該欄位，
# 一律用硬編預設字串，導致智慧詞彙學習對本地辨識完全沒有作用。
# 比照 Mac 版語義（git show 960f5e6:stt/mlx_whisper.py:128-129,154，51094bf 為對應
# Mac 原始碼庫的 commit，於本 repo 歷史中不可達）：build_vocab_prompt() 回傳值本身
# 就是完整的 initial_prompt（無詞彙時已內含預設語境句，有詞彙時取代並擴充），
# 是「取代」而非「串接」——沿用同一顆 model.transcribe() 的 initial_prompt 參數位。
def _run_transcribe(model, audio_np, language: str, initial_prompt: str = DEFAULT_INITIAL_PROMPT):
    return model.transcribe(
        audio_np,
        language=language,
        beam_size=5,
        initial_prompt=initial_prompt or DEFAULT_INITIAL_PROMPT,
        no_speech_threshold=0.6,
        condition_on_previous_text=False,
    )

# ── 這是隔離的子程序入口點 ────────────────────────────────────────────────
def _stt_worker(pipe_conn: multiprocessing.connection.Connection, config: dict):
    # 重大提醒: 這個 Process 是乾淨的，沒有 PyQt，沒有 pynput!
    
    import sys
    import os
    import faulthandler
    import logging
    from paths import APP_DATA_DIR
    import platform

    worker_log_path = APP_DATA_DIR / "worker_debug.log"
    faulthandler_path = APP_DATA_DIR / "worker_crash.log"
    
    # Open faulthandler log file to capture segfaults
    try:
        fh_file = open(str(faulthandler_path), "a")
        faulthandler.enable(file=fh_file)
    except: pass
    
    logging.basicConfig(
        filename=str(worker_log_path),
        level=logging.INFO,
        format='%(asctime)s [%(levelname)s] %(message)s',
        encoding='utf-8' # v2.8.27_V72: Fix Windows Mojibake
    )
    log = logging.getLogger("voicetype-worker")
    log.info("--- Worker Startup ---")

    # v2.8.27_V73: Register pipe for Tqdm progress reporting
    global _worker_pipe_for_tqdm
    _worker_pipe_for_tqdm = pipe_conn

    # v2.8.27_V69: The Missing Piece - AllocConsole is strictly required!
    # ctranslate2 (C++) will still crash with Access Violation in environments
    # without a valid console subsystem, EVEN IF fd 1 and 2 are NUL.
    if platform.system() == "Windows":
        import ctypes
        try:
            kernel32 = ctypes.windll.kernel32
            user32 = ctypes.windll.user32
            # 嘗試分配控制台，如果已經有控制台則沒關係
            if kernel32.AllocConsole():
                log.info("[stt-worker] Allocated fresh console.")
                hwnd = kernel32.GetConsoleWindow()
                if hwnd:
                    user32.ShowWindow(hwnd, 0) # SW_HIDE
            else:
                log.info("[stt-worker] Using existing console.")
        except Exception as e:
            log.warning(f"[stt-worker] Console init issue: {e}")

    # v2.8.27_V77: NVIDIA DLL Path Discovery (The "Make GPU Just Work" Patch)
    # MUST HAPPEN BEFORE IMPORTING faster_whisper or any torch/ctranslate2 components
    if platform.system() == "Windows":
        import ctypes
        try:
            # 1. First, inject paths from site-packages
            import site
            from pathlib import Path
            package_dirs = site.getsitepackages()
            for pdir in package_dirs:
                nvidia_root = Path(pdir) / "nvidia"
                if nvidia_root.exists():
                    for bin_dir in nvidia_root.glob("**/bin"):
                        if bin_dir.is_dir():
                            log.info(f"[stt-worker] Adding DLL directory: {bin_dir}")
                            os.add_dll_directory(str(bin_dir))
            
            # 2. Add current venv bin just in case
            venv_bin = Path(sys.executable).parent
            if (venv_bin / "cublas64_12.dll").exists():
                os.add_dll_directory(str(venv_bin))
                
        except Exception as e_dll:
            log.warning(f"[stt-worker] DLL injection issue: {e_dll}")

    # v2.8.27_V63: Environmental Fixes
    os.environ["KMP_DUPLICATE_LIB_OK"] = "TRUE"
    os.environ["MKL_THREADING_LAYER"] = "SEQUENTIAL"
    
    # Now safe to import
    from faster_whisper import WhisperModel
    import ctranslate2
    log.info(f"[stt-worker] CTranslate2 version: {ctranslate2.__version__}")
    
    model_size = config.get("whisper_model", "medium")
    device = config.get("whisper_device", "auto")
    compute_type = config.get("whisper_compute_type", "auto")
    
    # v2.8.27_V77: Hard Verification of CUDA DLLs BEFORE trying to load model
    # 2026-07-22: 抽成 stt/cuda_check.py:probe_cuda()，與 Dashboard
    # （ui/settings/dashboard_page.py）共用同一套判定，避免兩處各說各話
    # （見 docs/DECISIONS.md）。DLL 目錄探索在此已於上方跑過一次，
    # probe_cuda() 內重跑一次是無害的（add_dll_directory 可重複呼叫）。
    if device in ["auto", "cuda"]:
        from .cuda_check import probe_cuda
        cuda_status = probe_cuda()
        if cuda_status["accel_available"]:
            log.info("[stt-worker] CUDA check: cublas64_12 found and loadable.")
        else:
            log.warning(f"[stt-worker] CUDA check FAILED: {cuda_status['reason']}. FORCING CPU FALLBACK.")
            device = "cpu"
            compute_type = "int8" # Safest for CPU

    model = None
    try:
        from pathlib import Path
        model_cache_dir = str(APP_DATA_DIR / "whisper_models")
        Path(model_cache_dir).mkdir(parents=True, exist_ok=True)
        log.info(f"[stt-worker] Model cache dir: {model_cache_dir}")
        is_frozen = getattr(sys, 'frozen', False)
        
        # Mapping for faster-whisper models to HuggingFace Repos
        repo_map = {
            "tiny": "Systran/faster-whisper-tiny",
            "base": "Systran/faster-whisper-base",
            "small": "Systran/faster-whisper-small",
            "medium": "Systran/faster-whisper-medium",
            "large-v2": "Systran/faster-whisper-large-v2",
            "large-v3": "Systran/faster-whisper-large-v3",
            "large-v3-turbo": "deepdml/faster-whisper-large-v3-turbo-ct2"
        }
        repo_id = repo_map.get(model_size, f"Systran/faster-whisper-{model_size}")
        
        log.info(f"[stt-worker] Initializing {model_size} on {device}...")
        try:
            pipe_conn.send({"type": "progress", "value": 0, "detail": f"Loading {model_size}..."})
            os.environ["TQDM_DISABLE"] = "1"
            
            # Use local_files_only if possible to speed up READY signal
            model = WhisperModel(
                model_size, 
                device=device, 
                compute_type=compute_type, 
                cpu_threads=4, 
                download_root=model_cache_dir,
                local_files_only=False 
            )
            # v2.8.27_V77: Success path - send READY
            pipe_conn.send({"type": "progress", "value": 100, "detail": "Model Ready."})
            log.info(f"[stt-worker] Model loaded successfully on {model.model.device}.")
            pipe_conn.send({"type": "status", "ready": True})

        except Exception as e_load:
            log.error(f"[stt-worker] WhisperModel initial load failed: {e_load}")
            # Final desperate fallback to CPU
            if device != "cpu":
                log.info("[stt-worker] Attempting final emergency CPU fallback...")
                device = "cpu"
                compute_type = "int8"
                model = WhisperModel(model_size, device="cpu", compute_type="int8", cpu_threads=4, download_root=model_cache_dir)
                pipe_conn.send({"type": "status", "ready": True})
            else:
                raise e_load

    except Exception as e:
            log.error(f"[stt-worker] Model load/verify failed:\n{traceback.format_exc()}")
            # v2.8.27_V73: Nuclear option - if model.bin is missing/corrupted, wipe the snapshot
            try:
                import shutil
                msg = str(e).lower()
                if "model.bin" in msg or "unable to open file" in msg:
                    log.warning("[stt-worker] Corrupted model detected. Attempting to wipe snapshot for re-download...")
                    # We look for the snapshot directory in the cache
                    models_dir = Path(model_cache_dir)
                    for snapshot in models_dir.glob("**/snapshots/*"):
                        if snapshot.is_dir():
                            log.info(f"[stt-worker] Deleting potentially corrupted snapshot: {snapshot}")
                            shutil.rmtree(snapshot, ignore_errors=True)
            except Exception as _wipe_e:
                log.error(f"[stt-worker] Cleanup failed: {_wipe_e}")

            try:
                log.info(f"[stt-worker] Falling back to CPU int8...")
                model = WhisperModel(model_size, device="cpu", compute_type="int8", cpu_threads=4, download_root=model_cache_dir)
                
                # Verify CPU fallback too, just in case
                import numpy as np
                model.transcribe(np.zeros(1600, dtype=np.float32), language="en")
                
                pipe_conn.send({"type": "status", "ready": True})
                log.info(f"[stt-worker] CPU fallback (int8) model loaded.")
            except Exception as e2:
                log.error(f"[stt-worker] FATAL ERROR:\n{traceback.format_exc()}")
                pipe_conn.send({"type": "error", "message": f"Fatal STT Error: {e2}"})
                return
    except Exception as e:
        log.error(f"[stt-worker] Initialization failed:\n{traceback.format_exc()}")
        pipe_conn.send({"type": "error", "message": str(e)})
        return

    # 進入工作迴圈
    while True:
        try:
            if pipe_conn.poll(0.5):
                msg = pipe_conn.recv()
                
                if msg.get("type") == "quit":
                    log.info("[stt-worker] Received quit signal. Exiting.")
                    break
                    
                elif msg.get("type") == "transcribe":
                    # Consistently use "audio" as the key
                    audio_raw = msg.get("audio")
                    language = msg.get("language", "zh")
                    # Bug fix（2026-07-20）：讀取 client 端送來的詞彙 prompt（見上方
                    # _run_transcribe 註解）；空/缺一律 fallback 回預設字串。
                    initial_prompt = msg.get("prompt") or DEFAULT_INITIAL_PROMPT

                    if not audio_raw or len(audio_raw) < 100:
                        log.warning(f"[stt-worker] Received empty or tiny audio ({len(audio_raw) if audio_raw else 0} bytes). Skipping.")
                        pipe_conn.send({"type": "result", "text": ""})
                        continue

                    audio_len_kb = len(audio_raw) / 1024
                    log.info(f"[stt-worker] Starting transcription (Size: {audio_len_kb:.1f} KB, Lang: {language})")
                    
                    try:
                        import numpy as np
                        # Convert bytes to float32 numpy array (assuming 16-bit PCM 16kHz)
                        audio_np = np.frombuffer(audio_raw, dtype=np.int16).astype(np.float32) / 32768.0
                        
                        start_time = time.time()
                        segments, info = _run_transcribe(model, audio_np, language, initial_prompt)
                        
                        text = "".join(seg.text for seg in segments).strip()
                        trans_duration = time.time() - start_time
                        
                        log.info(f"[stt-worker] Result: '{text}' (Time: {trans_duration:.2f}s, Prob: {info.language_probability:.2f})")
                        pipe_conn.send({"type": "result", "text": text, "info": info.language})
                    except Exception as trans_e:
                        log.error(f"[stt-worker] Transcription error: {trans_e}\n{traceback.format_exc()}")
                        pipe_conn.send({"type": "error", "message": f"Transcribe failed: {trans_e}"})

                elif msg.get("type") == "warmup":
                    # Corrected warmup for WhisperModel
                    try:
                        log.info("[stt-worker] Executing warmup...")
                        import numpy as np
                        dummy_audio = np.zeros(1600, dtype=np.float32)
                        list(model.transcribe(dummy_audio, language="en"))
                        log.info("[stt-worker] Warmup done.")
                        pipe_conn.send({"type": "warmup_done"})
                    except Exception as e:
                        log.error(f"[stt-worker] Warmup failed: {e}")
                        pipe_conn.send({"type": "warmup_done"})
                        
        except EOFError:
            log.info("[stt-worker] Pipe closed by parent. Exiting.")
            break
        except KeyboardInterrupt:
            log.info("[stt-worker] Interrupted. Exiting.")
            break
        except Exception as e:
            log.error(f"[stt-worker] Unexpected error in loop: {e}")
            traceback.print_exc()

# ── 這是主程序使用的類別 (負責與子程序溝通) ──────────────────────────────
class SubprocessWhisperSTT(BaseSTT):
    def __init__(self, config: dict):
        self.config = config
        self._parent_conn, self._child_conn = multiprocessing.Pipe()
        self._lock = threading.Lock()
        
        print("[stt-mgr] Spawning Subprocess Whisper Worker using 'spawn' context...")
        # V37: 設置顯式的環境變數標記，確保 main.py 在 EXE 模式下能 100% 辨別子程序
        os.environ["VOICETYPE_STT_WORKER"] = "1"
        
        ctx = multiprocessing.get_context('spawn')
        self.worker_process = ctx.Process(
            target=_stt_worker, 
            args=(self._child_conn, self.config),
            daemon=True,
            name="STTWorker"
        )
        self.worker_process.start()
        # 啟動後在父程序清除，避免污染後續可能的其他子程序
        os.environ.pop("VOICETYPE_STT_WORKER", None)
        
        # v2.8.27_V44: 使用 thread-safe queue.Queue 作為本地分發 (避免 multiprocessing.Queue 的開銷)
        import queue
        self._ready_status = False
        self._error_message = None
        self._result_queue = queue.Queue() 
        
        # 啟動背景讀取執行緒
        self._stop_reader = threading.Event()
        self.reader_thread = threading.Thread(target=self._pipe_reader, daemon=True)
        self.reader_thread.start()

    def _pipe_reader(self):
        """唯一的 Pipe 讀取點，負責分發訊息"""
        import queue
        while not self._stop_reader.is_set():
            try:
                # 使用 poll + recv 防止阻塞過久
                if self._parent_conn.poll(0.5):
                    msg = self._parent_conn.recv()
                    m_type = msg.get("type")
                    
                    if m_type == "status" and msg.get("ready"):
                        self._ready_status = True
                        print("[stt-mgr] STT Worker reported ready (Async).")
                    elif m_type == "error":
                        self._error_message = msg.get("message")
                        # 也放入結果隊列以便 transcribe 知道出錯
                        self._result_queue.put(msg)
                    elif m_type == "result":
                        self._result_queue.put(msg)
                    elif m_type == "progress":
                        if hasattr(self, "on_progress") and self.on_progress:
                            self.on_progress(msg.get("value", 0), msg.get("detail", ""))
                    elif m_type == "warmup_done":
                        print("[stt-mgr] Warmup complete.")
            except (EOFError, ConnectionResetError):
                break
            except Exception as e:
                print(f"[stt-mgr] Pipe reader error: {e}")
                break

    @property
    def is_ready(self):
        return self._ready_status

    def transcribe(self, audio_bytes: bytes, language: str = "zh") -> str:
        if not audio_bytes:
            return ""
            
        try:
            from vocab.manager import build_vocab_prompt
            prompt = build_vocab_prompt()
        except Exception:
            prompt = "以下是繁體中文的語音內容："
            
        if not self.worker_process.is_alive():
            print("[stt-mgr] Worker process is dead. Re-initializing...")
            self.__init__(self.config) # Attempt re-init
            
        if not self._ready_status:
            print("[stt-mgr] Model not ready. Waiting up to 60s...")
            wait_start = time.time()
            while not self._ready_status and (time.time() - wait_start < 60):
                if not self.worker_process.is_alive():
                    print("[stt-mgr] Worker died while waiting for ready.")
                    break
                time.sleep(0.5)
            if not self._ready_status:
                print("[stt-mgr] Model loading timeout or crashed. Check worker_debug.log")
                return "（系統初始化中，請稍後再試...）"

        print("[stt-mgr] Dispatching transcription task to worker...")
        
        try:
            with self._lock: # V33: 防止主程序的多個執行緒 (例如 warmup 和 record_stop) 搶奪 pipe
                self._parent_conn.send({
                    "type": "transcribe",
                    "audio": audio_bytes, # Use "audio" to match worker's recv
                    "language": language,
                    "prompt": prompt
                })
                
                # V78: 實作訊息循環過濾機制，避免被中間的 progress/status 訊息干擾導致提前退出
                import queue
                try:
                    while True:
                        msg = self._result_queue.get(timeout=30.0) 
                        msg_type = msg.get("type")
                        
                        if msg_type == "result":
                            text_result = msg.get("text", "")
                            print(f"[stt-mgr] Received result ({msg.get('info', 'zh')}): {text_result}")
                            return text_result
                        elif msg_type == "error":
                            raise RuntimeError(msg.get("message"))
                        elif msg_type in ["progress", "status"]:
                            # 忽略中間訊息，繼續等待結果
                            continue
                        else:
                            print(f"[stt-mgr] Ignoring unknown IPC message: {msg_type}")
                            
                except queue.Empty:
                    if not self.worker_process.is_alive():
                        print("[stt-mgr] Worker died during transcription.")
                        raise RuntimeError("STT Worker process died unexpectedly.")
                    else:
                        print("[stt-mgr] timeout waiting for transcription (Queue Empty).")
                        raise RuntimeError("STT Transcription timed out.")
        except Exception as e:
            print(f"[stt-mgr] IPC Error during transcribe: {e}")
            raise RuntimeError(f"STT Transcription failed: {e}")

    def warmup(self):
        print("[stt-mgr] Sending warmup signal...")
        try:
            with self._lock:
                self._parent_conn.send({"type": "warmup"})
            # 這裡不阻塞等待，免得卡住主執行緒
        except Exception as e:
            print(f"[stt-mgr] Failed to send warmup: {e}")

    def __del__(self):
        try:
            self._parent_conn.send({"type": "quit"})
            if self.worker_process.is_alive():
                self.worker_process.join(timeout=1.0)
                if self.worker_process.is_alive():
                    self.worker_process.terminate()
        except Exception:
            pass
