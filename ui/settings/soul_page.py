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
    QListWidget, QTextEdit, QMessageBox, QCheckBox, QTableWidget,
    QTableWidgetItem, QComboBox, QHeaderView, QProgressDialog,
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

        layout.addWidget(self._create_auto_scenario_section())

        return page

    def _create_auto_scenario_section(self):
        """2026-07-23：前景視窗感知的情境模板自動切換（來源：docs/REFERENCES.md
        Wispr Flow 調研條目）。啟用勾選框 + 規則清單（程式檔名 → 情境模板）+
        「偵測目前前景程式」按鈕，方便使用者查到要填在規則裡的正確程式檔名。
        對應設定：config.py 的 auto_scenario_enabled/auto_scenario_rules；接線
        邏輯在 ui/app.py 的 _detect_auto_scenario()/_get_effective_scenario()。
        預設關閉、規則預設空，關閉時對現有行為零影響。"""
        section = QWidget()
        layout = QVBoxLayout(section)
        layout.setContentsMargins(0, 10, 0, 0)

        layout.addWidget(self._page_section_header("🪟 前景視窗自動情境切換"))

        desc = QLabel(
            "依「目前正在打字的應用程式」自動套用對應的情境模板（如在 Outlook 用商務回應、"
            "在 LINE 用社群貼文），只在按下錄音的那一刻判斷一次，不影響上方手動選擇的情境；"
            "僅在「AI 潤飾/翻譯」啟用時才有效果（情境模板只用於 LLM 潤飾階段）。"
        )
        desc.setWordWrap(True)
        desc.setStyleSheet("color: #888; font-size: 12px;")
        layout.addWidget(desc)

        self.auto_scenario_enabled_cb = QCheckBox("啟用前景視窗自動情境切換 (Auto Scenario by Foreground App)")
        self.auto_scenario_enabled_cb.setChecked(self.config.get("auto_scenario_enabled", False))
        layout.addWidget(self.auto_scenario_enabled_cb)

        # 規則清單：程式檔名（不分大小寫，副檔名可省略）→ 情境模板
        self.auto_scenario_table = QTableWidget(0, 2)
        self.auto_scenario_table.setHorizontalHeaderLabels(["程式檔名 (如 outlook.exe)", "情境模板"])
        self.auto_scenario_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        self.auto_scenario_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        self.auto_scenario_table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.auto_scenario_table.setStyleSheet(
            "background: rgba(20,20,30,150); border: 1px solid rgba(255,255,255,10); border-radius: 8px; color: #eee;"
        )
        self.auto_scenario_table.setMinimumHeight(140)
        layout.addWidget(self.auto_scenario_table)

        btn_row = QHBoxLayout()

        btn_add_rule = QPushButton("➕ 新增規則列")
        btn_add_rule.setStyleSheet("background: #2e7d32; color: white; padding: 5px; border-radius: 4px;")
        btn_add_rule.clicked.connect(lambda: self._add_auto_scenario_rule_row())
        btn_row.addWidget(btn_add_rule)

        btn_del_rule = QPushButton("🗑 刪除所選列")
        btn_del_rule.setStyleSheet("background: #c62828; color: white; padding: 5px; border-radius: 4px;")
        btn_del_rule.clicked.connect(self._remove_selected_auto_scenario_rule)
        btn_row.addWidget(btn_del_rule)

        btn_detect = QPushButton("🔍 偵測目前前景程式 (3 秒倒數)")
        btn_detect.setToolTip("按下後請立刻切換到你要偵測的目標視窗，3 秒後會抓取當時的前景程式並新增一列規則")
        btn_detect.clicked.connect(self._detect_foreground_app_for_rule)
        self.auto_scenario_detect_btn = btn_detect
        btn_row.addWidget(btn_detect)

        btn_row.addStretch()
        layout.addLayout(btn_row)

        # 首次載入延後填充，避免建構期間就觸發資料存取
        QTimer.singleShot(100, self._populate_auto_scenario_rules_table)

        return section

    def _available_scenario_names(self):
        """情境模板下拉選單的選項清單：'default'（基底靈魂/預設）+ SOUL_SCENARIO_DIR
        底下所有 *.md 檔案的檔名主體，與 ui/menu_bar.py 的手動選單邏輯一致。"""
        names = ["default"]
        if SOUL_SCENARIO_DIR.exists():
            names += sorted(f.stem for f in SOUL_SCENARIO_DIR.glob("*.md") if f.stem != "default")
        return names

    def _make_scenario_combo(self, current_value="default"):
        combo = QComboBox()
        options = self._available_scenario_names()
        if current_value and current_value not in options:
            options.append(current_value)  # 保留使用者既有設定，即使該情境檔已被刪除
        combo.addItems(options)
        idx = combo.findText(current_value or "default")
        if idx >= 0:
            combo.setCurrentIndex(idx)
        return combo

    def _add_auto_scenario_rule_row(self, process_name="", scenario="default"):
        row = self.auto_scenario_table.rowCount()
        self.auto_scenario_table.insertRow(row)
        self.auto_scenario_table.setItem(row, 0, QTableWidgetItem(process_name))
        self.auto_scenario_table.setCellWidget(row, 1, self._make_scenario_combo(scenario))
        return row

    def _remove_selected_auto_scenario_rule(self):
        rows = sorted({idx.row() for idx in self.auto_scenario_table.selectedIndexes()}, reverse=True)
        for row in rows:
            self.auto_scenario_table.removeRow(row)

    def _populate_auto_scenario_rules_table(self):
        self.auto_scenario_table.setRowCount(0)
        rules = self.config.get("auto_scenario_rules", {}) or {}
        for process_name, scenario in rules.items():
            self._add_auto_scenario_rule_row(process_name, scenario)

    def _collect_auto_scenario_rules(self) -> dict:
        """從表格讀出目前的規則（存檔用）：略過程式檔名空白的列。"""
        rules = {}
        for row in range(self.auto_scenario_table.rowCount()):
            name_item = self.auto_scenario_table.item(row, 0)
            name = name_item.text().strip() if name_item else ""
            if not name:
                continue
            combo = self.auto_scenario_table.cellWidget(row, 1)
            scenario = combo.currentText() if combo else "default"
            rules[name] = scenario
        return rules

    def _detect_foreground_app_for_rule(self):
        """按下當下前景視窗就是本設定視窗本身，偵測不到使用者實際想設定的目標
        程式——這裡用 3 秒倒數（QProgressDialog，比照既有麥克風測試按鈕的
        使用者體驗），提示使用者先切到目標視窗，倒數結束後才真正抓取前景程式，
        並直接新增一列規則（情境先預設為 default，使用者自行從下拉選正確的）。"""
        active_timer = getattr(self, "_foreground_detection_timer", None)
        if active_timer is not None and active_timer.isActive():
            return

        progress = QProgressDialog("請立刻切換到你要偵測的目標視窗...", None, 0, 3, self)
        progress.setWindowTitle("偵測前景程式")
        progress.setWindowModality(Qt.WindowModality.WindowModal)
        progress.setMinimumDuration(0)
        progress.setAutoClose(False)
        progress.setValue(0)
        progress.setLabelText("請切換到目標視窗... 3 秒後偵測")
        progress.show()

        self._foreground_detection_progress = progress
        self._foreground_detection_remaining = 3
        self.auto_scenario_detect_btn.setEnabled(False)

        timer = QTimer(self)
        timer.setInterval(1000)
        timer.timeout.connect(self._advance_foreground_detection)
        self._foreground_detection_timer = timer
        timer.start()

    def _advance_foreground_detection(self):
        """非阻塞倒數；Qt event loop 保持可用，使用者才能真的切到目標視窗。"""
        progress = getattr(self, "_foreground_detection_progress", None)
        if progress is None:
            return

        self._foreground_detection_remaining -= 1
        remaining = self._foreground_detection_remaining
        if remaining > 0:
            progress.setValue(3 - remaining)
            progress.setLabelText(f"請切換到目標視窗... {remaining} 秒後偵測")
            return

        self._finish_foreground_detection()

    def _finish_foreground_detection(self):
        from utils.foreground import get_foreground_process_name

        timer = getattr(self, "_foreground_detection_timer", None)
        if timer is not None:
            timer.stop()

        # 必須先抓取前景程式再關閉 progress。Windows 關閉 modal dialog 時可能
        # 把父 Settings 視窗重新帶到前景，反過來就只會抓到 pythonw.exe。
        proc_name = get_foreground_process_name()
        progress = getattr(self, "_foreground_detection_progress", None)
        if progress is not None:
            progress.setValue(3)
            progress.close()
        self.auto_scenario_detect_btn.setEnabled(True)
        self._foreground_detection_timer = None
        self._foreground_detection_progress = None

        if not proc_name:
            QMessageBox.warning(
                self, "偵測失敗",
                "無法取得前景程式名稱（可能不是 Windows 環境，或該視窗權限受限）。\n請手動輸入程式檔名。",
            )
            self._add_auto_scenario_rule_row("", "default")
            return

        row = self._add_auto_scenario_rule_row(proc_name, "default")
        self.auto_scenario_table.selectRow(row)
        QMessageBox.information(
            self, "偵測成功",
            f"偵測到前景程式：{proc_name}\n已新增一列規則，請從下拉選單選擇要套用的情境模板。",
        )

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
