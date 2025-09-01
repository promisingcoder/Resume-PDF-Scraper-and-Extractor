from typing import List, Set, Optional
from urllib.parse import quote_plus
import os
import random
import time

from playwright.sync_api import sync_playwright
from .utils import stable_sleep, is_pdf_url, head_is_pdf, USER_AGENT


def build_search_url(base_url: str, query: str) -> str:
    return f"{base_url.rstrip('/')}?q={quote_plus(query)}&category_general=1&language=en&time_range=&safesearch=1&theme=simple"


def fetch_result_links(url: str, max_results: int = 100, timeout_ms: int = 30000, headless: bool = True, debug_dir: Optional[str] = None, ignore_https_errors: bool = True) -> List[str]:
    links: List[str] = []
    seen: Set[str] = set()

    def collect_links_from_page() -> None:
        nonlocal links, seen
        anchors = page.query_selector_all("article.result a.url_header, article.result h3 a")
        for a in anchors:
            href = a.get_attribute("href")
            if not href:
                continue
            if href in seen:
                continue
            seen.add(href)
            links.append(href)

    # Add random delay to avoid rate limiting
    time.sleep(random.uniform(2, 5))
    
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=headless)
        context = browser.new_context(user_agent=USER_AGENT, ignore_https_errors=ignore_https_errors)
        page = context.new_page()
        page.set_default_timeout(timeout_ms)
        
        # Add extra headers to look more like a real browser
        page.set_extra_http_headers({
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.5",
            "Accept-Encoding": "gzip, deflate",
            "DNT": "1",
            "Connection": "keep-alive",
            "Upgrade-Insecure-Requests": "1"
        })
        
        page.goto(url)

        # Initial collect
        stable_sleep(0.7)
        collect_links_from_page()

        # Infinite scroll until max_results or two consecutive no-new scrolls
        no_new_streak = 0
        while len(links) < max_results and no_new_streak < 2:
            prev_count = len(links)
            try:
                page.evaluate("window.scrollBy(0, document.body.scrollHeight);")
            except Exception:
                pass
            stable_sleep(1.0)
            collect_links_from_page()
            if len(links) == prev_count:
                no_new_streak += 1
            else:
                no_new_streak = 0

        # Optional debug dump
        if debug_dir:
            os.makedirs(debug_dir, exist_ok=True)
            try:
                html_path = os.path.join(debug_dir, "search_page.html")
                with open(html_path, "w", encoding="utf-8") as f:
                    f.write(page.content())
            except Exception:
                pass
            try:
                img_path = os.path.join(debug_dir, "search_page.png")
                page.screenshot(path=img_path, full_page=True)
            except Exception:
                pass

        context.close()
        browser.close()

    # Limit results
    if max_results and len(links) > max_results:
        links = links[:max_results]
    return links


def filter_pdf_links(urls: List[str]) -> List[str]:
    pdfs: List[str] = []
    for url in urls:
        if is_pdf_url(url) or head_is_pdf(url):
            pdfs.append(url)
    return pdfs
