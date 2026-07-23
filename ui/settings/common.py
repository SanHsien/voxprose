"""Shared constants and small widget helpers used across the ui/settings/
page mixins (REVIEW.md #7 god-file split of ui/settings_window.py).

Everything in this file is a verbatim, unmodified relocation of code that
used to live at module scope in ui/settings_window.py — no logic, no
strings, and no behavior were changed during the split (see AGENTS.md
"開發約定" and docs/DECISIONS.md for the split's mapping table).
"""
import logging
import platform

from PyQt6.QtWidgets import QFrame, QHBoxLayout, QVBoxLayout, QWidget, QLabel, QPushButton
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QFont

log = logging.getLogger("voicetype.ui")
STT_ENGINES = ["local_whisper", "groq", "gemini", "openrouter"]
LLM_ENGINES = ["ollama", "openai", "claude", "openrouter", "gemini", "deepseek", "qwen"]
WHISPER_MODELS = ["tiny", "base", "small", "medium", "large"]
TRIGGER_MODES = ["push_to_talk", "toggle"]
HOTKEYS = ["right_option", "left_option", "right_ctrl", "f13", "f14", "f15"]
LLM_MODES = ["replace", "fast"]

from hotkey.listener import key_to_str, str_to_key


class GlassCard(QFrame):
    """A premium looking card with subtle border and background."""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setStyleSheet("""
            GlassCard {
                background-color: rgba(45, 45, 55, 180);
                border: 1px solid rgba(255, 255, 255, 30);
                border-radius: 12px;
            }
        """)

class SidebarButton(QPushButton):
    def __init__(self, icon_text, label, index, on_click, parent=None):
        super().__init__(parent)
        self.index = index
        self.setCheckable(True)
        import platform
        font_family = "Taipei Sans TC Beta" if platform.system() == "Darwin" else "Microsoft JhengHei"
        self.setText(f"{icon_text}  {label}")
        self.setFont(QFont(font_family, 16, QFont.Weight.Medium))

        self.setFixedHeight(60)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.clicked.connect(lambda: on_click(self.index))
        self.setStyleSheet("""
            QPushButton {
                background: transparent;
                border: none;
                color: #8a8d91;
                text-align: left;
                padding-left: 20px;
                border-radius: 12px;
            }
            QPushButton:hover {
                background: rgba(255, 255, 255, 10);
            }
            QPushButton:checked {
                background-color: #252a33;
                color: #7c4dff;
                font-weight: bold;
            }
        """)

CODE_TO_MAC_NAME = {
    61: "alt_r (Option右)",
    62: "ctrl_r (Control右)",
    60: "shift_r (Shift右)",
    54: "cmd_r (Command右)",
    55: "cmd (Command左)",
    56: "shift (Shift左)",
    59: "ctrl (Control左)",
    58: "alt (Option左)",
    63: "fn",
    116: "page_up",
    121: "page_down",
    115: "home",
    119: "end",
    117: "delete",
    114: "insert",
    123: "left",
    124: "right",
    125: "down",
    126: "up",
    53: "esc",
    105: "f13",
    107: "f14",
    113: "f15",
    106: "f16"
}

CODE_TO_WIN_NAME = {
    16: "shift",
    160: "shift_l (Shift 左)",
    161: "shift_r (Shift 右)",
    17: "ctrl",
    162: "ctrl_l (Ctrl 左)",
    163: "ctrl_r (Ctrl 右)",
    18: "alt",
    164: "alt_l (Alt 左)",
    165: "alt_r (Alt 右)",
    91: "win (Win左)",
    92: "win (Win右)",
    32: "space",
    13: "enter",
    27: "esc",
    20: "caps_lock",
    9: "tab",
    8: "backspace",
    46: "delete",
    33: "page_up",
    34: "page_down",
    35: "end",
    36: "home",
    37: "left",
    38: "up",
    39: "right",
    40: "down",
    45: "insert"
}

def translate_key_string(key_str):
    import re
    if not key_str:
        return "未設定"

    match = re.search(r'\(?code:(\d+)\)?', key_str, re.IGNORECASE)
    if not match:
        return key_str # fallback to literal if no code is present

    code = int(match.group(1))

    if platform.system() == "Windows":
        main_name = CODE_TO_WIN_NAME.get(code, f"Key {code}")
    else:
        main_name = CODE_TO_MAC_NAME.get(code, f"Key_{code}")

    parts = key_str.replace(f"(code:{code})", "").replace(f"code:{code}", "").split("+")
    mods = [p.strip() for p in parts if p.strip()]

    if mods:
        return f"{'+'.join(mods)} + {main_name}"
    return main_name

