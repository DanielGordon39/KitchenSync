from __future__ import annotations

import argparse
from dataclasses import dataclass
from pathlib import Path
from pprint import pprint
from typing import TYPE_CHECKING
from urllib.parse import urlparse

import yt_dlp

if TYPE_CHECKING:
    from recipe_text_parser import RecipeTextParseResult


DEFAULT_URL_FILE = Path(__file__).parent / "social_recipe_urls.txt"


@dataclass
class SocialProbeRow:
    index: int
    url: str
    platform: str
    status: str = "planned"


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Plan the next social-recipe import probe for a URL corpus."
    )
    parser.add_argument(
        "url_file",
        nargs="?",
        type=Path,
        default=DEFAULT_URL_FILE,
        help="Text file with one social-media recipe URL per line.",
    )
    return parser


def print_recipe_evidence(source_info: dict[str, object]) -> None:
    preview = {
        "recipe_fields_to_extract": {
            "name": "from description",
            "servings": "from description",
            "ingredients": "from bulleted description section",
            "steps": "from numbered description section",
            "tags": "from hashtags",
            "time_estimate": None,
        },
        "metadata_candidates": {
            "author": source_info.get("uploader"),
            "source_name": source_info.get("extractor"),
            "source_url": (
                source_info.get("webpage_url")
                or source_info.get("original_url")
            ),
            "imported_from": "yt-dlp",
            "main_image_uri": source_info.get("thumbnail"),
        },
        "evidence": {
            "has_description": bool(source_info.get("description")),
            "has_captions": bool(
                source_info.get("subtitles")
                or source_info.get("automatic_captions")
            ),
        },
    }

    pprint(preview, sort_dicts=False, width=100)

    print("\nRaw description evidence:\n")
    print(source_info.get("description") or "(no description)")


def print_parse_result(result: RecipeTextParseResult) -> None:
    print("\nRecipe text parser result:\n")
    pprint(result.model_dump(), sort_dicts=False, width=100)


def main() -> None:
    if __package__:
        from .recipe_text_parser import parse_recipe_text
    else:
        from recipe_text_parser import parse_recipe_text

    args = build_parser().parse_args()
    urls = read_urls(args.url_file)

    source_info = acquire_source(urls[0])
    print_recipe_evidence(source_info)

    description = source_info.get("description")
    if not isinstance(description, str) or not description.strip():
        print("\nNo description text is available for recipe parsing.")
        return

    parse_result = parse_recipe_text(description)
    print_parse_result(parse_result)
    breakpoint()


def read_urls(path: Path) -> list[str]:
    urls = []
    for line in path.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        urls.append(stripped)
    return urls


def acquire_source(url: str) -> dict[str, object]:
    with yt_dlp.YoutubeDL({}) as ydl:
        info = ydl.extract_info(url, download=False)
        return ydl.sanitize_info(info)


def identify_platform(url: str) -> str:
    parsed = urlparse(url)
    host = parsed.netloc.casefold().removeprefix("www.")
    path = parsed.path.casefold()

    if host in {"youtube.com", "m.youtube.com"}:
        return "youtube_shorts" if path.startswith("/shorts/") else "youtube"
    if host == "youtu.be":
        return "youtube"
    if host in {"instagram.com", "m.instagram.com"}:
        return "instagram"
    if host in {"tiktok.com", "m.tiktok.com", "vm.tiktok.com"}:
        return "tiktok"
    if host in {"facebook.com", "m.facebook.com", "fb.watch"}:
        return "facebook"
    return "unsupported"


def build_probe_rows(urls: list[str]) -> list[SocialProbeRow]:
    return [
        SocialProbeRow(index=index, url=url, platform=identify_platform(url))
        for index, url in enumerate(urls, start=1)
    ]


def print_probe_plan(rows: list[SocialProbeRow]) -> None:
    for row in rows:
        print(f"[{row.index}] {row.platform} / {row.status}: {row.url}")

    print()
    print("next probe boundaries")
    print("- acquire description, source metadata, captions, and image candidates")
    print("- transcribe downloaded audio only when usable captions are unavailable")
    print("- build a reviewable recipe candidate without saving it")
    print("- compare YouTube results with later TikTok, Instagram, and Facebook URLs")


# TODO(step 5): Prefer existing captions, then evaluate local faster-whisper transcription.
# TODO(step 6): Implement recipe text parsing one stage at a time in recipe_text_parser.py.
# TODO(step 7): Add fallback extraction only for incomplete or ambiguous parse results.
# TODO(step 8): Add observed TikTok, Instagram, and Facebook URLs one platform at a time.


if __name__ == "__main__":
    main()
