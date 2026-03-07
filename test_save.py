import sys
import json
from config import load_config, save_config, LOCAL_CONFIG_PATH
config = load_config()
print("Before:", config.get("hotkey_ptt"))
config["hotkey_ptt"] = "page_up (code:116)"
save_config(config)
print("After save. Now reading local file...")
with open(LOCAL_CONFIG_PATH, "r") as f:
    print(f.read())
