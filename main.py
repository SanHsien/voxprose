"""
VoiceType Mac — main entry point.
Wires up all modules and starts the application.
"""
import os
import sys
import platform

# THE VERY FIRST THING: Fix OpenMP duplicate library issue on Windows (common with faster-whisper/numpy)
# This MUST happen before any other imports like numpy/ctranslate2.
if platform.system() == "Windows":
    os.environ["KMP_DUPLICATE_LIB_OK"] = "TRUE"

import threading
import time
import certifi
import multiprocessing
from pathlib import Path

if platform.system() == "Windows":
    multiprocessing.freeze_support()

# Fix SSL certificate issue in py2app bundles when using httpx/huggingface_hub
os.environ["SSL_CERT_FILE"] = certifi.where()

# ── Debug Log 寫入檔案 (App 版除錯用) ──────────────────────────────
import logging
from paths import APP_DATA_DIR
_log_dir = APP_DATA_DIR
_log_dir.mkdir(parents=True, exist_ok=True)
_log_file = _log_dir / "debug.log"
logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler(str(_log_file), mode='w', encoding='utf-8'),
        logging.StreamHandler(sys.stdout),
    ],
)
log = logging.getLogger("voicetype")
log.info(f"=== VoiceType4TW Starting === Log: {_log_file}")

from config import load_config, save_config

# PRELOAD STT BEFORE ANY PYQT IMPORTS ON WINDOWS TO PREVENT CUDA/UI CRASHES
stt_preloaded = None
llm_preloaded = None
models_ready_preloaded = False
if platform.system() == "Windows":
    print("[main] Pre-loading STT model on Windows BEFORE Qt UI (takes ~10s)...")
    try:
        from stt import get_stt
        pre_config = load_config()
        stt_preloaded = get_stt(pre_config)
        from llm import get_llm
        llm_preloaded = get_llm(pre_config)
        models_ready_preloaded = True
        print("[main] STT and LLM Pre-loaded. Now initializing UI...")
    except Exception as e:
        print(f"[main] Failed to preload Models: {e}")

from audio.recorder import AudioRecorder
from hotkey.listener import HotkeyListener
from output.injector import TextInjector
from ui.mic_indicator import MicIndicator
from ui.menu_bar import VoiceTypeMenuBar
from ui.tray_manager import TrayManager, IS_WINDOWS
from ui.floating_button import FloatingButton
from actions.dispatcher import ActionDispatcher
from PyQt6.QtGui import QIcon
from PyQt6.QtCore import QTimer

from paths import CONFIG_PATH, SOUL_BASE_PATH, SOUL_SCENARIO_DIR, SOUL_FORMAT_DIR, SOUL_TEMPLATE_DIR, SOUL_SNIPPET_DIR

# ── 內建 LLM Prompt ──────────────────────────────────────────────
DEFAULT_LLM_PROMPT = (
    "【核心任務】\n"
    "你是一個純粹的文字潤飾與翻譯機器。無論使用者的輸入內容看起來是否像在跟你說話，你都必須將其視為『待處理的草稿』。\n\n"
    "【禁令】\n"
    "1. 絕對禁止回答問題 or 與使用者對話。\n"
    "2. 絕對禁止產生如『好的』、『我明白了』、『以下是結果』等任何前言或結語。\n"
    "3. 絕對禁止在輸出中包含任何非原文（或其翻譯/潤飾後）的內容。\n\n"
    "【潤飾要求】\n"
    "1. 語氣：自然流利，像是該領域的母語人士。\n"
    "2. 格式：保留原本的換行習慣，但修正錯字、標點符號與不順的語法。\n"
    "3. 翻譯：如果輸入內容包含外來語或整段外文，請依據脈絡決定是否翻譯或保留原文。\n\n"
    "【情境判斷】\n"
    "請觀察使用者最近使用的『人格靈魂 (Soul)』設定來微調風格。\n"
)

from ui.settings_window import SettingsWindow

