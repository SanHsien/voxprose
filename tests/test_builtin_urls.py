"""語音指令產生的連結要是可用的網址。

Regression:
- open_google_search 把查詢字串原樣接在 `?q=` 後面，「查 AT&T 股價」的 `&`、
  空白、`#` 會截斷或拆開查詢參數，產生的連結搜的不是使用者說的詞。
- open_website 用 startswith("http") 判斷是否已有通訊協定，「httpbin.org」
  這類以 http 開頭的網域不會補 https://，產出的不是網址。
"""
from actions.builtins import open_google_search, open_website


def test_google_search_escapes_query_delimiters():
    out = open_google_search("AT&T stock #1")
    assert "q=AT%26T%20stock%20%231" in out


def test_google_search_keeps_cjk_readable():
    assert "q=特斯拉股價" in open_google_search("特斯拉股價")


def test_google_search_empty_query():
    assert open_google_search("") == "請提供搜尋關鍵字。"


def test_open_website_adds_scheme_for_domains_starting_with_http():
    assert "https://httpbin.org" in open_website("httpbin.org")
    assert "https://httpd.apache.org" in open_website("httpd.apache.org")


def test_open_website_keeps_existing_scheme():
    assert "http://example.com" in open_website("http://example.com")
    assert "https://example.com" in open_website("https://example.com")
    assert "https://https://" not in open_website("https://example.com")
