import os
from typing import Callable, List, Dict, Optional

import rumps


class TrayManager:
    """macOS system tray manager using rumps."""

    def __init__(self, title: str, icon_path: str, menu_items: List[Dict]):
        self.title = title
        # Prefer template icon for automatic macOS theme switching
        base_dir = os.path.dirname(icon_path) if icon_path else ""
        templ = os.path.join(base_dir, "icon-menubarTemplate.png")
        self.icon_path = templ if os.path.exists(templ) else icon_path
        self.menu_items = menu_items
        self._tray = None

    def start(self, on_tick: Optional[Callable] = None):
        class App(rumps.App):
            def __init__(self, title, icon_path, items, tick_callback):
                super().__init__(title, icon=icon_path, quit_button=None)
                self.items = items
                self.tick_callback = tick_callback
                self._stop_ticker = False
                self._rebuild_menu()

            def _rebuild_menu(self):
                self.menu.clear()
                self._add_items(self.menu, self.items)

            def _add_items(self, menu_obj, items):
                for item in items:
                    name = item['label']
                    callback = item['callback']
                    submenu = item.get('submenu')

                    if name == "---":
                        menu_obj.add(None)
                        continue

                    if submenu:
                        sub = rumps.MenuItem(name)
                        menu_obj.add(sub)
                        self._add_items(sub, submenu)
                    else:
                        btn = rumps.MenuItem(name, callback=callback)
                        checked_val = item.get('checked', None)
                        if checked_val is not None:
                            btn.state = 1 if checked_val else 0
                        menu_obj.add(btn)

            @rumps.timer(0.1)
            def drive_tick(self, _):
                if not self._stop_ticker and self.tick_callback:
                    try:
                        self.tick_callback()
                    except Exception:
                        pass

        self._tray = App(self.title, self.icon_path, self.menu_items, on_tick)
        if self.icon_path and "Template" in self.icon_path:
            self._tray.template = True
        self._tray.run()

    def stop(self):
        self.stop_ticker()
        rumps.quit_application()

    def stop_ticker(self):
        if self._tray:
            self._tray._stop_ticker = True

    def update_menu(self, menu_items: List[Dict]):
        self.menu_items = menu_items
        if self._tray:
            self._tray.items = menu_items
            self._tray._rebuild_menu()

    def set_icon(self, status: str):
        """status: '🎙' | '🔴' | '⏳'"""
        if self._tray:
            self._tray.title = status

    def flash(self):
        pass
