"""Dashboard page mixin — split out of ui/settings_window.py (REVIEW.md #7).

Verbatim relocation of `_create_dashboard_page` and the status/model/
permission helper methods it depends on. No logic changes; see
ui/settings/common.py's module docstring and docs/DECISIONS.md for the
split's mapping table.
"""
import logging
import platform
from pathlib import Path

from PyQt6.QtWidgets import QHBoxLayout, QVBoxLayout, QWidget, QLabel, QListWidget, QScrollArea
from PyQt6.QtCore import Qt

from ui.settings.common import GlassCard, PermissionLight, ModelStatusLight

log = logging.getLogger("voicetype.ui")


class DashboardPageMixin:
    def _create_dashboard_page(self):
        # QScrollArea：內容超過視窗高度時捲動，而不是被 Qt 壓縮到文字重疊
        page = QScrollArea()
        page.setWidgetResizable(True)
        page.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        page.setStyleSheet("QScrollArea { background: transparent; border: none; }")
        container = QWidget()
        container.setStyleSheet("background: transparent;")
        layout = QVBoxLayout(container)
        layout.setContentsMargins(0, 0, 12, 0)
        layout.setSpacing(18)

        dash_header = QHBoxLayout()
        header = QLabel("Dashboard")
        header.setStyleSheet("font-size: 28px; font-weight: bold; color: #ffffff;")
        dash_header.addWidget(header)

        dash_header.addStretch()

        title_cn = QLabel("嘴炮輸入法")
        win_font = "Microsoft JhengHei" if platform.system() == "Windows" else "Taipei Sans TC Beta"
        title_cn.setStyleSheet(f"font-family: '{win_font}'; font-size: 22px; font-weight: bold; color: #7c4dff;")
        dash_header.addWidget(title_cn)


        # Add side margins to content but not to the header text alignment if needed
        dash_header_container = QWidget()
        dash_header_v = QVBoxLayout(dash_header_container)
        dash_header_v.setContentsMargins(0, 0, 0, 0) # Tight
        dash_header_v.addLayout(dash_header)
        layout.addWidget(dash_header_container)

        # Top Cards: Row 1
        cards_row1 = QHBoxLayout()
        cards_row1.setSpacing(15)

        # 1. Permission / System Environment Card
        if platform.system() == "Windows":
            # Windows: 顯示 GPU/CUDA 與麥克風資訊
            env_card = GlassCard()
            p_layout = QVBoxLayout(env_card)
            p_layout.setContentsMargins(20, 18, 20, 18)
            p_layout.setSpacing(8)
            lbl_p = QLabel("🖥️ 系統環境")
            lbl_p.setStyleSheet("font-weight: bold; color: #aaa; font-size: 13px;")
            p_layout.addWidget(lbl_p)

            # GPU / CUDA 偵測 (v2.8.27_V28: Robust check)
            gpu_text = "⏳ 偵測中..."
            cuda_color = "#888"
            try:
                # 優先檢查是否已有全域載入的 STT 實例可用於查詢
                # 我們可以透過 QApplication 獲取主 App 實例的高級方法
                # 或者直接嘗試導入 (現在有 libiomp5md.dll 了應該安全)
                import ctranslate2
                try:
                    cuda_count = ctranslate2.get_cuda_device_count()
                    if cuda_count > 0:
                        gpu_text = f"✅ CUDA GPU × {cuda_count} (加速可用)"
                        cuda_color = "#00e676"
                    else:
                        gpu_text = "⚠️ 未偵測到 CUDA GPU (CPU 模式)"
                        cuda_color = "#ffab40"
                except Exception as _inner_e:
                    log.warning(f"[ui] get_cuda_device_count failed: {_inner_e}")
                    gpu_text = "⚠️ GPU 偵測組件異常"
                    cuda_color = "#ffab40"
            except Exception as e:
                log.error(f"[ui] ctranslate2 import error in dashboard: {e}")
                gpu_text = "❌ 驅動組件遺失 (V28)"
                cuda_color = "#ff5252"

            self.lbl_gpu = QLabel(gpu_text)
            win_font = "Microsoft JhengHei" if platform.system() == "Windows" else ""
            self.lbl_gpu.setStyleSheet(f"color: {cuda_color}; font-size: 14px; font-weight: bold; font-family: '{win_font}';")
            self.lbl_gpu.setWordWrap(True)
            p_layout.addWidget(self.lbl_gpu)


            # 麥克風裝置偵測
            mic_text = "未知裝置"
            try:
                import sounddevice
                dev = sounddevice.query_devices(kind='input')
                mic_text = dev.get('name', '未知裝置')
            except Exception:
                mic_text = "無法偵測"

            self.lbl_mic_device = QLabel(f"🎤 {mic_text}")
            win_font = "Microsoft JhengHei" if platform.system() == "Windows" else ""
            self.lbl_mic_device.setStyleSheet(f"color: #e2e4e7; font-size: 13px; font-family: '{win_font}';")
            self.lbl_mic_device.setWordWrap(True)

            p_layout.addWidget(self.lbl_mic_device)
            p_layout.addStretch()

            cards_row1.addWidget(env_card, 1)

            # 建立隱藏的權限燈號（讓 _check_all_permissions 不炸）
            self.light_acc = PermissionLight("輔助功能", "")
            self.light_acc.hide()
            self.light_input = PermissionLight("輸入監聽", "")
            self.light_input.hide()
            self.light_mic = PermissionLight("麥克風", "")
            self.light_mic.hide()

        # 2. Model Card (New)
        model_card = GlassCard()
        m_layout = QVBoxLayout(model_card)
        m_layout.setContentsMargins(20, 18, 20, 18)
        m_layout.setSpacing(6)
        lbl_m = QLabel("🧠 AI 本地模型 (Faster-Whisper)")
        lbl_m.setStyleSheet("font-weight: bold; color: #aaa; font-size: 13px;")
        m_layout.addWidget(lbl_m)

        self.light_model_small = ModelStatusLight("Small", "500MB", "輕快，但精準度稍遜。")
        self.light_model_medium = ModelStatusLight("Medium", "1.5GB", "均衡型，首選推薦 (精準)。")
        self.light_model_large = ModelStatusLight("Large", "3.0GB", "極致精準，背景嘈雜也能辨識。")
        m_layout.addWidget(self.light_model_small)
        m_layout.addWidget(self.light_model_medium)
        m_layout.addWidget(self.light_model_large)
        m_layout.addStretch()
        cards_row1.addWidget(model_card, 1)

        # 3. Status Card
        status_card = GlassCard()
        status_layout = QVBoxLayout(status_card)
        status_layout.setContentsMargins(20, 18, 20, 18)
        status_layout.setSpacing(8)
        lbl_s = QLabel("📺 運行狀態")
        lbl_s.setStyleSheet("font-weight: bold; color: #aaa; font-size: 13px;")
        status_layout.addWidget(lbl_s)

        self.lbl_status_ai = QLabel("AI 潤飾: 已開啟")
        self.lbl_status_ai.setStyleSheet("color: #7c4dff; font-weight: bold; font-size: 16px;")
        status_layout.addWidget(self.lbl_status_ai)

        self.lbl_status_stt = QLabel("引擎: Local Whisper")
        self.lbl_status_stt.setStyleSheet("color: #888; font-size: 13px;")
        status_layout.addWidget(self.lbl_status_stt)

        self.lbl_status_auto = QLabel("全時模式: 關")
        self.lbl_status_auto.setStyleSheet("color: #888; font-size: 13px;")
        status_layout.addWidget(self.lbl_status_auto)
        status_layout.addStretch()
        cards_row1.addWidget(status_card, 1)

        layout.addLayout(cards_row1)

        # Bottom Cards: Row 2
        cards_row2 = QHBoxLayout()
        cards_row2.setSpacing(15)

        # 3. Quick Stats Card
        stats_card = GlassCard()
        sq_layout = QVBoxLayout(stats_card)
        sq_layout.setContentsMargins(20, 18, 20, 18)
        sq_layout.setSpacing(6)
        lbl_sq = QLabel("📈 今日語效")
        lbl_sq.setStyleSheet("font-weight: bold; color: #aaa; font-size: 13px;")
        sq_layout.addWidget(lbl_sq)
        self.lbl_today_count = QLabel("0 次錄音")
        self.lbl_today_count.setStyleSheet("color: #00e5ff; font-weight: bold; font-size: 26px;")
        sq_layout.addWidget(self.lbl_today_count)
        self.lbl_today_chars = QLabel("錄製約 0 字")
        self.lbl_today_chars.setStyleSheet("color: #888; font-size: 13px;")
        sq_layout.addWidget(self.lbl_today_chars)
        cards_row2.addWidget(stats_card, 1)

        # 4. Time Saved Card
        time_card = GlassCard()
        t_layout = QVBoxLayout(time_card)
        t_layout.setContentsMargins(20, 18, 20, 18)
        t_layout.setSpacing(6)
        lbl_tc = QLabel("⏱️ 累計省下時間")
        lbl_tc.setStyleSheet("font-weight: bold; color: #aaa; font-size: 13px;")
        t_layout.addWidget(lbl_tc)
        self.lbl_time_saved = QLabel("0 分鐘")
        self.lbl_time_saved.setStyleSheet("color: #ffab40; font-weight: bold; font-size: 26px;")
        t_layout.addWidget(self.lbl_time_saved)
        self.lbl_total_chars_desc = QLabel("共辨識 0 字")
        self.lbl_total_chars_desc.setStyleSheet("color: #888; font-size: 13px;")
        t_layout.addWidget(self.lbl_total_chars_desc)
        cards_row2.addWidget(time_card, 1)

        layout.addLayout(cards_row2)

        # ── Model Download Progress Card ──────────────────────
        from PyQt6.QtWidgets import QProgressBar
        self.download_card = GlassCard()
        dl_layout = QVBoxLayout(self.download_card)
        dl_layout.setContentsMargins(20, 18, 20, 18)
        dl_layout.setSpacing(8)
        lbl_dl = QLabel("⬇️ 模型下載進度")
        lbl_dl.setStyleSheet("font-weight: bold; color: #aaa; font-size: 13px;")
        dl_layout.addWidget(lbl_dl)

        self.lbl_download_status = QLabel("等待模型載入...")
        self.lbl_download_status.setStyleSheet("color: #00e5ff; font-size: 14px; font-weight: bold;")
        dl_layout.addWidget(self.lbl_download_status)

        self.download_progress = QProgressBar()
        self.download_progress.setRange(0, 0)  # 不確定進度 → 跑馬燈模式
        self.download_progress.setFixedHeight(8)
        self.download_progress.setStyleSheet("""
            QProgressBar { background: #1c1f26; border: 1px solid #2d333d; border-radius: 4px; }
            QProgressBar::chunk { background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #7c4dff, stop:1 #00e5ff); border-radius: 4px; }
        """)
        dl_layout.addWidget(self.download_progress)

        self.lbl_download_detail = QLabel("首次啟動需要下載 AI 模型，請確保網路暢通。")
        self.lbl_download_detail.setStyleSheet("color: #666; font-size: 11px;")
        dl_layout.addWidget(self.lbl_download_detail)

        layout.addWidget(self.download_card)
        # 預設隱藏：有模型就不需要看到
        self.download_card.setVisible(not self._is_model_present(self.config.get("whisper_model", "medium")))

        # Recent Activity Card
        recent_card = GlassCard()
        rc_layout = QVBoxLayout(recent_card)
        rc_layout.setContentsMargins(20, 18, 20, 18)
        rc_layout.setSpacing(8)
        lbl_rc = QLabel("💡 最近學到的詞彙")
        lbl_rc.setStyleSheet("font-weight: bold; color: #aaa; font-size: 13px;")
        rc_layout.addWidget(lbl_rc)
        self.dashboard_vocab = QListWidget()
        self.dashboard_vocab.setStyleSheet("background: transparent; border: none; font-size: 13px;")
        self.dashboard_vocab.setFixedHeight(120)
        rc_layout.addWidget(self.dashboard_vocab)
        layout.addWidget(recent_card)

        layout.addStretch()
        page.setWidget(container)
        return page

    def _update_dashboard_status(self):
        ai = "已開啟" if self.config.get("llm_enabled") else "已關閉"
        self.lbl_status_ai.setText(f"AI 潤飾: {ai}")
        self.lbl_status_ai.setStyleSheet(f"color: {'#7c4dff' if ai == '已開啟' else '#666'}; font-weight: bold; font-size: 16px;")

        eng = self.config.get("stt_engine", "local_whisper")
        self.lbl_status_stt.setText(f"引擎: {eng.upper()}")

        auto_on = self.config.get("auto_trigger_enabled", False)
        self.lbl_status_auto.setText(f"全時模式: {'開 (免按鍵)' if auto_on else '關'}")
        self.lbl_status_auto.setStyleSheet(
            f"color: {'#00e676' if auto_on else '#888'}; font-size: 13px;"
            + ("font-weight: bold;" if auto_on else ""))

        # 檢查權限與模型狀態
        self._check_all_permissions()
        self._check_local_models()

    def update_download_progress(self, status: str, value: int = -1, done: bool = False):
        """由 main.py 呼叫，更新模型下載進度卡片。"""
        try:
            if done:
                self.download_card.setVisible(False)
                self._check_local_models()  # 刷新模型綠燈
            else:
                self.download_card.setVisible(True)
                self.lbl_download_status.setText(status)
                if value >= 0:
                    self.download_progress.setRange(0, 100)
                    self.download_progress.setValue(value)
                else:
                    self.download_progress.setRange(0, 0) # Indeterminate
        except Exception:
            pass

    def _check_all_permissions(self):
        import logging
        log = logging.getLogger("voicetype")

        # Windows 不需要 macOS TCC 權限檢查，全部亮綠燈
        if platform.system() == "Windows":
            self.light_acc.set_status(True)
            self.light_input.set_status(True)
            self.light_mic.set_status(True)
            log.info("[PERM] Windows: All permissions auto-granted.")
            return

        log.info("[PERM] Windows: All permissions auto-granted.")

    def _check_local_models(self):
        """檢查 Faster-Whisper 模型是否已下載到本機快取"""
        self.light_model_small.set_status(self._is_model_present("small"))
        self.light_model_medium.set_status(self._is_model_present("medium"))
        self.light_model_large.set_status(self._is_model_present("large"))

    def _is_model_present(self, size: str) -> bool:
        try:
            from paths import APP_DATA_DIR
            # 先查 App 實際的 download_root（%APPDATA%/VoxProse/whisper_models），
            # 再退回 HuggingFace 預設快取（手動裝過的人可能放這）
            candidates = [
                APP_DATA_DIR / "whisper_models",
                Path.home() / ".cache" / "huggingface" / "hub",
            ]
            prefix = f"models--Systran--faster-whisper-{size}"
            for cache_path in candidates:
                if not cache_path.exists():
                    continue
                for p in cache_path.iterdir():
                    if p.is_dir() and p.name.startswith(prefix):
                        snap = p / "snapshots"
                        if snap.exists() and any(snap.iterdir()):
                            return True
            return False
        except Exception:
            return False
