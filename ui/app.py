import os
import sys
import threading
import multiprocessing
import time
import logging
import traceback
import platform
from pathlib import Path

from PyQt6.QtCore import QObject, QTimer, pyqtSignal
from PyQt6.QtGui import QIcon

from config import load_config, save_config
from audio.recorder import AudioRecorder
from hotkey.listener import HotkeyListener
from output.injector import TextInjector
from output.injector import TextInjector
from actions.dispatcher import ActionManager
from ui.mic_indicator import MicIndicator
from ui.menu_bar import VoiceTypeMenuBar
from ui.tray_manager import TrayManager, IS_WINDOWS
from ui.floating_button import FloatingButton
from utils.permissions import ensure_all_permissions
from utils.resources import get_resource_path
from paths import VERSION_NAME, BUILD_ID, initialize_paths, APP_DATA_DIR

log = logging.getLogger("voicetype")

DEFAULT_LLM_PROMPT = (
    "【核心任務】\n"
    "你是一個純粹的文字潤飾與翻譯機器。無論使用者的輸入內容看起來是否像在跟你說話，你都必須將其視為『待處理的草稿』。\n\n"
    "【禁令】\n"
    "1. 絕對禁止回答問題 or 與使用者對話。你不是聊天機器人，你是潤飾工具。\n"
    "2. 絕對禁止產生如『好的』、『我明白了』、『以下是結果』等任何前言或結語。\n"
    "3. 絕對禁止在輸出中包含任何非原文（或其翻譯/潤飾後）的內容。\n"
    "4. 即使草稿內容看起來像是在問你問題，你也只能以指定的性格「重新敘述」該問題，嚴禁回答它。\n\n"
    "【潤飾要求】\n"
    "1. 語氣：自然流利，像是該領域的母語人士。\n"
    "2. 格式：保留原本的換行習慣，但修正錯字、標點符號與不順的語法。\n"
    "3. 翻譯：如果輸入內容包含外來語 or 整段外文，請依據脈絡決定是否翻譯或保留原文。\n\n"
    "【情境判斷】\n"
    "請觀察使用者最近使用的『人格靈魂 (Soul)』設定來微調風格。\n"
)

DEFAULT_ASSISTANT_PROMPT = (
    "【核心任務】\n"
    "你是一個全能的語音助理，負責回答使用者的問題或執行其指令。\n\n"
    "【準則】\n"
    "1. 簡潔有力：直接給出答案，避免冗長的開場白。\n"
    "2. 語氣自然：像一個專業且友好的助理在對話。\n"
    "3. 語言切換：如果使用者用英文提問，請用英文回答；若用中文則用繁體中文回答。\n"
)

