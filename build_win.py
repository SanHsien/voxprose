import os
import sys
import shutil
import PyInstaller.__main__
from pathlib import Path

# --- 配置區 ---
APP_NAME = "VoiceType4TW"
ENTRY_POINT = "main.py"
ICON_PATH = "assets/icon.png"
DIST_PATH = Path("dist")
BUILD_PATH = Path("build")

def build():
    print("\n   VoiceType4TW - Windows Build Script")
    print("   Version: 2.8.27 (V69-ALLOC-CONSOLE)")
    
    # 1. 清理舊檔案
    if DIST_PATH.exists(): shutil.rmtree(DIST_PATH)
    if BUILD_PATH.exists(): shutil.rmtree(BUILD_PATH)

    # 2. 定義資料檔案
    added_data = [
        'assets;assets',
        'soul/scenario;soul/scenario',
        'soul/format;soul/format',
    ]

    # 3. 執行 PyInstaller
    params = [
        ENTRY_POINT,
        f'--name={APP_NAME}',
        '--windowed',
        f'--icon={ICON_PATH}',
        '--noconfirm',
        '--clean',
        '--collect-all=ctranslate2',
        '--collect-all=faster_whisper',
        '--collect-all=av',
        '--collect-all=sounddevice',
    ]

    for data in added_data:
        params.append(f'--add-data={data}')

    excluded_modules = [
        'torch', 'torchvision', 'torchaudio', 'cv2', 'clip',
        'unittest', 'tkinter', 'matplotlib', 'pandas', 'IPython'
    ]
    for ex in excluded_modules:
        params.append(f'--exclude-module={ex}')

    hidden_imports = [
        'PyQt6.QtCore',
        'PyQt6.QtGui',
        'PyQt6.QtWidgets',
        'PIL._imagingtk',
        'PIL.ImageQt',
    ]
    for hi in hidden_imports:
        params.append(f'--hidden-import={hi}')

    print(f"執行指令: pyinstaller {' '.join(params)}")
    PyInstaller.__main__.run(params)

    # ============================================================
    # V35: MKL DEADLOCK FIX
    # Restored MKL threading limits in main.py. Without them, 
    # OpenMP inside the spawned multiprocessing child attempts to spawn 
    # threads blindly on Windows, leading to an immediate 30-second deadlock.
    # ============================================================
    ct2_dll_path = DIST_PATH / APP_NAME / "_internal" / "ctranslate2" / "libiomp5md.dll"
    if ct2_dll_path.exists():
        print(f"[V35] DLL 保留完整: {ct2_dll_path} (無死鎖版)")
    else:
        print("[V35] WARNING: libiomp5md.dll 不存在，ctranslate2 可能無法運作")

    print("=== 構建完成 ===")

    print(f"執行檔位於: {DIST_PATH / APP_NAME / (APP_NAME + '.exe')}")

if __name__ == "__main__":
    build()
