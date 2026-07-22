"""Deterministic, platform-independent parsing for social recipe text.

This module accepts text that has already been acquired from a description,
caption, or transcript. It does not fetch URLs, call an LLM, save recipes, or
depend on a particular social-media platform.

The parser:

1. Normalize the source text into meaningful lines.
2. Analyze every line for independent recipe-concept evidence.
3. Group nearby, compatible line evidence into recipe sections.
4. Build a review-only candidate from supported sections.
5. Report unclassified text and decide whether fallback extraction is needed.

Design
------

The first analysis pass does not assign one final class to each line. It records
separate, non-exclusive strengths for concepts a line may belong to. For example,
an ``Ingredients`` line can strongly support both ``ingredient`` and ``heading``
without being an ingredient detail itself. ``ingredient`` means that the line
belongs with the ingredients part of a recipe. Ingredient-parser-nlp evidence
adjusts this existing strength; it does not create a separate ingredient-item
concept.

Concept strengths are rule weights, not probabilities, and do not need to add up
to one. Store them as numbers from ``0.0`` to ``1.0``; do not store categorical
values such as ``high`` or ``low``. Later grouping uses proximity and continuity:
ingredient-related lines
near an ingredient heading support one ingredients section; instruction-related
lines near each other support a steps section; adjacent narrative lines can form
a description.

For example, a future ``1. Chop the onion`` analysis might record
``ingredient: 0.1``, ``heading: 0.0``, and ``instruction: 0.9``. The exact
weights are future rule decisions, but the representation always uses numbers.

Blank lines retain their own structural evidence, such as ``blank`` and
``divider``. A blank run is stronger section-boundary evidence than one blank
line, but neither determines a boundary until the surrounding line evidence is
considered.

Ingredient-parser-nlp may provide ingredient-related evidence for each nonblank
line. Its result is supporting evidence only; section context still decides
whether ambiguous bullet lines belong to ingredients or instructions.
"""

import re
import unicodedata

from ingredient_parser import parse_ingredient
from pydantic import BaseModel, Field


