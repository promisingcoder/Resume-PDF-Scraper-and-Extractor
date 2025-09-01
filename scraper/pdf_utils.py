import os
from typing import List, Optional
from multiprocessing import Process, Queue

import fitz  # PyMuPDF
import requests
from .utils import ensure_directory, sanitize_filename, USER_AGENT


def download_pdf(url: str, download_dir: str, timeout: int = 1200) -> Optional[str]:
    ensure_directory(download_dir)
    try:
        filename = sanitize_filename(os.path.basename(url.split("?", 1)[0]) or "document.pdf", default="document.pdf")
        if not filename.lower().endswith(".pdf"):
            filename += ".pdf"
        dest_path = os.path.join(download_dir, filename)
        with requests.get(url, stream=True, timeout=timeout, headers={"User-Agent": USER_AGENT}) as r:
            r.raise_for_status()
            with open(dest_path, "wb") as f:
                for chunk in r.iter_content(chunk_size=8192):
                    if chunk:
                        f.write(chunk)
        return dest_path
    except Exception:
        return None


def extract_pdf_pages_text(pdf_path: str) -> List[str]:
    pages: List[str] = []
    with fitz.open(pdf_path) as doc:
        for page in doc:
            text = page.get_text("text")
            pages.append(text or "")
    return pages


def _extract_worker(pdf_path: str, q: Queue) -> None:
    try:
        pages = extract_pdf_pages_text(pdf_path)
        q.put(pages)
    except Exception:
        q.put(None)


def extract_pdf_pages_text_with_timeout(pdf_path: str, timeout_seconds: int = 1200) -> Optional[List[str]]:
    q: Queue = Queue()
    p: Process = Process(target=_extract_worker, args=(pdf_path, q))
    p.start()
    p.join(timeout_seconds)
    if p.is_alive():
        try:
            p.terminate()
        finally:
            p.join()
        return None
    try:
        return q.get_nowait()
    except Exception:
        return None
