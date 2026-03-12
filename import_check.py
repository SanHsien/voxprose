import sys
import os

print("[check] Starting submodule import check...")

# 模擬 paths 預熱
try:
    from paths import initialize_paths
    initialize_paths()
    print("[check] paths initialized.")
except Exception as e:
    print(f"[ERROR] paths init failed: {e}")
    sys.exit(1)

modules_to_test = [
    "utils.resources",
    "output.injector",
    "actions.dispatcher",
    "ui.mic_indicator",
    "ui.floating_button",
    "ui.tray_manager",
    "ui.menu_bar",
    "ui.app",
    "stt.subprocess_whisper"
]

print("[check] verifying ActionManager signature...")
from actions.dispatcher import ActionManager
_am = ActionManager(None, None)
print("[check] ActionManager init OK.")

for mod in modules_to_test:
    try:
        print(f"[check] Testing {mod}...", end=" ")
        __import__(mod)
        print("OK")
    except Exception as e:
        print(f"FAILED!\n[CRITICAL ERROR] {mod}: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

print("[SUCCESS] All core modules imported without NameError or SyntaxError.")
sys.exit(0)
