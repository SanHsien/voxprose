# Fix CGEventTap Auto-Recovery

## Problem

客戶回報「按了沒反應」——熱鍵完全失效但 app 本身還在跑。根因：macOS 會在 event tap callback 執行太慢（>1s）時**靜默停用** CGEventTap，之後所有按鍵事件都收不到。

目前 `hotkey/listener.py` 只在啟動時 `CGEventTapEnable` 一次（listener.py:207），沒有：
1. 處理 `kCGEventTapDisabledByTimeout` / `kCGEventTapDisabledByUserInput` 事件
2. watchdog 定期檢查 tap 狀態
3. 避免 callback 內做慢速 I/O（keystrike log 每次 key event 直接 `open(file, "a")`）

## Scope

三層防禦：

1. **Callback 內即時重啟**：`_macos_callback` 開頭攔截 `kCGEventTapDisabledBy*`，立刻 re-enable + `log.warning`
2. **Watchdog 備援**：QTimer 每 5 秒從 main thread 呼叫 `CGEventTapIsEnabled`，掉了就 re-enable
3. **Keystrike log 重構**：callback 內的檔案 I/O 改推入 `queue.Queue`，獨立 writer thread 每 0.5 秒 flush
4. **Re-enable 時全量 reset state**：避免「按住中被掉線」導致 `_key_states` 殘留產生第二次假死

## Non-goals

- 改動 Windows 分支（`_start_windows`）
- 改動 Linux 支援
- 改用 NSEvent global monitor 取代 CGEventTap

## Success Criteria

- Tap 因 timeout 被停用後，callback 內收到 disable 事件 → 100ms 內自動 re-enable
- 即使 layer 1 失效，watchdog 最多 5 秒後 re-enable
- Callback 單次執行時間從 ~數百 ms（含檔案 I/O）降至 <1 ms（queue put）
- 按住熱鍵過程中 tap 掉線 → re-enable 後下次按鍵即生效（不會殘留假死）
