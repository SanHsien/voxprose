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
        if IS_WINDOWS:
            if self._tray:
                self._tray.stop()
        else:
            import rumps
            rumps.quit_application()

    def update_menu(self, menu_items: List[Dict]):
        self.menu_items = menu_items
        if IS_WINDOWS:
            self._update_windows_menu()
        else:
            self._update_macos_menu()

    def _start_windows(self):
        try:
            from pystray import Icon, Menu, MenuItem
            from PIL import Image
            
            if self.icon_path and os.path.exists(self.icon_path):
                image = Image.open(self.icon_path)
            else:
                # Fallback to a plain 64x64 colored image if icon is missing
                print(f"[tray] Warning: Icon not found at {self.icon_path}. Using fallback.")
                image = Image.new('RGB', (64, 64), (124, 77, 255)) # Purple
            
            def create_menu():
                items = []
                for item in self.menu_items:
                    items.append(MenuItem(item['label'], item['callback'], checked=item.get('checked', None)))
                return Menu(*items)

            self._tray = Icon(self.title, image, self.title, menu=create_menu())
            self._tray.run()
        except Exception as e:
            print(f"[tray] Error in Windows tray: {e}")

    def _start_macos(self, on_tick: Optional[Callable] = None):
        try:
            import rumps
            class App(rumps.App):
                def __init__(self, title, icon, items, tick_callback):
                    super().__init__(title, icon=icon, quit_button=None)
                    self.items = items
                    self.tick_callback = tick_callback
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
                            # rumps doesn't have a direct "sub-menu" object, 
                            # we just add items to the MenuItem itself as if it were a menu
                            self._add_items_to_menu(sub_menu_item, submenu)
                        else:
                            btn = rumps.MenuItem(name, callback=callback)
                            if checked is not None:
                                btn.state = 1 if checked else 0
                            menu_obj.add(btn)

                @rumps.timer(0.1)
                def drive_tick(self, _):
                    if self.tick_callback:
                        self.tick_callback()

            self._tray = App(self.title, self.icon_path, self.menu_items, on_tick)
            self._tray.run()
        except ImportError:
            print("[tray] Error: rumps not found.")

    def _update_windows_menu(self):
        if self._tray:
            try:
                self._tray.menu = self._build_pystray_menu(self.menu_items)
            except Exception as e:
                print(f"[tray] Failed to update Windows tray menu: {e}")

    def _build_pystray_menu(self, items):
        from pystray import Menu, MenuItem
        out_items = []
        for item in items:
            if item.get('label') == "---":
                out_items.append(Menu.SEPARATOR)
            elif item.get('submenu'):
                sub_menu = self._build_pystray_menu(item['submenu'])
                out_items.append(MenuItem(item['label'], sub_menu))
            else:
                out_items.append(MenuItem(item['label'], item.get('callback') or (lambda _: None), checked=item.get('checked', None)))
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

    def flash(self):
        # Placeholder for visual feedback
        pass
