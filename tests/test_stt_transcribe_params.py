"""Mac 主線 13-2（`git show 51094bf:stt/mlx_whisper.py`）移植回歸測試。

驗證 faster-whisper 的 transcribe() 呼叫有帶入抗幻覺參數：
`no_speech_threshold=0.6` + `condition_on_previous_text=False`。
見 docs/mac-mainline-absorption-analysis.md 項目 13-2。

另含 2026-07-20 bug fix 回歸測試：worker 端過去從未讀取 IPC 訊息的 "prompt"
欄位（client 端 `SubprocessWhisperSTT.transcribe()` 送出的
`vocab.manager.build_vocab_prompt()` 結果），永遠用硬編預設字串，導致智慧
詞彙學習對本地辨識完全沒有作用。修復後 worker 讀取 "prompt" 欄位並轉交
`_run_transcribe()`，空/缺 fallback 回預設字串。
"""
import unittest
from unittest.mock import MagicMock

from stt.subprocess_whisper import _run_transcribe
from stt.local_whisper import LocalWhisperSTT


class SubprocessWhisperTranscribeParamsTest(unittest.TestCase):
    """子程序 worker 的轉錄呼叫（_stt_worker 本體需要真實子程序環境，
    故抽成 _run_transcribe 供 mock 驗證）。"""

    def test_no_speech_threshold_and_condition_on_previous_text_passed(self):
        model = MagicMock()
        model.transcribe.return_value = ("segments", "info")

        result = _run_transcribe(model, "audio_np", "zh")

        self.assertEqual(result, ("segments", "info"))
        model.transcribe.assert_called_once()
        _, kwargs = model.transcribe.call_args
        self.assertEqual(kwargs["no_speech_threshold"], 0.6)
        self.assertIs(kwargs["condition_on_previous_text"], False)
        self.assertEqual(kwargs["language"], "zh")
        self.assertEqual(kwargs["beam_size"], 5)

    def test_default_initial_prompt_when_not_specified(self):
        """未指定 initial_prompt 時，沿用既有硬編預設字串（向下相容）。"""
        model = MagicMock()
        model.transcribe.return_value = ("segments", "info")

        _run_transcribe(model, "audio_np", "zh")

        _, kwargs = model.transcribe.call_args
        self.assertEqual(kwargs["initial_prompt"], "以下是繁體中文的語音內容：")

    def test_custom_vocab_prompt_passed_through(self):
        """回歸測試：worker 端必須把詞彙庫 prompt 真正傳給 model.transcribe()，
        修復前這裡永遠是硬編預設字串，vocab.manager.build_vocab_prompt() 的
        結果從未被使用。"""
        model = MagicMock()
        model.transcribe.return_value = ("segments", "info")
        vocab_prompt = "以下是繁體中文的語音內容，常用詞彙包含：小克、Fable。"

        _run_transcribe(model, "audio_np", "zh", vocab_prompt)

        _, kwargs = model.transcribe.call_args
        self.assertEqual(kwargs["initial_prompt"], vocab_prompt)

    def test_empty_or_none_prompt_falls_back_to_default(self):
        """"prompt" 欄位空字串或 None 時 fallback 回預設字串，不把空字串
        直接餵給 model.transcribe()。"""
        model = MagicMock()
        model.transcribe.return_value = ("segments", "info")

        _run_transcribe(model, "audio_np", "zh", "")
        _, kwargs_empty = model.transcribe.call_args
        self.assertEqual(kwargs_empty["initial_prompt"], "以下是繁體中文的語音內容：")

        _run_transcribe(model, "audio_np", "zh", None)
        _, kwargs_none = model.transcribe.call_args
        self.assertEqual(kwargs_none["initial_prompt"], "以下是繁體中文的語音內容：")

    def test_worker_source_reads_prompt_field_from_ipc_message(self):
        """回歸守護：`_stt_worker` 本體需要真實子程序環境，無法直接呼叫測試，
        改用原始碼檢查確保迴圈確實從 IPC 訊息讀取 "prompt" 欄位並轉交
        `_run_transcribe`——這正是本次修復的核心，修復前 worker 完全不讀
        "prompt"，vocab.manager.build_vocab_prompt() 的結果從未被使用。"""
        import inspect
        from stt import subprocess_whisper as sw

        source = inspect.getsource(sw._stt_worker)

        self.assertIn('msg.get("prompt")', source)
        self.assertIn("_run_transcribe(model, audio_np, language, initial_prompt)", source)


class LocalWhisperTranscribeParamsTest(unittest.TestCase):
    """非 Windows 開發路徑用的 LocalWhisperSTT（stt/local_whisper.py）。"""

    def test_no_speech_threshold_and_condition_on_previous_text_passed(self):
        stt = LocalWhisperSTT.__new__(LocalWhisperSTT)  # 跳過 __init__（會載入真實模型）
        mock_model = MagicMock()
        mock_segment = MagicMock()
        mock_segment.text = "測試"
        mock_model.transcribe.return_value = ([mock_segment], MagicMock(language="zh"))
        stt.model = mock_model

        text = stt.transcribe(b"\x00\x01" * 100, language="zh")

        self.assertEqual(text, "測試")
        mock_model.transcribe.assert_called_once()
        _, kwargs = mock_model.transcribe.call_args
        self.assertEqual(kwargs["no_speech_threshold"], 0.6)
        self.assertIs(kwargs["condition_on_previous_text"], False)


if __name__ == "__main__":
    unittest.main()
