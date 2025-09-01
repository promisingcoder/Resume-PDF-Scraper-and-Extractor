import os
import re
import time
import hashlib
from urllib.parse import urlparse, urljoin

import requests


USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/138.0.0.0 Safari/537.36"
)


def ensure_directory(path: str) -> None:
    if not os.path.exists(path):
        os.makedirs(path, exist_ok=True)


def sanitize_filename(name: str, default: str = "file") -> str:
    name = re.sub(r"[\\/:*?\"<>|]+", "_", name)
    name = name.strip().strip(".")
    return name or default


def is_pdf_url(url: str) -> bool:
    parsed = urlparse(url)
    path = parsed.path.lower()
    return path.endswith(".pdf")


def absolutize_url(base_url: str, href: str) -> str:
    try:
        return urljoin(base_url, href)
    except Exception:
        return href


def head_is_pdf(url: str, timeout: int = 15) -> bool:
    try:
        resp = requests.head(url, allow_redirects=True, timeout=timeout, headers={"User-Agent": USER_AGENT})
        ctype = resp.headers.get("Content-Type", "").lower()
        return "application/pdf" in ctype
    except Exception:
        return False


def stable_sleep(seconds: float) -> None:
    end = time.time() + seconds
    while time.time() < end:
        time.sleep(min(0.05, end - time.time()))


def hash_for_url(url: str) -> str:
    return hashlib.sha256(url.encode("utf-8", errors="ignore")).hexdigest()[:12]
