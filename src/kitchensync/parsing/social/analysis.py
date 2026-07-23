"""Independent evidence analysis for normalized social-recipe lines."""

import re

from ingredient_parser import parse_ingredient

from .models import LineAnalysis
from .normalize import normalize_lines
from .patterns import (
    APPLIANCE_DIRECTION,
    BRACKETED_HEADING,
    BULLET_ITEM,
    COMPACT_MACROS,
    COOK_SETTING,
    IMPERATIVE_START,
    INGREDIENT_FOR_HEADING,
    INGREDIENT_HEADING,
    INSTRUCTION_HEADINGS,
    NUTRITION_HEADING,
    NUTRITION_VALUE,
    NUMBERED_INSTRUCTION,
    POST_RECIPE_HEADING,
    POST_RECIPE_LINE,
    RECIPE_WORD,
    SERIES_METADATA,
    SERVINGS_CUE,
    TIP_HEADING,
    TIP_LINE,
)


def analyze_lines(text: str) -> list[LineAnalysis]:
    """Record simple, non-exclusive evidence for every normalized source line."""

    return [
        analyze_line(line_number, line)
        for line_number, line in enumerate(normalize_lines(text), start=1)
    ]


def analyze_line(line_number: int, text: str) -> LineAnalysis:
    evidence: dict[str, float] = {}

    if not text:
        evidence["blank"] = 1.0
        return LineAnalysis(line_number=line_number, text=text, evidence=evidence)

    folded = text.casefold()
    bullet_match = BULLET_ITEM.match(text)
    bullet_content = bullet_match.group("content").strip() if bullet_match else None
    if bullet_match and not bullet_content:
        evidence["divider"] = 1.0
        return LineAnalysis(line_number=line_number, text=text, evidence=evidence)

    is_nutrition_heading = bool(NUTRITION_HEADING.fullmatch(text))
    nutrition_context = re.sub(r"\([^)]*\)", "", folded)
    nutrition_term_count = sum(
        term in nutrition_context for term in ("calorie", "protein", "carb", "fat")
    )
    is_nutrition_value = bool(
        NUTRITION_VALUE.match(text) or COMPACT_MACROS.match(text)
    ) or (
        any(character.isdigit() for character in text)
        and nutrition_term_count >= 2
    ) or bool(re.search(r"\b\d[\d,]*(?:\.\d+)?\s+calories?\s+per\b", text, re.I))
    mentions_nutrition = bool(re.search(r"\bnutrition\b|\bmacros?\b", folded))
    is_serving_sized_ingredient = bool(
        bullet_content
        and re.match(
            r"^\d+\s+servings?\s*\([^)]*\d[^)]*\)\s+\S",
            bullet_content,
            re.IGNORECASE,
        )
    )
    is_servings_value = bool(SERVINGS_CUE.search(text)) and not is_serving_sized_ingredient
    is_series_metadata = bool(SERIES_METADATA.search(text))
    is_cook_setting = bool(COOK_SETTING.match(text))
    is_appliance_direction = bool(APPLIANCE_DIRECTION.match(text))
    is_heading = (
        is_nutrition_heading
        or bool(BRACKETED_HEADING.fullmatch(text))
        or bool(INGREDIENT_HEADING.fullmatch(text))
        or bool(INGREDIENT_FOR_HEADING.fullmatch(text))
        or folded.rstrip(":") in INSTRUCTION_HEADINGS
        or bool(POST_RECIPE_HEADING.fullmatch(text))
        or (
            len(text) <= 40
            and sum(character.isalpha() for character in text) >= 3
            and text == text.upper()
        )
        or text.endswith(":")
        or (
            len(text) <= 40
            and bool(RECIPE_WORD.search(text))
            and not text.endswith((".", "!", "?"))
        )
    )
    instruction_text = re.sub(r"^[^\w]+", "", bullet_content or text)
    instruction_text = re.sub(
        r"^optional\s*:\s*", "", instruction_text, flags=re.IGNORECASE
    )
    instruction_text = re.sub(
        r"^you\s+(?:can|may)\s+", "", instruction_text, flags=re.IGNORECASE
    )
    has_later_imperative = any(
        sentence.strip().casefold().startswith("simply ")
        and IMPERATIVE_START.match(sentence.strip())
        for sentence in re.split(r"(?<=[.!?])\s+", instruction_text)[1:]
    )
    is_instruction = bool(
        NUMBERED_INSTRUCTION.match(text)
        or is_appliance_direction
        or (
            not BRACKETED_HEADING.fullmatch(text)
            and IMPERATIVE_START.match(instruction_text)
        )
        or has_later_imperative
        or TIP_LINE.match(text)
    )

    if is_heading:
        evidence["heading"] = 1.0
    elif mentions_nutrition:
        evidence["heading"] = 0.2
    if INGREDIENT_HEADING.fullmatch(text) or ("ingredient" in folded and is_heading):
        evidence["ingredient"] = 1.0
    if is_instruction or (
        is_heading
        and (
            any(heading in folded for heading in INSTRUCTION_HEADINGS)
            or TIP_HEADING.fullmatch(text)
        )
    ):
        evidence["instruction"] = 1.0
    if is_nutrition_heading or is_nutrition_value:
        evidence["nutrition"] = 1.0
    elif mentions_nutrition:
        evidence["nutrition"] = 0.2
        evidence["narrative"] = 1.0
    if is_servings_value:
        evidence["servings"] = 1.0
    if is_series_metadata:
        evidence["metadata"] = 1.0
    if POST_RECIPE_HEADING.fullmatch(text) or POST_RECIPE_LINE.match(text) or re.search(
        r"\bserved\s+in\b.*\bcontainers?\b", text, re.IGNORECASE
    ):
        evidence["metadata"] = 1.0
    if is_cook_setting:
        evidence["timing"] = 1.0
    if text.startswith("#"):
        evidence["tag"] = 1.0
    if re.match(r"^[-*•]?\s*(?:i|we)\s+recommend\b", text, re.IGNORECASE):
        evidence["instruction"] = 0.2
        evidence["narrative"] = 1.0

    ingredient_text = bullet_content if bullet_content is not None else text
    semantic_evidence = {
        "divider",
        "heading",
        "instruction",
        "metadata",
        "nutrition",
        "servings",
        "tag",
        "timing",
    }
    if not semantic_evidence.intersection(evidence):
        parsed_ingredient = _parse_ingredient(ingredient_text)
        if bullet_match:
            if _is_good_ingredient_parse(parsed_ingredient, ingredient_text):
                evidence["ingredient"] = 0.8
                evidence["instruction"] = 0.2
            else:
                evidence["ingredient"] = 0.2
                evidence["instruction"] = 0.8
        elif (
            len(text) <= 180
            and parsed_ingredient is not None
            and parsed_ingredient.amount
            and any(amount.starting_index <= 2 for amount in parsed_ingredient.amount)
        ):
            evidence["ingredient"] = 0.7

    if not evidence:
        evidence["narrative"] = 1.0

    return LineAnalysis(line_number=line_number, text=text, evidence=evidence)


def _parse_ingredient(text: str):
    try:
        return parse_ingredient(text)
    except Exception:
        return None


def _is_good_ingredient_parse(parsed, text: str) -> bool:
    if parsed is None or not parsed.name:
        return False
    if IMPERATIVE_START.match(text):
        return False
    if parsed.amount or len(parsed.name) > 1:
        return True
    if parsed.preparation or parsed.comment or parsed.purpose:
        return True

    name = parsed.name[0]
    parsed_name = name.text.strip().casefold().rstrip(".!?")
    source_text = text.strip().casefold().rstrip(".!?")
    if parsed_name != source_text:
        return True

    confidence = float(name.confidence or 0.0)
    return confidence >= 0.88 and not text.rstrip().endswith((".", "!", "?"))


def _looks_like_inline_ingredient_group(text: str) -> bool:
    heading, separator, body = text.partition(":")
    return bool(
        separator
        and 1 <= len(heading.split()) <= 6
        and body.strip()
        and _is_good_ingredient_parse(_parse_ingredient(body.strip()), body.strip())
    )
