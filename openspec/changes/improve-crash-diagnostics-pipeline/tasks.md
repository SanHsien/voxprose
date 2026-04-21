# Tasks

- [x] 新增 `utils/diagnostics.py` — 環境資訊、匯出診斷包邏輯
- [x] `main.py` 最頂端：提前 logging init、啟用 faulthandler、寫環境資訊
- [x] `main.py` 每個啟動步驟包 `log.info("[boot] ...")` breadcrumb
- [x] `ui/settings_window.py` 新增「匯出診斷包」按鈕（放在「關於/除錯」區域）
- [x] Config 脫敏：`utils/diagnostics.py` 內抹除 `*_api_key`
- [x] 本機測試匯出功能
