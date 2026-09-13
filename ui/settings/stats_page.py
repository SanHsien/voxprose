"""數據統計頁 mixin — split out of ui/settings_window.py (REVIEW.md #7).

Verbatim relocation of `_create_stats_page` and `_refresh_stats`. No logic
changes.
"""
import logging

from PyQt6.QtWidgets import QWidget, QVBoxLayout, QTreeWidget, QTreeWidgetItem, QPushButton

log = logging.getLogger("voicetype.ui")


class StatsPageMixin:
    def _create_stats_page(self):
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.addWidget(self._page_section_header("詳細分析數據"))

        self.stats_tree = QTreeWidget()
        self.stats_tree.setHeaderLabels(["範圍", "對話數", "語音長度", "轉錄字數", "省下時間"])
        layout.addWidget(self.stats_tree)

        self.btn_refresh_stats = QPushButton("重新整理數據")
        self.btn_refresh_stats.setObjectName("secondary")
        self.btn_refresh_stats.clicked.connect(self._refresh_stats)
        layout.addWidget(self.btn_refresh_stats)

        layout.addStretch()
        return page

    def _refresh_stats(self):
        self.stats_tree.clear()
        try:
            from stats.tracker import get_summary
            s = get_summary()
            self.lbl_today_count.setText(f"{s['today']['sessions']} 次錄音")
            self.lbl_today_chars.setText(f"錄製約 {s['today']['chars']} 字")

            # 計算省下時間 (以一般人打字速度 40字/分 計算)
            total_chars = s['total']['chars']
            saved_mins = total_chars / 40.0
            if saved_mins < 60:
                self.lbl_time_saved.setText(f"{saved_mins:.1f} 分鐘")
            else:
                self.lbl_time_saved.setText(f"{saved_mins/60.0:.1f} 小時")
            self.lbl_total_chars_desc.setText(f"累計辨識 {total_chars} 字")

            def format_saved(chars):
                mins = chars / 40.0
                if mins < 60: return f"{mins:.1f}m"
                return f"{mins/60.0:.1f}h"

            self.stats_tree.addTopLevelItem(QTreeWidgetItem([
                "今日", str(s["today"]["sessions"]), f"{s['today']['duration']}s", str(s["today"]["chars"]), format_saved(s["today"]["chars"])
            ]))
            self.stats_tree.addTopLevelItem(QTreeWidgetItem([
                "本週", str(s["week"]["sessions"]), f"{s['week']['duration']}s", str(s["week"]["chars"]), format_saved(s["week"]["chars"])
            ]))
            self.stats_tree.addTopLevelItem(QTreeWidgetItem([
                "累積", str(s["total"]["sessions"]), f"{s['total']['duration']}s", str(s["total"]["chars"]), format_saved(s["total"]["chars"])
            ]))
        except Exception as e:
            log.warning(f"[settings] Failed to refresh stats display: {e}")
