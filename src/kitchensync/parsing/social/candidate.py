"""Build review-only recipe candidates from analyzed and grouped text."""

import re

from .content import _field_content
from .models import LineAnalysis, RecipeFieldCandidate, SocialRecipeCandidate
from .name import _recipe_name
from .patterns import (
    HASHTAG,
    PROMOTIONAL_TEXT,
    SERVINGS_VALUE,
    SERVINGS_WORD_VALUE,
)


def build_social_recipe_candidate(
    line_analyses: list[LineAnalysis],
    field_candidates: list[RecipeFieldCandidate],
) -> SocialRecipeCandidate:
    """Build review-only recipe content from contextual field candidates."""

    return SocialRecipeCandidate(
        name=_recipe_name(line_analyses, field_candidates),
        description=_recipe_description(line_analyses, field_candidates),
        servings=_recipe_servings(line_analyses),
        raw_ingredients=_field_content(
            line_analyses,
            field_candidates,
            field="ingredients",
        ),
        steps=_field_content(line_analyses, field_candidates, field="steps"),
        tags=_recipe_tags(line_analyses),
        notes=_recipe_notes(line_analyses, field_candidates),
    )


def _recipe_description(
    line_analyses: list[LineAnalysis],
    field_candidates: list[RecipeFieldCandidate],
) -> str | None:
    candidate_lines = {
        line_number
        for candidate in field_candidates
        if candidate.field_scores.get("metadata.description", 0.0) >= 0.5
        for line_number in candidate.line_numbers
    }
    description_lines = [
        line.text
        for line in line_analyses
        if line.line_number in candidate_lines
        and line.evidence.get("narrative", 0.0) >= 0.8
        and len(line.text) >= 40
        and not PROMOTIONAL_TEXT.search(line.text)
    ]
    return "\n\n".join(description_lines) or None


def _recipe_servings(line_analyses: list[LineAnalysis]) -> int | None:
    word_values = {
        "one": 1,
        "two": 2,
        "three": 3,
        "four": 4,
        "five": 5,
        "six": 6,
        "seven": 7,
        "eight": 8,
        "nine": 9,
        "ten": 10,
        "eleven": 11,
        "twelve": 12,
    }
    for line in line_analyses:
        if re.search(
            r"\b\d+\s*(?:[-–]|\bor\b|\bto\b)\s*\d+\s+servings?\b",
            line.text,
            re.IGNORECASE,
        ):
            continue
        word_match = SERVINGS_WORD_VALUE.search(line.text)
        if word_match:
            return word_values[word_match.group("word").casefold()]
        match = SERVINGS_VALUE.search(line.text)
        if match:
            return int(
                match.group("first")
                or match.group("second")
                or match.group("third")
                or match.group("fourth")
                or match.group("fifth")
                or match.group("sixth")
                or match.group("seventh")
                or match.group("eighth")
                or match.group("ninth")
            )
    return None


def _recipe_tags(line_analyses: list[LineAnalysis]) -> list[str]:
    tags = []
    for line in line_analyses:
        for match in HASHTAG.finditer(line.text):
            tag = match.group("tag").casefold()
            if any(character.isalpha() for character in tag) and tag not in tags:
                tags.append(tag)
    return tags


def _recipe_notes(
    line_analyses: list[LineAnalysis],
    field_candidates: list[RecipeFieldCandidate],
) -> list[str]:
    line_numbers = {
        line_number
        for candidate in field_candidates
        if candidate.field_scores.get("notes", 0.0) >= 0.5
        for line_number in candidate.line_numbers
    }
    nutrition_lines = [
        line.text
        for line in line_analyses
        if line.line_number in line_numbers
        and line.evidence.get("nutrition", 0.0) >= 0.8
    ]
    return ["; ".join(nutrition_lines)] if nutrition_lines else []
