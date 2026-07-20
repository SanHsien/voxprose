"""
Floating mic level indicator window.
Shows at the bottom-center of the screen (just above Dock).
Displays an animated waveform bar and current state text.
"""
import sys
import os
import threading
from PyQt6.QtWidgets import QApplication, QWidget
from PyQt6.QtCore import Qt, QTimer, pyqtSignal, QObject, QUrl
from PyQt6.QtGui import QPainter, QColor, QPen, QFont, QFontMetrics, QCursor, QGuiApplication
from PyQt6.QtMultimedia import QSoundEffect
from utils.resources import get_resource_path


class _Signals(QObject):
    update_level = pyqtSignal(float)
    set_state = pyqtSignal(str)
    play_beep = pyqtSignal()
    set_prefix = pyqtSignal(str)
    set_label_suffix = pyqtSignal(str)
    show_window = pyqtSignal()
    hide_window = pyqtSignal()
    show_settings = pyqtSignal()
    flash = pyqtSignal()


class MicIndicatorWindow(QWidget):
    STATE_COLORS = {
        "recording": QColor(255, 80, 80),      # red
        "ai_recording": QColor(0, 220, 255),   # cyan/blue for AI modes
        "processing": QColor(255, 200, 50),    # yellow
        "done": QColor(80, 200, 120),          # green
        "loading": QColor(0, 122, 255),       # blue
        "error": QColor(255, 50, 50),          # bright red for errors
    }

    def __init__(self):
        super().__init__()
        self._level = 0.0
        self._state = "recording"
        self._prefix = ""  # 例如 "AI", "譯:日文"
        self._label_suffix = ""  # 例如 "(翻譯中: 英文)"
        self._bars = [0.0] * 20  # rolling bar history
        self._flash_active = False
        self._drag_pos = None
        self._is_dragging = False
        self._setup_window()
        
        # 音效器
        self._beep = QSoundEffect(self)
        from PyQt6.QtCore import QUrl
        beep_path = get_resource_path("assets/beep.wav")
        if os.path.exists(beep_path):
            self._beep.setSource(QUrl.fromLocalFile(beep_path))
            self._beep.setVolume(0.5)

        self._timer = QTimer(self)
        self._timer.timeout.connect(self._tick)
        self._timer.start(50)  # 20fps

    def _setup_window(self):
        import platform
        flags = (Qt.WindowType.FramelessWindowHint 
                 | Qt.WindowType.WindowStaysOnTopHint 
                 | Qt.WindowType.WindowDoesNotAcceptFocus)
        if platform.system() == "Windows":
            flags |= Qt.WindowType.Tool
        else:
            flags |= Qt.WindowType.ToolTip
            
        self.setWindowFlags(flags)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setAttribute(Qt.WidgetAttribute.WA_ShowWithoutActivating)
        self.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.setFixedSize(180, 32)
        self._reposition()

    def _reposition(self):
        # Detect which screen the cursor is currently on
        cursor_pos = QCursor.pos()
        screen_obj = QGuiApplication.screenAt(cursor_pos)

        # Fallback to primary screen if not found
        if not screen_obj:
            screen_obj = QGuiApplication.primaryScreen()

        if not screen_obj:
            return

        available = screen_obj.availableGeometry()

        # 位置記憶：若使用者曾在這個螢幕拖曳過 Indicator，回到偏好停靠位置
        from ui.positions import get_position, clamp_into
        saved = get_position("indicator", screen_obj.name())
        if saved:
            x, y = clamp_into(available, available.x() + saved[0],
                              available.y() + saved[1], self.width(), self.height())
            self.move(x, y)
            return

        x = available.x() + (available.width() - self.width()) // 2
        y = available.y() + available.height() - self.height() - 10
        self.move(x, y)

    # ── 拖曳與位置記憶 ──
    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self._drag_pos = event.globalPosition().toPoint()
            self._is_dragging = False

    def mouseMoveEvent(self, event):
        if event.buttons() & Qt.MouseButton.LeftButton and self._drag_pos:
            diff = event.globalPosition().toPoint() - self._drag_pos
            if diff.manhattanLength() > 5:
                self._is_dragging = True
            if self._is_dragging:
                self.move(self.pos() + diff)
                self._drag_pos = event.globalPosition().toPoint()

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            if self._is_dragging:
                self._save_position()
            self._drag_pos = None
            self._is_dragging = False

    def _save_position(self):
        screen_obj = QGuiApplication.screenAt(self.geometry().center())
        if not screen_obj:
            screen_obj = QGuiApplication.primaryScreen()
        if not screen_obj:
            return
        from ui.positions import save_position
        available = screen_obj.availableGeometry()
        save_position("indicator", screen_obj.name(),
                      self.x() - available.x(), self.y() - available.y())

    def _tick(self):
        self._bars = self._bars[1:] + [self._level]
        self.update()

    def set_level(self, level: float):
        self._level = max(0.0, min(1.0, level))

    def set_state(self, state: str):
        self._state = state
        if state == "done":
            self.trigger_flash()
            # "完成" 狀態多留一會兒
            QTimer.singleShot(1200, self.hide)
        elif state == "error":
            # 錯誤狀態留長一點，讓使用者看清楚
            QTimer.singleShot(3000, self.hide)
        self.update()

    def set_label_suffix(self, suffix: str):
        """設定額外的標籤文字，例如 '(翻譯中)'"""
        self._label_suffix = suffix
        self.update()

    def set_prefix(self, text: str):
        """設定左側顯示的前綴文字，例如 'AI' 或 '譯:日'"""
        self._prefix = text
        self.update()

    def trigger_flash(self):
        """閃爍一下背景以此作為回饋。"""
        self._flash_active = True
        self.update()
        QTimer.singleShot(500, self._stop_flash)
        
        # macOS/Windows 音效回饋
        import platform
        if platform.system() == "Darwin":
            import subprocess
            try:
                subprocess.Popen(["afplay", "/System/Library/Sounds/Glass.aiff"])
            except:
                pass
        elif platform.system() == "Windows":
            try:
                import winsound
                winsound.Beep(1000, 100)
            except:
                pass

    def _stop_flash(self):
        self._flash_active = False
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        # Background pill
        # 如果正在閃爍，使用亮藍色作為背景
        bg_color = QColor(0, 122, 255, 230) if self._flash_active else QColor(30, 30, 30, 210)
        painter.setBrush(bg_color)
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawRoundedRect(0, 0, self.width(), self.height(), self.height() // 2, self.height() // 2)

        # 內容配色
        text_base_color = QColor(255, 255, 255, 240) if self._flash_active else QColor(255, 255, 255, 200)
        prefix_color = QColor(255, 255, 255, 240) if self._flash_active else QColor(0, 122, 255, 220)
        wave_color = QColor(255, 255, 255, 240) if self._flash_active else self.STATE_COLORS.get(self._state, QColor(255, 80, 80))

        # ── 寬度計算與置中 ──
        import platform
        font_family = "PingFang TC" if platform.system() == "Darwin" else "Microsoft JhengHei"
        f_prefix = QFont(font_family, 8)
        f_prefix.setBold(True)
        f_label = QFont(font_family, 8)
        fm_prefix = QFontMetrics(f_prefix)
        fm_label = QFontMetrics(f_label)

        prefix_w = fm_prefix.horizontalAdvance(self._prefix) if self._prefix else 0
        prefix_gap = 8 if prefix_w > 0 else 0
        bar_w, gap = 3, 2
        total_bars = len(self._bars)
        bars_w = total_bars * (bar_w + gap) - gap
        label_map = {
            "recording": "錄音中...", 
            "ai_recording": "錄音中...", 
            "processing": "辨識中...", 
            "done": "完成", 
            "loading": "載入中...",
            "error": "錯誤"
        }
        label_text = label_map.get(self._state, "")
        if self._state not in ["done", "loading", "recording", "ai_recording"] and self._label_suffix:
            label_text += f" {self._label_suffix}"
            
        # 錯誤狀態時，如果有 suffix(例如 'Key 未填')，則優先顯示
        if self._state == "error" and self._label_suffix:
            label_text = f"錯誤: {self._label_suffix}"
            
        label_w = fm_label.horizontalAdvance(label_text)
        label_gap = 8 if label_w > 0 else 0
        total_content_w = prefix_w + prefix_gap + bars_w + label_gap + label_w
        start_x = (self.width() - total_content_w) // 2

        # ── 繪製內容 ──
        if self._prefix:
            painter.setPen(prefix_color)
            painter.setFont(f_prefix)
            painter.drawText(start_x, 0, prefix_w, self.height(),
                             Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft, self._prefix)
            start_x += prefix_w + prefix_gap

        center_y = self.height() // 2
        max_bar_h = 18
        for i, val in enumerate(self._bars):
            h = max(2, int(val * max_bar_h))
            x = start_x + i * (bar_w + gap)
            y = center_y - h // 2
            painter.setBrush(wave_color)
            painter.drawRoundedRect(x, y, bar_w, h, 1, 1)
        start_x += bars_w + label_gap

        painter.setPen(text_base_color)
        painter.setFont(f_label)
        painter.drawText(start_x, 0, label_w + 10, self.height(),
                         Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft, label_text)


class MicIndicator:
    """Thread-safe wrapper around MicIndicatorWindow."""

    def __init__(self):
        self._app: QApplication | None = None
        self._window: MicIndicatorWindow | None = None
        self._signals = _Signals()
        self._ready = threading.Event()

    def start_app(self):
        if QApplication.instance() is None:
            self._app = QApplication(sys.argv)
        else:
            self._app = QApplication.instance()
            
        import platform
        from PyQt6.QtGui import QFont, QPalette, QColor
        
        # ── 強制深色調色盤 (Fusion Dark Palette) ──
        self._app.setStyle("Fusion")
        dark_palette = QPalette()
        dark_palette.setColor(QPalette.ColorGroup.All, QPalette.ColorRole.Window, QColor(25, 25, 30))
        dark_palette.setColor(QPalette.ColorGroup.All, QPalette.ColorRole.WindowText, QColor(226, 228, 231))
        dark_palette.setColor(QPalette.ColorGroup.All, QPalette.ColorRole.Base, QColor(20, 20, 25))
        dark_palette.setColor(QPalette.ColorGroup.All, QPalette.ColorRole.AlternateBase, QColor(25, 25, 30))
        dark_palette.setColor(QPalette.ColorGroup.All, QPalette.ColorRole.ToolTipBase, Qt.GlobalColor.white)
        dark_palette.setColor(QPalette.ColorGroup.All, QPalette.ColorRole.ToolTipText, Qt.GlobalColor.white)
        dark_palette.setColor(QPalette.ColorGroup.All, QPalette.ColorRole.Text, QColor(226, 228, 231))
        dark_palette.setColor(QPalette.ColorGroup.All, QPalette.ColorRole.Button, QColor(25, 25, 30))
        dark_palette.setColor(QPalette.ColorGroup.All, QPalette.ColorRole.ButtonText, QColor(226, 228, 231))
        dark_palette.setColor(QPalette.ColorGroup.All, QPalette.ColorRole.BrightText, Qt.GlobalColor.red)
        dark_palette.setColor(QPalette.ColorGroup.All, QPalette.ColorRole.Link, QColor(124, 77, 255))
        dark_palette.setColor(QPalette.ColorGroup.All, QPalette.ColorRole.Highlight, QColor(124, 77, 255))
        dark_palette.setColor(QPalette.ColorGroup.All, QPalette.ColorRole.HighlightedText, Qt.GlobalColor.white)
        
        # 針對 Disable 狀態微調
        dark_palette.setColor(QPalette.ColorGroup.Disabled, QPalette.ColorRole.Text, Qt.GlobalColor.darkGray)
        dark_palette.setColor(QPalette.ColorGroup.Disabled, QPalette.ColorRole.ButtonText, Qt.GlobalColor.darkGray)
        
        self._app.setPalette(dark_palette)

        if platform.system() == "Windows":
            self._app.setFont(QFont("Microsoft JhengHei", 10))
            
        self._window = MicIndicatorWindow()
        def on_show():
            self._window._reposition()
            self._window.show()
        self._signals.update_level.connect(self._window.set_level)
        self._signals.set_state.connect(self._window.set_state)
        self._signals.set_prefix.connect(self._window.set_prefix)
        self._signals.set_label_suffix.connect(self._window.set_label_suffix)
        self._signals.show_window.connect(on_show)
        self._signals.hide_window.connect(self._window.hide)
        self._signals.flash.connect(self._window.trigger_flash)
        self._signals.play_beep.connect(self._window._beep.play)
        # 設置視窗回調由 VoiceTypeApp 連接
        self._ready.set()

    def show(self):
        self._ready.wait()
        self._signals.show_window.emit()

    def hide(self):
        self._ready.wait()
        self._signals.hide_window.emit()

    def show_settings(self):
        """Trigger showing the settings window from any thread."""
        self._ready.wait()
        self._signals.show_settings.emit()

    def flash(self):
        self._ready.wait()
        self._signals.flash.emit()

    def set_level(self, level: float):
        self._ready.wait()
        self._signals.update_level.emit(level)

    def set_state(self, state: str):
        self._ready.wait()
        self._signals.set_state.emit(state)

    def set_label_suffix(self, suffix: str):
        self._ready.wait()
        self._signals.set_label_suffix.emit(suffix)

    def set_prefix(self, text: str):
        self._ready.wait()
        self._signals.set_prefix.emit(text)

    def play_beep(self):
        self._ready.wait()
        self._signals.play_beep.emit()