NUMBERED_INSTRUCTION = re.compile(
    r"^(?:\d+[.)](?:\s+|(?=[A-Z]))|\d\ufe0f?\u20e3\s*)"
)
RECIPE_WORD = re.compile(r"\brecipe\b", re.IGNORECASE)
NUTRITION_HEADING = re.compile(
    r"^(?:macros?|nutrition(?:\s+(?:facts|info|information))?)"
    r"(?:\s+per\s+[^:]+)?\s*:?$",
    re.IGNORECASE,
)
NUTRITION_VALUE = re.compile(
    r"^[^\w\d]*(?:only\s+)?"
    r"(?:(protein|carb(?:ohydrate)?s?|fat|calories?|cals?|fiber|fibre|sugar|sodium)"
    r"\s*:?\s*\d|\d[\d,]*(?:\.\d+)?"
    r"(?:\s*[–-]\s*\d[\d,]*(?:\.\d+)?)?\s*(?:(?:calories?|k?cal)\b|"
    r"g\s*(?:protein|carbs?|fat)\b"
    r"(?:\s+(?:per\s+\w+|meal\s+prep))?[^\w\d]*$))",
    re.IGNORECASE,
)
COMPACT_MACROS = re.compile(
    r"^(?:\d+(?:\.\d+)?\s*g[pcf]\s*(?:[|/]\s*)?){2,}[^\w\d]*$",
    re.IGNORECASE,
)
BULLET_ITEM = re.compile(
    r"^(?:[^\w\s*•-]+\s*)?(?P<marker>[-*•])\s*(?P<content>.*)$"
)
BRACKETED_HEADING = re.compile(r"^\[[^\[\]]{1,40}\]$")
INGREDIENT_HEADING = re.compile(
    r"^(?:ingredients?\b(?:\s*\([^)]*\))?|all\s+you\s+need\s+is)\s*:?$",
    re.IGNORECASE,
)
INGREDIENT_FOR_HEADING = re.compile(
    r"^[^\w]*ingredients?\s+for\s+\d+\b.{0,60}$",
    re.IGNORECASE,
)
TIP_LINE = re.compile(r"^tip(?:\s+\d+)?:\s+\S", re.IGNORECASE)
TIP_HEADING = re.compile(r"^(?:important\s+)?tips?\s*:$", re.IGNORECASE)
POST_RECIPE_HEADING = re.compile(
    r"^(?:notes?|(?:freez(?:e|ing)|reheat(?:ing)?)(?:\s+instructions?)?|"
    r"storage(?:\s*&\s*(?:heating|reheating))?(?:\s+instructions?)?)"
    r"\s*[^\w]*$",
    re.IGNORECASE,
)
POST_RECIPE_LINE = re.compile(
    r"^(?:[-*•]\s*)?(?:freeze|from\s+fridge|from\s+frozen|refrigerate)\b",
    re.IGNORECASE,
)
SERIES_METADATA = re.compile(
    r"\bseries\b|\bep(?:isode)?\.?\s*\d+\b",
    re.IGNORECASE,
)
COOK_SETTING = re.compile(
    r"^(?:(?:high|low)\s*:\s*.+\b(?:hours?|minutes?|mins?)\b|"
    r"(?:air\s+fryer|oven)\s*:\s*.*\d+\s*°?\s*[cf]\b.*"
    r"\b(?:minutes?|mins?)\b)",
    re.IGNORECASE,
)
APPLIANCE_DIRECTION = re.compile(
    r"^(?:air\s+fryer|oven)\s*:\s*.*\d+\s*°?\s*[cf]\b.*"
    r"\b(?:minutes?|mins?)\b",
    re.IGNORECASE,
)
IMPERATIVE_START = re.compile(
    r"^(?:(?:(?:a\s+(?:great\s+)?|pro\s+)?tip\b.*?|"
    r"for\s+(?:the\s+)?[^,]{1,30}),\s*|"
    r"(?:in|into)\s+(?:a|the)\s+(?:(?:small|medium|large)\s+)?"
    r"(?:bowl|dish|pan|pot|skillet),?\s+|"
    r"(?:after|before|once|when)\s+[^,]{1,50},\s*|"
    r"(?:finally|meanwhile|next|simply|then(?:\s+simply)?)(?:,\s*|\s+))?"
    r"(?:add|air\s+fry|allow|arrange|assemble|bake|blend|boil|bring|brown|chop|coat|"
    r"combine|cook|cover|crush|dispense|divide|drizzle|finish|fold|form|fry|garnish|heat|"
    r"lay|layer|let|lift|make|marinate|mash|melt|microwave|mix|pat|place|"
    r"oven\s+bake|pour|preheat|refrigerate\s+overnight|reserve|roast|season|serve|simmer|slice|spray|spread|"
    r"soak|spin|spoon|stir|sear|take|throw|toast|top|toss|wake|whisk)\b",
    re.IGNORECASE,
)
INSTRUCTION_HEADINGS = ("directions", "how to", "instructions", "method", "steps")
SERVINGS_CUE = re.compile(
    r"\b(?:makes?|serves?)\s+~?\s*x?\s*\d+\b|"
    r"\b(?:makes?|serves?)\s+(?:one|two|three|four|five|six|seven|eight|"
    r"nine|ten|eleven|twelve)\b|"
    r"\bingredients?\s*\(\s*\d+\s+(?:\w+\s+){0,2}"
    r"(?:batch(?:es)?|serves?|servings?|portions?)\s*\)|"
    r"\bmacros?\s*\(\s*\d+\s+(?:bowls?|serves?|servings?|portions?|pieces?)\s*\)|"
    r"\bservings?\s*:\s*\d+\b|"
    r"\bingredients?\s+for\s+\d+\b|"
    r"\bper\s+\w+\s+of\s+\d+\b|"
    r"\b\d+(?:\s+(?!per\b)\w+){0,2}\s+servings?\b|"
    r"\bper\s+\w+\b.{0,20}\b\d+\s+total\b|"
    r"\b(?:divide|portion|split)\b.{0,100}\b(?:between|into|among)\s+\d+\s+"
    r"(?:meal\s+prep\s+)?(?:bowls?|containers?|plates?|portions?|servings?)\b",
    re.IGNORECASE,
)
SERVINGS_VALUE = re.compile(
    r"\b(?:makes?|serves?)\s+~?\s*x?\s*(?P<first>\d+)\b|"
    r"\bmacros?\s*\(\s*(?P<eighth>\d+)\s+"
    r"(?:bowls?|serves?|servings?|portions?|pieces?)\s*\)|"
    r"\bingredients?\s*\(\s*(?P<ninth>\d+)\s+(?:\w+\s+){0,2}"
    r"(?:batch(?:es)?|serves?|servings?|portions?)\s*\)|"
    r"\bservings?\s*:\s*(?P<fifth>\d+)\b|"
    r"\bingredients?\s+for\s+(?P<sixth>\d+)\b|"
    r"\bper\s+\w+\s+of\s+(?P<seventh>\d+)\b|"
    r"\b(?P<second>\d+)(?:\s+(?!per\b)\w+){0,2}\s+servings?\b|"
    r"\bper\s+\w+\b.{0,20}\b(?P<fourth>\d+)\s+total\b|"
    r"\b(?:divide|portion|split)\b.{0,100}\b(?:between|into|among)\s+"
    r"(?P<third>\d+)\s+(?:meal\s+prep\s+)?"
    r"(?:bowls?|containers?|plates?|portions?|servings?)\b",
    re.IGNORECASE,
)
SERVINGS_WORD_VALUE = re.compile(
    r"\b(?:makes?|serves?)\s+"
    r"(?P<word>one|two|three|four|five|six|seven|eight|nine|ten|eleven|twelve)\b",
    re.IGNORECASE,
)
SAVE_RECIPE_NAME = re.compile(
    r"\bsave\s+this\s+(?P<name>.+?)\s*[([]?\s*recipe\b",
    re.IGNORECASE,
)
HASHTAG = re.compile(r"#(?P<tag>[\w-]+)")
PROMOTIONAL_TEXT = re.compile(
    r"\b(?:comment|follow(?:ing)?|like\s*&\s*share|"
    r"link(?:ed)?\s+in\s+(?:my\s+)?bio|"
    r"save\s+(?:this|time|money|your\s+life)|"
    r"do\s+not\s+authorize|creator|let\s+me\s+know|"
    r"(?:do(?:n['’]t|\s+not)\s+forget\s+to\s+)?check\s+out|"
    r"printable\s+(?:recipe|version))\b",
    re.IGNORECASE,
)
EXTERNAL_FULL_RECIPE_CUE = re.compile(
    r"\b(?:printable\s+recipe|comment.{0,80}recipe|"
    r"link(?:ed)?\s+in\s+(?:my\s+)?bio)\b",
    re.IGNORECASE,
)


class SocialRecipeCandidate(BaseModel):
    """Incomplete recipe details extracted for review, never direct saving."""

    name: str | None = None
    description: str | None = None
    servings: int | None = None
    raw_ingredients: list[str] = Field(default_factory=list)
    steps: list[str] = Field(default_factory=list)
    tags: list[str] = Field(default_factory=list)
    notes: list[str] = Field(default_factory=list)


class LineAnalysis(BaseModel):
    """Independent recipe-concept evidence for one normalized source line."""

    line_number: int
    text: str
    evidence: dict[str, float] = Field(default_factory=dict)


class RecipeFieldCandidate(BaseModel):
    """Possible Recipe fields associated with one contextual run of lines."""

    field_scores: dict[str, float]
    line_numbers: list[int]
    lines: list[str]


class RecipeTextParseResult(BaseModel):
    """Candidate plus diagnostics from deterministic text parsing."""

    candidate: SocialRecipeCandidate | None = None
    line_analyses: list[LineAnalysis] = Field(default_factory=list)
    field_candidates: list[RecipeFieldCandidate] = Field(default_factory=list)
    unclassified_lines: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    fallback_recommended: bool = False


