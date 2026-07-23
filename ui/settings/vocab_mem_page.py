"""詞彙 & 記憶頁 mixin — split out of ui/settings_window.py (REVIEW.md #7).

Verbatim relocation of `_create_vocab_mem_page` and the vocab/learned-word/
long-term-memory refresh & mutation methods it depends on. No logic changes.
"""
import logging

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QPushButton,
    QListWidget, QTreeWidget, QTreeWidgetItem, QSplitter, QCheckBox, QMessageBox,
)
from PyQt6.QtCore import Qt

log = logging.getLogger("voicetype.ui")


class VocabMemPageMixin:
    def _create_vocab_mem_page(self):
        page = QWidget()
        layout = QVBoxLayout(page)

        splitter = QSplitter(Qt.Orientation.Horizontal)
        layout.addWidget(splitter)

        # Left: Vocab
        v_box = QWidget()
        v_layout = QVBoxLayout(v_box)
        v_layout.addWidget(QLabel("✏️ 私人詞庫"))
        self.vocab_list = QListWidget()
        v_layout.addWidget(self.vocab_list)

        vh = QHBoxLayout()
        self.vocab_input = QLineEdit()
        self.vocab_input.setPlaceholderText("新增...")
        self.btn_add_vocab = QPushButton("+")
        self.btn_add_vocab.setFixedWidth(50)
        self.btn_add_vocab.clicked.connect(self._add_vocab)
        vh.addWidget(self.vocab_input)
        vh.addWidget(self.btn_add_vocab)
        v_layout.addLayout(vh)

        self.btn_del_vocab = QPushButton("刪除已選")
        self.btn_del_vocab.setObjectName("danger")
        self.btn_del_vocab.clicked.connect(self._del_vocab)
        v_layout.addWidget(self.btn_del_vocab)

        # Right: Learned & Memory
        right_box = QWidget()
        rl = QVBoxLayout(right_box)

        rl.addWidget(QLabel("💡 AI 學習清單"))
        self.learned_list = QListWidget()
        rl.addWidget(self.learned_list)
        lh = QHBoxLayout()
        self.btn_promote = QPushButton("升格自訂")
        self.btn_promote.clicked.connect(self._promote_vocab)
        lh.addWidget(self.btn_promote)
        self.btn_delete_learned = QPushButton("刪除")
        self.btn_delete_learned.setObjectName("danger")
        self.btn_delete_learned.setMinimumHeight(40)  # 32px 會把中文字上下裁切
        self.btn_delete_learned.clicked.connect(self._delete_learned_word)
        lh.addWidget(self.btn_delete_learned)
        rl.addLayout(lh)

        rl.addWidget(QLabel("🧠 長期記憶"))
        self.mem_tree = QTreeWidget()
        self.mem_tree.setHeaderLabels(["時間", "快照"])
        rl.addWidget(self.mem_tree)

        mem_ctrl_row = QHBoxLayout()
        self.memory_inject_cb = QCheckBox("注入 LLM 記憶")
        self.memory_inject_cb.setChecked(False)
        mem_ctrl_row.addWidget(self.memory_inject_cb)
        mem_ctrl_row.addStretch()
        self.btn_del_memory = QPushButton("刪除選取")
        self.btn_del_memory.setObjectName("danger")
        self.btn_del_memory.setMinimumHeight(40)
        self.btn_del_memory.clicked.connect(self._delete_memory_entry)
        mem_ctrl_row.addWidget(self.btn_del_memory)
        self.btn_purge_memory = QPushButton("壓縮本週記憶")
        self.btn_purge_memory.setObjectName("danger")
        self.btn_purge_memory.setMinimumHeight(40)
        self.btn_purge_memory.clicked.connect(self._purge_memory)
        mem_ctrl_row.addWidget(self.btn_purge_memory)
        rl.addLayout(mem_ctrl_row)

        splitter.addWidget(v_box)
        splitter.addWidget(right_box)
        return page

    def _refresh_vocab(self):
        self.vocab_list.clear()
        try:
            from vocab.manager import load_custom_vocab
            for word in load_custom_vocab():
                self.vocab_list.addItem(word)
        except Exception as e:
            # 2026-07-23（broad except 清查）：詞庫清單原本靜默失敗，畫面「無聲
            # 空白」卻查不到原因——這正是本專案過去「引擎自始壞掉」的同類風險。
            log.warning(f"[settings] Failed to refresh vocab list: {e}")

    def _refresh_learned_vocab(self):
        self.learned_list.clear()
        self.dashboard_vocab.clear()
        try:
            from vocab.manager import load_all_learned_words, load_auto_memory
            memory = load_auto_memory()
            words = load_all_learned_words()
            for word in words:
                count = memory.get(word, 0)
                self.learned_list.addItem(f"{word} ({count})")
            # Dashboard only show top 5
            for word in words[:5]:
                self.dashboard_vocab.addItem(word)
        except Exception as e:
            log.warning(f"[settings] Failed to refresh learned vocab list: {e}")

    def _promote_vocab(self):
        item = self.learned_list.currentItem()
        if not item: return
        word = item.text().split(" (")[0]
        try:
            from vocab.manager import promote_learned_word
            promote_learned_word(word)
            self._refresh_vocab()
            self._refresh_learned_vocab()
        except Exception as e:
            QMessageBox.critical(self, "錯誤", str(e))

    def _delete_learned_word(self):
        item = self.learned_list.currentItem()
        if not item: return
        word = item.text().split(" (")[0]
        try:
            from vocab.manager import remove_learned_word
            remove_learned_word(word)
            self._refresh_learned_vocab()
        except Exception as e:
            QMessageBox.critical(self, "錯誤", str(e))

    def _refresh_memory(self):
        self.mem_tree.clear()
        try:
            from memory.manager import load_memory
            memory = load_memory()
            summary = memory.get("summary", "")
            if summary:
                item = QTreeWidgetItem(["[摘要]", summary[:60] + "..."])
                item.setData(0, Qt.ItemDataRole.UserRole, "__summary__")
                self.mem_tree.addTopLevelItem(item)
            for entry in reversed(memory.get("entries", [])):
                ts = entry.get("ts", "")
                text = (entry.get("llm") or entry.get("stt", ""))[:40]
                item = QTreeWidgetItem([ts[:16], text + "..."])
                item.setData(0, Qt.ItemDataRole.UserRole, ts)  # 完整 ts 作為刪除 key
                self.mem_tree.addTopLevelItem(item)
        except Exception as e:
            log.warning(f"[settings] Failed to refresh memory list: {e}")

    def _delete_memory_entry(self):
        item = self.mem_tree.currentItem()
        if not item:
            QMessageBox.information(self, "聲成文", "請先在長期記憶清單中選取一筆記錄。")
            return
        key = item.data(0, Qt.ItemDataRole.UserRole)
        if key == "__summary__":
            reply = QMessageBox.question(
                self, "確認刪除", "確定要清除長期記憶摘要嗎？（歸檔備份不受影響）",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
            if reply == QMessageBox.StandardButton.Yes:
                from memory.manager import clear_summary
                clear_summary()
                self._refresh_memory()
            return
        reply = QMessageBox.question(
            self, "確認刪除", f"確定要刪除「{item.text(1)}」這筆記憶嗎？",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        if reply == QMessageBox.StandardButton.Yes:
            from memory.manager import delete_entry
            delete_entry(key)
            self._refresh_memory()

    def _purge_memory(self):
        from memory.manager import load_memory
        count = len(load_memory().get("entries", []))
        if count == 0:
            QMessageBox.information(self, "記憶壓縮", "目前沒有可壓縮的記憶條目。")
            return
        reply = QMessageBox.question(
            self, "確認壓縮記憶",
            f"將 {count} 筆原始記錄壓縮為摘要，原始資料將歸檔保留。確定？",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.Cancel
        )
        if reply != QMessageBox.StandardButton.Yes:
            return
        try:
            from memory.manager import purge_and_summarize
            purged = purge_and_summarize()
            self._refresh_memory()
            QMessageBox.information(self, "壓縮完成", f"已壓縮 {purged} 筆記錄，摘要已更新。")
        except Exception as e:
            QMessageBox.critical(self, "錯誤", str(e))

    def _add_vocab(self):
        word = self.vocab_input.text().strip()
        if not word: return
        from vocab.manager import add_custom_word
        add_custom_word(word)
        self.vocab_input.clear()
        self._refresh_vocab()

    def _del_vocab(self):
        item = self.vocab_list.currentItem()
        if not item: return
        from vocab.manager import remove_custom_word
        remove_custom_word(item.text())
        self._refresh_vocab()
