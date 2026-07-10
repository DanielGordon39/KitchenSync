from pathlib import Path

from .result import ParseResult, ParseStatus


def parse_recipe_image(path: str | Path) -> ParseResult:
    # TODO: Extract recipe text from images and map it into Recipe fields.
    return ParseResult(
        status=ParseStatus.NOT_IMPLEMENTED,
        source=str(path),
        message="Image recipe parsing is not implemented yet.",
    )
