import sys
import platform
from PyQt6.QtWidgets import QWidget
from PyQt6.QtCore import Qt, pyqtSignal, QPoint
from PyQt6.QtGui import QPainter, QColor, QPixmap, QGuiApplication

class FloatingButton(QWidget):
    clicked = pyqtSignal()
    
    def __init__(self, icon_path):
        super().__init__()
        self._icon_path = icon_path
        self._drag_pos = None
        self._is_dragging = False
        self._setup_window()
        
    def _setup_window(self):
        flags = (Qt.WindowType.FramelessWindowHint | 
                 Qt.WindowType.WindowStaysOnTopHint |
                 Qt.WindowType.Tool)
        self.setWindowFlags(flags)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setFixedSize(56, 56)
        
        self._reposition()
        
    def _reposition(self):
        screen = QGuiApplication.primaryScreen()
        if screen:
            avail = screen.availableGeometry()
            # 放在右下角，預留一些邊距
            self.move(avail.x() + avail.width() - 90, avail.y() + avail.height() - 120)
            
    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        # 繪製半透明紫色背景圓形，配合使用者要求內縮 20 pixel (單邊 margin 10)
        margin = 10
        painter.setBrush(QColor(124, 77, 255, 230))
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawEllipse(margin, margin, self.width() - margin * 2, self.height() - margin * 2)
        
        # 繪製 VoiceType Logo
        if self._icon_path:
            pixmap = QPixmap(self._icon_path)
            if not pixmap.isNull():
                # 白色或圖示縮小置中
                scaled_size = 32
                scaled = pixmap.scaled(scaled_size, scaled_size, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)
                x = (self.width() - scaled.width()) // 2
                y = (self.height() - scaled.height()) // 2
                painter.drawPixmap(x, y, scaled)
                
    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self._drag_pos = event.globalPosition().toPoint()
            self._is_dragging = False
            
    def mouseMoveEvent(self, event):
        if event.buttons() & Qt.MouseButton.LeftButton and self._drag_pos:
            diff = event.globalPosition().toPoint() - self._drag_pos
            if diff.manhattanLength() > 5:  # 稍微拖曳才判定為移動
                self._is_dragging = True
            if self._is_dragging:
                self.move(self.pos() + diff)
                self._drag_pos = event.globalPosition().toPoint()
                
    def set_menu_items(self, items):
        self._menu_items = items

    def _show_menu(self):
        if not hasattr(self, '_menu_items') or not self._menu_items:
            self.clicked.emit()
            return
            
        from PyQt6.QtWidgets import QMenu
        from PyQt6.QtGui import QAction, QFont
        
        menu = QMenu(self)
        menu.setStyleSheet("""
            QMenu {
                background-color: #2d2d37;
                border: 1px solid rgba(255, 255, 255, 30);
                border-radius: 8px;
                color: #e2e4e7;
                font-family: 'Microsoft JhengHei';
                font-size: 14px;
                padding: 4px;
            }
            QMenu::item {
                padding: 6px 24px;
                border-radius: 4px;
            }
            QMenu::item:selected {
                background-color: #7c4dff;
                color: white;
            }
            QMenu::separator {
                height: 1px;
                background-color: rgba(255, 255, 255, 30);
                margin: 4px 0;
            }
            QMenu::indicator {
                width: 14px;
                height: 14px;
                margin-left: 6px;
            }
            QMenu::indicator:checked {
                image: url(assets/check.png); /* Fallback to standard if asset missing */
                background-color: #7c4dff;
                border-radius: 3px;
            }
        """)

        def add_items(parent_menu, items):
            for item in items:
                label = item.get('label', '')
                if label == "---":
                    parent_menu.addSeparator()
                elif 'submenu' in item and item['submenu']:
                    sub = parent_menu.addMenu(label)
                    add_items(sub, item['submenu'])
                else:
                    action = QAction(label, parent_menu)
                    if item.get('checked') is not None:
                        action.setCheckable(True)
                        action.setChecked(item['checked'])
                    if item.get('callback'):
                        action.triggered.connect(lambda checked=False, cb=item['callback'], act=action: cb(act))
                    parent_menu.addAction(action)

        add_items(menu, self._menu_items)
        
        # Position menu above the button
        pos = self.mapToGlobal(QPoint(0, 0))
        # Default show above and left-aligned
        menu.exec(QPoint(pos.x(), pos.y() - menu.sizeHint().height()))

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            if not self._is_dragging:
                self._show_menu()
            self._drag_pos = None
            self._is_dragging = False

    def enterEvent(self, event):
        # 游標滑過時稍微放大或是改變不透明度
        self.update()
        super().enterEvent(event)

    def leaveEvent(self, event):
        self.update()
        super().leaveEvent(event)
