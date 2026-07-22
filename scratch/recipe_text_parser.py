"""Compatibility imports for the promoted social-recipe text parser."""

from kitchensync.parsing.social import (
    LineAnalysis,
    RecipeFieldCandidate,
    RecipeTextParseResult,
    SocialRecipeCandidate,
    analyze_line,
    analyze_lines,
    build_field_candidates,
    build_social_recipe_candidate,
    normalize_lines,
    parse_recipe_text,
)

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
