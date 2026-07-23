"""系統設定頁 mixin — split out of ui/settings_window.py (REVIEW.md #7).

Verbatim relocation of `_create_general_page` and the hotkey-test/diagnostics
button handlers it wires up. No logic changes.
"""
import os
import platform

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGridLayout, QFrame, QLabel, QPushButton,
    QCheckBox, QMessageBox, QApplication,
)
from PyQt6.QtCore import Qt

from ui.settings.common import HotkeyRecorderButton


class GeneralPageMixin:
    def _create_general_page(self):
        page = QWidget()
        layout = QVBoxLayout(page)

        layout.addWidget(self._page_section_header("⌨️ 設定錄音按鍵"))

        hotkey_grid = QFrame()
        grid_layout = QVBoxLayout(hotkey_grid)

        row_ptt = QHBoxLayout()
        self.btn_ptt = HotkeyRecorderButton(self.config.get("hotkey_ptt", "alt_r"))
        self.btn_ptt.setFixedHeight(32)
        # v2.9.1: Fixed width so it's not too long and doesn't overlap
        self.btn_ptt.setFixedWidth(160)

        self.btn_test_rec = QPushButton("🚀 測試")
        self.btn_test_rec.setToolTip("按住測試 PTT 收音")
        self.btn_test_rec.setFixedWidth(85) # v2.9.1: Wider for label visibility
        self.btn_test_rec.setFixedHeight(32)
        self.btn_test_rec.setStyleSheet("background: #444; border-radius: 4px; font-size: 13px; font-weight: bold;")
        self.btn_test_rec.pressed.connect(self.test_start.emit)
        self.btn_test_rec.released.connect(self.test_stop.emit)

        lbl_ptt = QLabel("錄音按住 (PTT)")
        lbl_ptt.setFixedWidth(120)
        row_ptt.addWidget(lbl_ptt)
        row_ptt.addWidget(self.btn_ptt)
        row_ptt.addWidget(self.btn_test_rec)
        row_ptt.addStretch(1) # Ensure alignment
        grid_layout.addLayout(row_ptt)

        # v2.8.15: Re-add LLM Hotkey
        row_llm = QHBoxLayout()
        self.btn_llm = HotkeyRecorderButton(self.config.get("hotkey_llm", "f14"))
        self.btn_llm.setFixedHeight(32)
        self.btn_llm.setFixedWidth(160)

        self.btn_test_llm = QPushButton("🚀 測試")
        self.btn_test_llm.setFixedWidth(85)
        self.btn_test_llm.setFixedHeight(32)
        self.btn_test_llm.setStyleSheet("background: #444; border-radius: 4px; font-size: 13px; font-weight: bold;")
        self.btn_test_llm.clicked.connect(self.test_llm.emit)

        lbl_llm = QLabel("潤飾模式 (LLM)")
        lbl_llm.setFixedWidth(120)
        row_llm.addWidget(lbl_llm)
        row_llm.addWidget(self.btn_llm)
        row_llm.addWidget(self.btn_test_llm)
        row_llm.addStretch(1)
        grid_layout.addLayout(row_llm)

        row_toggle = QHBoxLayout()
        self.btn_toggle = HotkeyRecorderButton(self.config.get("hotkey_toggle", "f13"))
        self.btn_toggle.setFixedHeight(32)
        self.btn_toggle.setFixedWidth(160)

        self.btn_test_toggle = QPushButton("🚀 測試")
        self.btn_test_toggle.setToolTip("點按測試 Toggle 收音")
        self.btn_test_toggle.setFixedWidth(85) # v2.9.1: Wider
        self.btn_test_toggle.setFixedHeight(32)
        self.btn_test_toggle.setStyleSheet("background: #444; border-radius: 4px; font-size: 13px; font-weight: bold;")
        self.btn_test_toggle.clicked.connect(self.test_toggle.emit)

        lbl_toggle = QLabel("錄音開關 (Toggle)")
        lbl_toggle.setFixedWidth(120)
        row_toggle.addWidget(lbl_toggle)
        row_toggle.addWidget(self.btn_toggle)
        row_toggle.addWidget(self.btn_test_toggle)
        row_toggle.addStretch(1)
        grid_layout.addLayout(row_toggle)

        layout.addWidget(hotkey_grid)

        layout.addWidget(self._page_section_header("⚙️ 偏好設定"))
        self.auto_paste = QCheckBox("結果自動貼上 (Paste automatically)")
        self.auto_paste.setChecked(self.config.get("auto_paste", True))
        layout.addWidget(self.auto_paste)

        self.show_floating_button = QCheckBox("顯示浮動按鈕 (Show Floating Button)")
        self.show_floating_button.setChecked(self.config.get("show_floating_button", True))
        layout.addWidget(self.show_floating_button)

        self.completion_sound = QCheckBox("錄音完成時播放音效 (Play sound on completion)")
        self.completion_sound.setChecked(self.config.get("completion_sound", True))
        layout.addWidget(self.completion_sound)

        self.debug_mode = QCheckBox("啟用詳細日誌輸出 (Debug logging)")
        self.debug_mode.setChecked(self.config.get("debug_mode", False))
        layout.addWidget(self.debug_mode)

        self.debug_demo_mode = QCheckBox("情境模擬 Demo 版 (需API KEY連結雲端LLM) (Debug Scenario Demo Mode)") #咖啡版功能
        self.debug_demo_mode.setChecked(self.config.get("is_demo", False)) #咖啡版功能
        layout.addWidget(self.debug_demo_mode) #咖啡版功能

        self.output_prefix = QCheckBox("顯示模式名稱前綴 (需API KEY連結雲端LLM)  (Output with Mode Prefix)") #咖啡版功能
        self.output_prefix.setChecked(self.config.get("output_prefix", False)) #咖啡版功能
        layout.addWidget(self.output_prefix) #咖啡版功能

        self.showcase_mode = QCheckBox("LLM 展示版 (需API KEY連結雲端LLM)  (LLM Showcase Mode: [STT] + [LLM])") #咖啡版功能
        self.showcase_mode.setChecked(self.config.get("showcase_mode", False)) #咖啡版功能
        layout.addWidget(self.showcase_mode) #咖啡版功能

        layout.addWidget(self._page_section_header("🛠️ 診斷與修復"))

        diag_grid = QGridLayout()
        diag_grid.setContentsMargins(0, 5, 0, 5)
        diag_grid.setSpacing(10)

        # v2026-07-20: 麥克風測試按鈕本體邏輯（sd.rec + numpy RMS）本來就是跨平台
        # 程式碼，未呼叫任何 macOS 專屬 API；先前 _run_mic_test() 內有一段
        # `if platform.system() != "Darwin": 彈窗「此診斷功能目前專為 macOS 設計」`
        # 的誤植擋板，導致這裡連按鈕都被藏起來（Windows 使用者完全看不到、也永遠
        # 用不到一個其實能動的功能）。已移除該擋板（見 _run_mic_test 內註解與
        # docs/DECISIONS.md），這裡同步取消 Windows 隱藏。
        self.btn_mic_test = QPushButton("🎤 麥克風測試與診斷 (Mic Test)")
        self.btn_mic_test.setObjectName("secondary")
        self.btn_mic_test.clicked.connect(self._run_mic_test)
        diag_grid.addWidget(self.btn_mic_test, 0, 0)

        self.btn_run_self_check = QPushButton("🔍 系統自我檢測 (Self-Check)")
        self.btn_run_self_check.setObjectName("secondary")
        self.btn_run_self_check.clicked.connect(self._run_self_check)
        diag_grid.addWidget(self.btn_run_self_check, 0, 1)

        # 註：self_check.py 本身邏輯也是跨平台（下載 tiny whisper 模型做真實轉錄
        # 測試），但這顆按鈕是否該在 Windows 顯示不在本次任務範圍內（任務只點名
        # 麥克風測試/系統診斷 stub），維持原本的 Windows 隱藏，避免無關的範圍蔓延。
        if platform.system() == "Windows":
            self.btn_run_self_check.hide()

        # Mac 主線 11-3（v2.9.11 崩潰診斷管道，docs/mac-mainline-absorption-analysis.md）
        # 移植 + Windows 化改寫：一鍵匯出診斷包（環境資訊＋裝置清單＋日誌＋脫敏設定）
        self.btn_export_diagnostics = QPushButton("📦 匯出診斷包 (Export Diagnostics)")
        self.btn_export_diagnostics.setObjectName("secondary")
        self.btn_export_diagnostics.clicked.connect(self._run_export_diagnostics)
        diag_grid.addWidget(self.btn_export_diagnostics, 1, 0, 1, 2)  # Span 2 columns

        self.btn_view_logs = QPushButton("📄 檢視詳細日誌 (View Detail Logs)")
        self.btn_view_logs.setObjectName("secondary")
        self.btn_view_logs.clicked.connect(self._view_debug_log)
        diag_grid.addWidget(self.btn_view_logs, 2, 0, 1, 2)  # Span 2 columns

        self.btn_open_folder = QPushButton("📂 開啟數據與模型目錄 (Open Data/Models)")
        self.btn_open_folder.setObjectName("secondary")
        self.btn_open_folder.clicked.connect(self._open_data_folder)
        diag_grid.addWidget(self.btn_open_folder, 3, 0, 1, 2) # Span 2 columns

        layout.addLayout(diag_grid)

        layout.addStretch()
        return page

    def _run_self_check(self):
        import subprocess
        import sys
        import os
        # 2026-07-21 拆分（REVIEW #7）：這個檔案現在住在 ui/settings/ 底下，比原本
        # ui/settings_window.py 多一層目錄，往上多 dirname 一次才能回到 repo root。
        script_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "self_check.py")
        if os.path.exists(script_path):
            # Launch in a new terminal window on Windows
            if platform.system() == "Windows":
                subprocess.Popen(["cmd.exe", "/c", "start", sys.executable, script_path])
            else:
                subprocess.Popen([sys.executable, script_path])
        else:
            QMessageBox.warning(self, "錯誤", f"找不到檢測程式：{script_path}")

    def _run_export_diagnostics(self):
        """Mac 主線 11-3（v2.9.11 崩潰診斷管道）移植＋Windows 化：一鍵匯出診斷包
        （環境資訊＋音訊裝置清單＋debug.log/main_crash.log 尾段＋
        脫敏設定摘要）到桌面 zip，方便回報問題。實際邏輯在 utils/diagnostics.py。"""
        from paths import APP_DATA_DIR
        from utils.diagnostics import export_diagnostic_bundle

        try:
            zip_path = export_diagnostic_bundle(APP_DATA_DIR, self.config)
        except Exception as e:
            QMessageBox.critical(self, "匯出失敗", f"匯出診斷包時發生錯誤：{e}")
            return

        if zip_path is None:
            QMessageBox.critical(self, "匯出失敗", "無法產生診斷包，請查看 debug.log 了解詳情。")
            return

        QMessageBox.information(
            self, "匯出成功",
            f"診斷包已匯出至：\n{zip_path}\n\n"
            "內含環境資訊、麥克風裝置清單、日誌片段與已去除 API Key 的設定摘要，"
            "可直接提供給支援人員協助排查問題。"
        )

    def _view_debug_log(self):
        from paths import APP_DATA_DIR
        log_path = APP_DATA_DIR / "debug.log"
        if log_path.exists():
            import os, platform
            if platform.system() == "Windows":
                os.startfile(str(log_path))
            else:
                import subprocess
                subprocess.run(["open", str(log_path)])
        else:
            QMessageBox.information(self, "資訊", f"日誌檔案尚未建立：\n{log_path}")

    def _open_data_folder(self):
        from paths import APP_DATA_DIR
        if APP_DATA_DIR.exists():
            import os, platform
            if platform.system() == "Windows":
                os.startfile(str(APP_DATA_DIR))
            else:
                import subprocess
                subprocess.run(["open", str(APP_DATA_DIR)])
        else:
            QMessageBox.information(self, "資訊", f"數據目錄尚未建立：\n{APP_DATA_DIR}")

    def _run_mic_test(self):
        # 2026-07-20：移除「非 macOS 就拒絕」的誤植擋板。以下測試邏輯
        # （sd.rec + numpy RMS）本來就不含任何 macOS 專屬 API，下面的錯誤訊息
        # 原本就已經是針對 Windows 隱私權設定寫的（見 energy < 1e-7 分支），
        # 擋板本身才是不一致的地方。詳見 docs/DECISIONS.md 2026-07-20 條目。
        from PyQt6.QtWidgets import QMessageBox, QProgressDialog
        import sounddevice as sd
        import numpy as np
        import time

        reply = QMessageBox.question(self, "麥克風測試",
                                   "即將開始 3 秒鐘的錄音測試，請對著麥克風說話。\n\n準備好了嗎？",
                                   QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)

        if reply == QMessageBox.StandardButton.No:
            return

        # Create a non-modal (but blocking) progress dialog
        progress = QProgressDialog("正在錄音中，請說話...", None, 0, 3, self)
        progress.setWindowTitle("麥克風測試")
        progress.setWindowModality(Qt.WindowModality.WindowModal)
        progress.show()

        fs = 16000
        duration = 3.0

        try:
            recording = sd.rec(int(duration * fs), samplerate=fs, channels=1, dtype='float32')

            for i in range(3):
                progress.setValue(i)
                QApplication.processEvents()
                time.sleep(1)

            sd.wait()
            progress.setValue(3)
            progress.close()

            energy = np.sqrt(np.mean(recording**2))

            if energy < 1e-7:
                QMessageBox.critical(self, "測試失敗",
                    "偵測到【完全靜音】(Silence)。\n\n請至 Windows 設定 → 隱私權 → 麥克風，確認已授權本程式存取麥克風。")
            elif energy < 1e-3:
                QMessageBox.warning(self, "測試警告",
                    f"音訊能源過低 ({energy:.6f})。\n\n請檢查系統輸入音量設定。")
            else:
                QMessageBox.information(self, "測試成功",
                    f"成功接收音訊資料！\n能源強度: {energy:.6f}\n您的麥克風運作正常。")

        except Exception as e:
            if 'progress' in locals(): progress.close()
            QMessageBox.critical(self, "錯誤", f"錄音測試失敗: {str(e)}")
