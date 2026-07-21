"""
Modern VoiceType Settings Window using PyQt6.
Features tabs for General, STT/LLM, Vocab/Memory, and Stats.

2026-07-21（REVIEW.md #7 god-file 拆分）：本檔案原本是 ~2164 行的單一大檔，內含
七個分頁的建構邏輯與輔助方法。現在拆分為 `ui/settings/` 子套件，每個分頁一個
mixin 檔（`dashboard_page.py`／`engine_page.py`／`soul_page.py`／
`vocab_mem_page.py`／`sync_page.py`／`stats_page.py`／`general_page.py`），
共用元件與常數集中在 `ui/settings/common.py`。本檔保留為薄殼：用多重繼承把
所有分頁 mixin 混入 `SettingsWindow` 類別本身（`self.xxx` 呼叫方式完全不變，
只是方法定義搬到別的檔案），並組裝視窗骨架（sidebar、footer、頁面堆疊）。

對外只有一條契約：`from ui.settings_window import SettingsWindow`。拆分細節與
「原方法 → 新檔」對應表見 docs/DECISIONS.md。
"""
import sys
import os
import platform
from pathlib import Path
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QStackedWidget, QLabel, QPushButton, QMessageBox,
)
from PyQt6.QtCore import Qt, pyqtSignal, QTimer
from PyQt6.QtGui import QFont

import logging
from config import load_config, save_config
from paths import SOUL_BASE_PATH, SOUL_SCENARIO_DIR, SOUL_FORMAT_DIR, SOUL_TEMPLATE_DIR, BUILD_ID

from ui.settings.common import CommonPageMixin, SidebarButton, SNSButton
from ui.settings.dashboard_page import DashboardPageMixin
from ui.settings.engine_page import EnginePageMixin
from ui.settings.soul_page import SoulPageMixin
from ui.settings.vocab_mem_page import VocabMemPageMixin
from ui.settings.sync_page import SyncPageMixin
from ui.settings.stats_page import StatsPageMixin
from ui.settings.general_page import GeneralPageMixin

log = logging.getLogger("voicetype.ui")


