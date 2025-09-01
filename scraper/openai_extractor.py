from typing import Dict, Any, List, Optional
import json
import re
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type
from openai import OpenAI


EXPECTED_KEYS = ["name", "email", "github", "education", "experiences"]


def _empty_result() -> Dict[str, Any]:
    return {
        "name": None,
        "email": None,
        "github": None,
        "education": None,
        "experiences": [],
    }


def _normalize_email(text: Optional[str]) -> Optional[str]:
    if not text:
        return None
    m = re.search(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}", text)
    return m.group(0) if m else None


def _normalize_github(text: Optional[str]) -> Optional[str]:
    if not text:
        return None
    m = re.search(r"https?://(?:www\.)?github\.com/[A-Za-z0-9_.-]+", text, re.IGNORECASE)
    return m.group(0) if m else None


def _merge_results(base: Dict[str, Any], update: Dict[str, Any]) -> Dict[str, Any]:
    result = dict(base)
    # Prefer non-null, longer-looking name
    if update.get("name") and (not result.get("name") or len(update["name"]) > len(result["name"])):
        result["name"] = update["name"].strip()
    # Email is the most important; prefer valid email
    new_email = _normalize_email(update.get("email"))
    if new_email:
        result["email"] = new_email
    # Github
    new_github = _normalize_github(update.get("github"))
    if new_github:
        result["github"] = new_github
    # Education
    if update.get("education"):
        if result.get("education"):
            if len(update["education"]) > len(result["education"]):
                result["education"] = update["education"].strip()
        else:
            result["education"] = update["education"].strip()
    # Experiences
    if isinstance(update.get("experiences"), list):
        for item in update["experiences"]:
            item_s = str(item).strip()
            if item_s and item_s not in result["experiences"]:
                result["experiences"].append(item_s)
    return result


SYSTEM_PROMPT = (
    "You extract resume data from raw PDF page text. Return STRICT JSON with keys: "
    "name (string or null), email (string or null), github (string or null), "
    "education (string or null), experiences (array of strings). Do not include extra keys."
)


def _make_user_prompt(page_text: str) -> str:
    return (
        "From this resume page text, extract the fields. If a field is unknown, use null.\n\n"
        f"PAGE TEXT:\n{page_text}\n\n"
        "Respond with ONLY JSON."
    )


@retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=1, max=10), reraise=True)
def _extract_from_page(client: OpenAI, model: str, page_text: str) -> Dict[str, Any]:
    resp = client.chat.completions.create(
        model=model,
        temperature=0,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": _make_user_prompt(page_text)},
        ]
    )
    content = resp.choices[0].message.content or "{}"
    try:
        data = json.loads(content)
    except Exception:
        # Try to salvage JSON via regex
        m = re.search(r"\{[\s\S]*\}", content)
        data = json.loads(m.group(0)) if m else {}
    # Normalize keys and shape
    result = _empty_result()
    for k in EXPECTED_KEYS:
        val = data.get(k)
        if k == "email":
            result[k] = _normalize_email(val)
        elif k == "github":
            result[k] = _normalize_github(val)
        elif k == "experiences":
            if isinstance(val, list):
                result[k] = [str(x).strip() for x in val if str(x).strip()]
            else:
                result[k] = []
        else:
            result[k] = str(val).strip() if isinstance(val, str) and val.strip() else None
    return result


def extract_resume_from_pages(openai_api_key: str, pages: List[str], model: str = "gpt-4o-mini") -> Dict[str, Any]:
    client = OpenAI(api_key=openai_api_key)
    merged = _empty_result()
    for page_text in pages:
        if not page_text:
            continue
        try:
            page_result = _extract_from_page(client, model, page_text)
            merged = _merge_results(merged, page_result)
        except Exception:
            # Skip page on failure
            continue
    return merged
