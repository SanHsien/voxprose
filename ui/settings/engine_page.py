"""STT/LLM 辨識引擎頁 mixin — split out of ui/settings_window.py (REVIEW.md #7).

Verbatim relocation of `_create_stt_llm_page` and the Whisper-model /
microphone-device helper methods it depends on. No logic changes.
"""
import logging

from PyQt6.QtWidgets import (
    QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QComboBox, QCheckBox, QScrollArea,
    QWidget, QSlider,
)
from PyQt6.QtCore import Qt, QTimer

from ui.settings.common import STT_ENGINES, LLM_ENGINES, LLM_MODES

log = logging.getLogger("voicetype.ui")


class EnginePageMixin:
    def _create_stt_llm_page(self):
        page = QScrollArea()
        page.setWidgetResizable(True)
        container = QWidget()
        layout = QVBoxLayout(container)
        layout.setSpacing(25)

        layout.addWidget(self._page_section_header("🎙 語音辨識配置"))
        self.stt_engine = self._add_grid_row(layout, "核心引擎", QComboBox())
        engine_meta = {
            "local_whisper": "Local Whisper (RTX顯卡加速, 也支援 CPU/GPU)",
            "groq":          "Groq Whisper (神級雲端超極速)",
            "gemini":        "Gemini (雲端 API)",
            "openrouter":    "OpenRouter (雲端 API)",
        }
        for eng in STT_ENGINES:
            self.stt_engine.addItem(engine_meta.get(eng, eng), eng)

        self.whisper_model = self._add_grid_row(layout, "Whisper 規格", QComboBox())
        self._populate_whisper_models()

        self.groq_key = self._add_grid_row(layout, "Groq API Key (選填)", QLineEdit())
        self.groq_key.setEchoMode(QLineEdit.EchoMode.Password)

        self.language = self._add_grid_row(layout, "優先辨識語言", QComboBox())
        lang_meta = {
            "zh": "繁體中文",
            "en": "英文",
            "ja": "日文",
            "ko": "韓文",
            "yue": "粵語",
            "auto": "自動偵測"
        }
        for code, name in lang_meta.items():
            self.language.addItem(f"{name} ({code})", code)

        # Mac 主線 v2.9.7（7-1/7-2/7-3）移植：麥克風裝置選擇 + 增益 + AGC
        layout.addWidget(self._page_section_header("🎚 麥克風選擇與增益"))

        self.mic_device_combo = self._add_grid_row(layout, "輸入裝置", QComboBox())
        self._last_mic_device_names = []
        self._populate_mic_devices()

        # 每 2 秒偵測一次裝置清單是否變動（插拔耳機/USB 麥克風），與 Mac 版一致
        self._mic_poll_timer = QTimer(self)
        self._mic_poll_timer.timeout.connect(self._check_mic_devices_changed)
        self._mic_poll_timer.start(2000)

        gain_row = QHBoxLayout()
        gain_lbl = QLabel("增益 / AGC")
        gain_lbl.setFixedWidth(160)
        self.mic_gain_slider = QSlider(Qt.Orientation.Horizontal)
        self.mic_gain_slider.setRange(50, 300)  # 50=×0.5, 100=×1.0（不變）, 300=×3.0
        self.mic_gain_slider.setValue(self.config.get("mic_gain", 100))
        _gain_init = self.config.get("mic_gain", 100)
        self.mic_gain_val_lbl = QLabel(f"×{_gain_init / 100:.1f}")
        self.mic_gain_val_lbl.setFixedWidth(42)
        self.mic_gain_slider.valueChanged.connect(
            lambda v: self.mic_gain_val_lbl.setText(f"×{v / 100:.1f}")
        )
        self.mic_gain_auto_cb = QCheckBox("自動 (AGC)")
        self.mic_gain_auto_cb.setChecked(self.config.get("mic_gain_auto", True))
        gain_row.addWidget(gain_lbl)
        gain_row.addWidget(self.mic_gain_slider, stretch=1)
        gain_row.addWidget(self.mic_gain_val_lbl)
        gain_row.addWidget(self.mic_gain_auto_cb)
        layout.addLayout(gain_row)

        layout.addWidget(self._page_section_header("🤖 大語言模型潤飾 (LLM) 配置"))
        self.llm_enabled = QCheckBox("啟用高階智慧潤飾與翻譯")
        layout.addWidget(self.llm_enabled)

        self.llm_engine = self._add_grid_row(layout, "模型提供者", QComboBox())
        self.llm_engine.addItems(LLM_ENGINES)

        self.llm_mode = self._add_grid_row(layout, "內容注入模式", QComboBox())
        self.llm_mode.addItems(LLM_MODES)

        # API Keys
        self.openai_key = self._add_grid_row(layout, "OpenAI API Key", QLineEdit())
        self.openai_key.setEchoMode(QLineEdit.EchoMode.Password)

        self.anthropic_key = self._add_grid_row(layout, "Anthropic (Claude) Key", QLineEdit())
        self.anthropic_key.setEchoMode(QLineEdit.EchoMode.Password)

        self.gemini_key = self._add_grid_row(layout, "Gemini API Key", QLineEdit())
        self.gemini_key.setEchoMode(QLineEdit.EchoMode.Password)

        self.openrouter_key = self._add_grid_row(layout, "OpenRouter API Key", QLineEdit())
        self.openrouter_key.setEchoMode(QLineEdit.EchoMode.Password)

        self.qwen_key = self._add_grid_row(layout, "通義千問 (Qwen) Key", QLineEdit())
        self.qwen_key.setEchoMode(QLineEdit.EchoMode.Password)

        self.deepseek_key = self._add_grid_row(layout, "DeepSeek API Key", QLineEdit())
        self.deepseek_key.setEchoMode(QLineEdit.EchoMode.Password)

        layout.addWidget(self._page_section_header("🪄 AI 魔術指令"))
        self.magic_trigger = self._add_grid_row(layout, "啟動咒語 (例如: 嘿 助理)", QLineEdit())
        self.magic_trigger.setPlaceholderText("預設為: 嘿 VoiceType")

        container.setLayout(layout)
        page.setWidget(container)
        return page

    def _populate_whisper_models(self):
        """依據模型大小、本機狀態與推薦程度，格式化顯示 COMBOBOX 選單內容"""
        self.whisper_model.clear()
        meta = {
            "tiny":   ("75MB",  "極速辨識"),
            "base":   ("145MB", "快速辨識"),
            "small":  ("500MB", "輕量，速度快"),
            "medium": ("1.5GB", "均衡型，推薦首選"),
            "large":  ("3.0GB", "極限型，最精準"),
        }
        # 依序加入 Tiny 到 Large
        for m in ["tiny", "base", "small", "medium", "large"]:
            if m in meta:
                size, desc = meta[m]
                is_ready = self._is_model_present(m)
                status = " (已就緒)" if is_ready else " (未下載)"
                label = f"{m.upper():<8} [{size}] - {desc}{status}"
                self.whisper_model.addItem(label, m) # m 為內部代號，例如 "medium"

    def _check_mic_devices_changed(self):
        """2 秒輪詢：裝置清單（名稱序列）若變動就重新整理下拉選單（插拔偵測）。"""
        try:
            import sounddevice as sd
            devices = sd.query_devices()
            names = [d["name"] for d in devices if d.get("max_input_channels", 0) > 0]
        except Exception as e:
            # 這裡是 2 秒輪詢的插拔偵測，用 debug 而非 warning 避免持續噪音。
            log.debug(f"[settings] Mic device poll failed: {e}")
            names = []
        if names != self._last_mic_device_names:
            self._populate_mic_devices()

    def _populate_mic_devices(self):
        """列舉 sounddevice 輸入裝置，保留目前選取項（或 config 裡的值）。"""
        prev_selection = self.mic_device_combo.currentData() if self.mic_device_combo.count() else None
        self.mic_device_combo.clear()
        self.mic_device_combo.addItem("系統預設 (System Default)", None)
        names = []
        try:
            import sounddevice as sd
            devices = sd.query_devices()
            for i, dev in enumerate(devices):
                if dev.get("max_input_channels", 0) > 0:
                    names.append(dev["name"])
                    self.mic_device_combo.addItem(f"{dev['name']}  (#{i})", i)
        except Exception as e:
            log.warning(f"[settings] 無法列舉麥克風裝置: {e}")
        self._last_mic_device_names = names

        restore = prev_selection if prev_selection is not None else self.config.get("mic_device")
        if restore is not None:
            idx = self.mic_device_combo.findData(restore)
            if idx >= 0:
                self.mic_device_combo.setCurrentIndex(idx)
            # 裝置不存在了（拔線）：保持索引 0（系統預設），呼應 recorder 端的 fallback
