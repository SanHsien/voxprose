"""Windows 真人音訊驗證：以同一份錄音比較 RMS 與真 Silero VAD。

這支腳本只需要使用者依提示發出四種聲音，會輸出 JSON 與 Markdown 證據。
預設不保存原始錄音；加上 ``--keep-wav`` 才會留下 WAV。
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import tempfile
import wave
from datetime import datetime
from pathlib import Path
from typing import Callable

import numpy as np


SOURCE_OVERRIDE = os.environ.get("VOXPROSE_SOURCE_ROOT")
ROOT = Path(SOURCE_OVERRIDE or Path(__file__).resolve().parents[2]).resolve()
EXPECTED_MODULES = (
    ROOT / "audio" / "vad" / "rms_vad.py",
    ROOT / "audio" / "vad" / "silero_vad.py",
)
if SOURCE_OVERRIDE:
    for expected_module in EXPECTED_MODULES:
        if not expected_module.is_file():
            raise RuntimeError(
                f"VOXPROSE_SOURCE_ROOT 未包含預期模組：{expected_module}"
            )
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import audio.vad.rms_vad as rms_vad_module
import audio.vad.silero_vad as silero_vad_module


IMPORTED_MODULES = {
    "rms_vad": Path(rms_vad_module.__file__).resolve(),
    "silero_vad": Path(silero_vad_module.__file__).resolve(),
}
for module_name, module_path in IMPORTED_MODULES.items():
    try:
        module_path.relative_to(ROOT)
    except ValueError as exc:
        raise RuntimeError(
            f"{module_name} 模組來源不在指定 root 內：{module_path}"
        ) from exc

RmsVAD = rms_vad_module.RmsVAD
SAMPLE_RATE = silero_vad_module.SAMPLE_RATE
SileroVAD = silero_vad_module.SileroVAD


BLOCK_SAMPLES = 800
SCENARIOS = (
    ("speech", "正常說一句「今天天氣真好」"),
    ("cough", "咳嗽一至兩聲，其餘保持安靜"),
    ("breathing", "靠近平常距離呼吸，不要說話"),
    ("ambient", "製造平常的鍵盤／風扇／環境雜音，不要說話"),
)


def analyze_pcm(
    pcm: np.ndarray,
    threshold: float,
    rms_factory: Callable[[], object] = RmsVAD,
    silero_factory: Callable[[], object] = SileroVAD,
) -> dict:
    """以各自全新的引擎分析同一份單聲道 int16 PCM。"""
    samples = np.asarray(pcm, dtype=np.int16).reshape(-1)
    if samples.size == 0:
        raise ValueError("錄音沒有樣本")

    engines = {"rms": rms_factory(), "silero": silero_factory()}
    levels = {name: [] for name in engines}
    for start in range(0, samples.size, BLOCK_SAMPLES):
        block = samples[start : start + BLOCK_SAMPLES]
        if block.size < BLOCK_SAMPLES:
            block = np.pad(block, (0, BLOCK_SAMPLES - block.size))
        shaped = block.reshape(-1, 1)
        for name, engine in engines.items():
            levels[name].append(float(engine.compute_level(shaped)))

    physical_rms = float(
        np.sqrt(np.mean(samples.astype(np.float32) ** 2)) / 32768.0
    )
    peak = float(np.max(np.abs(samples.astype(np.float32))) / 32768.0)
    result = {
        "samples": int(samples.size),
        "duration_sec": round(samples.size / SAMPLE_RATE, 3),
        "physical_rms": round(physical_rms, 6),
        "peak": round(peak, 6),
    }
    for name, values in levels.items():
        result[name] = {
            "max": round(max(values), 6),
            "mean": round(sum(values) / len(values), 6),
            "trigger_blocks": sum(value >= threshold for value in values),
            "total_blocks": len(values),
            "triggered": any(value >= threshold for value in values),
        }
    return result


def assess_results(results: dict) -> tuple[str, list[str]]:
    reasons: list[str] = []
    speech = results["speech"]
    if speech["physical_rms"] < 0.002:
        return "BLOCKED", ["說話錄音能量過低，無法證明麥克風收到真人語音"]
    if not speech["rms"]["triggered"] or not speech["silero"]["triggered"]:
        reasons.append("RMS 與 Silero 未同時觸發正常說話")

    noise_names = ("cough", "breathing", "ambient")
    rms_false = sum(results[name]["rms"]["triggered"] for name in noise_names)
    silero_false = sum(results[name]["silero"]["triggered"] for name in noise_names)
    if silero_false >= rms_false:
        reasons.append(
            f"非語音觸發數未明顯下降（RMS={rms_false}，Silero={silero_false}）"
        )

    return ("FAIL", reasons) if reasons else (
        "PASS",
        [f"正常說話兩者皆觸發；非語音觸發 RMS={rms_false}、Silero={silero_false}"],
    )


def _record(duration: float, device: int | None) -> np.ndarray:
    import sounddevice as sd

    recording = sd.rec(
        int(duration * SAMPLE_RATE),
        samplerate=SAMPLE_RATE,
        channels=1,
        dtype="int16",
        device=device,
    )
    sd.wait()
    return np.asarray(recording, dtype=np.int16).reshape(-1)


def _write_wav(path: Path, pcm: np.ndarray) -> None:
    with wave.open(str(path), "wb") as output:
        output.setnchannels(1)
        output.setsampwidth(2)
        output.setframerate(SAMPLE_RATE)
        output.writeframes(np.asarray(pcm, dtype="<i2").tobytes())


def _write_markdown(path: Path, report: dict) -> None:
    lines = [
        "# VoxProse 真人 VAD 驗證",
        "",
        f"- 結果：**{report['status']}**",
        f"- 時間：{report['created_at']}",
        f"- 門檻：{report['threshold']}",
        f"- Silero 模型：`{report['silero_model']}`",
        "",
        "|情境|音訊 RMS|RMS max／觸發 blocks|Silero max／觸發 blocks|",
        "|---|---:|---:|---:|",
    ]
    for name, _instruction in SCENARIOS:
        item = report["scenarios"][name]
        lines.append(
            f"|{name}|{item['physical_rms']:.6f}|"
            f"{item['rms']['max']:.6f}／{item['rms']['trigger_blocks']}|"
            f"{item['silero']['max']:.6f}／{item['silero']['trigger_blocks']}|"
        )
    lines.extend(["", "## 判定", ""])
    lines.extend(f"- {reason}" for reason in report["reasons"])
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--duration", type=float, default=3.0, help="每段錄音秒數")
    parser.add_argument("--threshold", type=float, default=0.15, help="VAD 觸發門檻")
    parser.add_argument("--device", type=int, default=None, help="sounddevice 輸入裝置索引")
    parser.add_argument("--output", type=Path, default=None, help="JSON 報告路徑")
    parser.add_argument("--keep-wav", action="store_true", help="保留四段原始 WAV")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    if args.duration <= 0:
        raise ValueError("--duration 必須大於 0")
    if not 0 <= args.threshold <= 1:
        raise ValueError("--threshold 必須介於 0 與 1")

    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    output = (
        args.output.resolve()
        if args.output
        else Path(tempfile.gettempdir()) / f"voxprose-vad-{stamp}.json"
    )
    output.parent.mkdir(parents=True, exist_ok=True)

    probe = SileroVAD()
    model_path = Path(probe.model_path).resolve()
    del probe
    print(f"[INFO] Source root: {ROOT}")
    for module_name, module_path in IMPORTED_MODULES.items():
        print(f"[INFO] {module_name} module: {module_path}")
    print(f"[INFO] Silero model: {model_path}")
    print(f"[INFO] 每段錄音 {args.duration:.1f} 秒；門檻 {args.threshold:.2f}")

    results = {}
    wav_dir = output.with_suffix("")
    if args.keep_wav:
        wav_dir.mkdir(parents=True, exist_ok=True)
    for name, instruction in SCENARIOS:
        input(f"\n[{name}] {instruction}。準備好後按 Enter 開始：")
        print("錄音中…")
        pcm = _record(args.duration, args.device)
        results[name] = analyze_pcm(pcm, args.threshold)
        if args.keep_wav:
            _write_wav(wav_dir / f"{name}.wav", pcm)
        print(
            f"完成：RMS max={results[name]['rms']['max']:.4f}，"
            f"Silero max={results[name]['silero']['max']:.4f}"
        )

    status, reasons = assess_results(results)
    report = {
        "status": status,
        "created_at": datetime.now().astimezone().isoformat(timespec="seconds"),
        "source_root": str(ROOT),
        "vad_modules": {
            name: str(path) for name, path in IMPORTED_MODULES.items()
        },
        "threshold": args.threshold,
        "silero_model": str(model_path),
        "scenarios": results,
        "reasons": reasons,
        "wav_retained": args.keep_wav,
    }
    output.write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    markdown = output.with_suffix(".md")
    _write_markdown(markdown, report)
    print(f"[{status}] JSON: {output}")
    print(f"[{status}] Markdown: {markdown}")
    return 0 if status == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
