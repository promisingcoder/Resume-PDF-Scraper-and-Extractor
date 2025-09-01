import argparse
import json
from typing import List, Tuple, Set, Any


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Count unique records in a JSONL file")
    parser.add_argument("--file", required=True, help="Path to resumes.jsonl")
    parser.add_argument(
        "--by",
        default="id",
        help=(
            "Comma-separated keys to determine uniqueness (e.g., 'id' or 'email' or 'email,id'). "
            "Defaults to 'id'."
        ),
    )
    return parser.parse_args()


def make_key(record: dict, keys: List[str]) -> Tuple[Any, ...]:
    return tuple(record.get(k) for k in keys)


def main() -> int:
    args = parse_args()
    keys = [k.strip() for k in args.by.split(",") if k.strip()]

    total_lines = 0
    parsed_records = 0
    seen: Set[Tuple[Any, ...]] = set()

    try:
        with open(args.file, "r", encoding="utf-8") as f:
            for line in f:
                total_lines += 1
                line = line.strip()
                if not line:
                    continue
                try:
                    obj = json.loads(line)
                except Exception:
                    continue
                parsed_records += 1
                seen.add(make_key(obj, keys))
    except FileNotFoundError:
        print(f"File not found: {args.file}")
        return 1

    unique_count = len(seen)
    print(f"File: {args.file}")
    print(f"Total lines: {total_lines}")
    print(f"Parsed records: {parsed_records}")
    print(f"Unique by [{', '.join(keys)}]: {unique_count}")
    if parsed_records:
        dupes = parsed_records - unique_count
        print(f"Duplicates by [{', '.join(keys)}]: {dupes}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