def normalize_lines(text: str) -> list[str]:
    """Return trimmed source lines without interpreting blank lines or content."""
    return [line.strip() for line in text.splitlines()]


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


def build_field_candidates(
    line_analyses: list[LineAnalysis],
) -> list[RecipeFieldCandidate]:
    """Associate ordered line blocks with possible Recipe model fields."""
    candidates: list[tuple[RecipeFieldCandidate, bool]] = []
    for block, hard_break_before in _context_blocks(line_analyses):
        candidate = _field_candidate(block)
        if candidate is None:
            continue

        if (
            candidates
            and not hard_break_before
            and _dominant_field(candidates[-1][0]) == _dominant_field(candidate)
        ):
            previous, previous_hard_break = candidates[-1]
            candidates[-1] = (
                RecipeFieldCandidate(
                    field_scores={
                        field: max(
                            previous.field_scores.get(field, 0.0),
                            candidate.field_scores.get(field, 0.0),
                        )
                        for field in previous.field_scores.keys()
                        | candidate.field_scores.keys()
                    },
                    line_numbers=previous.line_numbers + candidate.line_numbers,
                    lines=previous.lines + candidate.lines,
                ),
                previous_hard_break,
            )
        else:
            candidates.append((candidate, hard_break_before))

    return [candidate for candidate, _ in candidates]


def _context_blocks(
    line_analyses: list[LineAnalysis],
) -> list[tuple[list[LineAnalysis], bool]]:
    blocks: list[tuple[list[LineAnalysis], bool]] = []
    current: list[LineAnalysis] = []
    current_hard_break = False
    next_hard_break = False

    def finish_current() -> None:
        nonlocal current, current_hard_break
        if current:
            blocks.append((current, current_hard_break))
            current = []
            current_hard_break = False

    for line in line_analyses:
        if "divider" in line.evidence:
            finish_current()
            next_hard_break = True
            continue
        if "blank" in line.evidence:
            finish_current()
            continue
        if line.evidence.get("heading", 0.0) >= 0.8 and current:
            finish_current()
        if not current:
            current_hard_break = next_hard_break
            next_hard_break = False
        current.append(line)

    finish_current()
    return blocks


def _field_candidate(block: list[LineAnalysis]) -> RecipeFieldCandidate | None:
    if not block:
        return None

    field_scores: dict[str, float] = {}
    concept_fields = {
        "ingredient": "ingredients",
        "instruction": "steps",
        "nutrition": "notes",
        "tag": "tags",
    }
    for concept, field in concept_fields.items():
        score = sum(line.evidence.get(concept, 0.0) for line in block) / len(block)
        if score:
            field_scores[field] = round(score, 2)

    narrative_score = sum(
        line.evidence.get("narrative", 0.0) for line in block
    ) / len(block)
    if narrative_score:
        field_scores["metadata.description"] = round(narrative_score * 0.6, 2)
        field_scores["notes"] = max(
            field_scores.get("notes", 0.0),
            round(narrative_score * 0.2, 2),
        )

    if _looks_like_ingredient_component(block):
        field_scores["ingredients"] = max(field_scores.get("ingredients", 0.0), 0.6)
    if _looks_like_bare_ingredient_list(block):
        field_scores["ingredients"] = max(field_scores.get("ingredients", 0.0), 0.6)
    if block[0].line_number == 1 and len(block[0].text) <= 100:
        field_scores["name"] = 0.7
    elif any(RECIPE_WORD.search(line.text) for line in block):
        field_scores["name"] = 0.3
    if any(SERVINGS_CUE.search(line.text) for line in block):
        field_scores["servings"] = 0.7

    field_scores = {
        field: score for field, score in field_scores.items() if score >= 0.2
    }
    if not field_scores:
        return None
    return RecipeFieldCandidate(
        field_scores=field_scores,
        line_numbers=[line.line_number for line in block],
        lines=[line.text for line in block],
    )


def _looks_like_ingredient_component(block: list[LineAnalysis]) -> bool:
    if len(block) < 2:
        return False
    if any(
        block[0].evidence.get(concept, 0.0)
        for concept in ("ingredient", "instruction", "nutrition", "tag")
    ):
        return False
    if (
        block[0].evidence.get("heading", 0.0) < 0.8
        and (
            block[0].evidence.get("narrative", 0.0) < 0.8
            or len(block[0].text) > 40
            or block[0].text.endswith((".", "!", "?"))
            or (
                len(block) == 2
                and not re.match(r"^(?:for|to)\b", block[0].text, re.IGNORECASE)
                and not re.search(r"[^\w\s:.,!?]$", block[0].text)
            )
        )
    ):
        return False

    body = block[1:]
    bullet_contents = [
        match.group("content").strip()
        for line in body
        if (match := BULLET_ITEM.match(line.text))
    ]
    if (
        len(bullet_contents) == len(body)
        and any(
            _is_good_ingredient_parse(_parse_ingredient(text), text)
            for text in bullet_contents
        )
        and not any(IMPERATIVE_START.match(text) for text in bullet_contents)
    ):
        return True
    ingredient_like = sum(
        len(line.text) <= 80
        and _is_good_ingredient_parse(
            _parse_ingredient(
                (match.group("content").strip() if (match := BULLET_ITEM.match(line.text)) else line.text)
            ),
            (match.group("content").strip() if match else line.text),
        )
        for line in body
    )
    return ingredient_like / len(body) >= 0.6


def _looks_like_bare_ingredient_list(block: list[LineAnalysis]) -> bool:
    if len(block) < 2:
        return False
    if any(
        BULLET_ITEM.match(line.text)
        or line.evidence.get("heading", 0.0) >= 0.8
        or line.evidence.get("nutrition", 0.0) >= 0.2
        or line.evidence.get("servings", 0.0) >= 0.2
        or line.evidence.get("instruction", 0.0) >= 0.5
        or line.evidence.get("metadata", 0.0) >= 0.5
        or line.evidence.get("tag", 0.0) >= 0.5
        or line.evidence.get("timing", 0.0) >= 0.5
        or line.text.endswith((".", "!", "?"))
        or len(line.text) > 60
        for line in block
    ):
        return False
    return all(
        _is_good_ingredient_parse(_parse_ingredient(line.text), line.text)
        for line in block
    )


