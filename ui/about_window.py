"""About dialog for 聲成文 VoxProse."""

import platform
import sys
from pathlib import Path

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont, QPixmap
from PyQt6.QtWidgets import (
    QApplication,
    QDialog,
    QFrame,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)


class AboutDialog(QDialog):
    def __init__(self, is_dark=False):
        super().__init__()
        self.setWindowTitle("關於 聲成文 VoxProse")
        self.setMinimumSize(620, 620)
        self.resize(680, 720)
        self._is_dark = is_dark
        self._setup_ui()

    def _setup_ui(self):
        bg_color = "#17191f" if self._is_dark else "#f7f8fb"
        panel_color = "#20232b" if self._is_dark else "#ffffff"
        text_color = "#f4f6fb" if self._is_dark else "#20232b"
        muted_color = "#aeb4c2" if self._is_dark else "#5f6673"
        border_color = "#343946" if self._is_dark else "#dfe3ea"
        font_family = (
            "PingFang TC" if platform.system() == "Darwin" else "Microsoft JhengHei"
        )

        self.setStyleSheet(
            f"""
            QDialog {{
                background-color: {bg_color};
                font-family: "{font_family}";
            }}
            QScrollArea, QWidget#aboutContent {{
                background-color: {bg_color};
                border: none;
            }}
            QFrame#creditsCard {{
                background-color: {panel_color};
                border: 1px solid {border_color};
                border-radius: 14px;
            }}
            QPushButton {{
                min-width: 120px;
                min-height: 40px;
                padding: 0 22px;
                border-radius: 8px;
                background: #6d4aff;
                color: white;
                font-size: 14px;
                font-weight: 700;
                border: none;
            }}
            QPushButton:hover {{ background: #7d61ff; }}
            QPushButton:pressed {{ background: #5938df; }}
            """
        )

        root_layout = QVBoxLayout(self)
        root_layout.setContentsMargins(0, 0, 0, 18)
        root_layout.setSpacing(8)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        content = QWidget()
        content.setObjectName("aboutContent")
        layout = QVBoxLayout(content)
        layout.setContentsMargins(48, 34, 48, 28)
        layout.setSpacing(14)

        icon_label = QLabel()
        icon_path = Path(__file__).parent.parent / "assets" / "icon.png"
        if icon_path.exists():
            pixmap = QPixmap(str(icon_path))
            icon_label.setPixmap(
                pixmap.scaled(
                    128,
                    128,
                    Qt.AspectRatioMode.KeepAspectRatio,
                    Qt.TransformationMode.SmoothTransformation,
                )
            )
        icon_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(icon_label)

        name_label = QLabel("聲成文 VoxProse")
        name_label.setFont(QFont(font_family, 24, QFont.Weight.Bold))
        name_label.setStyleSheet(f"color: {text_color};")
        name_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(name_label)

        tagline_label = QLabel(
            "在 Windows 上，把自然語音變成清楚文字。\n"
            "Local-first AI voice typing for Windows."
        )
        tagline_label.setWordWrap(True)
        tagline_label.setStyleSheet(
            f"color: {muted_color}; font-size: 14px; line-height: 1.5;"
        )
        tagline_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(tagline_label)

        from paths import VERSION_NAME

        version_label = QLabel(VERSION_NAME)
        version_label.setWordWrap(True)
        version_label.setStyleSheet(
            f"color: {muted_color}; font-size: 12px; padding: 6px 10px;"
        )
        version_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(version_label)

        credits_card = QFrame()
        credits_card.setObjectName("creditsCard")
        credits_layout = QVBoxLayout(credits_card)
        credits_layout.setContentsMargins(24, 20, 24, 20)
        credits_layout.setSpacing(10)

        credits_title = QLabel("開源與維護")
        credits_title.setFont(QFont(font_family, 15, QFont.Weight.Bold))
        credits_title.setStyleSheet(f"color: {text_color};")
        credits_layout.addWidget(credits_title)

        credits = QLabel(
            "本專案衍生自 VoiceType4TW，專注 Windows 10/11。\n\n"
            "原創作者：吉米丘（Jimmy Chiu）、CC58TW\n"
            "上游 Windows 專用版維護：go-mask\n"
            "聲成文 VoxProse 維護：SanHsien\n"
            "AI 開發協作：Claude Code、OpenAI Codex\n\n"
            "授權：MIT（完整聲明見 LICENSE 與 NOTICE.md）"
        )
        credits.setWordWrap(True)
        credits.setTextFormat(Qt.TextFormat.PlainText)
        credits.setStyleSheet(
            f"color: {muted_color}; font-size: 13px; line-height: 1.55;"
        )
        credits_layout.addWidget(credits)
        layout.addWidget(credits_card)
        layout.addStretch()

        scroll.setWidget(content)
        root_layout.addWidget(scroll, 1)

        btn_close = QPushButton("關閉")
        btn_close.clicked.connect(self.accept)
        footer = QHBoxLayout()
        footer.addStretch()
        footer.addWidget(btn_close)
        footer.addStretch()
        root_layout.addLayout(footer)


if __name__ == "__main__":
    app = QApplication(sys.argv)
    dialog = AboutDialog(is_dark=True)
    dialog.show()
    sys.exit(app.exec())
