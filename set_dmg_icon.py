#!/usr/bin/env python3
import sys
import os
from pathlib import Path

def set_icon(file_path, icon_path):
    """Set a custom icon for a file or folder on macOS using built-in APIs."""
    try:
        from Cocoa import NSWorkspace, NSImage
        import objc
    except ImportError:
        print("[Icon Fix] Error: pyobjc not found. Cannot set custom DMG icon.")
        return False

    if not os.path.exists(file_path):
        print(f"[Icon Fix] Error: Target file {file_path} not found.")
        return False
    if not os.path.exists(icon_path):
        print(f"[Icon Fix] Error: Icon file {icon_path} not found.")
        return False

    ws = NSWorkspace.sharedWorkspace()
    img = NSImage.alloc().initWithContentsOfFile_(str(Path(icon_path).absolute()))
    if not img:
        print(f"[Icon Fix] Error: Could not load image from {icon_path}")
        return False
        
    success = ws.setIcon_forFile_options_(img, str(Path(file_path).absolute()), 0)
    return success

if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Usage: set_dmg_icon.py <target_file> <icon_image>")
        sys.exit(1)
    
    target = sys.argv[1]
    icon = sys.argv[2]
    
    print(f"[DMG Icon] Setting {icon} as icon for {target}...")
    if set_icon(target, icon):
        print("[DMG Icon] Success!")
    else:
        print("[DMG Icon] Failed to set icon.")