def _menu_component_lines(line_analyses: list[LineAnalysis]) -> set[int]:
    blocks = [block for block, _ in _context_blocks(line_analyses)]
    first_content = next((line.text for line in line_analyses if line.text), "")
    context_words = set(re.findall(r"[a-z]{3,}", first_content.casefold()))
    selected_lines: set[int] = set()

    for index, block in enumerate(blocks[:-1]):
        if not any(line.evidence.get("nutrition", 0.0) >= 0.8 for line in block):
            continue
        outcome_match = next(
            (
                re.search(r"\bmix\b.*?\bfor\b(?P<outcome>.+)$", line.text, re.I)
                for later_block in blocks[index + 1 :]
                for line in later_block
                if line.evidence.get("instruction", 0.0) >= 0.5
            ),
            None,
        )
        if not outcome_match:
            continue
        outcome_words = set(
            re.findall(r"[a-z]{3,}", outcome_match.group("outcome").casefold())
        )
        meaningful_words = (context_words | outcome_words) - {
            "all",
            "bowl",
            "for",
            "hack",
            "mix",
            "style",
            "together",
        }
        candidates = [
            line
            for line in block
            if line.evidence.get("nutrition", 0.0) < 0.5
            and line.evidence.get("metadata", 0.0) < 0.5
            and line.evidence.get("tag", 0.0) < 0.5
        ]
        matched = {
            line.line_number
            for line in candidates
            if line.evidence.get("ingredient", 0.0) >= 0.5
            or set(re.findall(r"[a-z]{3,}", line.text.casefold())) & meaningful_words
        }
        if len(matched) >= 2:
            selected_lines.update(matched)

    return selected_lines


def _dominant_field(candidate: RecipeFieldCandidate) -> str:
    return max(candidate.field_scores, key=candidate.field_scores.get)


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


