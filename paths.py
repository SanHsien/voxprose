import os
from pathlib import Path

# Get user home directory and create standard app support directory
HOME = Path.home()
import platform
IS_WINDOWS = platform.system() == "Windows"

if IS_WINDOWS:
    # Windows: %APPDATA%/VoiceType4TW
    APP_DATA_DIR = Path(os.environ.get("APPDATA", str(HOME / "AppData" / "Roaming"))) / "VoiceType4TW"
else:
    # macOS: ~/Library/Application Support/VoiceType4TW
    APP_DATA_DIR = HOME / "Library" / "Application Support" / "VoiceType4TW"

# Ensure the directory exists
APP_DATA_DIR.mkdir(parents=True, exist_ok=True)

# 📄 基於指標的同步系統 (Synchronized Path Redirection)
# 儲存同步目錄的指標檔案 (此檔案永遠留於本機 AppData)
SYNC_POINTER_PATH = APP_DATA_DIR / "sync_path.txt"

def get_sync_base_dir() -> Path:
    """獲取目前的數據基礎目錄，若有同步指標則重定向至雲端目錄"""
    if SYNC_POINTER_PATH.exists():
        try:
            path_str = SYNC_POINTER_PATH.read_text(encoding="utf-8").strip()
            if path_str:
                sync_path = Path(path_str)
                if sync_path.exists() and sync_path.is_dir():
                    return sync_path
        except Exception:
            pass
    return APP_DATA_DIR

# 核心同步目錄 (根據指標動態重定向)
SYNC_BASE_DIR = get_sync_base_dir()

# 設定檔拆分：本機 (Local) 與 全域同步 (Global)
# 本機設定 (永遠存放於 AppData，存放熱鍵等裝置特定資訊)
LOCAL_CONFIG_PATH = APP_DATA_DIR / "config_local.json"
# 全域設定 (可跟隨指標同步，存放 API Key 與 Prompt)
GLOBAL_CONFIG_PATH = SYNC_BASE_DIR / "config_global.json"

# v2.5 新版三層式靈魂目錄 (動態跟隨 SYNC_BASE_DIR)
SOUL_DIR = SYNC_BASE_DIR / "soul"
SOUL_SCENARIO_DIR = SOUL_DIR / "scenario"
SOUL_BASE_PATH = SOUL_SCENARIO_DIR / "default.md"
SOUL_FORMAT_DIR = SOUL_DIR / "format"
SOUL_TEMPLATE_DIR = SOUL_DIR / "templates"
SOUL_SNIPPET_DIR = SOUL_DIR / "snippets"

# 其他需同步的資料目錄
VOCAB_DIR = SYNC_BASE_DIR / "vocab"
MEMORY_DIR = SYNC_BASE_DIR / "memory"
STATS_DIR = SYNC_BASE_DIR / "stats"
AI_PERMANENT_MEMORY_PATH = SYNC_BASE_DIR / "ai_permanent_memory.md"

BUILD_ID = "BUILD-0304-DEV"  # v2.8.1 dev
VERSION_NAME = "v2.8.1-dev"
KEYSTRIKE_LOG_PATH = APP_DATA_DIR / "keystrike.log"

# 舊版路徑 (用於遷移)
OLD_SOUL_PATH = APP_DATA_DIR / "soul.md"

import shutil
import sys

def get_data_dir(subfolder: str) -> Path:
    d = APP_DATA_DIR / subfolder
    d.mkdir(parents=True, exist_ok=True)
    return d

# Initial data migration
def _initialize_data():
    res_path = os.environ.get("RESOURCEPATH")
    base_dir = Path(res_path) if res_path else Path(__file__).parent
    
    # 建立目錄
    SOUL_DIR.mkdir(parents=True, exist_ok=True)
    SOUL_SCENARIO_DIR.mkdir(parents=True, exist_ok=True)
    SOUL_FORMAT_DIR.mkdir(parents=True, exist_ok=True)
    SOUL_TEMPLATE_DIR.mkdir(parents=True, exist_ok=True)
    SOUL_SNIPPET_DIR.mkdir(parents=True, exist_ok=True)

    # 1. 舊版單一 soul.md 遷移至 soul/base.md
    if OLD_SOUL_PATH.exists() and not SOUL_BASE_PATH.exists():
        try:
            shutil.move(str(OLD_SOUL_PATH), str(SOUL_BASE_PATH))
        except Exception:
            pass

    # 2. 複製內建模板 (情境與格式)
    def sync_defaults(sub_path, dest_dir):
        src_dir = base_dir / sub_path
        if src_dir.exists():
            for f in src_dir.glob("*.md"):
                dest_file = dest_dir / f.name
                # 如果目標不存在，則從 bundle 複製預設值
                # 這樣使用者修改後就不會被覆蓋，但新用戶能拿到最讚的預設集
                if not dest_file.exists():
                    try:
                        shutil.copy2(f, dest_file)
                    except Exception:
                        pass

    sync_defaults("soul/scenario", SOUL_SCENARIO_DIR)
    sync_defaults("soul/format", SOUL_FORMAT_DIR)

    # 3. 如果沒檔案，從 bundle 複製預設值
    for filename in ["config.json"]:
        bundled_file = base_dir / filename
        user_file = APP_DATA_DIR / filename
        if bundled_file.exists() and not user_file.exists():
            try:
                shutil.copy2(bundled_file, user_file)
            except Exception:
                pass
    
    # 複製內建模板 (如果有在 bundle 裡的話)
    # 這裡暫時依賴 main.py 啟動時自動檢查
                
_initialize_data()
