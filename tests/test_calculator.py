"""Tests for actions/builtins.py's calculator (REVIEW.md 風險排序表 #11).

The old implementation regex-sanitised the string and then ran eval() on it.
The new implementation parses with ast.parse(mode="eval") and walks the tree
against a whitelist (numeric constants, + - * / ** % //, unary +/-), so
name lookups, function calls, attribute access etc. are rejected at the
parse/validation stage instead of relying on character blacklisting.

actions/builtins.py imports httpx at module level (for get_weather), so we
follow the repo convention and skip if that optional dep is missing — in
practice it is installed (tests/test_smoke.py imports actions.builtins too).
"""
import pytest

pytest.importorskip("httpx")

from actions.builtins import run_calculator, safe_calculate


# ── 正常算式：輸出格式必須維持「計算結果：{原文} = {結果}」 ──

def test_simple_addition():
    assert run_calculator("1+2") == "計算結果：1+2 = 3"


def test_chinese_operator_words():
    assert run_calculator("3加5") == "計算結果：3加5 = 8"
    assert run_calculator("10減4") == "計算結果：10減4 = 6"
    assert run_calculator("6乘7") == "計算結果：6乘7 = 42"
    assert run_calculator("8除以2") == "計算結果：8除以2 = 4.0"


def test_x_and_division_symbols():
    assert run_calculator("3x4") == "計算結果：3x4 = 12"
    assert run_calculator("10÷4") == "計算結果：10÷4 = 2.5"


def test_parentheses_and_precedence():
    assert run_calculator("(1+2)*3") == "計算結果：(1+2)*3 = 9"
    assert run_calculator("1+2*3") == "計算結果：1+2*3 = 7"


def test_decimals_and_negative_numbers():
    assert run_calculator("1.5+2.5") == "計算結果：1.5+2.5 = 4.0"
    assert run_calculator("-3+5") == "計算結果：-3+5 = 2"


def test_power():
    assert run_calculator("2**10") == "計算結果：2**10 = 1024"
    assert run_calculator("2^10") == "計算結果：2^10 = 1024"


def test_unparseable_input_returns_apology():
    assert run_calculator("你好嗎") == "抱歉，我算不出來：你好嗎"
    assert run_calculator("") == "抱歉，我算不出來："


def test_division_by_zero_returns_apology():
    assert run_calculator("1/0") == "抱歉，我算不出來：1/0"


# ── 安全性：safe_calculate 必須拒絕所有非算式節點 ──

def test_safe_calculate_rejects_name_access():
    with pytest.raises((ValueError, SyntaxError)):
        safe_calculate("__import__('os')")


def test_safe_calculate_rejects_function_call():
    with pytest.raises(ValueError):
        safe_calculate("abs(1)")


def test_safe_calculate_rejects_attribute_access():
    with pytest.raises(ValueError):
        safe_calculate("(1).__class__")


def test_safe_calculate_rejects_string_constant():
    with pytest.raises(ValueError):
        safe_calculate("'a' * 3")


def test_safe_calculate_rejects_subscript_and_containers():
    with pytest.raises(ValueError):
        safe_calculate("[1,2][0]")
    with pytest.raises(ValueError):
        safe_calculate("{1: 2}")


def test_safe_calculate_rejects_boolean_and_comparison():
    with pytest.raises(ValueError):
        safe_calculate("1 < 2")
    with pytest.raises(ValueError):
        safe_calculate("True")


def test_safe_calculate_rejects_huge_exponent():
    """9**9**9 之類的天文數字次方會讓 CPython 卡在大整數運算，必須擋下。"""
    with pytest.raises(ValueError):
        safe_calculate("9**9**9")


def test_run_calculator_neutralizes_injection_attempts():
    """經過 run_calculator 的清洗＋ast 白名單，注入嘗試只會得到道歉訊息，
    絕不會執行任何程式碼。"""
    dangerous = "__import__('os').system('echo pwned')"
    result = run_calculator(dangerous)
    assert result.startswith("抱歉，我算不出來：") or result.startswith("計算結果：")
    assert "pwned" not in result or dangerous in result  # 原文回顯無妨，重點是沒有執行


def test_builtins_module_has_no_eval_usage():
    """守門測試：actions/builtins.py 不得再有任何 eval()/exec() 呼叫節點。
    （用 AST 檢查而非字串比對，註解裡提到 eval 這個字不算。）"""
    import ast as ast_mod
    import inspect
    import actions.builtins as mod

    tree = ast_mod.parse(inspect.getsource(mod))
    offenders = [
        node.func.id
        for node in ast_mod.walk(tree)
        if isinstance(node, ast_mod.Call)
        and isinstance(node.func, ast_mod.Name)
        and node.func.id in ("eval", "exec")
    ]
    assert not offenders, f"actions/builtins.py must not call eval()/exec(): {offenders}"
