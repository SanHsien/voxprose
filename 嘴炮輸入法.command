#!/bin/zsh
# VoiceType4TW macOS Launcher — 從 source code 直接啟動
set -e

# 一律用 framework Python 3.12（py2app build 與專案依賴所在的 Python）。
# 不要用 $PATH 上的 python3，因為那會撞到 homebrew Python 3.14 / 系統 Python，
# 兩者通常都沒裝專案依賴（sounddevice / mlx / PyQt6 等）。
PYTHON_BIN="/Library/Frameworks/Python.framework/Versions/3.12/bin/python3.12"

if [ ! -x "$PYTHON_BIN" ]; then
    echo "❌ 找不到 framework Python 3.12：$PYTHON_BIN"
    echo "   請從 https://www.python.org/downloads/macos/ 安裝 Python 3.12 framework build"
    echo "   再執行：$PYTHON_BIN -m pip install -r \"$(dirname "$0")/requirements.txt\""
    exit 1
fi

CD_PATH="$(dirname "$0")"
cd "$CD_PATH"

echo "🚀 嘴炮輸入法 (VoiceType4TW) 從 source 啟動 (Python $($PYTHON_BIN -c 'import sys;print(sys.version.split()[0])'))..."
exec "$PYTHON_BIN" main.py
