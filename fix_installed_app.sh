#!/bin/bash
# fix_installed_app.sh: Patches the installed /Applications/嘴炮輸入法.app
# with the correct MLX dylib files that py2app missed.
# Run this AFTER installing the DMG.

APP="/Applications/嘴炮輸入法.app"
if [ ! -d "$APP" ]; then
    echo "[ERROR] /Applications/嘴炮輸入法.app not found. Please install the DMG first."
    exit 1
fi

echo "[Fix] Applying MLX patch to installed app..."
python3 post_build_fix_installed.py

echo "[Fix] Done! Please restart 嘴炮輸入法."
