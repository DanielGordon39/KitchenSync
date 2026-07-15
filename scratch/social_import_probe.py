from __future__ import annotations

import argparse
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import urlparse


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


def main() -> None:
    args = build_parser().parse_args()
    rows = build_probe_rows(read_urls(args.url_file))
    print_probe_plan(rows)


def read_urls(path: Path) -> list[str]:
    urls = []
    for line in path.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        urls.append(stripped)
    return urls


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


# TODO(step 4): Acquire a source evidence bundle with yt-dlp or a platform fallback.
# TODO(step 5): Prefer existing captions, then evaluate local faster-whisper transcription.
# TODO(step 6): Extract a review-only recipe candidate; do not call the save boundary yet.
# TODO(step 7): Add observed TikTok, Instagram, and Facebook URLs one platform at a time.


if __name__ == "__main__":
    main()
