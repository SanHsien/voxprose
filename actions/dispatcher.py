import re
from actions.builtins import get_weather, get_current_time, open_google_search, open_website, run_calculator

class ActionManager:
    def __init__(self, injector, indicator):
        self.injector = injector
        self.indicator = indicator

    def dispatch(self, text: str) -> bool:
        """
        解析語音文字，如果匹配到指令則執行動作並回傳 True，否則回傳 False。
        """
        text = text.strip("。，！？ ")
        
        # 1. 天氣
        if re.search(r"天氣(如何|怎麼樣|好不好)?$", text) or "查天氣" in text:
            result = get_weather()
            self._finish_action(result)
            return True
            
        # 2. 時間
        if re.search(r"(現在)?幾點(了)?$|現在時間", text):
            result = get_current_time()
            self._finish_action(result)
            return True
            
        # 3. 搜尋
        search_match = re.search(r"(幫我)?(搜尋|搜一下|查一下|查詢一下|查詢|查|找一下)(.+)", text)
        if search_match:
            query = search_match.group(3).strip()
            # 移除開頭或結尾的贅詞以提升搜尋精準度
            # 例如 "幫我查一下 [特斯拉的股價]" 中的 "一下" 可能被誤抓進 query
            query = re.sub(r"^(一下|看看|看看是|到底|一下關於)", "", query).strip()
            query = re.sub(r"(是多少|幾塊錢|是多少錢|的價格|是什麼|是什麼呢)$", "", query).strip()
            result = open_google_search(query)
            self._finish_action(result)
            return True
            
        # 4. 開網頁
        web_match = re.search(r"(打開|開啟)(?:網站)?(.+)", text)
        if web_match:
            site = web_match.group(2).strip()
            # 排除掉常見的情境名稱，避免誤觸
            if site not in ["客訴模式", "IG模式", "正常模式"]:
                result = open_website(site)
                self._finish_action(result)
                return True

        # 5. 計算機
        if re.search(r"\d+[\+\-\*\/x加減乘除]", text):
            result = run_calculator(text)
            self._finish_action(result)
            return True

        # 6. 切換模式 (System Switch)
        switch_match = re.search(r"(切換|換到|變成|設定為)(?:至)?(.+)(模式|靈魂|人格|情境)?", text)
        if switch_match:
            target = switch_match.group(2).strip()
            # 依據關鍵字判斷目標
            if "國語" in target or "中文" in target or "正常" in target:
                msg = self._perform_switch(translation_lang=None, active_scenario="default")
            elif "英文" in target:
                msg = self._perform_switch(translation_lang="en", active_scenario="商務回應") # v2.7.32: 商務英文已刪除，改用商務回應
            elif "日文" in target:
                msg = self._perform_switch(translation_lang="ja")
            elif "情商" in target or "大師" in target:
                msg = self._perform_switch(active_scenario="情商大師")
            elif "商務回應" in target or "回應" in target:
                msg = self._perform_switch(active_scenario="商務回應")
            elif "社群" in target or "貼文" in target:
                 msg = self._perform_switch(active_scenario="社群貼文")
            else:
                return False
            
            self._finish_action(msg)
            return True

        return False

    def _perform_switch(self, translation_lang=None, active_scenario=None):
        """執行設定變更並存檔。"""
        from config import load_config, save_config
        cfg = load_config()
        updated = False
        msg = "模式已切換"
        
        if translation_lang is not None or "translation_lang" in cfg:
            cfg["translation_lang"] = translation_lang
            updated = True
            msg = f"已切換至 {translation_lang or '自動'} 語系"
            
        if active_scenario:
            cfg["active_scenario"] = active_scenario
            updated = True
            msg += f" 並載入 {active_scenario} 情境"
            
        if updated:
            save_config(cfg)
            # 觸發主程式重載 (這裡暫時透過存檔觸發，因為 main 有監聽或定時重載，或是之後由 main 呼叫 refresh)
            return msg
        return "未偵測到變動"

    def _finish_action(self, msg: str):
        """執行完動作後的統一回饋。"""
        self.indicator.flash()
        self.indicator.set_state("done")
        # 語音指令的回應通常也直接注入到目前輸入框，或是僅在 Dashboard 顯示
        # 這裡設定直接注入，方便使用者直接得到答案
        self.injector.inject(f"「{msg}」")
