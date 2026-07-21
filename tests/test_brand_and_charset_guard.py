"""守門測試：防止「品牌改名／簡體字」問題回流。

背景（2026-07-22 品牌殘留清掃任務）：維護者發現程式改名為「聲成文 VoxProse」
後，UI 仍多處顯示舊名「嘴炮輸入法」，README 也混入簡體字「个人」。這些問題
本質上是同一類回歸——散落在多個檔案的文字資產，人工全文審閱容易漏網。本檔
把當時的清掃結果轉成 CI 會擋下的守門測試，往後任何人（或 AI agent）不小心
打回舊名/簡體字/原作者個人網址，pytest 會直接失敗。

三道守門：
1. `test_no_simplified_characters_in_repo`
   全 repo 逐字元比對「簡體字→繁體字」對照表，抓出非正體用字。刻意採 Python
   逐字元比對而非 grep 的 regex／位元組比對，避免多位元組 UTF-8 序列的假陽性
   （AGENTS.md/CLAUDE.md 記載過這個教訓）。對照表只收錄「不會在正體中文語境
   中合法獨立出現」的簡體字，刻意排除后/裡/台/出/干/谷/舍/志/卷/表/只/沖/松/
   着/系/斗/肯/皮/耳/蒙/薄/藏 這類在正體中文裡也是合法獨立字的多音義字，避免
   誤殺「皇后」「公里」之類的合法正體用法。
2. `test_no_legacy_brand_name_in_ui`
   `ui/**` 原始碼不得出現舊產品自稱「嘴炮輸入法」／「嘴砲輸入法」——這是
   使用者實際會在視窗/選單看到的文案，必須跟品牌名同步；`NOTICE.md`／
   `README*.md`／`LICENSE`／`VERSIONS.md` 等描述「歷史沿革／fork 出處」的
   文件不受此限（見 docs/DECISIONS.md 對「歷史沿革語意 vs. 品牌自稱」的
   判斷準則）。
3. `test_no_legacy_author_personal_urls_in_ui`
   `ui/**` 原始碼不得含原作者個人社群/贊助網域字串（2026-07-22 維護者指示
   移除 SNS 按鈕與導流連結後新增）。上游 GitHub repo 連結
   （`jfamily4tw/voicetype4tw-mac`）屬必要的溯源資訊，不在此限——這道測試
   只鎖「個人社群/贊助域名」，不鎖「上游專案來源」。
"""
import os
import subprocess
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent

# 這個測試檔本身的對照表 dict 字面量會含大量簡體字（拿來當比對用），必須排除
# 自己，否則會誤判自己有問題。
_SELF_RELATIVE_PATH = Path(__file__).resolve().relative_to(REPO_ROOT).as_posix()


# ---------------------------------------------------------------------------
# 1. 簡體字掃描
# ---------------------------------------------------------------------------

