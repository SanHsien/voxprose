"""靈魂設定頁 mixin — split out of ui/settings_window.py (REVIEW.md #7).

Verbatim relocation of `_create_soul_page` and `_create_file_list_tab`
(shared by the 性格模式 sub-tab). No logic changes; see
ui/settings/common.py's module docstring and docs/DECISIONS.md for the
split's mapping table.
"""
import logging
import os
import platform
from pathlib import Path

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QPushButton,
    QListWidget, QTextEdit, QMessageBox,
)
from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import QFont

log = logging.getLogger("voicetype.ui")

from paths import SOUL_SCENARIO_DIR


class SoulPageMixin:
    def _create_soul_page(self):
        from PyQt6.QtWidgets import QTabWidget
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setSpacing(10)

        layout.addWidget(self._page_section_header("✨ AI 靈魂與情境治理"))

        self.soul_tabs = QTabWidget()
        self.soul_tabs.setStyleSheet("""
            QTabWidget::pane { border: 1px solid rgba(255,255,255,10); border-radius: 8px; background: rgba(30,30,40,100); }
            QTabBar::tab { background: transparent; color: #8a8d91; padding: 10px 20px; font-size: 14px; }
            QTabBar::tab:selected { color: #7c4dff; border-bottom: 2px solid #7c4dff; font-weight: bold; }
        """)

        # 1. 基底靈魂
        base_tab = QWidget()
        base_layout = QVBoxLayout(base_tab)
        self.soul_prompt = QTextEdit()
        # Monaco 是 macOS 專屬字型（Mac 版複製殘留）；Windows 內建等寬字型用 Consolas
        self.soul_prompt.setFont(QFont("Consolas", 12))
        self.soul_prompt.setPlaceholderText("輸入 AI 的基底靈魂提示詞 (人格、風格、去贅詞規則)...")
        self.soul_prompt.setStyleSheet("background: rgba(20,20,30,150); border: 1px solid rgba(255,255,255,10); border-radius: 8px; color: #eee;")
        base_layout.addWidget(self.soul_prompt)
        self.soul_tabs.addTab(base_tab, "🏠 基底靈魂")

        # 2. 情境瀏覽 (v2.7.32: 改名為性格模式)
        scenario_tab = self._create_file_list_tab(SOUL_SCENARIO_DIR, "這裡存放不同場景的提示詞（性格模式），例如：社群貼文、商務回應。") #咖啡版功能
        self.soul_tabs.addTab(scenario_tab, "🎭 性格模式") #咖啡版功能

        # 3. 格式瀏覽 (v2.7.32: 隱藏)
        # format_tab = self._create_file_list_tab(SOUL_FORMAT_DIR, "這裡決定輸出的格式。")
        # self.soul_tabs.addTab(format_tab, "📝 輸出格式")

        # 4. 模板管理 (v2.7.32: 隱藏)
        # template_tab = self._create_file_list_tab(SOUL_TEMPLATE_DIR, "這裡存放儲存過的範例。")
        # self.soul_tabs.addTab(template_tab, "📌 我的模板")

        layout.addWidget(self.soul_tabs)
        return page

    def _create_file_list_tab(self, directory: Path, desc: str, is_json: bool = False):
        tab = QWidget()
        layout = QVBoxLayout(tab)

        # 頂部操作區
        controls_layout = QVBoxLayout()
        desc_lbl = QLabel(desc)
        desc_lbl.setStyleSheet("color: #888; font-size: 12px;")
        controls_layout.addWidget(desc_lbl)

        create_layout = QHBoxLayout()
        new_item_name = QLineEdit()
        new_item_name.setPlaceholderText("輸入新項目名稱...")
        new_item_name.setStyleSheet("background: rgba(0,0,0,50); border: 1px solid #444; border-radius: 4px; padding: 4px; color: #fff;")

        btn_add = QPushButton("➕ 新增項目")
        btn_add.setFixedWidth(100)
        btn_add.setStyleSheet("background: #2e7d32; color: white; padding: 5px; border-radius: 4px;")

        btn_del = QPushButton("🗑 刪除所選")
        btn_del.setFixedWidth(100)
        btn_del.setStyleSheet("background: #c62828; color: white; padding: 5px; border-radius: 4px;")

        create_layout.addWidget(new_item_name)
        create_layout.addWidget(btn_add)
        create_layout.addWidget(btn_del)
        controls_layout.addLayout(create_layout)

        layout.addLayout(controls_layout)

        lst = QListWidget()
        lst.setStyleSheet("background: rgba(20,20,30,150); border: 1px solid rgba(255,255,255,10); border-radius: 8px; color: #eee;")
        layout.addWidget(lst)

        def refresh():
            lst.clear()
            if not directory.exists(): return
            ext = "*.json" if is_json else "*.md"
            for f in sorted(directory.glob(ext)):
                if f.name == "default.md": continue # v2.7.32: 隱藏預設靈魂以免使用者誤改
                lst.addItem(f.name)

        QTimer.singleShot(100, refresh)

        # 內容編輯區 (不再是純預覽，改為可編輯)
        layout.addWidget(QLabel("內容編輯："))
        editor = QTextEdit()
        editor.setFont(QFont("Consolas", 11))  # 同上：Monaco 為 macOS 字型，改用 Windows 內建 Consolas
        editor.setStyleSheet("background: rgba(40,40,50,150); color: #fff; border: 1px solid rgba(255,255,255,20); border-radius: 8px;")
        layout.addWidget(editor)

        btn_save = QPushButton("💾 儲存修改")
        btn_save.setStyleSheet("background: #7c4dff; color: white; padding: 10px; border-radius: 6px; font-weight: bold;")
        btn_save.hide() # 初始隱藏
        layout.addWidget(btn_save)

        def on_item_clicked(item):
            fpath = directory / item.text()
            if fpath.exists():
                text = fpath.read_text(encoding="utf-8")
                if is_json:
                    import json
                    try:
                        data = json.loads(text)
                        text = json.dumps(data, indent=2, ensure_ascii=False)
                    except (json.JSONDecodeError, TypeError, ValueError) as e:
                        # 2026-07-23（broad except 清查）：這裡只可能是 JSON
                        # 解析相關錯誤，bare except 過寬——收窄型別，並補一筆
                        # debug log（純美化失敗不影響編輯，仍以原文顯示）。
                        log.debug(f"[soul_page] JSON pretty-print skipped ({fpath}): {e}")
                editor.setPlainText(text)
                btn_save.show()

        def on_save():
            item = lst.currentItem()
            if not item: return
            fpath = directory / item.text()
            try:
                fpath.write_text(editor.toPlainText(), encoding="utf-8")
                QMessageBox.information(self, "成功", f"「{item.text()}」已儲存。")
            except Exception as e:
                QMessageBox.critical(self, "錯誤", f"儲存失敗：{e}")

        def on_add():
            name = new_item_name.text().strip()
            if not name:
                QMessageBox.warning(self, "提示", "請輸入項目名稱。")
                return

            filename = f"{name}.json" if is_json else f"{name}.md"
            fpath = directory / filename
            if fpath.exists():
                QMessageBox.warning(self, "警告", "名稱已存在！")
                return

            try:
                fpath.write_text("# 新項目\n在此輸入設定...", encoding="utf-8")
                new_item_name.clear()
                refresh()
                # 選中新項目
                items = lst.findItems(filename, Qt.MatchFlag.MatchExactly)
                if items:
                    lst.setCurrentItem(items[0])
                    on_item_clicked(items[0])
            except Exception as e:
                QMessageBox.critical(self, "錯誤", f"建立失敗：{e}")

        def on_delete():
            item = lst.currentItem()
            if not item: return
            reply = QMessageBox.question(self, "確認刪除", f"確定要刪除「{item.text()}」嗎？", QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
            if reply == QMessageBox.StandardButton.Yes:
                (directory / item.text()).unlink()
                refresh()
                editor.clear()
                btn_save.hide()

        lst.itemClicked.connect(on_item_clicked)
        btn_add.clicked.connect(on_add)
        btn_del.clicked.connect(on_delete)
        btn_save.clicked.connect(on_save)

        open_label = "📂 從檔案總管開啟資料夾" if platform.system() == "Windows" else "📂 在 Finder 中打開資料夾"
        btn_open = QPushButton(open_label)
        btn_open.setStyleSheet("background: transparent; border: 1px solid #3d4452; color: #888; font-size: 11px;")

        def _open_folder():
            try:
                directory.mkdir(parents=True, exist_ok=True)
                if platform.system() == "Windows":
                    os.startfile(str(directory))  # 原本的 `open` 是 macOS 指令，Windows 上無效
                else:
                    os.system(f"open '{directory}'")
            except Exception as e:
                QMessageBox.warning(self, "聲成文", f"無法開啟資料夾：{e}")

        btn_open.clicked.connect(_open_folder)
        layout.addWidget(btn_open)

        return tab
