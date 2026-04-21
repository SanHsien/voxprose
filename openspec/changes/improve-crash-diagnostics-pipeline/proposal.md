# Improve Crash Diagnostics Pipeline

## Problem

使用者在朋友 M3 Pro 上一開就崩，icon 消失無對話框、debug.log 停在 warmup 之前。無法靠現有 log 定位真因（MLX Metal / PyObjC dylib / py2app 封裝問題三者都有可能）。

xattr -cr 已試無效，排除 Gatekeeper/quarantine。

## Scope

長期診斷管道，讓「下次有人崩潰，證據自動完整到手」：

1. **faulthandler** 在 main.py 最早期啟用（`import faulthandler; faulthandler.enable(file=log_file_handle)`），捕捉 Python 層抓不到的 SIGSEGV/SIGBUS/SIGABRT 並寫入 debug.log
2. **logging 初始化提前** 到 `import certifi` 之前，確保 top-level import 崩也有 log
3. **啟動 breadcrumb** — 每個高風險步驟前後寫 `log.info("[boot] step N: XXX")`：
   - certifi import
   - paths.migrate_legacy_data
   - config load
   - sounddevice/AudioRecorder init
   - MLX import
   - MLX warmup
   - LLM init
4. **環境資訊記錄** — log 開頭寫 macOS version、chip（`platform.processor()`）、RAM、Python version、MLX 版本
5. **診斷匯出按鈕** — 設定頁新增「匯出診斷包」，一鍵打包：
   - debug.log（最後 2000 行）
   - keystrike.log（最後 500 行）
   - `~/Library/Logs/DiagnosticReports/` 裡最近 3 份 `嘴炮輸入法-*.ips` 或 `.crash`
   - 系統資訊 txt
   - config_local.json（API key 脫敏）
   - 輸出至桌面 `VoiceType4TW_診斷_YYYYMMDD_HHMMSS.zip`
   - 壓完自動開 Finder 反白
6. **macOS signal handler** — 額外補 `signal.signal(SIGTERM, ...)` log `[SHUTDOWN] SIGTERM received`，方便分辨主動退出 vs OS kill

## Non-goals

- 不做遠端遙測（privacy）
- 不自動上傳到 server
- 不影響效能（faulthandler 與 log.info 成本可忽略）

## Success Criteria

- 下次任何人崩潰，debug.log 至少能定位到「崩在第幾步」
- 若崩在 native code（Metal / PyObjC），faulthandler 寫入 C-level stack trace
- 使用者 3 秒內完成「匯出診斷包」並把 zip 傳給開發者
