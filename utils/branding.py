import os
import sys
import logging
import platform

log = logging.getLogger("voicetype.branding")

# v2.8.27_V87: Ultimate Taskbar Branding Utility
# This ID is rotated to force Windows to clear its taskbar icon cache.
APP_USER_MODEL_ID = 'jfamily.voicetype4tw.v87.ultimate.stable'

def init_windows_id():
    """Set the AppUserModelID for Windows Taskbar grouping."""
    if platform.system() == "Windows":
        try:
            import ctypes
            ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(APP_USER_MODEL_ID)
            log.info(f"AppUserModelID set: {APP_USER_MODEL_ID}")
        except Exception as e:
            log.warning(f"Failed to set AppUserModelID: {e}")

def apply_branding(app_or_window):
    """
    Apply branding icon to a QApplication instance or a QWidget.
    Ensures consistent dinosaur icon across all windows.
    """
    if platform.system() == "Darwin":
        return # macOS handles menubar and dock icons differently
        
    try:
        from PyQt6.QtGui import QIcon
        from utils.resources import get_resource_path
        
        ico_path = get_resource_path("assets/icon.ico")
        if os.path.exists(ico_path):
            icon = QIcon(ico_path)
            # If it's the app instance, it sets the global default
            # If it's a window (QWidget), it sets the window-specific icon (helps grouping)
            app_or_window.setWindowIcon(icon)
            log.debug(f"Branding applied from: {ico_path}")
    except Exception as e:
        log.error(f"Failed to apply branding: {e}")
