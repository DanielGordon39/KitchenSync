"""Lossless line normalization for acquired social text."""


def normalize_lines(text: str) -> list[str]:
    """Return trimmed source lines without interpreting blank lines or content."""

    return [line.strip() for line in text.splitlines()]