# 簡體專用字 → 繁體對照表：僅收錄「不會在正體中文語境中合法獨立出現」的簡體
# 字。刻意排除在正體中文裡也是合法獨立字的多音義候選字（后/裡⇔里/台/出/干/
# 谷/舍/志/卷/表/只/沖/松/着/系/斗/肯/皮/耳/蒙/薄/藏……），避免誤殺「皇后」
# 「公里」「台灣」之類的合法正體用法。可視需要擴充，但新增前務必先確認該字
# 沒有這類歧義。
_SIMP_TO_TRAD = {
    "个": "個", "这": "這", "问": "問", "题": "題", "说": "說", "时": "時",
    "会": "會", "对": "對", "开": "開", "关": "關", "应": "應", "该": "該",
    "数": "數", "据": "據", "实": "實", "现": "現", "显": "顯", "设": "設",
    "备": "備", "处": "處", "优": "優", "让": "讓", "从": "從", "为": "為",
    "与": "與", "并": "並", "电": "電", "单": "單", "双": "雙", "变": "變",
    "总": "總", "结": "結", "线": "線", "组": "組", "级": "級", "统": "統",
    "继": "繼", "续": "續", "维": "維", "输": "輸", "载": "載", "辑": "輯",
    "转": "轉", "编": "編", "码": "碼", "页": "頁", "类": "類", "风": "風",
    "验": "驗", "错": "錯", "键": "鍵", "长": "長", "间": "間", "见": "見",
    "发": "發", "经": "經", "过": "過", "还": "還", "进": "進", "运": "運",
    "选": "選", "适": "適", "银": "銀", "静": "靜", "须": "須", "预": "預",
    "领": "領", "频": "頻", "颜": "顏", "习": "習", "乐": "樂", "买": "買",
    "卖": "賣", "东": "東", "车": "車", "软": "軟", "网": "網", "标": "標",
    "击": "擊", "图": "圖",
    "书": "書", "画": "畫", "术": "術", "医": "醫", "药": "藥", "务": "務",
    "刚": "剛", "刘": "劉", "华": "華", "汉": "漢", "记": "記",
    "认": "認", "识": "識", "语": "語", "详": "詳", "议": "議", "论": "論",
    "谈": "談", "请": "請", "读": "讀", "讲": "講", "许": "許", "诉": "訴",
    "评": "評", "调": "調", "证": "證", "试": "試", "课": "課", "词": "詞",
    "译": "譯", "护": "護", "报": "報", "担": "擔", "拥": "擁", "择": "擇",
    "拦": "攔", "拨": "撥", "挂": "掛", "挥": "揮", "损": "損", "换": "換",
    "断": "斷", "无": "無", "旧": "舊", "机": "機",
    "权": "權", "杂": "雜", "极": "極", "构": "構", "样": "樣", "档": "檔",
    "梦": "夢", "检": "檢", "欢": "歡", "汇": "匯", "汤": "湯", "沟": "溝",
    "没": "沒", "泪": "淚", "洁": "潔", "测": "測", "浊": "濁", "涂": "塗",
    "润": "潤", "涨": "漲", "灭": "滅", "灯": "燈", "点": "點", "热": "熱",
    "爱": "愛", "牵": "牽", "犹": "猶", "环": "環", "琐": "瑣", "疗": "療",
    "盘": "盤", "监": "監",
    "睁": "睜", "矿": "礦", "礼": "禮", "祸": "禍", "种": "種",
    "积": "積", "称": "稱", "简": "簡", "粮": "糧",
    "红": "紅", "纪": "紀", "纯": "純", "纸": "紙", "纲": "綱",
    "纳": "納", "纵": "縱", "纷": "紛", "纹": "紋", "练": "練",
    "细": "細", "织": "織", "终": "終", "绍": "紹",
    "绑": "綁", "给": "給", "络": "絡", "绝": "絕",
    "绩": "績", "绪": "緒", "绿": "綠", "缘": "緣", "缓": "緩",
    "缩": "縮", "罗": "羅", "义": "義",
    "职": "職", "联": "聯", "肃": "肅", "肤": "膚", "肮": "骯",
    "胁": "脅", "胆": "膽", "胜": "勝", "脏": "髒", "脑": "腦", "腊": "臘",
    "腾": "騰", "舰": "艦", "艰": "艱", "芦": "蘆", "苍": "蒼", "范": "範",
    "茎": "莖", "荐": "薦", "荡": "蕩", "莹": "瑩", "萧": "蕭", "营": "營",
    "蔷": "薔", "蔼": "藹",
    "虏": "虜", "虑": "慮", "虫": "蟲", "虽": "雖", "衅": "釁", "补": "補",
    "衬": "襯", "袄": "襖", "视": "視", "觉": "覺", "触": "觸", "计": "計",
    "训": "訓", "讯": "訊", "讨": "討", "讼": "訟",
    "访": "訪", "诈": "詐", "诊": "診", "诗": "詩", "诚": "誠",
    "话": "話", "诞": "誕", "询": "詢", "诫": "誡",
    "误": "誤", "诵": "誦", "诸": "諸", "诺": "諾", "扫": "掃",
}

# 掃描的文字副檔名（避免對 assets/ 等二進位資產做文字解碼）
_TEXT_EXTS = {
    ".py", ".ps1", ".bat", ".iss", ".cs", ".yml", ".yaml", ".md", ".txt",
    ".json", ".cfg", ".ini", ".toml",
}
_EXCLUDE_DIR_PREFIXES = ("assets/",)
_NO_EXT_TEXT_BASENAMES = {"LICENSE", "NOTICE"}


