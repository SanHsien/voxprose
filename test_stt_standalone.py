import os
import sys
import time
import multiprocessing

if sys.platform == "Windows":
    multiprocessing.freeze_support()
    os.environ["MKL_THREADING_LAYER"] = "SEQUENTIAL" 
    os.environ["MKL_NUM_THREADS"] = "1"
    os.environ["OMP_NUM_THREADS"] = "1"
    os.environ["MKL_DOMAIN_NUM_THREADS"] = "1"

# Import internal modules
from config import load_config
from audio.recorder import AudioRecorder
from stt.subprocess_whisper import SubprocessWhisperSTT

def run_test():
    print("[TEST] 載入設定...")
    config = load_config()
    config["stt_engine"] = "faster_whisper"
    
    print("[TEST] 啟動 STT 子程序...")
    stt = SubprocessWhisperSTT(config)
    
    print("[TEST] 等待模型載入就緒...")
    start_wait = time.time()
    while not stt._ready_status and time.time() - start_wait < 30:
        if not stt.worker_process.is_alive():
            print("[TEST] [錯誤] STT Worker 死亡！可能重現了 EXE 行為，立即回報！")
            return
        time.sleep(0.5)
        
    if not stt._ready_status:
        print("[TEST] [錯誤] STT 模型載入超時！")
        stt.shutdown()
        return
        
    print(f"[TEST] 模型準備就緒 (耗時 {time.time()-start_wait:.2f} 秒)！")
    
    # Init audio recorder
    recorder = AudioRecorder(samplerate=16000, channels=1)
    
    duration = 5
    print(f"\n[TEST] [START] 錄音開始！請說話 ({duration} 秒)...")
    recorder.start()
    
    for i in range(duration, 0, -1):
        print(f"       剩餘 {i} 秒...")
        time.sleep(1)
        
    print("[TEST] [STOP] 錄音結束，正在取得音檔...")
    wav_bytes = recorder.stop()
    print(f"[TEST] 取出 WAV 音檔 (大小: {len(wav_bytes)} bytes)")
    
    print("[TEST] 將音檔送入 STT 子程序進行非同步辨識...")
    stt_start_time = time.time()
    result = stt.transcribe(wav_bytes, language="zh")
    stt_duration = time.time() - stt_start_time
    
    print("\n" + "="*50)
    print(">>> 辨識結果判定 <<<")
    if result.strip():
        print(f"[OK] 成功辨識文字: 「{result}」")
        print(f"[TIME] 耗時: {stt_duration:.2f} 秒")
    else:
        print("[FAIL] 辨識失敗或為空字串！")
    print("="*50 + "\n")
    
    print("[TEST] 關閉系統生命週期...")
    stt.shutdown()
    print("[TEST] 測試完畢。")

if __name__ == "__main__":
    run_test()