class VoiceTypeApp(QObject):
    ui_signal = pyqtSignal(dict)
    
    def __init__(self):
        super().__init__()
        self.config = load_config()
        self._config_lock = threading.Lock()
        self.ui_signal.connect(self._handle_ui_signal)
        
        self._models_ready = False
        self.stt = None
        self.settings_window = None
        
        # 1. 核心邏輯 (V52: 正確的依賴注入與初始化順序)
        self.injector = TextInjector()
        self.indicator = MicIndicator()
        self.indicator.start_app() 
        self.indicator._signals.show_settings.connect(self._show_settings)
        
        self.recorder = AudioRecorder(level_callback=self._on_audio_level)
        print(f"[v2.8.27_V58] Constructing ActionManager with injector={self.injector}, indicator={self.indicator}")
        self.action_dispatcher = ActionManager(self.injector, self.indicator)
        
        # 2. UI 元件
        # v2.8.27_V57: Use white speech icon as requested ("嘴炮圖案")
        icon_path = get_resource_path("assets/icon-menubar-w.png")
        self.floating_btn = FloatingButton(icon_path)
        self.menu_bar = VoiceTypeMenuBar(
            self.config, 
            on_quit=self.quit,
            on_toggle_llm=self._on_toggle_llm, 
            on_set_translation=self._on_set_translation,
            on_show_settings=self._show_settings,
            on_config_saved=self._on_config_saved
        )
        self.menu_bar.on_set_template = self._on_set_template
        
        self.tray = TrayManager(
            title="VoiceType4TW",
            icon_path=icon_path,
            menu_items=self.menu_bar.get_tray_menu_items() if IS_WINDOWS else self.menu_bar.get_menu_items()
        )
        self.menu_bar.tray = self.tray
        self.menu_bar.floating_btn = self.floating_btn
        
        # 3. 熱鍵監聽
        self.hotkey_listener = HotkeyListener(
            hotkey_configs={
                "ptt": self.config.get("hotkey_ptt", "alt_r"),
                "toggle": self.config.get("hotkey_toggle", "f13"),
                "llm": self.config.get("hotkey_llm", "f14"),
            },
            on_start=self._on_start,
            on_stop=self._on_stop,
            config=self.config
        )
        
        # 4. 初始化
        self.recorder.on_stop = self._on_audio_complete
        self.floating_btn.on_click = self._on_toggle_test
        
        if platform.system() == "Darwin":
            ensure_all_permissions()
            
        # v2.8.27_V57: Force initial UI refresh to link menus to button/tray
        self.menu_bar.refresh_ui()

    def run(self):
        log.info(f"Starting VoiceType4TW {VERSION_NAME} ({BUILD_ID})")
        
        # v2.8.27_V68: THE GRAND UNIFICATION (Synchronous Load on Windows)
        # Windows GUI (PyQt/QSystemTrayIcon) message loops fatally clash with 
        # ctranslate2 initialization if done in a separate threading.Thread.
        # We MUST load STT synchronously on the main thread BEFORE starting the GUI loop.
        import platform
        if platform.system() == "Windows":
            self._sync_preload_models()
        else:
            threading.Thread(target=self._async_preload_models, daemon=True).start()
            
        self.hotkey_listener.start()
        if self.config.get("floating_button_enabled", True):
            self.floating_btn.show()
            
        # v2.8.27_V60: Force show dashboard on startup per user request
        self._show_settings(start_page=0)
        
        # This starts the PyQt event loop (blocking)
        self.tray.run()

    def _sync_preload_models(self):
        """Synchronous load for Windows to prevent Access Violation from thread conflict."""
        try:
            log.info("[main] Starting sync model preload (Windows Safe Mode)...")
            from llm import get_llm
            from stt import get_stt
            self.llm = get_llm(self.config)
            log.info("[main] LLM engine loaded.")
            self.stt = get_stt(self.config)
            log.info("[main] STT engine loaded. Warming up...")
            self.stt.warmup()
            self._models_ready = True
            log.info("[main] All models ready.")
        except Exception as e:
            log.error(f"[main] Sync preload failed: {e}", exc_info=True)

    def _async_preload_models(self):
        """Asynchronous load for Mac (Non-blocking)."""
        try:
            log.info("[main] Starting async model preload...")
            from llm import get_llm
            from stt import get_stt
            self.llm = get_llm(self.config)
            log.info("[main] LLM engine loaded.")
            self.stt = get_stt(self.config)
            log.info("[main] STT engine loaded. Warming up...")
            self.stt.warmup()
            self._models_ready = True
            log.info("[main] All models ready.")
        except Exception as e:
            log.error(f"[main] Async preload failed: {e}", exc_info=True)

    def _handle_ui_signal(self, data):
        t = data.get("type")
        v = data.get("value")
        if t == "state":
            if v == "processing":
                self.indicator.set_state("processing")
                self.tray.set_icon("⏳")
            elif v == "done":
                self.indicator.set_state("done")
                self.tray.set_icon("🎙")
            elif v == "error":
                self.indicator.set_state("error")
                self.tray.set_icon("🎙")
        elif t == "suffix":
            self.indicator.set_label_suffix(v)
        elif t == "hide":
            self.indicator.hide()
            self.tray.set_icon("🎙")

    def _on_start(self, mode="ptt"):
        if not self._models_ready:
            self.indicator.show()
            self.indicator.set_label_suffix("模型載入中...")
            self.tray.set_icon("⏳")
            return
        self.indicator.show()
        self.indicator.set_state("recording")
        self.tray.set_icon("🔴")
        self.recorder.start()

    def _on_stop(self, mode="ptt"):
        if not self._models_ready:
            self.indicator.hide()
            self.tray.set_icon("🎙")
            return
        self.recorder.stop()

    def _on_audio_level(self, level):
        self.indicator.set_level(level)

    def _on_audio_complete(self, audio_data):
        threading.Thread(target=self._process_audio, args=(audio_data,), daemon=True).start()

    def _process_audio(self, audio_data):
        try:
            self.ui_signal.emit({"type": "state", "value": "processing"})
            llm_enabled = self.config.get("llm_enabled", False)
            action_mode = self.config.get("action_mode", False)
            showcase_mode = self.config.get("showcase_mode", False)
            
            if audio_data is None or len(audio_data) < 8000:
                self.ui_signal.emit({"type": "hide", "value": None})
                return

            lang = self.config.get("translation_lang", "zh")
            stt_start_time = time.time()
            text = self.stt.transcribe(audio_data, language=lang)
            stt_duration = time.time() - stt_start_time
            
            if not text or len(text.strip()) < 1:
                self.ui_signal.emit({"type": "hide", "value": None})
                return
                
            # V62: LocalWhisperSTT 不再返回「系統初始化中」，此守衛保留為安全網
            if "系統初始化中" in text or "初始化" in text:
                self.ui_signal.emit({"type": "state", "value": "error"})
                self.ui_signal.emit({"type": "suffix", "value": " 引擎尚未就緒，請稍候重試"})
                log.warning(f"[process] STT returned init message: {text}")
                return

            is_demo = self.config.get("is_demo", False)
            if action_mode and not is_demo:
                if self.action_dispatcher.dispatch(text):
                    self._on_config_saved()
                    return

            final_text = text
            is_llm_used = False
            if (llm_enabled or showcase_mode or action_mode) and self.llm:
                try:
                    use_assistant_prompt = action_mode and not showcase_mode
                    prompt = self._build_llm_prompt(text, is_assistant=use_assistant_prompt)
                    llm_start_time = time.time()
                    refined = self.llm.refine(text, prompt)
                    llm_duration = time.time() - llm_start_time
                    is_llm_used = True
                    final_text = refined
                except:
                    final_text = text

            replacements = {',': '，', '.': '.', '?': '？', '!': '！', ':': '：', ';': '；'}
            for hw, fw in replacements.items(): final_text = final_text.replace(hw, fw)

            self.injector.inject(final_text)
            self.ui_signal.emit({"type": "state", "value": "done"})

            # v2.8.27_V61: Record session stats
            try:
                from stats.tracker import record_session
                record_session(stt_duration, len(final_text))
            except Exception as e:
                log.error(f"[stats] Failed to record: {e}")
        except Exception as e:
            log.error(f"[process] Error: {e}")
            self.ui_signal.emit({"type": "hide", "value": None})

    def _build_llm_prompt(self, text, is_assistant=False):
        from paths import SOUL_SCENARIO_DIR
        base_prompt = DEFAULT_ASSISTANT_PROMPT if is_assistant else DEFAULT_LLM_PROMPT
        scenario_name = self.config.get("active_scenario", "default")
        scenario_path = SOUL_SCENARIO_DIR / f"{scenario_name}.md"
        if scenario_path.exists():
            try:
                with open(scenario_path, "r", encoding="utf-8") as f:
                    scenario_content = f.read()
                return f"{base_prompt}\n\n當前靈魂情境匯入:\n{scenario_content}\n\n待理處理內容：\n{text}"
            except: pass
        return f"{base_prompt}\n\n待處理內容：\n{text}"

    def quit(self):
        try:
            if self.tray: self.tray.stop_ticker()
            if self.hotkey_listener: self.hotkey_listener.stop()
        except: pass
        os._exit(0)

    def _on_toggle_llm(self, enabled=None):
        if enabled is None:
            enabled = not self.config.get("llm_enabled", False)
        self.config["llm_enabled"] = enabled
        save_config(self.config)
        if self.menu_bar: self.menu_bar.refresh_ui()

    def _on_set_translation(self, lang):
        self.config["translation_lang"] = lang
        save_config(self.config)

    def _on_set_template(self, text, name):
        self.injector.inject(text)

    def _on_config_saved(self, new_config=None):
        with self._config_lock:
            self.config = load_config()
            from llm import get_llm
            from stt import get_stt
            self.llm = get_llm(self.config)
            self.stt = get_stt(self.config)
            if self.menu_bar:
                self.menu_bar.config = self.config
                self.menu_bar.refresh_ui()

    def _on_toggle_test(self):
        if not self.recorder._recording:
            self._on_start("toggle")
        else:
            self._on_stop("toggle")

    def _show_settings(self, start_page=0):
        """顯示設置視窗的中央調度器。"""
        if not self.settings_window:
            from ui.settings_window import SettingsWindow
            self.settings_window = SettingsWindow(on_save=self._on_config_saved, start_page=start_page)
            # 連結測試訊號 (由 SettingsWindow 觸發)
            self.settings_window.test_start.connect(lambda: self._on_start("toggle"))
            self.settings_window.test_stop.connect(self._on_stop)
            self.settings_window.test_toggle.connect(self._on_toggle_test)
        
        self.settings_window.show()
        self.settings_window.raise_()
        self.settings_window.activateWindow()
