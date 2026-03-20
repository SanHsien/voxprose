"""
SkinManager — 讀取 skin 描述檔並生成全域 QSS。
新增 skin：在 ui/skins/ 放置 Python 檔，並在 AVAILABLE_SKINS 登記。
"""

AVAILABLE_SKINS: dict[str, str] = {
    "titanium": "Titanium",
    "classic_dark": "Classic Dark",
}


class SkinManager:
    _current_skin: dict = None
    _current_name: str = "titanium"

    @classmethod
    def load(cls, skin_name: str) -> dict:
        try:
            if skin_name == "titanium":
                from ui.skins.titanium import SKIN
            elif skin_name == "classic_dark":
                from ui.skins.classic_dark import SKIN
            else:
                from ui.skins.classic_dark import SKIN
            cls._current_skin = SKIN
            cls._current_name = skin_name
        except ImportError:
            from ui.skins.classic_dark import SKIN
            cls._current_skin = SKIN
            cls._current_name = "classic_dark"
        return cls._current_skin

    @classmethod
    def current(cls) -> dict:
        if cls._current_skin is None:
            cls.load(cls._current_name)
        return cls._current_skin

    @classmethod
    def build_qss(cls, font_family: str = "PingFang TC") -> str:
        s = cls.current()
        return f"""
QMainWindow {{
    background-color: {s['bg_window']};
}}
QWidget#sidebar_container {{
    background-color: {s['bg_sidebar']};
}}
QStackedWidget {{
    background-color: {s['bg_window']};
}}
QLabel {{
    color: {s['text_primary']};
    font-family: '{font_family}';
}}
QLineEdit, QComboBox, QTextEdit, QListWidget, QTreeWidget {{
    font-family: '{font_family}';
    background-color: {s['bg_input']};
    border: 1px solid {s['bg_input_border']};
    border-radius: {s['input_radius']};
    color: {s['text_primary']};
    padding: 8px;
    selection-background-color: {s['selection_bg']};
}}
QAbstractItemView {{
    background-color: {s['bg_input']};
    color: {s['text_primary']};
    border: 1px solid {s['bg_input_border']};
    selection-background-color: {s['selection_bg']};
    outline: none;
}}
QTreeWidget::item {{ padding: 4px; }}
QHeaderView::section {{
    background-color: {s['bg_input']};
    color: {s['text_secondary']};
    padding: 6px;
    border: none;
    font-weight: bold;
}}
QPushButton {{
    background-color: {s['accent']};
    color: {s['btn_text']};
    border-radius: {s['button_radius']};
    padding: 10px 20px;
    font-weight: bold;
    border: none;
}}
QPushButton:hover {{ background-color: {s['accent_hover']}; }}
QPushButton#secondary {{
    background-color: {s['btn_secondary_bg']};
    color: {s['text_primary']};
}}
QPushButton#danger {{
    background-color: transparent;
    border: 1px solid {s['bg_input_border']};
    color: {s['danger']};
}}
QPushButton#danger:hover {{
    background-color: {s['bg_input_border']};
    color: {s['danger']};
}}
SidebarButton {{
    background: transparent;
    border: none;
    color: {s['text_secondary']};
    text-align: left;
    padding-left: 20px;
    border-radius: 10px;
}}
SidebarButton:hover {{
    background: rgba(255, 255, 255, 8);
    color: {s['text_primary']};
}}
SidebarButton:checked {{
    background-color: {s['sidebar_selected_bg']};
    color: {s['sidebar_selected_text']};
    font-weight: bold;
    border-left: 2px solid {s['sidebar_selected_text']};
}}
GlassCard {{
    background-color: {s['bg_card']};
    border: 1px solid {s['card_border']};
    border-radius: {s['card_radius']};
}}
QScrollArea {{ border: none; background: transparent; }}
QScrollBar:vertical {{
    border: none;
    background: transparent;
    width: 6px;
}}
QScrollBar::handle:vertical {{
    background: {s['scrollbar']};
    border-radius: 3px;
    min-height: 20px;
}}
QCheckBox {{ color: {s['text_primary']}; spacing: 10px; }}
QCheckBox::indicator {{ width: 18px; height: 18px; }}
{s.get('qss_extra', '')}
"""