class HotkeyRecorderButton(QPushButton):
    """A button that captures the next key press to set a hotkey."""
    key_changed = pyqtSignal(str)

    def __init__(self, current_key_str, is_dark=True):
        super().__init__()
        self._key_str = current_key_str
        self._recording = False
        self._is_dark = is_dark
        self._update_text()
        self.clicked.connect(self._start_recording)
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        self.setMinimumHeight(32)

    @property
    def key_str(self):
        return self._key_str

    @key_str.setter
    def key_str(self, val):
        self._key_str = val
        self._update_text()

    def set_key(self, key_str):
        self.key_str = key_str

    def _update_text(self):
        if self._recording:
            self.setText("錄製中...")
            self.setStyleSheet("background: palette(highlight); color: white; border-radius: 6px;")
        else:
            display_text = translate_key_string(self._key_str) if self._key_str else "未設定"
            self.setText(display_text)
            self.setStyleSheet("""
                QPushButton {
                    background: rgba(255, 255, 255, 10);
                    border: 1px solid rgba(255, 255, 255, 20);
                    color: #ddd;
                    border-radius: 6px;
                    padding-left: 10px;
                    text-align: left;
                }
                QPushButton:hover {
                    background: rgba(255, 255, 255, 15);
                }
            """)

    def _start_recording(self):
        self._recording = True
        self._update_text()
        self.setFocus()

    def keyPressEvent(self, event):
        if not self._recording:
            super().keyPressEvent(event)
            return

        try:
            key = event.key()
            modifiers = event.modifiers()
            native_code = event.nativeVirtualKey()

            # v2.8.27_V13: Request exact Left/Right modifier Virtual Keycode natively
            if platform.system() == "Windows":
                import ctypes
                user32 = ctypes.windll.user32
                if native_code == 18:
                    if user32.GetAsyncKeyState(164) & 0x8000: native_code = 164
                    elif user32.GetAsyncKeyState(165) & 0x8000: native_code = 165
                elif native_code == 17:
                    if user32.GetAsyncKeyState(162) & 0x8000: native_code = 162
                    elif user32.GetAsyncKeyState(163) & 0x8000: native_code = 163
                elif native_code == 16:
                    if user32.GetAsyncKeyState(160) & 0x8000: native_code = 160
                    elif user32.GetAsyncKeyState(161) & 0x8000: native_code = 161

            log.info(f"[recorder] Captured QtKey={key}, NativeCode={native_code}")

            # Capture native modifiers for Fn key support
            try:
                native_mods = event.nativeModifiers()
                is_fn = bool(native_mods & 0x800000) # kCGEventFlagMaskSecondaryFn
            except Exception as e:
                log.debug(f"[recorder] Failed to read native modifiers (Fn key detection): {e}")
                is_fn = False

            # v2.8.17: Modifier-only hotkeys (e.g., single Right Ctrl, Right Cmd)
            # These are single-key modifier hotkeys that should record immediately
            SINGLE_MODIFIER_KEYS = {
                Qt.Key.Key_Control: "ctrl",
                Qt.Key.Key_Alt: "alt",
                Qt.Key.Key_Shift: "shift",
                Qt.Key.Key_Meta: "cmd",
                Qt.Key.Key_AltGr: "alt",
            }

            if key in SINGLE_MODIFIER_KEYS:
                # v2.8.24: Store purely as code:XX format
                self._key_str = f"code:{native_code}"
                self._recording = False
                self._update_text()
                self.key_changed.emit(self._key_str)
                self.clearFocus()
                log.info(f"[recorder] Recorded modifier key: {self._key_str}")
                return

            # For composite keys (e.g., Ctrl+A, Cmd+Shift+S)
            modifier_map = []
            if modifiers & Qt.KeyboardModifier.ControlModifier: modifier_map.append("ctrl")
            if modifiers & Qt.KeyboardModifier.AltModifier: modifier_map.append("alt")
            if modifiers & Qt.KeyboardModifier.ShiftModifier: modifier_map.append("shift")
            if modifiers & Qt.KeyboardModifier.MetaModifier: modifier_map.append("cmd")
            if is_fn: modifier_map.append("fn")

            # Use raw code for composite payload
            full_list = [m for m in modifier_map] + [f"code:{native_code}"]
            self._key_str = "+".join(full_list)

            self._recording = False
            self._update_text()
            self.key_changed.emit(self._key_str)
            self.clearFocus()
            log.info(f"[recorder] Recorded combo: {self._key_str}")
        except Exception as e:
            import traceback
            log.error(f"[recorder] Error in keyPressEvent: {e}\n{traceback.format_exc()}")
            self._recording = False
            self._update_text()
            self.clearFocus()
        else:
            pass  # keyAccepted


