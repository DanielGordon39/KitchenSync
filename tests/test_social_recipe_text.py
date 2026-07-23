from __future__ import annotations

import json
from pathlib import Path

from kitchensync.parsing import parse_recipe_text


CASE_DIR = (
    Path(__file__).parents[1]
    / "scratch"
    / "archive"
    / "instagram"
    / "social_recipe_cases"
)
SCORED_FIELDS = {"name", "servings", "raw_ingredients", "steps", "tags"}


def test_social_recipe_text_matches_complete_frozen_example():
    _assert_frozen_case("014-korean-spicy-tofu-stew-meal-prep.json")


def test_social_recipe_text_matches_fallback_frozen_example():
    _assert_frozen_case("006-stealth-health-cookbook-promotion.json")


def _assert_frozen_case(filename: str) -> None:
    case = json.loads((CASE_DIR / filename).read_text(encoding="utf-8"))

    result = parse_recipe_text(case["source_text"])

    assert result.candidate is not None
    assert result.candidate.model_dump(include=SCORED_FIELDS) == case["expected"]
    assert (not result.fallback_recommended) == case["expected_complete"]