def _recipe_name(
    line_analyses: list[LineAnalysis],
    field_candidates: list[RecipeFieldCandidate],
) -> str | None:
    for line in line_analyses:
        match = SAVE_RECIPE_NAME.search(line.text)
        if match:
            return _clean_recipe_name(match.group("name"))

    for line in line_analyses:
        series_name = re.search(
            r"\bepisode\s+\d+\s+of\s+[^:]{1,80}:\s*"
            r"(?P<name>[^.!?]{1,80})[.!?]",
            line.text,
            re.IGNORECASE,
        )
        if series_name:
            return _clean_recipe_name(series_name.group("name"))

    for line in line_analyses:
        if re.search(r"\bepisode\s+\d+\s*[/|:–—-]\s*\S", line.text, re.IGNORECASE):
            return _clean_recipe_name(line.text)

    for line in line_analyses:
        labeled_title = re.match(
            r"^[^\w]*recipe\s*:\s*(?P<name>.+)$",
            line.text,
            re.IGNORECASE,
        )
        if labeled_title:
            return _clean_recipe_name(labeled_title.group("name"))

    for line in line_analyses:
        if (
            re.search(r"\((?:makes?|serves?)\s+\d+[^)]*\)", line.text, re.IGNORECASE)
            and line.evidence.get("ingredient", 0.0) < 0.5
            and line.evidence.get("nutrition", 0.0) < 0.5
        ):
            name = _clean_recipe_name(line.text)
            if (
                name
                and len(name) <= 80
                and not re.match(
                    r"^(?:macro|macros|nutrition)\b", name, re.IGNORECASE
                )
                and name.casefold() not in {
                    "macro",
                    "macros",
                    "nutrition",
                    "nutrition facts",
                    "recipe",
                }
                and not re.match(
                    r"^per\s+(?:bowl|serve|serving)\b", name, re.IGNORECASE
                )
            ):
                return name

    first_content_index = next(
        (index for index, line in enumerate(line_analyses) if line.text),
        None,
    )
    if first_content_index is not None:
        first_layout_text = line_analyses[first_content_index].text
        first_layout_name = _clean_recipe_name(first_layout_text)
        first_layout_words = [
            word for word in first_layout_name.split() if any(c.isalpha() for c in word)
        ]
        title_case_ratio = (
            sum(
                next(c for c in word if c.isalpha()).isupper()
                for word in first_layout_words
            )
            / len(first_layout_words)
            if first_layout_words
            else 0.0
        )
        nearby_yield = any(
            line.evidence.get("servings", 0.0) >= 0.8
            for line in line_analyses[first_content_index + 1 : first_content_index + 5]
        )
        if (
            first_layout_name
            and len(first_layout_name) <= 80
            and (
                len(first_layout_words) <= 8
                and title_case_ratio >= 0.8
                or len(first_layout_words) <= 12
                and nearby_yield
            )
            and not first_layout_text.startswith("#")
            and line_analyses[first_content_index].evidence.get("metadata", 0.0) < 0.5
            and not re.match(
                r"^(?:i|this|these|we|you)\b", first_layout_name, re.IGNORECASE
            )
            and not re.search(
                r"\band\s+it['’]s\s+.+?\s+too\b",
                first_layout_text,
                re.IGNORECASE,
            )
            and not first_layout_text.endswith((".", "!", "?"))
            and not PROMOTIONAL_TEXT.search(first_layout_text)
        ):
            return first_layout_name
    if (
        first_content_index is not None
        and first_content_index + 1 < len(line_analyses)
        and re.fullmatch(
            r"\([^)]{1,80}\)",
            line_analyses[first_content_index + 1].text,
        )
        and not PROMOTIONAL_TEXT.search(line_analyses[first_content_index].text)
    ):
        subtitle_layout_name = _clean_recipe_name(
            line_analyses[first_content_index].text
        )
        if subtitle_layout_name and len(subtitle_layout_name) <= 80:
            return subtitle_layout_name

    if first_content_index is not None:
        first_content_line = line_analyses[first_content_index].text
        inline_emoji = re.search(r"[\U0001F000-\U0001FAFF]", first_content_line)
        if (
            inline_emoji
            and line_analyses[first_content_index].evidence.get("metadata", 0.0) < 0.5
        ):
            emoji_prefix = first_content_line[: inline_emoji.start()].strip()
            emoji_suffix = first_content_line[inline_emoji.start() :]
            cased_letters = [character for character in emoji_prefix if character.isalpha()]
            uppercase_ratio = (
                sum(character.isupper() for character in cased_letters)
                / len(cased_letters)
                if cased_letters
                else 0.0
            )
            emoji_prefix_word_count = sum(
                any(character.isalnum() for character in word)
                for word in emoji_prefix.split()
            )
            emoji_prefix_words = [
                word
                for word in emoji_prefix.split()
                if any(character.isalpha() for character in word)
            ]
            title_initial_ratio = (
                sum(
                    next(character for character in word if character.isalpha()).isupper()
                    for word in emoji_prefix_words
                )
                / len(emoji_prefix_words)
                if emoji_prefix_words
                else 0.0
            )
            semantic_emoji_suffix = re.sub(
                r"^[\U0001F000-\U0001FAFF\u2600-\u27BF\ufe0f\u200d\s]+",
                "",
                emoji_suffix,
            )
            if uppercase_ratio >= 0.8 or emoji_prefix_word_count <= 8 and (
                not any(character.isalnum() for character in emoji_suffix)
                or title_initial_ratio >= 0.8
                and re.match(
                    r"^(?:a|an|for|if|the|these|this|when|you)\b",
                    semantic_emoji_suffix,
                    re.IGNORECASE,
                )
            ):
                emoji_prefix_name = _clean_recipe_name(emoji_prefix)
                if emoji_prefix_name and len(emoji_prefix_name) <= 80:
                    return emoji_prefix_name

    for line in line_analyses:
        demonstrative_action = re.match(
            r"^(?:this|these)\s+(?P<name>.{1,80}?)\s+"
            r"(?:make|makes|taste|tastes)\b",
            re.sub(r"^[^\w]+", "", line.text),
            re.IGNORECASE,
        )
        if demonstrative_action:
            action_name = _clean_recipe_name(demonstrative_action.group("name"))
            if action_name and len(action_name.split()) <= 8:
                return action_name

    for line in line_analyses:
        demonstrative_subject = re.match(
            r"^this\s+(?P<subject>.{1,80}?)\s+is\b",
            re.sub(r"^[^\w]+", "", line.text),
            re.IGNORECASE,
        )
        if not demonstrative_subject:
            continue
        title_tail = re.search(
            r"(?P<name>[A-Z][\w'’&-]*(?:\s+(?:[A-Z][\w'’&-]*|&)){1,7})$",
            demonstrative_subject.group("subject"),
        )
        if title_tail:
            return _clean_recipe_name(title_tail.group("name"))

    first_content = next((line.text for line in line_analyses if line.text), "")
    mixed_tag_match = re.match(
        r"^(?:#[\w-]+\s+)+(?P<name>[^#].+)$",
        first_content,
    )
    if mixed_tag_match:
        mixed_tag_name = _clean_recipe_name(mixed_tag_match.group("name"))
        if (
            mixed_tag_name
            and len(mixed_tag_name) <= 80
            and len(mixed_tag_name.split()) <= 8
            and not PROMOTIONAL_TEXT.search(mixed_tag_name)
        ):
            return mixed_tag_name

    first_sentence_match = re.match(
        r"^(?P<name>[^.!?]{1,80})[.!?]\s+\S",
        re.sub(r"^[^\w]+", "", first_content),
    )
    if first_sentence_match:
        first_sentence_name = _clean_recipe_name(first_sentence_match.group("name"))
        first_sentence_word_count = sum(
            any(character.isalnum() for character in word)
            for word in first_sentence_name.split()
        )
        if (
            first_sentence_name
            and first_sentence_word_count <= 8
            and not PROMOTIONAL_TEXT.search(first_sentence_name)
        ):
            return first_sentence_name

    subject_content = re.sub(r"^[^\w]+", "", first_content)
    demonstrative_match = re.match(
        r"^(?:this|these)\s+(?P<name>[\w][\w'’& -]{1,60}?)\s+(?:is|are)\b",
        subject_content,
        re.IGNORECASE,
    )
    if demonstrative_match:
        subject = demonstrative_match.group("name").strip()
        if subject.casefold() not in {"dish", "food", "meal", "recipe"}:
            return subject

    subject_match = re.match(
        r"^(?P<name>[\w][\w'’& -]{1,60}?)\s+(?:is|are)\b",
        subject_content,
        re.IGNORECASE,
    )
    if subject_match:
        subject = subject_match.group("name").strip()
        if subject.casefold() not in {"he", "it", "she", "that", "these", "they", "this"}:
            return subject

    for line in line_analyses:
        subject_match = re.match(
            r"^(?:this|these)\s+(?P<name>[\w][\w'’& -]{1,60}?)\s+(?:is|are)\b",
            re.sub(r"^[^\w]+", "", line.text),
            re.IGNORECASE,
        )
        if subject_match:
            subject = subject_match.group("name").strip()
            if subject.casefold() not in {"dish", "food", "meal", "recipe"}:
                return subject

    generic_names = {
        "announcement",
        "announcements",
        "details",
        "directions",
        "full",
        "full recipe",
        "here is the",
        "here’s the",
        "ingredient",
        "ingredients",
        "instructions",
        "method",
        "recipe",
        "steps",
        "topped with",
    }
    ingredient_context_lines = {
        line_number
        for candidate in field_candidates
        if candidate.field_scores.get("ingredients", 0.0) >= 0.5
        for line_number in candidate.line_numbers
    }
    for line in line_analyses:
        if (
            not line.text
            or BULLET_ITEM.match(line.text)
            or line.line_number in ingredient_context_lines
        ):
            continue
        nutrition_dish_match = re.search(
            r"\bmacros?\s+(?:for\s+each|per)\s+"
            r"(?P<name>[^(:]{1,60}?)(?:\s*\(|\s*:|$)",
            line.text,
            re.IGNORECASE,
        )
        if nutrition_dish_match:
            nutrition_dish_name = _clean_recipe_name(
                nutrition_dish_match.group("name")
            )
            if nutrition_dish_name.casefold() not in {
                "portion",
                "serve",
                "serving",
            }:
                return nutrition_dish_name
        name = _clean_recipe_name(line.text)
        normalized_name = unicodedata.normalize("NFKC", name).casefold()
        if not name or normalized_name in generic_names:
            continue
        if re.match(r"^(?:i|we|you)\b", name, re.IGNORECASE):
            continue
        if re.match(r"^per\s+(?:bowl|serve|serving)\b", name, re.IGNORECASE):
            continue
        suffix_was_removed = name != _clean_recipe_name_without_nutrition(line.text)
        if PROMOTIONAL_TEXT.search(line.text) and not suffix_was_removed:
            continue
        if not suffix_was_removed and any(
            line.evidence.get(concept, 0.0) >= 0.5
            for concept in (
                "ingredient",
                "instruction",
                "metadata",
                "nutrition",
                "servings",
                "tag",
                "timing",
            )
        ):
            continue
        if line.text.endswith((".", "!", "?")) and not suffix_was_removed:
            continue
        lexical_word_count = sum(
            any(character.isalnum() for character in word) for word in name.split()
        )
        if len(name) <= 80 and lexical_word_count <= 8:
            return name
    return None


