from __future__ import annotations

import argparse
import json
from pathlib import Path

from social_import_probe import DEFAULT_URL_FILE, acquire_source, read_urls


SCRATCH_DIR = Path(__file__).parent
CASE_DIR = SCRATCH_DIR / "facebook_recipe_cases"
FAILURE_PATH = SCRATCH_DIR / "facebook_recipe_acquisition_failures.json"


def record_failure(index: int, url: str, error: str) -> None:
    records = (
        json.loads(FAILURE_PATH.read_text(encoding="utf-8"))
        if FAILURE_PATH.exists()
        else []
    )
    record = {"queue_index": index, "source_url": url, "acquisition_error": error}
    records = [item for item in records if item["queue_index"] != index]
    records.append(record)
    records.sort(key=lambda item: item["queue_index"])
    FAILURE_PATH.write_text(
        json.dumps(records, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Freeze one Facebook description acquired by the existing probe."
    )
    parser.add_argument("index", type=int)
    args = parser.parse_args()

    urls = read_urls(DEFAULT_URL_FILE)
    if not 1 <= args.index <= len(urls):
        parser.error(f"index must be between 1 and {len(urls)}")
    url = urls[args.index - 1]

    try:
        source_info = acquire_source(url)
    except Exception as error:
        record_failure(args.index, url, str(error))
        print(f"{args.index:03}: acquisition-failure: {error}")
        return 0

    description = source_info.get("description")
    if not isinstance(description, str) or not description.strip():
        record_failure(args.index, url, "No usable description was returned.")
        print(f"{args.index:03}: acquisition-failure: no usable description")
        return 0

    case_id = f"{args.index:03}-acquired"
    case = {
        "id": case_id,
        "queue_index": args.index,
        "platform": "facebook",
        "creator": source_info.get("uploader"),
        "source_url": url,
        "resolved_source_url": (
            source_info.get("webpage_url")
            or source_info.get("original_url")
            or url
        ),
        "source_name": source_info.get("extractor") or "facebook",
        "thumbnail_url": source_info.get("thumbnail"),
        "source_text_kind": "description",
        "source_text": description,
        "expected": None,
        "expected_complete": None,
        "accepted": False,
        "notes": [
            "Source evidence frozen from the existing yt-dlp acquisition probe "
            "before oracle labeling."
        ],
    }
    CASE_DIR.mkdir(exist_ok=True)
    path = CASE_DIR / f"{case_id}.json"
    path.write_text(
        json.dumps(case, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(f"{args.index:03}: acquired: {path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
