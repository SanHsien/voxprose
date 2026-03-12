import os
import sys
import threading
import platform
import multiprocessing
import multiprocessing.connection
import time
import io
import traceback

# v2.8.27_V70: THE ULTIMATE DEFENSE - threading.Thread.start Hook (Global)
try:
    _orig_thread_start = threading.Thread.start
    def _hooked_thread_start(self, *args, **kwargs):
        cls_name = str(self.__class__)
        thread_name = str(getattr(self, "name", ""))
        if "tqdm" in cls_name.lower() or "tqdm" in thread_name.lower():
            return
        return _orig_thread_start(self, *args, **kwargs)
    threading.Thread.start = _hooked_thread_start
except Exception: pass

# Force tqdm mock and kill monitor EARLY
os.environ["TQDM_DISABLE"] = "1"
os.environ["TQDM_DISABLE_MONITOR"] = "1"
try:
    from unittest.mock import MagicMock
    class MagicPackage(MagicMock):
        def __getattr__(self, name): return self
        def __call__(self, *args, **kwargs): return self
    mock_tqdm = MagicPackage()
    sys.modules['tqdm'] = mock_tqdm
    sys.modules['tqdm.auto'] = mock_tqdm
    sys.modules['tqdm.std'] = mock_tqdm
    sys.modules['tqdm._monitor'] = mock_tqdm
    sys.modules['tqdm.notebook'] = mock_tqdm
    
    import tqdm._monitor
    tqdm._monitor.TqdmMonitor.run = lambda self: None
except Exception: pass

from .base import BaseSTT

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
            log.warning(f"[stt-worker] AllocConsole attempted: {e}")

    # v2.8.27_V63: Critical environment setup for EXE subprocess stability
    os.environ["KMP_DUPLICATE_LIB_OK"] = "TRUE"
    os.environ["MKL_THREADING_LAYER"] = "SEQUENTIAL"
    os.environ["OMP_NUM_THREADS"] = "4" # v2.8.27_V72: Increase for speed
    os.environ["CT2_VERBOSE"] = "-1" 
    os.environ["CT2_USE_EXPERIMENTAL_PACKED_GEMM"] = "0"
    
    from faster_whisper import WhisperModel
    import ctranslate2
    log.info(f"[stt-worker] CTranslate2 version: {ctranslate2.__version__}")
    
    model_size = config.get("whisper_model", "medium")
    
    # v2.8.27_V69: With AllocConsole back, we can safely use GPU in frozen mode again.
    # No more CPU fallback required!
    import sys
    device = "auto"
    compute_type = "int8"
    
    model = None
    try:
        from pathlib import Path
        model_cache_dir = str(APP_DATA_DIR / "whisper_models")
        Path(model_cache_dir).mkdir(parents=True, exist_ok=True)
        log.info(f"[stt-worker] Model cache dir: {model_cache_dir}")
        is_frozen = getattr(sys, 'frozen', False)
        log.info(f"[stt-worker] Loading Whisper {model_size} (Device: {device}, Type: {compute_type}, Frozen: {is_frozen}) ...")

        
        model = WhisperModel(model_size, device=device, compute_type=compute_type, cpu_threads=4, download_root=model_cache_dir)
        log.info(f"[stt-worker] Model loaded successfully on {model.model.device}.")
        pipe_conn.send({"type": "status", "ready": True})
    except Exception as e:
        log.error(f"[stt-worker] Model load failed:\n{traceback.format_exc()}")
        try:
            log.info(f"[stt-worker] Falling back to CPU int8...")
            model = WhisperModel(model_size, device="cpu", compute_type="int8", cpu_threads=4, download_root=model_cache_dir)
            pipe_conn.send({"type": "status", "ready": True})
            log.info(f"[stt-worker] CPU fallback (int8) model loaded.")
        except Exception as e2:
            log.error(f"[stt-worker] FATAL ERROR:\n{traceback.format_exc()}")
            pipe_conn.send({"type": "error", "message": str(e2)})
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
                    audio_bytes = msg.get("audio_bytes")
                    language = msg.get("language", "zh")
                    prompt = msg.get("prompt", "以下是繁體中文的語音內容：")
                    
                    if not audio_bytes:
                        pipe_conn.send({"type": "result", "text": ""})
                        continue

                    audio_io = io.BytesIO(audio_bytes)
                    try:
                        segments, info = model.transcribe(
                            audio_io,
                            language=language,
                            beam_size=1,
                            vad_filter=True,
                            initial_prompt=prompt,
                        )
                        text = "".join(seg.text for seg in segments).strip()
                        pipe_conn.send({"type": "result", "text": text, "info": info.language})
                        log.info(f"[stt-worker] Transcribed successfully: {text}")
                    except Exception as trans_e:
                        log.error(f"[stt-worker] Transcription error: {trans_e}")
                        traceback.print_exc()
                        pipe_conn.send({"type": "error", "message": f"Transcribe failed: {trans_e}"})

                elif msg.get("type") == "warmup":
                    # Simple warmup
                    try:
                        # Dummy audio (1 second of silence at 16kHz)
                        dummy_audio = b'\x00' * (16000 * 2) 
                        model.generate_vad_segments(dummy_audio) # fast way to wake up OpenMP
                        pipe_conn.send({"type": "warmup_done"})
                    except Exception:
                        pipe_conn.send({"type": "warmup_done"}) # Ignore errors in warmup
                        
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
                    "audio_bytes": audio_bytes,
                    "language": language,
                    "prompt": prompt
                })
                
                # V43: 從 _result_queue 讀取，不再直接 poll Pipe
                import queue
                try:
                    msg = self._result_queue.get(timeout=60.0)
                    if msg.get("type") == "result":
                        text_result = msg.get("text", "")
                        print(f"[stt-mgr] Received result ({msg.get('info', 'zh')}): {text_result}")
                        return text_result
                    elif msg.get("type") == "error":
                        print(f"[stt-mgr] Worker reported error: {msg.get('message')}")
                        return ""
                except queue.Empty:
                    if not self.worker_process.is_alive():
                        print("[stt-mgr] Worker died during transcription.")
                    else:
                        print("[stt-mgr] timeout waiting for transcription (Queue Empty).")
                    return ""
        except Exception as e:
            print(f"[stt-mgr] IPC Error during transcribe: {e}")
            return ""

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
