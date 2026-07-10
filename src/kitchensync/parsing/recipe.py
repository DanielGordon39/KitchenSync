from pathlib import Path
from urllib.parse import urlparse

from .image import parse_recipe_image
from .pdf import parse_recipe_pdf
from .result import ParseResult, ParseStatus
from .web import parse_recipe_url


def parse_recipe(source: str | Path) -> ParseResult:
    source_text = str(source)

    if _is_url(source_text):
        return parse_recipe_url(source_text)

    suffix = Path(source_text).suffix.lower()
    if suffix == ".pdf":
        return parse_recipe_pdf(Path(source_text))

    if suffix in {".avif", ".bmp", ".gif", ".jpeg", ".jpg", ".png", ".tif", ".tiff", ".webp"}:
        return parse_recipe_image(Path(source_text))

    return ParseResult(
        status=ParseStatus.UNSUPPORTED_SOURCE,
        source=source_text,
        message="Recipe source is not a supported URL, PDF, or image.",
    )


def _is_url(source: str) -> bool:
    parsed = urlparse(source)
    return parsed.scheme in {"http", "https"} and bool(parsed.netloc)