def _clean_recipe_name(text: str) -> str:
    text = re.sub(
        r"^\s*\([^)]*\brecipe\b[^)]*\)\s*",
        "",
        text,
        flags=re.IGNORECASE,
    )
    text = re.sub(
        r"^.*?\bepisode\s+\d+\s*[/|:–—-]\s*",
        "",
        text,
        flags=re.IGNORECASE,
    )
    text = re.sub(
        r"\s+(?:[^\w\s]+\s*)?\bfollow\s+@\w+.*$",
        "",
        text,
        flags=re.IGNORECASE,
    )
    text = re.sub(
        r"[.!?]?\s+\d+(?:\.\d+)?\s*(?:calories?|k?cal)\b.*$",
        "",
        text,
        flags=re.IGNORECASE,
    )
    text = re.sub(
        r"\s*\((?:makes?|serves?)\s+\d+[^)]*\)\s*[^\w]*$",
        "",
        text,
        flags=re.IGNORECASE,
    )
    text = re.sub(
        r"\s+@\S+\s+code\s+\S+.*$",
        "",
        text,
        flags=re.IGNORECASE,
    )
    text = re.sub(
        r"\s+and\s+it['’]s\s+.+?\s+too\s*$",
        "",
        text,
        flags=re.IGNORECASE,
    )
    text = re.sub(r"\s*\(\s*recipe\b.*$", "", text, flags=re.IGNORECASE)
    text = re.sub(r"\s+recipe\b.*$", "", text.strip(), flags=re.IGNORECASE)
    text = re.sub(r"[\U0001F000-\U0001FAFF\ufe0f\u200d]+", " ", text)
    text = re.sub(r"^[^\w]+|[^\w]+$", "", text)
    return " ".join(text.split())


def _clean_recipe_name_without_nutrition(text: str) -> str:
    text = re.sub(
        r"\s+and\s+it['’]s\s+.+?\s+too\s*$",
        "",
        text,
        flags=re.IGNORECASE,
    )
    text = re.sub(r"\s*\(\s*recipe\b.*$", "", text, flags=re.IGNORECASE)
    text = re.sub(r"\s+recipe\b.*$", "", text.strip(), flags=re.IGNORECASE)
    text = re.sub(r"[\U0001F000-\U0001FAFF\ufe0f\u200d]+", " ", text)
    text = re.sub(r"^[^\w]+|[^\w]+$", "", text)
    return " ".join(text.split())


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


