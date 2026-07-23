import json
import os

DEFAULT_CONFIG = {
    "hotkey_ptt": "alt_r",
    "hotkey_toggle": "f13",
    "hotkey_llm": "f14",
    # STT
    "stt_engine": "local_whisper",
    "whisper_model": "medium",
    "groq_api_key": "",
    "language": "zh",
    # LLM
    "llm_enabled": False,
    "llm_engine": "ollama",
    "llm_mode": "replace",   # "replace" | "fast"
    "llm_prompt": "",        # 留空使用內建 prompt
    "ollama_model": "llama3",
    "ollama_base_url": "http://localhost:11434",
    "openai_api_key": "",
    "openai_model": "gpt-4o-mini",
    "anthropic_api_key": "",
    "anthropic_model": "claude-3-haiku-20240307",
    "openrouter_api_key": "",
    "openrouter_model": "google/gemini-2.5-flash",  # v2.9.16 Mac 主線 16-4：2.0-flash-001 已屬淘汰風險模型
    "gemini_api_key": "",
    "gemini_model": "gemini-2.0-flash",
    "gemini_stt_model": "gemini-2.0-flash",
    "qwen_api_key": "",
    "qwen_model": "qwen-plus",
    "deepseek_api_key": "",
    "deepseek_model": "deepseek-chat",
    # 記憶
    "memory_enabled": True,
    # v3.3.0：STT 後簡體→繁體轉換（見 utils/zh_convert.py）。預設開啟——
    # 本產品定位是繁體中文工具，Whisper 偶爾誤判輸出簡體字對使用者而言
    # 就是辨識錯誤，理應預設修正。不列入 LOCAL_KEYS：這是文字處理行為
    # 偏好（跟 memory_enabled/llm_enabled 同類），不是機器特定設定
    # （不像 hotkey/mic_device 那樣換一台機器就該重設），值得跨裝置同步。
    "zh_convert_enabled": True,
    # v2.5 靈魂系統
    "active_scenario": "default",
    "active_format": "natural",
    "action_mode": False,
    # 統計 / Debug
    "debug_mode": False,
    "is_demo": False,
    # 其他
    "auto_paste": True,
    "magic_trigger": "嘿 VoiceType",
    # v2.9.8 全時自動觸發 (VAD)
    "auto_trigger_enabled": False,
    "auto_trigger_sensitivity": 0.15,   # 0~1 觸發門檻（與音量條同尺度）
    "auto_trigger_silence_sec": 1.5,    # 靜音多久視為一句結束
    # 語音偵測引擎："rms"（現行能量+遲滯門檻，預設）｜"silero"（Silero VAD
    # 神經網路，需 onnxruntime 已安裝且模型可下載，缺任一優雅降級回 rms，
    # 見 audio/vad/__init__.py:get_vad_engine() 與 docs/DECISIONS.md）
    "vad_engine": "rms",
    # Mac 主線 v2.9.7（7-1/7-2/7-3）移植：麥克風裝置選擇 + 增益 + AGC
    "mic_device": None,      # None = 系統預設；否則為 sounddevice 裝置索引
    "mic_gain": 100,         # 手動基底放大倍率（50~300，100=×1.0 不變）
    "mic_gain_auto": True,   # 啟用 AGC 自動微調（獨立 _agc_factor，不覆蓋手動 gain）
}
# 🔑 所有 *_api_key 欄位一律本地專屬，絕不進雲端同步（見 docs/DECISIONS.md 遷移決策）
API_KEY_FIELDS = {k for k in DEFAULT_CONFIG if k.endswith("_api_key")}

# 🗝️ 本地設定白名單 (不進行雲端同步的項目)
LOCAL_KEYS = {
    "hotkey_ptt", "hotkey_toggle", "hotkey_llm", "hotkey",
    "trigger_mode", "show_floating_button", "completion_sound",
    "debug_mode", "is_demo", "output_prefix",
    "showcase_mode",
    "stt_engine", "whisper_model",
    # 麥克風靈敏度與觸發習慣屬於機器特定設定，不做雲端同步；vad_engine 是
    # 否可用取決於這台機器有沒有裝 onnxruntime/下載過模型，同屬機器特定。
    "auto_trigger_enabled", "auto_trigger_sensitivity", "auto_trigger_silence_sec",
    "vad_engine",
    # 麥克風裝置選擇 / 增益 / AGC 是機器特定設定，不做雲端同步
    "mic_device", "mic_gain", "mic_gain_auto",
} | API_KEY_FIELDS

from paths import GLOBAL_CONFIG_PATH, LOCAL_CONFIG_PATH, APP_DATA_DIR

