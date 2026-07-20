import ast
import operator
import webbrowser
import time
from datetime import datetime
import httpx

def get_weather():
    """使用 wttr.in 獲取當地天氣文字描述。"""
    try:
        # wttr.in/?format=3 回傳簡短的一行天氣
        response = httpx.get("https://wttr.in/?format=3", timeout=5.0)
        if response.status_code == 200:
            return f"當前天氣：{response.text.strip()}"
    except Exception as e:
        return f"無法獲取天氣資訊：{e}"
    return "天氣伺服器暫時沒有回應。"

def get_current_time():
    now = datetime.now()
    return f"現在時間是：{now.strftime('%Y-%m-%d %H:%M:%S')}"

def open_google_search(query: str):
    if not query: return "請提供搜尋關鍵字。"
    url = f"https://www.google.com/search?q={query}"
    # v2.7.32: 禁用自動開啟瀏覽器，改為返回 URL 供使用者參考
    print(f"[action] Prevented opening Google: {url}")
    # import pyperclip; pyperclip.copy(url) # 可選：改存到剪貼簿
    return f"【搜尋連結已建立】{url}"

def open_website(url: str):
    if not url.startswith("http"):
        url = "https://" + url
    # v2.7.32: 禁用自動開啟瀏覽器
    print(f"[action] Prevented opening URL: {url}")
    return f"【網頁連結已建立】{url}"

# --- REVIEW.md 風險排序表 #11：計算機改用 ast 白名單解析，移除 eval() ---
# 舊實作只靠正則清洗字元後直接 eval(clean_expr)：清洗雖然把注入面收得很
# 窄，但 eval() 本身仍然是「執行任意 Python 表達式」的通用機制，理論上只要
# 清洗邏輯有漏洞（例如忘記擋掉某個字元組合）就直接淪為任意程式碼執行。改
# 用 ast.parse(mode="eval") 對語法樹逐節點檢查，只允許數字常數與加減乘除、
# 次方、取模、整數除法、正負號——沒有 Name/Call/Attribute 等節點，
# `__import__`、屬性存取、函式呼叫這類節點在解析階段就會被直接拒絕，不是
# 靠字串黑名單擋。
_ALLOWED_BINOPS = {
    ast.Add: operator.add,
    ast.Sub: operator.sub,
    ast.Mult: operator.mul,
    ast.Div: operator.truediv,
    ast.Pow: operator.pow,
    ast.Mod: operator.mod,
    ast.FloorDiv: operator.floordiv,
}
_ALLOWED_UNARYOPS = {
    ast.UAdd: operator.pos,
    ast.USub: operator.neg,
}
_MAX_POW_EXPONENT = 1000  # 避免 9**9**9 這類天文數字讓計算卡住


def _safe_eval_node(node):
    if isinstance(node, ast.Expression):
        return _safe_eval_node(node.body)
    if isinstance(node, ast.Constant):
        if isinstance(node.value, bool) or not isinstance(node.value, (int, float)):
            raise ValueError(f"Unsupported constant: {node.value!r}")
        return node.value
    if isinstance(node, ast.BinOp):
        op_type = type(node.op)
        if op_type not in _ALLOWED_BINOPS:
            raise ValueError(f"Unsupported operator: {op_type.__name__}")
        left = _safe_eval_node(node.left)
        right = _safe_eval_node(node.right)
        if op_type is ast.Pow and abs(right) > _MAX_POW_EXPONENT:
            raise ValueError("Exponent too large")
        return _ALLOWED_BINOPS[op_type](left, right)
    if isinstance(node, ast.UnaryOp):
        op_type = type(node.op)
        if op_type not in _ALLOWED_UNARYOPS:
            raise ValueError(f"Unsupported unary operator: {op_type.__name__}")
        return _ALLOWED_UNARYOPS[op_type](_safe_eval_node(node.operand))
    raise ValueError(f"Unsupported expression node: {type(node).__name__}")


def safe_calculate(expr: str):
    """安全地計算一個只含數字與 + - * / ** % // () 的算式字串。

    只接受 ast 白名單裡的節點類型（常數、二元運算、正負號）；任何其他節點
    （名稱查找、函式呼叫、屬性存取、串列/字典等）在 ast.parse 之後的檢查
    階段就會被 ValueError 擋下，不會被執行。
    """
    tree = ast.parse(expr, mode="eval")
    return _safe_eval_node(tree)


def run_calculator(expr: str):
    # 簡單的計算機邏輯，使用安全的計算方式或交給 LLM
    # 這裡先做基礎字串清理，把中文/符號運算子換成 Python 運算子
    clean_expr = (
        expr.replace("x", "*")
        .replace("÷", "/")
        .replace("加", "+")
        .replace("減", "-")
        .replace("乘", "*")
        .replace("除以", "/")
        .replace("^", "**")  # 次方
    )
    # 移除所有非數字與運算符
    import re
    clean_expr = re.sub(r'[^\d\+\-\*\/\.\(\) ]', '', clean_expr)
    try:
        result = safe_calculate(clean_expr)
        return f"計算結果：{expr} = {result}"
    except Exception:
        return f"抱歉，我算不出來：{expr}"
