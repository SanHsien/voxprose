import os
import platform
import threading
from typing import Callable, List, Dict, Optional

IS_WINDOWS = platform.system() == "Windows"

class TrayManager:
    """
    Unified system tray manager for macOS (rumps) and Windows (pystray).
    """
    def __init__(self, title: str, icon_path: str, menu_items: List[Dict]):
        self.title = title
        # v2.8.4: Prefer template icon for automatic macOS theme switching
        base_dir = os.path.dirname(icon_path)
        templ = os.path.join(base_dir, "icon-menubarTemplate.png")
        if not IS_WINDOWS and os.path.exists(templ):
            self.icon_path = templ
        else:
            self.icon_path = icon_path

        self.menu_items = menu_items
        self._tray = None
        self._loop_thread = None

    def start(self, on_tick: Optional[Callable] = None):
        if IS_WINDOWS:
            self._start_windows()
        else:
            self._start_macos(on_tick)

    def stop(self):
        # Stop ticker first to avoid calls during app teardown
        self.stop_ticker()
        
        if IS_WINDOWS:
            if self._tray:
                self._tray.stop()
        else:
            import rumps
            rumps.quit_application()

    def stop_ticker(self):
        """Stop the background loop that drives Qt events (macOS)."""
        if not IS_WINDOWS and self._tray:
            self._tray._stop_ticker = True

    def update_menu(self, menu_items: List[Dict]):
        self.menu_items = menu_items
        if IS_WINDOWS:
            self._update_windows_menu()
        else:
            self._update_macos_menu()

    def _start_windows(self):
        try:
            from PyQt6.QtWidgets import QSystemTrayIcon, QMenu, QApplication
            from PyQt6.QtGui import QIcon, QAction
            import logging
            t_log = logging.getLogger("voicetype.tray")
            
            t_log.info(f"[tray] Starting Windows Tray (QSystemTrayIcon) with icon: {self.icon_path}")
            
            app = QApplication.instance()
            if not app:
                t_log.error("[tray] Critical: QApplication not found. Tray cannot start.")
                return

            if not QSystemTrayIcon.isSystemTrayAvailable():
                t_log.error("[tray] Critical: System tray is not available on this system.")
                return
            
            icon = QIcon(self.icon_path)
            self._tray = QSystemTrayIcon(icon, app)
            self._tray.setToolTip(self.title)
            
            # Static menu construction
            menu = self._build_qt_menu(self.menu_items)
            self._tray.setContextMenu(menu)
            
            self._tray.show()
            t_log.info("[tray] QSystemTrayIcon shown successfully.")
            
            # Store the menu to prevent it from being garbage collected
            self._qt_menu = menu

        except Exception as e:
            import traceback
            msg = f"[tray] CRITICAL Windows QSystemTrayIcon error: {e}\n{traceback.format_exc()}"
            print(msg)
            logging.getLogger("voicetype").error(msg)

    def _start_macos(self, on_tick: Optional[Callable] = None):
        try:
            import rumps
            class App(rumps.App):
                def __init__(self, title, icon_path, items, tick_callback):
                    super().__init__(title, icon=icon_path, quit_button=None)
                    self.items = items
                    self.tick_callback = tick_callback
                    self._stop_ticker = False
                    self._rebuild_menu()

                def _rebuild_menu(self):
                    self.menu.clear()
                    self._add_items_to_menu(self.menu, self.items)

                def _add_items_to_menu(self, menu_obj, items):
                    for item in items:
                        name = item['label']
                        callback = item['callback']
                        checked = item.get('checked', False)
                        submenu = item.get('submenu', None)

                        if name == "---":
                            menu_obj.add(None)
                            continue

                        if submenu:
                            # Create a nested menu item
                            sub_menu_item = rumps.MenuItem(name)
                            menu_obj.add(sub_menu_item)
                            self._add_items_to_menu(sub_menu_item, submenu)
                        else:
                            # Check if explicitly None or missing
                            checked_val = item.get('checked', None)
                            btn = rumps.MenuItem(name, callback=callback)
                            if checked_val is not None:
                                btn.state = 1 if checked_val else 0
                            menu_obj.add(btn)

                @rumps.timer(0.1)
                def drive_tick(self, _):
                    if not self._stop_ticker and self.tick_callback:
                        try:
                            self.tick_callback()
                        except:
                            # Catch errors during shutdown when objects might be dead
                            pass

            self._tray = App(self.title, self.icon_path, self.menu_items, on_tick)
            # v2.8.4: Force template mode if it's a template icon
            if self.icon_path and "Template" in self.icon_path:
                self._tray.template = True
                
            self._tray.run()
        except ImportError:
            print("[tray] Error: rumps not found.")

    def _update_windows_menu(self):
        if self._tray:
            try:
                import logging
                menu = self._build_qt_menu(self.menu_items)
                self._tray.setContextMenu(menu)
                self._qt_menu = menu  # Keep reference
                logging.getLogger("voicetype.tray").debug("[tray] Windows QSystemTrayIcon menu updated.")
            except Exception as e:
                print(f"[tray] Failed to update Windows tray menu: {e}")

    def _build_qt_menu(self, items, parent=None):
        from PyQt6.QtWidgets import QMenu
        from PyQt6.QtGui import QAction
        import logging
        
        menu = QMenu(parent)
        for item in items:
            label = item.get('label', '')
            callback = item.get('callback')
            checked = item.get('checked', None)
            submenu = item.get('submenu')

            if label == "---":
                menu.addSeparator()
                continue

            if submenu:
                sub_menu_obj = self._build_qt_menu(submenu, menu)
                sub_menu_obj.setTitle(label)
                menu.addMenu(sub_menu_obj)
                continue

            action = QAction(label, menu)
            
            if checked is not None:
                action.setCheckable(True)
                action.setChecked(bool(checked))
                
            if callback:
                # Capture callback safely
                def make_handler(cb, lbl=label):
                    def safe_handler():
                        try:
                            logging.getLogger("voicetype.tray").debug(f"[tray] QAction clicked: {lbl}")
                            # Qt signals don't pass the item itself natively in a way pystray does,
                            # so we pass the action as the sender to match rumps sender object
                            cb(action)
                        except Exception as e:
                            import traceback
                            msg = f"[tray] Error in Qt callback for '{lbl}': {e}\n{traceback.format_exc()}"
                            print(msg)
                            logging.getLogger("voicetype.tray").error(msg)
                    return safe_handler
                
                action.triggered.connect(make_handler(callback))
                
            menu.addAction(action)
            
        return menu

    def _build_pystray_menu(self, items):
        from pystray import Menu, MenuItem
        out_items = []
        for item in items:
            label = item.get('label', '')
            callback = item.get('callback')
            checked = item.get('checked', None)
            submenu = item.get('submenu')

            if label == "---":
                # v2.8.27: Strict usage of pystray.Menu.SEPARATOR. 
                # Never use None, as it crashes pystray visibility checks.
                out_items.append(Menu.SEPARATOR)
                continue

            if submenu:
                sub_menu_obj = self._build_pystray_menu(submenu)
                out_items.append(MenuItem(label, sub_menu_obj))
                continue

            # Callback wrapper: pystray passes (icon, item)
            # We must capture 'callback' in the closure correctly
            def make_handler(cb, lbl=label):
                if not cb: return None
                
                def safe_handler(icon, item):
                    try:
                        import logging
                        logging.getLogger("voicetype.tray").debug(f"[tray] Item clicked: {lbl}")
                        cb(item)
                    except Exception as e:
                        import traceback
                        msg = f"[tray] Error in callback for '{lbl}': {e}\n{traceback.format_exc()}"
                        print(msg)
                        logging.getLogger("voicetype.tray").error(msg)
                
                return safe_handler

            handler = make_handler(callback)
            
            if checked is not None:
                # 'checked' is a callable receiving 'item'
                # We capture the current bool state
                state = bool(checked)
                out_items.append(MenuItem(label, handler, checked=lambda item, s=state: s))
            else:
                out_items.append(MenuItem(label, handler))
                
        return Menu(*out_items)

    def _update_macos_menu(self):
        if self._tray:
            self._tray.items = self.menu_items
            self._tray._rebuild_menu()

    def set_icon(self, status: str):
        """status: '🎙' (idle), '🔴' (recording), '⏳' (processing)"""
        # On macOS, rumps uses 'title' for the icon emoji string
        # On Windows, pystray would need actual image files, but for now we might stick to console or simple tray update
        if not IS_WINDOWS:
            if self._tray:
                self._tray.title = status
        else:
            # TODO: Implementation for Windows pystray icon update (requires .ico files)
            pass

    def run(self):
        """啟動事件循環 (Windows 為 Qt Loop, macOS 為 Rumps Loop)"""
        if IS_WINDOWS:
            self.start()
            from PyQt6.QtWidgets import QApplication
            import sys
            app = QApplication.instance()
            if app:
                sys.exit(app.exec())
            else:
                # Fallback if app wasn't created yet
                app = QApplication(sys.argv)
                self.start() # Re-call to bind to new app instance
                sys.exit(app.exec())
        else:
            self.start() # macOS start includes .run() loop