def _field_content(
    line_analyses: list[LineAnalysis],
    field_candidates: list[RecipeFieldCandidate],
    *,
    field: str,
) -> list[str]:
    single_tip = sum(bool(TIP_LINE.match(line.text)) for line in line_analyses) == 1
    if field == "steps":
        numbered_metadata_lines = {
            line.line_number
            for block, _ in _context_blocks(line_analyses)
            if block[0].evidence.get("heading", 0.0) >= 0.8
            and block[0].evidence.get("metadata", 0.0) >= 0.8
            for line in block
        }
        numbered_steps: list[str] = []
        numbered_line_numbers: list[int] = []
        numbered_consumed_line_numbers: set[int] = set()
        current_step: list[str] = []
        for line in line_analyses:
            numbered_match = NUMBERED_INSTRUCTION.match(line.text)
            if numbered_match:
                numbered_line_numbers.append(line.line_number)
                numbered_consumed_line_numbers.add(line.line_number)
                if current_step:
                    numbered_steps.append(" ".join(current_step))
                if line.line_number in numbered_metadata_lines:
                    current_step = []
                    continue
                current_step = [NUMBERED_INSTRUCTION.sub("", line.text).strip()]
                continue
            if not current_step:
                continue
            if (
                not line.text
                or not any(character.isalnum() for character in line.text)
                or line.evidence.get("heading", 0.0) >= 0.8
                or line.text.startswith("#")
                or PROMOTIONAL_TEXT.search(line.text)
            ):
                numbered_steps.append(" ".join(current_step))
                current_step = []
                continue
            current_step.append(line.text)
            numbered_consumed_line_numbers.add(line.line_number)
        if current_step:
            numbered_steps.append(" ".join(current_step))
        if numbered_steps:
            last_numbered_line = max(numbered_line_numbers)
            for line in line_analyses:
                if (
                    line.line_number <= last_numbered_line
                    or line.line_number in numbered_consumed_line_numbers
                    or line.line_number in numbered_metadata_lines
                    or line.evidence.get("heading", 0.0) >= 0.8
                    or line.evidence.get("instruction", 0.0) < 0.5
                    or PROMOTIONAL_TEXT.search(line.text)
                ):
                    continue
                trailing_step = re.sub(r"^[^\w]+", "", line.text).strip()
                if trailing_step:
                    numbered_steps.append(trailing_step)
            return numbered_steps

    ingredient_component_blocks = [
        block
        for block, _ in _context_blocks(line_analyses)
        if _looks_like_ingredient_component(block)
    ]
    component_heading_lines = {
        block[0].line_number for block in ingredient_component_blocks
    }
    contextual_ingredient_lines = {
        line.line_number
        for block, _ in _context_blocks(line_analyses)
        if (
            block[0].evidence.get("heading", 0.0) >= 0.8
            and block[0].evidence.get("ingredient", 0.0) >= 0.8
        )
        or _looks_like_ingredient_component(block)
        or _looks_like_bare_ingredient_list(block)
        for line in block
    }
    headed_bullet_ingredient_lines: set[int] = set()
    for block, _ in _context_blocks(line_analyses):
        if (
            block[0].evidence.get("heading", 0.0) < 0.8
            or any(
                block[0].evidence.get(concept, 0.0) >= 0.5
                for concept in ("instruction", "metadata", "nutrition", "tag")
            )
        ):
            continue
        for source_line in block[1:]:
            if NUMBERED_INSTRUCTION.match(source_line.text):
                break
            if (
                (bullet_match := BULLET_ITEM.match(source_line.text))
                and _is_good_ingredient_parse(
                    _parse_ingredient(bullet_match.group("content").strip()),
                    bullet_match.group("content").strip(),
                )
            ):
                headed_bullet_ingredient_lines.add(source_line.line_number)
    contextual_ingredient_lines.update(headed_bullet_ingredient_lines)
    explicit_optional_ingredient_lines = {
        source_line.line_number
        for candidate in field_candidates
        if any(
            heading_line.line_number in candidate.line_numbers
            and heading_line.evidence.get("heading", 0.0) >= 0.8
            and heading_line.evidence.get("ingredient", 0.0) >= 0.8
            for heading_line in line_analyses
        )
        for source_line in line_analyses
        if source_line.line_number in candidate.line_numbers
        and re.match(r"^optional\b[^:]{0,80}:", source_line.text, re.IGNORECASE)
    }
    contextual_ingredient_lines.update(explicit_optional_ingredient_lines)
    short_contextual_ingredient_lines = {
        source_line.line_number
        for candidate in field_candidates
        if candidate.field_scores.get("ingredients", 0.0) >= 0.6
        for source_line in line_analyses
        if source_line.line_number in candidate.line_numbers
        and source_line.evidence.get("narrative", 0.0) >= 0.8
        and len(source_line.text) <= 60
        and not source_line.text.endswith((".", "!", "?"))
    }
    contextual_ingredient_lines.update(short_contextual_ingredient_lines)
    inline_serving_ingredient_lines = {
        line.line_number
        for line in line_analyses
        if re.match(
            r"^(?:(?:to\s+serve|for\s+serving)|"
            r"(?:optional(?:\s*&\s*customi[sz]able)?\s+)?toppings?|garnish)\s*:",
            line.text,
            re.IGNORECASE,
        )
        and _looks_like_inline_ingredient_group(line.text)
        and line.evidence.get("nutrition", 0.0) < 0.5
    }
    contextual_ingredient_lines.update(inline_serving_ingredient_lines)
    menu_component_lines = _menu_component_lines(line_analyses)
    contextual_ingredient_lines.update(menu_component_lines)
    for index, line in enumerate(line_analyses[:-1]):
        next_line = line_analyses[index + 1]
        if (
            line.line_number in contextual_ingredient_lines
            and not BULLET_ITEM.match(line.text)
            and BULLET_ITEM.match(next_line.text)
            and len(line.text) <= 40
            and not (
                (parsed_heading := _parse_ingredient(line.text))
                and parsed_heading.amount
            )
        ):
            component_heading_lines.add(line.line_number)
        if index == 0:
            continue
        previous_line = line_analyses[index - 1]
        if (
            previous_line.evidence.get("heading", 0.0) >= 0.8
            and previous_line.evidence.get("ingredient", 0.0) >= 0.8
            and line.line_number in contextual_ingredient_lines
            and line.text
            and next_line.text
            and not BULLET_ITEM.match(line.text)
            and not any(character.isdigit() for character in line.text)
        ):
            parsed_line = _parse_ingredient(line.text)
            parsed_next_line = _parse_ingredient(next_line.text)
            if (
                not (parsed_line and parsed_line.amount)
                and parsed_next_line
                and parsed_next_line.amount
            ):
                component_heading_lines.add(line.line_number)
    contextual_step_lines = {
        line.line_number
        for block, _ in _context_blocks(line_analyses)
        if block[0].evidence.get("heading", 0.0) >= 0.8
        and block[0].evidence.get("instruction", 0.0) >= 0.8
        for line in block
    }
    contextual_metadata_lines = {
        line.line_number
        for block, _ in _context_blocks(line_analyses)
        if block[0].evidence.get("heading", 0.0) >= 0.8
        and block[0].evidence.get("metadata", 0.0) >= 0.8
        for line in block
    }
    first_ingredient_heading_line = next(
        (
            line.line_number
            for line in line_analyses
            if line.evidence.get("heading", 0.0) >= 0.8
            and line.evidence.get("ingredient", 0.0) >= 0.8
        ),
        None,
    )
    first_servings_line = next(
        (
            line.line_number
            for line in line_analyses
            if line.evidence.get("servings", 0.0) >= 0.8
        ),
        None,
    )
    first_content_line = next(
        (line.line_number for line in line_analyses if line.text),
        None,
    )
    first_ingredient_content_line = next(
        (
            line.line_number
            for line in line_analyses
            if line.line_number != first_content_line
            and line.evidence.get("ingredient", 0.0) >= 0.5
        ),
        None,
    )
    if field == "steps":
        line_numbers = {
            line.line_number
            for line in line_analyses
            if line.evidence.get("instruction", 0.0) >= 0.5
        } | contextual_step_lines
    else:
        line_numbers = {
            line_number
            for candidate in field_candidates
            if candidate.field_scores.get(field, 0.0) >= 0.5
            and (field != "ingredients" or len(candidate.line_numbers) >= 2)
            for line_number in candidate.line_numbers
        } | menu_component_lines
        if field == "ingredients":
            line_numbers |= contextual_ingredient_lines
    values = []
    for index, line in enumerate(line_analyses):
        if (
            field == "ingredients"
            and values
            and re.fullmatch(r"\([^\n]+\)", line.text)
        ):
            previous_nonblank = next(
                (
                    candidate
                    for candidate in reversed(line_analyses[:index])
                    if candidate.text
                ),
                None,
            )
            next_nonblank = next(
                (
                    candidate
                    for candidate in line_analyses[index + 1 :]
                    if candidate.text
                ),
                None,
            )
            if (
                previous_nonblank is not None
                and previous_nonblank.line_number in line_numbers
                and next_nonblank is not None
                and next_nonblank.line_number in line_numbers
            ):
                values[-1] = f"{values[-1]} {line.text}"
                continue
        if line.line_number not in line_numbers:
            continue
        if (
            line.evidence.get("heading", 0.0) >= 0.8
            or line.line_number in component_heading_lines
        ):
            continue
        if (
            field == "ingredients"
            and (
                first_ingredient_heading_line is not None
                and line.line_number < first_ingredient_heading_line
                or
                line.line_number in contextual_step_lines
                or line.line_number in contextual_metadata_lines
                or
                any(
                    line.evidence.get(concept, 0.0) >= 0.5
                    for concept in (
                        "metadata",
                        "nutrition",
                        "tag",
                        "timing",
                    )
                )
                or (
                    line.evidence.get("servings", 0.0) >= 0.5
                    and not (
                        line.line_number in contextual_ingredient_lines
                        and line.evidence.get("heading", 0.0) < 0.8
                        and not re.match(
                            r"^(?:makes?|serves?)\b", line.text, re.IGNORECASE
                        )
                        and _is_good_ingredient_parse(
                            _parse_ingredient(
                                (
                                    BULLET_ITEM.match(line.text).group("content")
                                    if BULLET_ITEM.match(line.text)
                                    else line.text
                                ).strip()
                            ),
                            (
                                BULLET_ITEM.match(line.text).group("content")
                                if BULLET_ITEM.match(line.text)
                                else line.text
                            ).strip(),
                        )
                    )
                )
                or (
                    line.evidence.get("instruction", 0.0) >= 0.5
                    and not (
                        line.line_number in contextual_ingredient_lines
                        and (
                            _looks_like_inline_ingredient_group(line.text)
                            or not IMPERATIVE_START.match(
                                NUMBERED_INSTRUCTION.sub(
                                    "",
                                    BULLET_ITEM.match(line.text).group("content")
                                    if BULLET_ITEM.match(line.text)
                                    else line.text
                                ).strip()
                            )
                        )
                    )
                )
                or (
                    line.evidence.get("ingredient", 0.0) < 0.5
                    and line.line_number not in contextual_ingredient_lines
                )
            )
        ):
            continue
        if field == "steps":
            bullet_match = BULLET_ITEM.match(line.text)
            instruction_text = (
                bullet_match.group("content").strip() if bullet_match else line.text
            )
            if (
                first_servings_line is not None
                and first_ingredient_content_line is not None
                and line.line_number < first_servings_line
                and line.line_number < first_ingredient_content_line
                or
                line.line_number in contextual_metadata_lines
                or PROMOTIONAL_TEXT.search(line.text)
                or
                line.line_number in contextual_ingredient_lines
                and (
                    _looks_like_inline_ingredient_group(line.text)
                    or not IMPERATIVE_START.match(
                        NUMBERED_INSTRUCTION.sub("", instruction_text).strip()
                    )
                )
            ):
                continue
            if (
                line.evidence.get("instruction", 0.0) < 0.5
                and line.line_number not in contextual_step_lines
            ):
                continue
        text = line.text
        bullet_match = BULLET_ITEM.match(text)
        if bullet_match:
            text = bullet_match.group("content").strip()
        elif field == "ingredients":
            text = re.sub(
                r"^(?:[\U0001F000-\U0001FAFF\u2600-\u27BF\ufe0f\u200d]+\s*)+",
                "",
                text,
            ).strip()
        if field == "steps":
            text = NUMBERED_INSTRUCTION.sub("", text).strip()
            text = re.sub(r"^[^\w]+", "", text)
            if single_tip:
                text = re.sub(
                    r"^tip(?:\s+\d+)?:\s*", "", text, flags=re.IGNORECASE
                )
        if text:
            values.append(text)
    return values


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


