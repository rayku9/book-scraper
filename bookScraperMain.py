"""
Barnes & Noble book scraper

Behavior of scraper may change with b&n site
"""

import time
from typing import Optional

import requests
from bs4 import BeautifulSoup
from flask import Flask, jsonify

app = Flask(__name__, static_url_path="", static_folder="static")

TARGET_URL = ("https://www.barnesandnoble.com/b/books/teens-ya/"
    "science-technology-teens/_/N-29Z8q8Z19vx?Ns=P_Sales_Rank%7C0")

# realistic user
HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
    )
}

# CSS
SELECTORS = {
    "record": ("li", "pb-s mt-m bd-bottom-disabled-gray record"),
    "author": ("div", "product-shelf-author contributors"),
    "title": ("h3", "product-info-title"),
}

# cache
CACHE_SECONDS = 600
_cache: dict = {"timestamp": 0.0, "data": None}


def _extract_text(record, tag: str, class_name: str) -> Optional[str]:
    """get text out of element"""
    element = record.find(tag, class_=class_name)
    if element is None:
        return None

    text = element.text.strip()
    # author names often prefixed by --, needs to be removed
    if text.lower().startswith("by "):
        text = text[3:].strip()
    return text


def scrape_books() -> list:
    """get page and parse out (author, title) pairs"""
    response = requests.get(TARGET_URL, headers=HEADERS, timeout=10)
    response.raise_for_status()

    soup = BeautifulSoup(response.text, "html.parser")
    record_tag, record_class = SELECTORS["record"]
    records = soup.find_all(record_tag, class_=record_class)

    books = []
    for record in records:
        author = _extract_text(record, *SELECTORS["author"])
        title = _extract_text(record, *SELECTORS["title"])

        # skip any incomplete records
        if not author or not title:
            continue

        books.append({"author": author, "title": title})

    return books


@app.route("/getbooks")
def get_books():
    now = time.time()
    if _cache["data"] is not None and (now - _cache["timestamp"]) < CACHE_SECONDS:
        return jsonify(_cache["data"])

    try:
        books = scrape_books()
    except requests.RequestException as exc:
        return jsonify({"error": f"Failed to fetch listing page: {exc}"}), 502

    _cache["data"] = books
    _cache["timestamp"] = now
    return jsonify(books)


@app.route("/")
def root():
    return app.send_static_file("index.html")


if __name__ == "__main__":
    # run
    app.run(host="127.0.0.1", port=5000, debug=True)
    