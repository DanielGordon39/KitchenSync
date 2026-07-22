from __future__ import annotations

from dataclasses import dataclass
from urllib.parse import urlparse

import yt_dlp


@dataclass(frozen=True)
class InstagramSource:
    description: str | None
    author: str | None
    source_name: str
    source_url: str
    thumbnail_url: str | None


def validate_instagram_url(url: str) -> str:
    url = url.strip()
    parsed = urlparse(url)
    host = (parsed.hostname or "").casefold()
    segments = [segment.casefold() for segment in parsed.path.split("/") if segment]
    if (
        parsed.scheme not in {"http", "https"}
        or host not in {"instagram.com", "www.instagram.com", "m.instagram.com"}
        or not any(
            segment in {"p", "reel"} and index + 1 < len(segments)
            for index, segment in enumerate(segments)
        )
    ):
        raise ValueError("Enter a public Instagram post or reel URL.")
    return url


def acquire_instagram_source(url: str) -> InstagramSource:
    url = validate_instagram_url(url)
    with yt_dlp.YoutubeDL(
        {"quiet": True, "no_warnings": True, "skip_download": True}
    ) as downloader:
        info = downloader.sanitize_info(downloader.extract_info(url, download=False))

    return InstagramSource(
        description=_text(info.get("description")),
        author=_text(info.get("uploader")),
        source_name=_text(info.get("extractor")) or "Instagram",
        source_url=(
            _text(info.get("webpage_url"))
            or _text(info.get("original_url"))
            or url
        ),
        thumbnail_url=_text(info.get("thumbnail")),
    )


def _text(value: object) -> str | None:
    return value.strip() if isinstance(value, str) and value.strip() else None
