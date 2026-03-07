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
            from pystray import Icon, Menu, MenuItem
            from PIL import Image
            
            if self.icon_path and os.path.exists(self.icon_path):
                image = Image.open(self.icon_path)
            else:
                # Fallback to a plain 64x64 colored image if icon is missing
                print(f"[tray] Warning: Icon not found at {self.icon_path}. Using fallback.")
                image = Image.new('RGB', (64, 64), (124, 77, 255)) # Purple
            
            def create_menu():
                return self._build_pystray_menu(self.menu_items)

            self._tray = Icon(self.title, image, self.title, menu=create_menu())
            self._tray.run()
        except Exception as e:
            print(f"[tray] Error in Windows tray: {e}")

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
                self._tray.menu = self._build_pystray_menu(self.menu_items)
            except Exception as e:
                print(f"[tray] Failed to update Windows tray menu: {e}")

    def _build_pystray_menu(self, items):
        from pystray import Menu, MenuItem
        out_items = []
        for item in items:
            label = item.get('label', '')
            callback = item.get('callback') or (lambda _: None)
            checked = item.get('checked', None)
            submenu = item.get('submenu')

            if label == "---":
                out_items.append(Menu.SEPARATOR)
            elif submenu:
                sub_menu_obj = self._build_pystray_menu(submenu)
                out_items.append(MenuItem(label, sub_menu_obj))
            else:
                # Wrap callback to match rumps: callback(sender)
                # pystray provides (icon, item), we pass item as sender
                wrapped_cb = (lambda i, it, cb=callback: cb(it)) if callback else None
                
                if checked is not None:
                    # pystray checked needs a callable or bool
                    # We use a lambda to ensure it stays in sync with our state
                    out_items.append(MenuItem(label, wrapped_cb, checked=lambda _: checked))
                else:
                    out_items.append(MenuItem(label, wrapped_cb))
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
