"""Deterministic, platform-independent parsing for social recipe text.

The package accepts text that has already been acquired from a description,
caption, or transcript. It does not fetch URLs, call an LLM, save recipes, or
depend on a particular social-media platform.

Parsing remains a five-stage pipeline: normalize lines, analyze independent
evidence, group contextual fields, build a review-only candidate, and report
whether missing content recommends fallback handling.
"""

from .analysis import analyze_line, analyze_lines
from .candidate import build_social_recipe_candidate
from .fallback import candidate_warnings
from .grouping import build_field_candidates
from .models import (
    LineAnalysis,
    RecipeFieldCandidate,
    RecipeTextParseResult,
    SocialRecipeCandidate,
)
from .normalize import normalize_lines

__all__ = [
    "LineAnalysis",
    "RecipeFieldCandidate",
    "RecipeTextParseResult",
    "SocialRecipeCandidate",
    "analyze_line",
    "analyze_lines",
    "build_field_candidates",
    "build_social_recipe_candidate",
    "normalize_lines",
    "parse_recipe_text",
]


def parse_recipe_text(text: str) -> RecipeTextParseResult:
    """Return line evidence, field associations, and review-only recipe content."""

    line_analyses = analyze_lines(text)
    field_candidates = build_field_candidates(line_analyses)
    candidate = build_social_recipe_candidate(line_analyses, field_candidates)
    warnings = candidate_warnings(candidate, line_analyses)
    return RecipeTextParseResult(
        candidate=candidate,
        line_analyses=line_analyses,
        field_candidates=field_candidates,
        unclassified_lines=[line.text for line in line_analyses if not line.evidence],
        warnings=warnings,
        fallback_recommended=bool(warnings),
    )
