import os
import sys
from pathlib import Path

def get_resource_path(relative_path: str) -> str:
    """
    Get the absolute path to a resource, supporting both development and PyInstaller.
    """
    if hasattr(sys, '_MEIPASS'):
        # PyInstaller creates a temp folder and stores path in _MEIPASS
        base_path = Path(sys._MEIPASS)
    else:
        # Development mode
        base_path = Path(__file__).parent.parent
    
    res_path = base_path / relative_path
    if not res_path.exists():
        # Double check if it's in the current working directory relative path
        alt_path = Path(os.getcwd()) / relative_path
        if alt_path.exists():
            return str(alt_path)
            
    return str(res_path)
