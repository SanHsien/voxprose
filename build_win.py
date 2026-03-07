import os
import sys
import shutil
import PyInstaller.__main__
from pathlib import Path

# --- 配置區 ---
APP_NAME = "VoiceType4TW"
ENTRY_POINT = "main.py"
ICON_PATH = "assets/icon.png" # PyInstaller 會自動處理轉換，若有 .ico 更好
DIST_PATH = Path("dist")
BUILD_PATH = Path("build")

def build():
    print(f"=== 開始構建 {APP_NAME} Windows 版本 ===")
    
    # 1. 清理舊檔案
    if DIST_PATH.exists(): shutil.rmtree(DIST_PATH)
    if BUILD_PATH.exists(): shutil.rmtree(BUILD_PATH)

    # 2. 定義資料檔案 (格式: '來源;目標')
    # Windows 使用分號 ; 作為路徑分隔符
    added_data = [
        'assets;assets',
        'soul/scenario;soul/scenario',
        'soul/format;soul/format',
    ]

    # 3. 執行 PyInstaller
    params = [
        ENTRY_POINT,
        f'--name={APP_NAME}',
        '--windowed', # 使用視窗模式 (不顯示終端)
        f'--icon={ICON_PATH}',
        '--noconfirm',
        '--clean',
    ]

    for data in added_data:
        params.append(f'--add-data={data}')

    # 4. 處理隱藏匯入 (有些動態載入的模組需要明確指定)
    hidden_imports = [
        'PyQt6.QtCore',
        'PyQt6.QtGui',
        'PyQt6.QtWidgets',
        'pystray._win32',
        'PIL._imagingtk',
        'PIL.ImageQt',
    ]
    for hi in hidden_imports:
        params.append(f'--hidden-import={hi}')

    print(f"執行指令: pyinstaller {' '.join(params)}")
    PyInstaller.__main__.run(params)

    # 5. 後處理：檢查是否需要手動複製特定 DLL (例如 CUDA)
    # faster-whisper 有時需要手動將 cudnn_*.dll 放入 dist 目錄
    print("=== 構建完成 ===")
    print(f"執行檔位於: {DIST_PATH / APP_NAME / (APP_NAME + '.exe')}")

if __name__ == "__main__":
    build()