class PermissionLight(QWidget):
    def __init__(self, label_text, preference_url):
        super().__init__()
        self.url = preference_url
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 5, 0, 5)

        self.dot = QFrame()
        self.dot.setFixedSize(12, 12)
        self.dot.setStyleSheet("background-color: #555; border-radius: 6px;")
        layout.addWidget(self.dot)

        self.label = QLabel(label_text)
        win_font = "Microsoft JhengHei" if platform.system() == "Windows" else ""
        self.label.setStyleSheet(f"color: #e2e4e7; font-size: 14px; font-family: '{win_font}';")
        self.label.setWordWrap(True)
        layout.addWidget(self.label)


        layout.addStretch()

        self.fix_btn = QPushButton("設定")
        self.fix_btn.setFixedWidth(60)
        self.fix_btn.setStyleSheet("""
            QPushButton {
                background-color: #2d333d;
                color: #8a8d91;
                font-size: 11px;
                padding: 2px 5px;
            }
            QPushButton:hover { background-color: #3d4452; color: #fff; }
        """)
        self.fix_btn.clicked.connect(self._open_preference)
        layout.addWidget(self.fix_btn)

    def _open_preference(self):
        import subprocess
        if platform.system() == "Windows":
            import os
            os.startfile(self.url)
        else:
            subprocess.run(["open", self.url])

    def set_status(self, authorized: bool):
        color = "#00e676" if authorized else "#ff5252"
        self.dot.setStyleSheet(f"background-color: {color}; border-radius: 6px;")
        status_text = " (已授權)" if authorized else " (未授權)"
        # Note: We keep the original label text and just update the color dot
        self.fix_btn.setVisible(not authorized)



class ModelStatusLight(QWidget):
    def __init__(self, model_name, size_info, desc_text):
        super().__init__()
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 5, 0, 5)
        layout.setSpacing(2)

        top_layout = QHBoxLayout()
        self.dot = QFrame()
        self.dot.setFixedSize(10, 10)
        self.dot.setStyleSheet("background-color: #555; border-radius: 5px;")
        top_layout.addWidget(self.dot)

        self.label = QLabel(f"{model_name} ({size_info})")
        win_font = "Microsoft JhengHei" if platform.system() == "Windows" else ""
        self.label.setStyleSheet(f"color: #e2e4e7; font-size: 13px; font-weight: bold; font-family: '{win_font}';")
        top_layout.addWidget(self.label)

        top_layout.addStretch()
        layout.addLayout(top_layout)

        self.desc = QLabel(desc_text)
        win_font = "Microsoft JhengHei" if platform.system() == "Windows" else ""
        self.desc.setStyleSheet(f"color: #888; font-size: 11px; margin-left: 18px; font-family: '{win_font}';")
        self.desc.setWordWrap(True)

        layout.addWidget(self.desc)

    def set_status(self, downloaded: bool):
        # 綠色代表已就緒，灰色代表未下載
        color = "#00e676" if downloaded else "#444"
        self.dot.setStyleSheet(f"background-color: {color}; border-radius: 5px;")


class CommonPageMixin:
    """Small layout helpers shared by every `_create_*_page` method across
    the page mixins in this package. Mixed into SettingsWindow alongside the
    page mixins in ui/settings_window.py."""

    def _page_section_header(self, text):
        l = QLabel(text)
        l.setStyleSheet("font-weight: bold; font-size: 16px; color: #7c4dff; margin-top: 10px; margin-bottom: 5px;")
        return l

    def _add_grid_row(self, layout, label_text, widget):
        row = QHBoxLayout()
        l = QLabel(label_text)
        l.setFixedWidth(160)
        row.addWidget(l)
        row.addWidget(widget)
        layout.addLayout(row)
        return widget
