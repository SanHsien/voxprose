"""簡體→繁體 STT 後處理。

概念吸收自上游 jfamily4tw/voicetype4tw-mac `main` 分支 805b007
（v2.9.18「mac apple local correction」，`llm/apple_local.py` 內的
`_to_traditional()`）：Whisper 偶爾會把中文語音轉錄成簡體輸出
（實測範例見 tests/test_zh_convert.py，本檔案不逐字引用簡體字樣本，
避免觸發 tests/test_brand_and_charset_guard.py 的全 repo 簡體字掃描），
但本產品（聲成文 VoxProse）定位是繁體中文工具，簡體輸出對使用者而言
就是辨識錯誤。上游把這段轉換嵌在
macOS 專屬的 Apple Local LLM 校正功能裡，我們沒有那個平台專屬功能，
但「簡轉繁」這個概念本身與 macOS 無關，值得獨立抽成通用後處理步驟，
接在 `ui/app.py:_process_audio` 的統一路徑（幻覺過濾之後、詞彙修正
之前，見該檔案的接線點與理由）。

刻意只用 OpenCC 設定檔 "s2t"（純粹簡體字→繁體字轉換），不用
"s2twp"——後者會額外把大陸慣用詞轉換成台灣慣用詞（例如「軟件」→
「軟體」、「打印」→「列印」），已經觸及詞彙選字層，可能與使用者
在 `vocab/manager.py` 自訂的詞彙/慣用語衝突（見 `apply_vocab_correction`）。
本模組的職責單純只是「修正 Whisper 誤判成簡體」，不做用詞在地化。

`opencc-python-reimplemented` 是選用依賴（`requirements-win.txt`）：
環境未安裝時優雅降級為原樣返回文字，不拋錯、不擋主流程——讓使用者
繼續能用 STT，遠比為了一個後處理步驟擋下整條轉錄鏈路重要。
"""
from __future__ import annotations

_converter = None
_converter_load_attempted = False


def _get_converter():
    """延遲載入並快取 OpenCC 轉換器；載入失敗時快取 None，避免每次呼叫
    都重新嘗試 import（尤其未安裝時，import 失敗有一定開銷）。"""
    global _converter, _converter_load_attempted
    if _converter_load_attempted:
        return _converter
    _converter_load_attempted = True
    try:
        from opencc import OpenCC
        _converter = OpenCC("s2t")
    except Exception as e:
        print(f"[zh_convert] OpenCC 未安裝或初始化失敗，簡轉繁停用（文字將原樣返回）: {e}")
        _converter = None
    return _converter


def to_traditional(text: str) -> str:
    """將文字中的簡體字轉換為繁體。

    opencc 未安裝、初始化失敗、或轉換過程拋例外時，一律原樣返回輸入文字
    （優雅降級，不拋錯）。空字串／None 安全。
    """
    if not text:
        return text
    converter = _get_converter()
    if converter is None:
        return text
    try:
        return converter.convert(text)
    except Exception as e:
        print(f"[zh_convert] 轉換失敗，文字原樣返回: {e}")
        return text


def convert_if_enabled(text: str, config: dict) -> str:
    """依 `config["zh_convert_enabled"]`（預設 True，見 `config.py`
    `DEFAULT_CONFIG`）決定是否套用簡轉繁。關閉時原樣返回，不呼叫 OpenCC。
    """
    if not config.get("zh_convert_enabled", True):
        return text
    return to_traditional(text)
