from pathlib import Path

from .result import ParseResult, ParseStatus


def parse_recipe_pdf(path: str | Path) -> ParseResult:
    # TODO: Extract recipe text from PDFs and map it into Recipe fields.
    return ParseResult(
        status=ParseStatus.NOT_IMPLEMENTED,
        source=str(path),
        message="PDF recipe parsing is not implemented yet.",
    )
