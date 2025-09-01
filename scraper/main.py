import os
import sys
import json
import argparse
from typing import List, Dict, Any, Optional

from dotenv import load_dotenv
from tqdm import tqdm

from .searx_scraper import fetch_result_links, filter_pdf_links, build_search_url
from .page_discovery import discover_pdf_links_from_pages
from .pdf_utils import download_pdf, extract_pdf_pages_text_with_timeout
from .openai_extractor import extract_resume_from_pages
from .utils import ensure_directory, hash_for_url


def parse_args(argv: List[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Resume PDF scraper and extractor")

    parser.add_argument("--config", type=str, default=None, help="JSON config file with multiple dorks (urls/queries/items)")

    group = parser.add_mutually_exclusive_group(required=False)
    group.add_argument("--url", type=str, help="Full SearXNG search URL to visit")
    group.add_argument("--query", nargs="+", help="Search query terms to build URL for priv.au")

    parser.add_argument("--base", type=str, default="https://priv.au/search", help="Base search URL (default: priv.au/search)")
    parser.add_argument("--max-results", type=int, default=100, help="Max result links to collect (auto-scrolls until reached or stalled)")

    parser.add_argument("--download-dir", type=str, default="downloads", help="Directory to store PDFs")
    parser.add_argument("--out", type=str, default="output/resumes.jsonl", help="Output JSONL file path")

    parser.add_argument("--model", type=str, default="gpt-4o-mini", help="OpenAI model name")
    parser.add_argument("--timeout-ms", type=int, default=30000, help="Playwright default timeout in ms")

    parser.add_argument("--download-timeout", type=int, default=1200, help="Per-PDF download timeout seconds (default 1200=20min)")
    parser.add_argument("--extract-timeout", type=int, default=1200, help="Per-PDF text extraction timeout seconds (default 1200=20min)")

    headless_group = parser.add_mutually_exclusive_group()
    headless_group.add_argument("--headless", dest="headless", action="store_true", help="Run browser headless (default)")
    headless_group.add_argument("--no-headless", dest="headless", action="store_false", help="Run browser with visible window")
    parser.set_defaults(headless=True)

    # HTTPS certificate error handling
    cert_group = parser.add_mutually_exclusive_group()
    cert_group.add_argument("--ignore-https-errors", dest="ignore_https_errors", action="store_true", help="Ignore HTTPS certificate errors (default)")
    cert_group.add_argument("--strict-cert", dest="ignore_https_errors", action="store_false", help="Do not ignore HTTPS certificate errors")
    parser.set_defaults(ignore_https_errors=True)

    parser.add_argument("--debug-dir", type=str, default=None, help="Directory to save debug HTML/screenshot")

    return parser.parse_args(argv)


def _load_jobs_from_config(config_path: str, default_base: str) -> Dict[str, Any]:
    with open(config_path, "r", encoding="utf-8") as f:
        data = json.load(f)
    return data


def _expand_jobs_from_config(data: Dict[str, Any], default_base: str) -> List[Dict[str, Any]]:
    jobs: List[Dict[str, Any]] = []

    urls = data.get("urls") or []
    for u in urls:
        if isinstance(u, str) and u.strip():
            jobs.append({"url": u.strip()})

    queries = data.get("queries") or []
    for q in queries:
        if isinstance(q, str) and q.strip():
            jobs.append({"query": q.strip(), "base": data.get("base", default_base)})

    for item in data.get("items", []) or []:
        if not isinstance(item, dict):
            continue
        u = item.get("url")
        q = item.get("query")
        b = item.get("base", data.get("base", default_base))
        if isinstance(u, str) and u.strip():
            jobs.append({"url": u.strip()})
        elif isinstance(q, str) and q.strip():
            jobs.append({"query": q.strip(), "base": b})

    return jobs


def _pick_api_key(env_key: Optional[str], config_keys: Optional[List[str]], idx: int) -> Optional[str]:
    # Round-robin between provided config keys; fallback to env
    if config_keys:
        return config_keys[idx % len(config_keys)]
    return env_key


def main(argv: List[str]) -> int:
    load_dotenv()
    args = parse_args(argv)

    # Load config if provided
    config_data: Dict[str, Any] = {}
    if args.config:
        try:
            config_data = _load_jobs_from_config(args.config, args.base)
        except Exception as e:
            print(f"ERROR reading config {args.config}: {e}", file=sys.stderr)
            return 3

    api_keys: Optional[List[str]] = config_data.get("api_keys") if config_data else None

    env_api_key = os.getenv("OPENAI_API_KEY")
    if not env_api_key and not api_keys:
        print("ERROR: OPENAI_API_KEY is not set and no api_keys provided in config.", file=sys.stderr)
        return 2

    ensure_directory(os.path.dirname(args.out) or ".")
    ensure_directory(args.download_dir)

    # Build job list
    if args.config:
        jobs = _expand_jobs_from_config(config_data, args.base)
    else:
        if not args.url and not args.query:
            print("ERROR: provide --config or one of --url / --query", file=sys.stderr)
            return 4
        if args.url:
            jobs = [{"url": args.url}]
        else:
            query_terms = args.query if isinstance(args.query, list) else args.query
            query_str = " ".join(query_terms) if isinstance(query_terms, list) else (query_terms or "")
            jobs = [{"query": query_str, "base": args.base}]

    total_rows_written = 0

    # Process each job sequentially
    for idx, job in enumerate(jobs, start=1):
        if "url" in job:
            url = job["url"]
            label = hash_for_url(url)
        else:
            query_str = job["query"]
            base = job.get("base", args.base)
            url = build_search_url(base, query_str)
            label = hash_for_url(query_str)

        local_debug_dir = None
        if args.debug_dir:
            local_debug_dir = os.path.join(args.debug_dir, f"job_{idx}_{label}")
            ensure_directory(local_debug_dir)

        print(f"[Job {idx}/{len(jobs)}] Visiting search page and auto-scrolling...")
        result_links = fetch_result_links(
            url,
            max_results=args.max_results,
            timeout_ms=args.timeout_ms,
            headless=args.headless,
            debug_dir=local_debug_dir,
            ignore_https_errors=args.ignore_https_errors,
        )

        print(f"[Job {idx}/{len(jobs)}] Collected {len(result_links)} result links. Filtering direct PDFs...")
        direct_pdf_urls = filter_pdf_links(result_links)

        non_pdf_links = [u for u in result_links if u not in direct_pdf_urls]
        print(f"[Job {idx}/{len(jobs)}] Discovering PDFs inside {len(non_pdf_links)} result pages...")
        discovered_pdf_urls = discover_pdf_links_from_pages(
            non_pdf_links,
            timeout_ms=args.timeout_ms,
            headless=args.headless,
            ignore_https_errors=args.ignore_https_errors,
        )

        # Deduplicate
        pdf_url_set = { *direct_pdf_urls, *discovered_pdf_urls }
        pdf_urls = list(pdf_url_set)

        print(f"[Job {idx}/{len(jobs)}] Found {len(pdf_urls)} total PDF links. Downloading & extracting...")
        rows: List[Dict[str, Any]] = []

        for r_idx, pdf_url in enumerate(tqdm(pdf_urls, desc=f"[Job {idx}] PDFs")):
            pdf_path = download_pdf(pdf_url, args.download_dir, timeout=args.download_timeout)
            if not pdf_path:
                continue
            pages = extract_pdf_pages_text_with_timeout(pdf_path, timeout_seconds=args.extract_timeout)
            if pages is None:
                continue

            # Select API key (round-robin across config keys; fallback to env)
            api_key = _pick_api_key(env_api_key, api_keys, r_idx)
            if not api_key:
                continue

            extracted = extract_resume_from_pages(api_key, pages, model=args.model)
            row = {
                **extracted,
                "source_url": pdf_url,
                "pdf_path": pdf_path,
                "id": hash_for_url(pdf_url),
            }
            rows.append(row)

        print(f"[Job {idx}/{len(jobs)}] Appending {len(rows)} records to {args.out}")
        with open(args.out, "a", encoding="utf-8") as f:
            for row in rows:
                f.write(json.dumps(row, ensure_ascii=False) + "\n")
        total_rows_written += len(rows)

    print(f"Done. Total records appended across jobs: {total_rows_written}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