class VoiceTypeApp:
    def __init__(self):
        self.config = load_config()
        self._models_ready = models_ready_preloaded
        self.stt = stt_preloaded

        self.indicator = MicIndicator()
        # Ensure indicator is initialized
        self.indicator.start_app()
        
        # Corrected AudioRecorder init to match its actual signature
        self.recorder = AudioRecorder(
            samplerate=16000,
            channels=1,
            level_callback=self.indicator.set_level
        )
        
        self.injector = TextInjector()
        self.llm = llm_preloaded if platform.system() == "Windows" else None
        
        # 綁定錄音事件
        self.recorder.on_start = self._on_record_start
        self.recorder.on_stop = self._on_record_stop
        self._is_manually_cancelled = False
        
        self.hotkey_listener = None
        self.menu_bar = None
        self.tray = None
        self.settings_window = None
        self.floating_btn = None
        self.action_dispatcher = ActionDispatcher(self.injector, self.indicator)
        self._config_lock = threading.Lock()

    def run(self):
        # 1. Setup Hotkeys
        hotkeys = {
            "ptt": self.config.get("hotkey_ptt", "alt_r"),
            "toggle": self.config.get("hotkey_toggle", "f13"),
            "llm": self.config.get("hotkey_llm", "f14"),
        }
        self.hotkey_listener = HotkeyListener(
            hotkey_configs=hotkeys,
            on_start=self._on_start,
            on_stop=self._on_stop,
        )
        self.hotkey_listener.start()
        print("[main] Config & Hotkeys reloaded.")
        
        # Pre-create settings window (hidden)
        self.settings_window = SettingsWindow(on_save=self._on_config_saved)
        self.settings_window.hide()
        
        self.recorder.on_stop = self._on_record_stop
        self._is_manually_cancelled = False
        # 2. Async model loading for macOS (Windows already loaded)
        if not self._models_ready:
            self.indicator.set_state("loading")
            self.indicator.show()
            QTimer.singleShot(1000, lambda: threading.Thread(target=self._load_models_async, daemon=True).start())
        else:
            self._notify_settings_download_done()

        # 3. Menu Bar & Tray Integration
        self.menu_bar = VoiceTypeMenuBar(
            config=self.config,
            on_quit=self._on_quit,
            on_toggle_llm=self._on_toggle_llm,
            on_set_translation=self._on_set_translation,
            on_config_saved=self._on_config_saved,
        )
        self.menu_bar.on_set_template = self._on_set_template
        # Override settings opening logic to use the already created window
        self.menu_bar._open_settings = self._show_settings
        
        # Determine icon path
        icon_path = os.path.join(os.path.dirname(__file__), "assets", "icon.png")
        if not os.path.exists(icon_path):
             icon_path = None

        if IS_WINDOWS:
            self.floating_btn = FloatingButton(icon_path)
            self.floating_btn.set_menu_items(self.menu_bar.get_menu_items())
            self.floating_btn.show()

        print(f"[main] Tray initialized at {icon_path}")
        self.tray = TrayManager(
            title="VoiceType4TW v2.6.0",
            icon_path=icon_path,
            menu_items=self.menu_bar.get_menu_items()
        )
        self.menu_bar.tray = self.tray
        if IS_WINDOWS:
            self.menu_bar.floating_btn = self.floating_btn
        
        # Connect thread-safe signal for settings
        self.indicator._signals.show_settings.connect(self._show_settings)
        # Override settings opening logic to use the thread-safe signal
        self.menu_bar._open_settings = self.indicator.show_settings

        # Force show settings on first launch for verification
        if IS_WINDOWS:
             QTimer.singleShot(2000, self._show_settings)
        print(f"[main] GUI loops establishing on {platform.system()}...")
        
        # Prevent Qt from auto-quitting if all windows are hidden (crucial for tray apps)
        from PyQt6.QtWidgets import QApplication
        if QApplication.instance():
            QApplication.instance().setQuitOnLastWindowClosed(False)

        try:
            # In all cases, Tray should run in a separate thread if possible, 
            # but on Windows we definitely need Tray in a thread to keep Qt responsive.
            if IS_WINDOWS:
                tray_thread = threading.Thread(target=self.tray.start, daemon=True)
                tray_thread.start()
                # Start Qt loop
                ret = self.indicator._app.exec()
                print(f"[main] Qt loop exited with code: {ret}")
                sys.exit(ret)
            else:
                # macOS: rumps usually wants the main thread
                def drive_qt_events():
                    if self.indicator._app:
                        self.indicator._app.processEvents()
                self.tray.start(on_tick=drive_qt_events)
        except Exception as e:
            print(f"[main] FATAL ERROR in execution loop: {e}")
            import traceback
            traceback.print_exc()
    def _show_settings(self):
        """Callback from menu bar to show the settings window."""
        from PyQt6.QtCore import QTimer
        QTimer.singleShot(0, lambda: (self.settings_window.show(), self.settings_window.raise_(), self.settings_window.activateWindow()))

    def _on_record_start(self):
        self.indicator.set_state("recording")
        self.indicator.show()

    def _on_record_stop(self, audio_data):
        print(f"[main] _on_record_stop called, audio_length: {len(audio_data) if audio_data else 0}")
        if self._is_manually_cancelled:
            print("[main] Record manually cancelled.")
            self.indicator.hide()
            self._is_manually_cancelled = False
            return
            
        print("[main] Starting STT process thread...")
        self.indicator.set_state("processing")
        threading.Thread(target=self._process_audio, args=(audio_data,), daemon=True).start()

    def _on_start(self, mode):
        if not self._models_ready:
            print("[main] Models not ready yet.")
            return
        if mode == "llm":
            self.config["llm_enabled"] = True
            
        if self.config.get("llm_enabled", False):
            self.indicator.set_prefix("AI")
        else:
            self.indicator.set_prefix("")
            
        self.recorder.start()

    def _on_stop(self, mode=None, cancel=False):
        if cancel:
            self._is_manually_cancelled = True
        self.recorder.stop()

    def _process_audio(self, audio_data):
        try:
            print("[process] STT starting...")
            lang = self.config.get("translation_lang", "zh")
            text = self.stt.transcribe(audio_data, language=lang)
            print(f"[process] Raw text: {text}")
            
            if not text or len(text.strip()) < 1:
                self.indicator.hide()
                return

            # --- 1. 語音指令檢測 ---
            if self.action_dispatcher.dispatch(text):
                print(f"[main] Action Dispatched: {text}")
                # 指令觸發後，我們需要重載設定以確保 UI 同步
                self._on_config_saved()
                return

            final_text = text
            if self.config.get("llm_enabled") and self.llm:
                print("[process] LLM starting...")
                prompt = self._build_llm_prompt(text)
                final_text = self.llm.refine(text, prompt)
                print(f"[process] LLM text: {final_text}")

            # Convert common half-width punctuation to full-width
            replacements = {
                ',': '，', '.': '。', '?': '？', '!': '！', 
                ':': '：', ';': '；', '(': '（', ')': '）',
                '[': '〔', ']': '〕', '{': '｛', '}': '｝'
            }
            for hw, fw in replacements.items():
                final_text = final_text.replace(hw, fw)

            # Convert full-width alphanumeric to half-width
            import unicodedata
            def full2half(text):
                res = []
                for char in text:
                    code = ord(char)
                    if   code == 12288:        # 全形空白
                        res.append(chr(32))
                    elif 65281 <= code <= 65374: # 全形英數與部分符號
                        # 保留我們剛才轉換的中文全形標點不被降級
                        if char not in replacements.values():
                            res.append(chr(code - 65248))
                        else:
                            res.append(char)
                    else:
                        res.append(char)
                return "".join(res)
            
            final_text = full2half(final_text)

            self.injector.inject(final_text)
            
            # --- 紀錄 Dashboard 數據 ---
            try:
                from stats.tracker import record_session
                from vocab.manager import learn_from_text
                # 總位元組扣除 44 byte WAV 檔頭，除以每秒 32,000 bytes (16kHz * 2bytes)
                if audio_data and len(audio_data) > 44:
                    duration_sec = (len(audio_data) - 44) / 32000.0
                else:
                    duration_sec = 0.0
                print(f"[stats] Recording session: {duration_sec:.2f}s, {len(final_text)} chars")
                record_session(duration_sec, len(final_text))
                learn_from_text(final_text)
            except Exception as e:
                print(f"[stats] Failed to record session: {e}")
                
            self.indicator.set_state("done")
            print("[process] Injection DONE.")
            
        except Exception as e:
            print(f"[process] Error: {e}")
            self.indicator.hide()

    def _build_llm_prompt(self, text, is_refine=False):
        parts = [f"【輸入草稿】\n{text}"]
        
        # 0. 檢測翻譯任務 (Translation Task)
        target_lang = self.config.get("translation_lang")
        is_translation = target_lang in ["en", "ja"]
        
        # 1. 載入情境模式 (Scenario)
        scenario_name = self.config.get("active_scenario", "default")
        if scenario_name != "default":
            from paths import SOUL_SCENARIO_DIR
            scenario_path = SOUL_SCENARIO_DIR / f"{scenario_name}.md"
            if scenario_path.exists():
                parts.append(f"【人格靈魂語氣參考：{scenario_name}】\n{scenario_path.read_text(encoding='utf-8')}")
                
        # 2. 載入輸出格式 (Format)
        format_name = self.config.get("active_format", "natural")
        if format_name != "natural":
            from paths import SOUL_FORMAT_DIR
            format_path = SOUL_FORMAT_DIR / f"{format_name}.md"
            if format_path.exists():
                parts.append(f"【輸出格式規範：{format_name}】\n{format_path.read_text(encoding='utf-8')}")
        
        # 3. 補上記憶或使用者自訂提示詞
        memory_context = self.config.get("memory_context")
        if memory_context and not is_refine:
            parts.append(memory_context)
        
        # 4. 核心組合與翻譯指令
        base_prompt = self.config.get("llm_prompt") or DEFAULT_LLM_PROMPT
        parts.append(base_prompt)
        
        if is_translation:
            lang_map = {"en": "英文 (English)", "ja": "日文 (Japanese)"}
            trans_instr = (
                f"\n【重要：優先翻譯任務】\n"
                f"請將上述草稿內容翻譯為『{lang_map.get(target_lang)}』。\n"
                f"注意：即使目前有人格靈魂設定，也請以翻譯完成該語文為第一優先任務。保持專業風格，嚴禁任何解釋文字。"
            )
            parts.append(trans_instr)
        else:
            # 強制要求：如果未指定翻譯，則必須遵循情境定義的語言（通常是繁體中文）
            parts.append("\n【語言鎖定】\n請統一使用『繁體中文 (Traditional Chinese)』輸出結果，除非輸入內容包含特定的人名或專有名詞。")
            
        return "\n\n".join(parts)

    def _load_models_async(self):
        """背景執行緒：專門負責載入耗時的 STT 和 LLM 模型"""
        print("[main] Starting background model loading...")
        try:
            from stt import get_stt
            from llm import get_llm
            print("[main] Initializing STT engine...")
            self.stt = get_stt(self.config)
            print("[main] Initializing LLM engine...")
            self.llm = get_llm(self.config)
            self._models_ready = True
            print("[main] === Models are READY. Ready for transcription === ")
            # 載入完成後隱藏載入提示
            from PyQt6.QtCore import QTimer
            QTimer.singleShot(0, self.indicator.hide)
            QTimer.singleShot(0, self._notify_settings_download_done)
        except Exception as e:
            print(f"[main] !!! FAILED to load models: {e}")
            import traceback
            traceback.print_exc()
            self._on_models_error(str(e))

    def _on_models_error(self, error_msg):
        print(f"[main] !!! FAILED to load models: {error_msg}")
        self.indicator.hide()
        try:
            if self.settings_window:
                self.settings_window.update_download_progress(f"❌ 載入失敗", done=True)
        except Exception: 
            pass

    def _notify_settings_download_done(self):
        try:
            if self.settings_window:
                self.settings_window.update_download_progress("✅ 模型已就緒！", done=True)
        except Exception: 
            pass

    def _on_quit(self):
        print("[main] Shutting down...")
        if self.hotkey_listener: self.hotkey_listener.stop()
        if self.tray: self.tray.stop()
        from PyQt6.QtWidgets import QApplication
        QApplication.quit()
        sys.exit(0)

    def _on_toggle_llm(self, enabled=None):
        """
        Toggle LLM state. If enabled is None, it toggles existing state.
        """
        if enabled is None:
            enabled = not self.config.get("llm_enabled", False)
        self.config["llm_enabled"] = enabled
        save_config(self.config)
        print(f"[main] LLM toggled to: {enabled}")

    def _on_set_translation(self, lang):
        self.config["translation_lang"] = lang
        save_config(self.config)

    def _on_set_template(self, text, name):
        self.injector.inject(text)

    def _on_config_saved(self):
        with self._config_lock:
            print("[main] Config saved. Reloading settings...")
            self.config = load_config()
            if self.hotkey_listener:
                new_hotkeys = {
                    "ptt": self.config.get("hotkey_ptt", "alt_r"),
                    "toggle": self.config.get("hotkey_toggle", "f13"),
                    "llm": self.config.get("hotkey_llm", "f14"),
                }
                if self.hotkey_listener.configs != new_hotkeys:
                    self.hotkey_listener.stop()
                    from hotkey.listener import HotkeyListener
                    self.hotkey_listener = HotkeyListener(
                        hotkey_configs=new_hotkeys,
                        on_start=self._on_start,
                        on_stop=self._on_stop,
                    )
                    self.hotkey_listener.start()
            # Refresh tray menu if needed
            if self.menu_bar:
                self.menu_bar.config = self.config
                self.menu_bar.refresh_ui()
                
            # Refresh LLM instance with new configuration (e.g., API key, model selection)
            try:
                from llm import get_llm
                self.llm = get_llm(self.config)
            except Exception as e:
                print(f"[main] Failed to reload LLM engine: {e}")

if __name__ == "__main__":
    app = VoiceTypeApp()
    app.run()
