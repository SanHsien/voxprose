# Tasks

- [x] Layer 1: `_macos_callback` 開頭攔截 `kCGEventTapDisabledByTimeout` / `kCGEventTapDisabledByUserInput`，即時 `CGEventTapEnable(True)` + `reset_state()` + log
- [x] Layer 2: 新增 `_start_watchdog()` 以 `threading.Timer` 循環每 5 秒檢查 `CGEventTapIsEnabled`（非 Qt thread，避免與 rumps/qt 耦合）
- [x] Layer 3a: 新增 `_keystrike_queue: queue.Queue` + `_keystrike_writer_loop()` daemon thread
- [x] Layer 3b: `_macos_callback` 內原本 `open(KEYSTRIKE_LOG_PATH, "a")` 改為 `_keystrike_queue.put_nowait((timestamp, ev_type, keycode, matched_mode))`
- [x] `stop()` 正確停 watchdog + flush keystrike queue
- [x] Log warnings with counter: 紀錄 tap 掉線次數，方便後續觀察
