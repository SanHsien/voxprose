"""雲端同步頁 mixin — split out of ui/settings_window.py (REVIEW.md #7).

Verbatim relocation of `_create_sync_page` and the sync-directory set/clear/
migrate logic it depends on. No logic changes.
"""
from pathlib import Path

import shutil

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QFrame,
    QFileDialog, QMessageBox,
)

from ui.settings.common import GlassCard


class SyncPageMixin:
    def _create_sync_page(self):
        page = QWidget()
        layout = QVBoxLayout(page)
        # Shift everything UP
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(20)

        layout.addWidget(self._page_section_header("☁️ 雲端同步 & NAS (Cross-Platform Sync)"))

        desc = QLabel(
            "透過設定同步目錄，您可以在多台 Mac 或 PC 之間共用「靈魂情境」、「詞彙」與「AI 記憶」。\n"
            "建議選擇您的 NAS 同步資料夾、iCloud 或 Google Drive 目錄。\n\n"
            "※ 注意：本機「控制熱鍵」與硬體偏好設定仍會保持各機獨立，不會互相干擾。"
        )
        desc.setWordWrap(True)
        desc.setStyleSheet("color: #8a8d91; line-height: 1.6; font-size: 14px;")
        layout.addWidget(desc)

        sync_panel = QFrame()
        sync_panel.setStyleSheet("""
            QFrame {
                background-color: rgba(124, 77, 255, 15);
                border: 1px solid rgba(124, 77, 255, 40);
                border-radius: 12px;
            }
        """)
        sync_layout = QVBoxLayout(sync_panel)
        sync_layout.setContentsMargins(25, 25, 25, 25)
        sync_layout.setSpacing(20)

        self.sync_status_lbl = QLabel("目前狀態：本地存儲 (Local Only)")
        self.sync_status_lbl.setStyleSheet("color: #ccc; font-weight: bold; font-size: 16px;")
        sync_layout.addWidget(self.sync_status_lbl)

        sync_btns = QHBoxLayout()
        self.btn_set_sync_dir = QPushButton("🔗 連結同步目錄 (Connect Sync Folder)")
        self.btn_set_sync_dir.setMinimumHeight(45)
        self.btn_set_sync_dir.clicked.connect(self._set_sync_directory)
        sync_btns.addWidget(self.btn_set_sync_dir)

        self.btn_clear_sync = QPushButton("🔌 取消同步")
        self.btn_clear_sync.setObjectName("danger")
        self.btn_clear_sync.setFixedWidth(130)
        self.btn_clear_sync.setMinimumHeight(45)
        self.btn_clear_sync.clicked.connect(self._clear_sync_directory)
        sync_btns.addWidget(self.btn_clear_sync)
        sync_layout.addLayout(sync_btns)

        from paths import SYNC_POINTER_PATH
        if SYNC_POINTER_PATH.exists():
            try:
                path_str = SYNC_POINTER_PATH.read_text(encoding="utf-8").strip()
                if path_str:
                    self.sync_status_lbl.setText(f"✅ 已連結同步：{path_str}")
                    self.sync_status_lbl.setStyleSheet("color: #00e676; font-weight: bold; font-size: 16px;")
            except: pass

        layout.addWidget(sync_panel)

        warning_box = GlassCard()
        w_layout = QVBoxLayout(warning_box)
        w_layout.setContentsMargins(15, 15, 15, 15)
        w_lbl = QLabel("🛡️ 安全性提醒：AI API Key 一律只存在本機，不會進入同步目錄；同步目錄仍包含 Prompt、靈魂設定等其他資料，請確保該空間僅由您本人存取。")
        w_lbl.setStyleSheet("color: #ffab40; font-size: 13px;")
        w_lbl.setWordWrap(True)
        w_layout.addWidget(w_lbl)
        layout.addWidget(warning_box)

        layout.addStretch()
        return page

    # ── 同步邏輯 (Sync Logic) ────────────────────────────────────
    def _set_sync_directory(self):
        """選擇同步目錄並引導遷移資料。"""
        dir_path = QFileDialog.getExistingDirectory(self, "選擇 NAS 或雲端同步資料夾")
        if not dir_path:
            return

        from paths import SYNC_POINTER_PATH, APP_DATA_DIR

        # 1. 存入指標
        try:
            SYNC_POINTER_PATH.write_text(dir_path, encoding="utf-8")
        except Exception as e:
            QMessageBox.critical(self, "失敗", f"無法寫入同步指針：{e}")
            return

        # 2. 詢問是否遷移資料
        reply = QMessageBox.question(
            self, "資料遷移",
            "是否要將目前的靈魂情境、辭典與記憶「遷移」到新的同步目錄中？\n\n"
            "※ 如果該目錄已有資料，選『否』將直接連結現有資料。",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )

        if reply == QMessageBox.StandardButton.Yes:
            self._migrate_to_sync(Path(dir_path))

        QMessageBox.information(self, "成功", "同步路徑已設定完成！請重啟應用程式以生效。")
        self.sync_status_lbl.setText(f"✅ 已同步至：{dir_path}")
        self.sync_status_lbl.setStyleSheet("color: #00e676; font-weight: bold;")

    def _migrate_to_sync(self, target_base: Path):
        """將本地資料搬移至同步目錄。"""
        from paths import APP_DATA_DIR
        folders_to_sync = ["soul", "vocab", "memory", "stats"]
        files_to_sync = ["ai_permanent_memory.md"]

        for folder in folders_to_sync:
            src = APP_DATA_DIR / folder
            dst = target_base / folder
            if src.exists():
                try:
                    if dst.exists(): shutil.rmtree(dst)
                    shutil.copytree(src, dst)
                except Exception as e:
                    print(f"[Sync] Error migrating folder {folder}: {e}")

        for filename in files_to_sync:
            src = APP_DATA_DIR / filename
            dst = target_base / filename
            if src.exists():
                try:
                    shutil.copy2(src, dst)
                except Exception as e:
                    print(f"[Sync] Error migrating file {filename}: {e}")

    def _clear_sync_directory(self):
        """取消同步。"""
        from paths import SYNC_POINTER_PATH
        if SYNC_POINTER_PATH.exists():
            SYNC_POINTER_PATH.unlink()
            QMessageBox.information(self, "重設", "已取消同步，改回使用本地存儲。請重啟程式。")
            self.sync_status_lbl.setText("目前狀態：本地存儲 (Local Only)")
            self.sync_status_lbl.setStyleSheet("color: #aaa; font-weight: bold;")