def load_config() -> dict:
    """載入設定：合併本機設定與全域同步設定。"""
    config = DEFAULT_CONFIG.copy()
    
    # 0. 舊版 config.json 遷移邏輯 (v2.9.0 升級防護)
    old_config_path = APP_DATA_DIR / "config.json"
    if old_config_path.exists():
        try:
            with open(old_config_path, "r", encoding="utf-8") as f:
                legacy_config = json.load(f)
            # 先跟目前的 config 合併（確保 legacy 有值的地方蓋掉 default）
            config.update(legacy_config)
            # 立即觸發拆分儲存，這樣會產生 config_local.json 與 config_global.json
            save_config(config) 
            # 成功遷移後刪除舊檔
            os.remove(old_config_path)
        except Exception as e:
            # 2026-07-23（broad except 清查）：舊版單一 config.json 遷移失敗
            # 原本完全靜默，使用者設定莫名其妙沒被搬過來時完全無跡可查。
            print(f"[config] Legacy config.json migration failed: {e}")

    # 1. 載入全域設定 (Global) - 優先權低
    global_data = None
    if os.path.exists(GLOBAL_CONFIG_PATH):
        try:
            with open(GLOBAL_CONFIG_PATH, "r", encoding="utf-8") as f:
                global_data = json.load(f)
            # 過濾掉不該出現在全域的本地 key
            config.update({k: v for k, v in global_data.items() if k not in LOCAL_KEYS})
        except Exception as e:
            # 2026-07-23（broad except 清查）：全域設定檔（同步目錄）損毀時原本
            # 靜默退回 None，使用者會發現「設定全部消失」卻查不到原因。
            print(f"[config] Failed to load global config ({GLOBAL_CONFIG_PATH}): {e}")
            global_data = None

    # 1b. 一次性遷移：舊版曾把 API Key 等現已列入 LOCAL_KEYS 的欄位存進全域
    # (雲端同步) 設定檔，這裡偵測到殘留就搬進本機、並從全域檔案移除，讓既有
    # 使用者無感升級、金鑰不再落在同步資料夾（docs/DECISIONS.md 有記錄）。
    if global_data:
        leaked_to_local = {k: v for k, v in global_data.items() if k in LOCAL_KEYS}
        if leaked_to_local:
            config.update(leaked_to_local)

            # 全域檔案立即改寫成不含這些 key 的版本，避免之後任何一次
            # save_config() 之前，同步資料夾仍暫時含有金鑰。
            remaining_global = {k: v for k, v in global_data.items() if k not in LOCAL_KEYS}
            try:
                GLOBAL_CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)
                with open(GLOBAL_CONFIG_PATH, "w", encoding="utf-8") as f:
                    json.dump(remaining_global, f, ensure_ascii=False, indent=2)
            except Exception as e:
                print(f"[config] Failed to rewrite global config after key migration: {e}")

            # 同步寫回本機設定檔，讓遷移的值立刻落地（不用等下一次
            # save_config() 才產生 config_local.json）。
            try:
                existing_local = {}
                if os.path.exists(LOCAL_CONFIG_PATH):
                    with open(LOCAL_CONFIG_PATH, "r", encoding="utf-8") as f:
                        existing_local = json.load(f)
                existing_local.update(leaked_to_local)
                with open(LOCAL_CONFIG_PATH, "w", encoding="utf-8") as f:
                    json.dump(existing_local, f, ensure_ascii=False, indent=2)
            except Exception as e:
                print(f"[config] Failed to write migrated keys to local config: {e}")

    # 2. 載入本機設定 (Local) - 優先權高
    if os.path.exists(LOCAL_CONFIG_PATH):
        try:
            with open(LOCAL_CONFIG_PATH, "r", encoding="utf-8") as f:
                local_data = json.load(f)
            config.update(local_data)
        except Exception as e:
            # 2026-07-23（broad except 清查）：本機設定檔損毀時原本靜默退回
            # default，熱鍵/麥克風裝置等機器專屬設定會無聲重置，難以回報排查。
            print(f"[config] Failed to load local config ({LOCAL_CONFIG_PATH}): {e}")

    return config


def save_config(config: dict) -> None:
    """儲存設定：依據白名單拆分並分別寫入本機與同步目錄。"""
    # 拆分資料
    local_data = {k: v for k, v in config.items() if k in LOCAL_KEYS}
    global_data = {k: v for k, v in config.items() if k not in LOCAL_KEYS}

    # 儲存本機配置
    try:
        with open(LOCAL_CONFIG_PATH, "w", encoding="utf-8") as f:
            json.dump(local_data, f, ensure_ascii=False, indent=2)
    except Exception as e:
        print(f"[config] Error saving local config: {e}")

    # 儲存全域配置
    try:
        # 確保全域所在的父目錄存在 (可能在 NAS 上)
        GLOBAL_CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)
        with open(GLOBAL_CONFIG_PATH, "w", encoding="utf-8") as f:
            json.dump(global_data, f, ensure_ascii=False, indent=2)
    except Exception as e:
        print(f"[config] Error saving global config: {e}")
