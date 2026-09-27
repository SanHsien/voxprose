"""ui.settings — SettingsWindow 拆分後的分頁子套件（REVIEW.md #7）。

`ui/settings_window.py`（原本 ~2164 行的 god file）依設定頁拆分到這個子套件，
每個頁面一個檔案 + 共用元件/常數集中在 `common.py`。`ui/settings_window.py`
保留為薄殼：組裝 `SettingsWindow` 類別（用 mixin 多重繼承把各頁的方法混入同一
個類別，行為與拆分前完全相同——`self.xxx` 呼叫不因為方法定義在哪個檔案而改變），
對外 `from ui.settings_window import SettingsWindow` 這條路徑不變。

本套件不對外匯出任何符號；請一律經由 `ui.settings_window` 存取
`SettingsWindow`，不要直接 import 這裡的分頁 mixin 類別。
"""
