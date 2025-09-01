from typing import List, Set

from playwright.sync_api import sync_playwright
from .utils import is_pdf_url, head_is_pdf, absolutize_url, stable_sleep, USER_AGENT


def discover_pdf_links_from_pages(urls: List[str], timeout_ms: int = 30000, max_per_page: int = 20, headless: bool = True, ignore_https_errors: bool = True) -> List[str]:
    discovered: List[str] = []
    seen: Set[str] = set()

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=headless)
        context = browser.new_context(user_agent=USER_AGENT, ignore_https_errors=ignore_https_errors)
        page = context.new_page()
        page.set_default_timeout(timeout_ms)

        for url in urls:
            try:
                page.goto(url)
            except Exception:
                continue
            stable_sleep(0.4)

            anchors = page.query_selector_all("a[href]")
            count = 0
            for a in anchors:
                if count >= max_per_page:
                    break
                href = a.get_attribute("href")
                if not href:
                    continue
                abs_href = absolutize_url(page.url, href)
                if abs_href in seen:
                    continue
                if is_pdf_url(abs_href) or head_is_pdf(abs_href):
                    seen.add(abs_href)
                    discovered.append(abs_href)
                    count += 1

        context.close()
        browser.close()

    return discovered