def _git_ls_files():
    out = subprocess.run(
        ["git", "ls-files"], cwd=REPO_ROOT, capture_output=True, text=True,
        check=True, encoding="utf-8", errors="replace",
    )
    return out.stdout.splitlines()


def _is_text_candidate(rel_path: str) -> bool:
    if rel_path.startswith(_EXCLUDE_DIR_PREFIXES):
        return False
    if rel_path == _SELF_RELATIVE_PATH:
        return False
    _, ext = os.path.splitext(rel_path)
    if ext:
        return ext.lower() in _TEXT_EXTS
    return os.path.basename(rel_path) in _NO_EXT_TEXT_BASENAMES


def _find_simplified_chars():
    hits = []
    for rel in _git_ls_files():
        if not _is_text_candidate(rel):
            continue
        full = REPO_ROOT / rel
        try:
            text = full.read_text(encoding="utf-8")
        except (UnicodeDecodeError, FileNotFoundError, IsADirectoryError):
            continue
        for lineno, line in enumerate(text.splitlines(), start=1):
            for ch in line:
                if ch in _SIMP_TO_TRAD:
                    hits.append(f"{rel}:{lineno}: '{ch}' -> '{_SIMP_TO_TRAD[ch]}' | {line.strip()}")
    return hits


def test_no_simplified_characters_in_repo():
    hits = _find_simplified_chars()
    assert not hits, (
        "發現疑似簡體字（見 tests/test_brand_and_charset_guard.py 對照表）：\n"
        + "\n".join(hits)
    )


# ---------------------------------------------------------------------------
# 2. 舊品牌名稱（使用者可見 UI 字串）
# ---------------------------------------------------------------------------

_LEGACY_BRAND_STRINGS = ["嘴炮輸入法", "嘴砲輸入法", "嘴炮", "嘴砲"]


def _iter_ui_py_files():
    ui_dir = REPO_ROOT / "ui"
    for path in ui_dir.rglob("*.py"):
        if "__pycache__" in path.parts:
            continue
        yield path


def test_no_legacy_brand_name_in_ui():
    hits = []
    for path in _iter_ui_py_files():
        text = path.read_text(encoding="utf-8")
        rel = path.resolve().relative_to(REPO_ROOT).as_posix()
        for lineno, line in enumerate(text.splitlines(), start=1):
            for needle in _LEGACY_BRAND_STRINGS:
                if needle in line:
                    hits.append(f"{rel}:{lineno}: contains legacy brand string '{needle}' | {line.strip()}")
    assert not hits, (
        "ui/** 出現舊品牌自稱「嘴炮輸入法/嘴砲輸入法」，使用者可見文案必須改為"
        "「聲成文」/「VoxProse」：\n" + "\n".join(hits)
    )


# ---------------------------------------------------------------------------
# 3. 原作者個人社群／贊助網址（2026-07-22 新增）
# ---------------------------------------------------------------------------

# 注意：這裡刻意只鎖「個人社群/贊助網域」，不鎖上游 GitHub repo
# （jfamily4tw/voicetype4tw-mac）——那是必要的 fork 溯源資訊，文件裡允許保留。
_LEGACY_AUTHOR_URL_NEEDLES = [
    "jimmy4tw", "Jimmy4.TW", "jimmy4.tw", "portaly.cc", "hi.jimmy4.tw",
    "buymeacoffee", "linepay", "acykjcms",
]


def test_no_legacy_author_personal_urls_in_ui():
    hits = []
    for path in _iter_ui_py_files():
        text = path.read_text(encoding="utf-8")
        rel = path.resolve().relative_to(REPO_ROOT).as_posix()
        lower_lines = text.splitlines()
        for lineno, line in enumerate(lower_lines, start=1):
            low = line.lower()
            for needle in _LEGACY_AUTHOR_URL_NEEDLES:
                if needle.lower() in low:
                    hits.append(f"{rel}:{lineno}: contains legacy author URL fragment '{needle}' | {line.strip()}")
    assert not hits, (
        "ui/** 出現原作者個人社群/贊助網址殘留，本 fork 不應在自己的 UI 裡替"
        "原作者導流（見 docs/DECISIONS.md 2026-07-22 決策）：\n" + "\n".join(hits)
    )


if __name__ == "__main__":
    import sys
    sys.exit(pytest.main([__file__, "-v"]))