class SettingsWindow(
    QMainWindow,
    CommonPageMixin,
    DashboardPageMixin,
    EnginePageMixin,
    SoulPageMixin,
    VocabMemPageMixin,
    SyncPageMixin,
    StatsPageMixin,
    GeneralPageMixin,
):
    test_start = pyqtSignal()
    test_stop = pyqtSignal()
    test_toggle = pyqtSignal()
    test_llm = pyqtSignal()   # v2.8.15: LLM Mode hotkey test

    def __init__(self, on_save=None, start_page=0):
        super().__init__()
        self.config = load_config()
        self.on_save = on_save
        self._is_dark = True # Pro mode is dark by default

        # Windows: Ensure window is popped up and focused (but not always on top)
        if platform.system() == "Windows":
             # v2.8.27_V87: Explicitly set window icon via branding utility
             from utils.branding import apply_branding
             apply_branding(self)
             pass

        self._setup_ui()
        self._load_data()

        # 根據語言動態設定視窗標題
        from paths import VERSION_NAME
        lang = self.config.get("language", "zh")
        if "zh" in lang:
            win_font = "Microsoft JhengHei" if platform.system() == "Windows" else "Taipei Sans TC Beta"
            self.setFont(QFont(win_font))
            self.setWindowTitle(f"聲成文 {VERSION_NAME}")
        else:
            self.setWindowTitle(f"VoxProse {VERSION_NAME}")

        # 設定啟動頁面
        if 0 <= start_page < len(self.sidebar_buttons):
            # 延遲一點點執行，避免在 UI 還沒完全掛載時觸發 visibility 切換
            QTimer.singleShot(10, lambda: self._on_sidebar_changed(start_page))

    def _setup_ui(self):
        from paths import VERSION_NAME
        self.setWindowTitle(f"VoxProse {VERSION_NAME}")
        # 最小寬度需容納側欄 240px + 三張卡片不被裁切
        self.setMinimumSize(1080, 720)
        self.resize(1200, 840)

        # Ensure it pops up correctly on Windows
        self.raise_()
        self.activateWindow()

        # Premium CSS
        win_font = "Microsoft JhengHei" if platform.system() == "Windows" else "PingFang TC"
        from utils.resources import get_resource_path
        check_icon = get_resource_path("assets/check.png").replace("\\", "/")
        self.setStyleSheet("""
            QMainWindow {
                background-color: #0f1115;
            }
            QWidget#sidebar_container {
                background-color: #16191f;
                border-right: 1px solid #252a33;
            }
            QStackedWidget {
                background-color: #0f1115;
            }
            QListWidget#sidebar {
                background: transparent;
                border: none;
                outline: none;
                padding: 15px;
            }
            QListWidget#sidebar::item {
                padding: 20px;
                color: #8a8d91;
                border-radius: 12px;
                margin-bottom: 10px;
            }
            QListWidget#sidebar::item:selected {
                background-color: #252a33;
                color: #7c4dff;
                font-weight: bold;
            }
            QLabel {
                color: #e2e4e7;
                font-family: '""" + win_font + """';
            }
            QLineEdit, QComboBox, QTextEdit, QListWidget, QTreeWidget {
                font-family: '""" + win_font + """';
                background-color: #1c1f26;
                border: 1px solid #2d333d;
                border-radius: 8px;
                color: #e2e4e7;
                padding: 8px;
                selection-background-color: #3d4452;
            }
            /* 強制選單彈出框也是深色 */
            QAbstractItemView {
                background-color: #1c1f26;
                color: #e2e4e7;
                border: 1px solid #2d333d;
                selection-background-color: #3d4452;
                outline: none;
            }
            QTreeWidget::item { padding: 4px; }
            QHeaderView::section {
                background-color: #1c1f26;
                color: #8a8d91;
                padding: 6px;
                border: none;
                font-weight: bold;
            }
            QPushButton {
                background-color: #7c4dff;
                color: white;
                border-radius: 8px;
                padding: 10px 20px;
                font-weight: bold;
                border: none;
            }
            QPushButton:hover { background-color: #9575cd; }
            QPushButton#secondary {
                background-color: #2d333d;
                color: #e2e4e7;
            }
            QPushButton#danger {
                background-color: transparent;
                border: 1px solid #ff5252;
                color: #ff5252;
            }
            QPushButton#danger:hover {
                background-color: #ff5252;
                color: white;
            }
            QScrollArea { border: none; background: transparent; }
            QScrollBar:vertical {
                border: none;
                background: transparent;
                width: 6px;
            }
            QScrollBar::handle:vertical {
                background: #3d3d4d;
                border-radius: 3px;
                min-height: 20px;
            }
            QCheckBox { color: #e2e4e7; spacing: 10px; }
            /* 勾選框：深色背景上必須有明顯外框，否則與底色溶在一起 */
            QCheckBox::indicator {
                width: 18px; height: 18px;
                border: 2px solid #5a6270;
                border-radius: 4px;
                background-color: #1c1f26;
            }
            QCheckBox::indicator:hover { border-color: #7c4dff; }
            QCheckBox::indicator:checked {
                background-color: #7c4dff;
                border-color: #7c4dff;
                image: url(\"""" + check_icon + """\");
            }
        """)

        central = QWidget()
        self.setCentralWidget(central)
        main_layout = QHBoxLayout(central)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # Sidebar
        sidebar_container = QWidget()
        sidebar_container.setObjectName("sidebar_container")
        sidebar_container.setFixedWidth(240)
        sidebar_layout = QVBoxLayout(sidebar_container)
        sidebar_layout.setContentsMargins(0, 0, 0, 0)

        logo_container = QWidget()
        logo_vbox = QVBoxLayout(logo_container)
        logo_vbox.setContentsMargins(0, 50, 0, 0) # Apply 50px Margin Top
        logo_vbox.setSpacing(0)

        lbl_en = QLabel("VoxProse")
        lbl_en.setStyleSheet("font-family: 'Myriad Pro'; font-weight: bold; font-size: 28px; color: white;")
        lbl_en.setAlignment(Qt.AlignmentFlag.AlignCenter)

        from paths import VERSION_NAME
        os_ver = f"Windows Version" if platform.system() == "Windows" else f"macOS Version "
        lbl_os = QLabel(os_ver)
        lbl_os.setStyleSheet("font-family: 'Myriad Pro'; font-style: italic; font-size: 12px; color: #8a8d91;")
        lbl_os.setAlignment(Qt.AlignmentFlag.AlignCenter)

        logo_vbox.addWidget(lbl_en)
        logo_vbox.addWidget(lbl_os)
        sidebar_layout.addWidget(logo_container)

        # Menu List - Use Layout instead of QListWidget for perfect visibility
        self.menu_group = QWidget()
        self.menu_layout = QVBoxLayout(self.menu_group)
        self.menu_layout.setContentsMargins(10, 20, 10, 0)
        self.menu_layout.setSpacing(5)

        self.sidebar_buttons = []
        menus = [
            ("🏠", "Dashboard"),
            ("🎙", "辨識 & AI"),
            ("✨", "靈魂設定"),
            ("📚", "詞彙 & 記憶"),
            ("☁️", "雲端同步"),
            ("📊", "數據統計"),
            ("⚙️", "系統設定")
        ]

        for i, (icon, label) in enumerate(menus):
            btn = SidebarButton(icon, label, i, self._on_sidebar_changed)
            self.menu_layout.addWidget(btn)
            self.sidebar_buttons.append(btn)

        self.sidebar_buttons[0].setChecked(True) # Default
        sidebar_layout.addWidget(self.menu_group)

        sidebar_layout.addStretch()

        # Credits and SNS at Bottom
        from paths import VERSION_NAME
        credit_box = QLabel(f"{VERSION_NAME}\n\n主要開發者：吉米丘, CC58TW\n協助開發者：Claude Code")
        credit_box.setStyleSheet("color: #555; font-size: 10px; margin-left: 25px; line-height: 1.2;")
        sidebar_layout.addWidget(credit_box)

        sns_container = QWidget()
        sns_layout = QHBoxLayout(sns_container)
        sns_layout.setContentsMargins(25, 5, 25, 20) # Left align with credit box
        sns_layout.setAlignment(Qt.AlignmentFlag.AlignLeft)
        sns_layout.setSpacing(10)

        _assets_dir = str(Path(__file__).parent.parent / "assets")
        sns_links = [
            (os.path.join(_assets_dir, "sns-youtube.png"), "https://youtube.com/@Jimmy4TW"),
            (os.path.join(_assets_dir, "sns-facebook.png"), "https://www.facebook.com/acykjcms"),
            (os.path.join(_assets_dir, "sns-instagram.png"), "https://www.instagram.com/jimmy4tw/"),
            (os.path.join(_assets_dir, "sns-tiktok.png"), "https://www.tiktok.com/@jimmy4tw"),
            (os.path.join(_assets_dir, "sns-threads.png"), "https://www.threads.net/@jimmy4tw"),
            (os.path.join(_assets_dir, "sns-4tw.png"), "https://Jimmy4.TW/")
        ]

        for icon_path, url in sns_links:
            btn = SNSButton(icon_path, url)
            sns_layout.addWidget(btn)

        sidebar_layout.addWidget(sns_container)

        main_layout.addWidget(sidebar_container)

        # Content Area
        content_container = QWidget()
        self.content_layout = QVBoxLayout(content_container)
        self.content_layout.setContentsMargins(32, 40, 32, 28)

        self.stack = QStackedWidget()
        self.content_layout.addWidget(self.stack)

        # Pages
        self.stack.addWidget(self._create_dashboard_page())
        self.stack.addWidget(self._create_stt_llm_page())
        self.stack.addWidget(self._create_soul_page())
        self.stack.addWidget(self._create_vocab_mem_page())
        self.stack.addWidget(self._create_sync_page())
        self.stack.addWidget(self._create_stats_page())
        self.stack.addWidget(self._create_general_page())

        # Footer Actions (Grouped for visibility control)
        self.footer_widget = QWidget()
        footer = QHBoxLayout(self.footer_widget)
        footer.setContentsMargins(0, 20, 0, 0)
        self.btn_save = QPushButton("儲存設定")
        self.btn_save.clicked.connect(self._save_action)
        self.btn_cancel = QPushButton("放棄設定")
        self.btn_cancel.setObjectName("secondary")
        self.btn_cancel.clicked.connect(self.close)

        footer.addStretch()
        footer.addWidget(self.btn_cancel)
        footer.addWidget(self.btn_save)
        self.content_layout.addWidget(self.footer_widget)

        # Initial footer visibility
        self._on_sidebar_changed(0)

        main_layout.addWidget(content_container)

    def _on_sidebar_changed(self, idx):
        # Update button states
        for i, btn in enumerate(self.sidebar_buttons):
            btn.setChecked(i == idx)

        self.stack.setCurrentIndex(idx)
        # Dashboard (0) and Stats (5) hide save buttons
        self.footer_widget.setVisible(idx not in [0, 5])

    # --- Data and Logic ---
    def _load_data(self):
        if SOUL_BASE_PATH.exists():
            raw_bytes = SOUL_BASE_PATH.read_bytes()
            content = ""
            for enc in ["utf-8-sig", "utf-8", "big5", "utf-16", "gbk"]:
                try:
                    content = raw_bytes.decode(enc)
                    break
                except UnicodeDecodeError:
                    continue
            if not content:
                # Fallback directly to replace if all fail
                content = raw_bytes.decode("utf-8", errors="replace")
            self.soul_prompt.setPlainText(content)

        # 1. 語音辨識
        stt_val = self.config.get("stt_engine", "local_whisper")
        stt_idx = self.stt_engine.findData(stt_val)
        if stt_idx >= 0: self.stt_engine.setCurrentIndex(stt_idx)
        else: self.stt_engine.setCurrentText(stt_val)

        m_val = self.config.get("whisper_model", "medium")
        m_idx = self.whisper_model.findData(m_val)
        if m_idx >= 0: self.whisper_model.setCurrentIndex(m_idx)
        else: self.whisper_model.setCurrentText(m_val)

        self.groq_key.setText(self.config.get("groq_api_key", ""))

        # 麥克風裝置 / 增益 / AGC
        self._populate_mic_devices()
        self.mic_gain_slider.setValue(self.config.get("mic_gain", 100))
        self.mic_gain_auto_cb.setChecked(self.config.get("mic_gain_auto", True))

        # 2. 語言與 AI 配置
        lang_val = self.config.get("language", "zh")
        lang_idx = self.language.findData(lang_val)
        if lang_idx >= 0: self.language.setCurrentIndex(lang_idx)
        else: self.language.setCurrentText(lang_val)

        self.llm_enabled.setChecked(self.config.get("llm_enabled", False))
        self.llm_engine.setCurrentText(self.config.get("llm_engine", "ollama"))
        self.llm_mode.setCurrentText(self.config.get("llm_mode", "replace"))

        # API Keys
        self.openai_key.setText(self.config.get("openai_api_key", ""))
        self.anthropic_key.setText(self.config.get("anthropic_api_key", ""))
        self.gemini_key.setText(self.config.get("gemini_api_key", ""))
        self.openrouter_key.setText(self.config.get("openrouter_api_key", ""))
        self.qwen_key.setText(self.config.get("qwen_api_key", ""))
        self.deepseek_key.setText(self.config.get("deepseek_api_key", ""))

        self.magic_trigger.setText(self.config.get("magic_trigger", "嘿 VoiceType"))

        # 3. 系統設定 (Critical: fix UI overwriting disk with stale state)
        self.btn_ptt.key_str = self.config.get("hotkey_ptt", "alt_r")
        self.btn_toggle.key_str = self.config.get("hotkey_toggle", "f13")
        self.btn_llm.key_str = self.config.get("hotkey_llm", "f14")

        self.auto_paste.setChecked(self.config.get("auto_paste", True))
        self.show_floating_button.setChecked(self.config.get("show_floating_button", True))
        self.completion_sound.setChecked(self.config.get("completion_sound", True))
        self.debug_mode.setChecked(self.config.get("debug_mode", False))
        self.debug_demo_mode.setChecked(self.config.get("is_demo", False))
        self.output_prefix.setChecked(self.config.get("output_prefix", False))
        self.separate_keystrike_log.setChecked(self.config.get("separate_keystrike_log", False))
        self.showcase_mode.setChecked(self.config.get("showcase_mode", False))
        self.memory_inject_cb.setChecked(self.config.get("memory_enabled", False))

        # Refreshes
        self._refresh_vocab()
        self._refresh_learned_vocab()
        self._refresh_memory()
        self._refresh_stats()
        self._update_dashboard_status()

    def refresh_config(self, new_config):
        """外部呼叫：強制重載設定到 UI (防止 stale data)"""
        self.config = new_config.copy()
        self._load_data()

    def _save_action(self):
        self.config["stt_engine"] = self.stt_engine.currentData() or self.stt_engine.currentText()
        # 使用 currentData 取得內部代號如 "medium" 而非顯示文字
        self.config["whisper_model"] = self.whisper_model.currentData() or self.whisper_model.currentText()
        self.config["groq_api_key"] = self.groq_key.text().strip()
        self.config["mic_device"] = self.mic_device_combo.currentData()
        self.config["mic_gain"] = self.mic_gain_slider.value()
        self.config["mic_gain_auto"] = self.mic_gain_auto_cb.isChecked()
        self.config["language"] = self.language.currentData() or self.language.currentText()
        self.config["llm_enabled"] = self.llm_enabled.isChecked()
        self.config["llm_engine"] = self.llm_engine.currentText()
        self.config["llm_mode"] = self.llm_mode.currentText()
        self.config["openai_api_key"] = self.openai_key.text().strip()
        self.config["anthropic_api_key"] = self.anthropic_key.text().strip()
        self.config["gemini_api_key"] = self.gemini_key.text().strip()
        self.config["openrouter_api_key"] = self.openrouter_key.text().strip()
        self.config["qwen_api_key"] = self.qwen_key.text().strip()
        self.config["deepseek_api_key"] = self.deepseek_key.text().strip()
        self.config["magic_trigger"] = self.magic_trigger.text().strip() or "嘿 VoiceType"
        self.config["hotkey_ptt"] = self.btn_ptt.key_str
        self.config["hotkey_toggle"] = self.btn_toggle.key_str
        self.config["hotkey_llm"] = self.btn_llm.key_str

        log.info(f"[save] Writing UI hotkeys to config: PTT={self.config['hotkey_ptt']}, Toggle={self.config['hotkey_toggle']}, LLM={self.config['hotkey_llm']}")
        self.config["auto_paste"] = self.auto_paste.isChecked()
        self.config["completion_sound"] = self.completion_sound.isChecked()
        self.config["debug_mode"] = self.debug_mode.isChecked()
        self.config["is_demo"] = self.debug_demo_mode.isChecked() # Match key used in main.py
        self.config["output_prefix"] = self.output_prefix.isChecked()
        self.config["separate_keystrike_log"] = self.separate_keystrike_log.isChecked()
        self.config["show_floating_button"] = self.show_floating_button.isChecked()
        self.config["showcase_mode"] = self.showcase_mode.isChecked()
        self.config["memory_enabled"] = self.memory_inject_cb.isChecked()

        try:
            SOUL_BASE_PATH.write_text(self.soul_prompt.toPlainText().strip(), encoding="utf-8")
        except: pass

        save_config(self.config)
        # v2.7.32: Windows 穩定性優先，提示手動重啟而非自動連鎖反應
        QMessageBox.information(self, "嘴炮輸入法", "設定已儲存！\n\n為了確保「啟動防護」與「載入模組」完整生效，請務必手動『結束並重啟』本程式。")
        if self.on_save: self.on_save(self.config)
        self.close()

    def run(self):
        self.show()


def has_api_key(config: dict) -> bool:
    stt = config.get("stt_engine", "local_whisper")
    if stt == "local_whisper" and (not config.get("llm_enabled") or config.get("llm_engine") == "ollama"):
        return True
    for k in ["groq_api_key", "openai_api_key", "openrouter_api_key"]:
        if config.get(k): return True
    return False


if __name__ == "__main__":
    app = QApplication(sys.argv)
    win = SettingsWindow()
    win.show()
    sys.exit(app.exec())
