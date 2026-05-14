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
# 一律用 framework Python 3.12（與 py2app build 同一顆，site-packages 才對得上）。
PYTHON_BIN="/Library/Frameworks/Python.framework/Versions/3.12/bin/python3.12"
if [ ! -x "$PYTHON_BIN" ]; then
    echo "[ERROR] 找不到 framework Python 3.12：$PYTHON_BIN"
    exit 1
fi
"$PYTHON_BIN" post_build_fix_installed.py

echo "[Fix] Done! Please restart 嘴炮輸入法."