def _candidate_warnings(
    candidate: SocialRecipeCandidate,
    line_analyses: list[LineAnalysis],
) -> list[str]:
    warnings = []
    if not candidate.name:
        warnings.append("No reliable recipe name was found.")
    if not candidate.raw_ingredients:
        warnings.append("No ingredient section was found.")
    if not candidate.steps:
        source_text = "\n".join(line.text for line in line_analyses)
        if EXTERNAL_FULL_RECIPE_CUE.search(source_text):
            warnings.append(
                "The source points to a full printable recipe. Ask the user to open it "
                "and provide its URL before accepting this incomplete recipe."
            )
        else:
            warnings.append("No instruction section was found.")
    return warnings


def parse_recipe_text(text: str) -> RecipeTextParseResult:
    """Return line evidence, field associations, and review-only recipe content."""

    line_analyses = analyze_lines(text)
    field_candidates = build_field_candidates(line_analyses)
    candidate = build_social_recipe_candidate(line_analyses, field_candidates)
    warnings = _candidate_warnings(candidate, line_analyses)
    return RecipeTextParseResult(
        candidate=candidate,
        line_analyses=line_analyses,
        field_candidates=field_candidates,
        unclassified_lines=[line.text for line in line_analyses if not line.evidence],
        warnings=warnings,
        fallback_recommended=bool(warnings),
    )
