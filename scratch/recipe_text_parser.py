"""Platform-independent scratch boundary for parsing recipe-like text.

This module accepts text that has already been acquired from a description,
caption, or transcript. It does not fetch URLs, call an LLM, save recipes, or
depend on a particular social-media platform.

Planned tutorial stages:

1. Normalize the source text into meaningful lines.
2. Analyze every line for independent recipe-concept evidence.
3. Group nearby, compatible line evidence into recipe sections.
4. Build a review-only candidate from supported sections.
5. Report unclassified text and decide whether fallback extraction is needed.

Temporary working design
------------------------

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


assert normalize_lines("") == []
assert normalize_lines("  \n\t\n") == ["", ""]
assert normalize_lines("  Pasta  \n\n  1 cup tomatoes  ") == [
    "Pasta",
    "",
    "1 cup tomatoes",
]
assert normalize_lines("• salt\r\n#weeknight\nMix  well") == [
    "• salt",
    "#weeknight",
    "Mix  well",
]
assert normalize_lines("Ingredients\n\nDirections") == [
    "Ingredients",
    "",
    "Directions",
]

assert analyze_line(1, "-1 cup rice").evidence == {
    "ingredient": 0.8,
    "instruction": 0.2,
}
assert analyze_line(1, "-A drizzle of olive oil").evidence == {
    "ingredient": 0.8,
    "instruction": 0.2,
}
assert analyze_line(1, "•Brown the garlic.").evidence == {
    "instruction": 1.0,
}
assert analyze_line(1, "•Add pasta cooking water, cream and stir.").evidence == {
    "instruction": 1.0,
}
assert analyze_line(1, "-").evidence == {"divider": 1.0}
assert analyze_line(1, "Macros per serving:").evidence == {
    "heading": 1.0,
    "nutrition": 1.0,
}
assert analyze_line(1, "Protein: 46g").evidence == {"nutrition": 1.0}
assert analyze_line(1, "548 Calories | 51g Protein").evidence == {"nutrition": 1.0}
assert analyze_line(1, "66g Protein Meal Prep").evidence == {"nutrition": 1.0}
assert analyze_line(1, "66g Protein Meal Prep💪🏼").evidence == {"nutrition": 1.0}
assert analyze_line(1, "71gC | 10gF | 66gP").evidence == {"nutrition": 1.0}
assert analyze_line(
    1, "It’s 305 calories per, I said under 300 in the video and misspoke"
).evidence == {"nutrition": 1.0}
assert analyze_line(
    1, "*I recommend using a whey/casein blend for the best texture."
).evidence == {"instruction": 0.2, "narrative": 1.0}
assert analyze_line(
    1,
    "2 chicken thighs (substitute with 1 chicken breast for more protein and less calories)",
).evidence == {"ingredient": 0.7}
assert analyze_line(1, "The goal is 40lbs in 90 days").evidence == {
    "narrative": 1.0
}
assert analyze_line(1, "Meals for Weight-loss: Ep 9").evidence == {"metadata": 1.0}
assert analyze_line(1, "Servings: 4").evidence == {"servings": 1.0}
assert _recipe_servings(analyze_lines("Calories per slice of 10")) == 10
assert analyze_line(1, "Ingredients for 2 sweet potato boats 🛶").evidence == {
    "heading": 1.0,
    "ingredient": 1.0,
    "servings": 1.0,
}
assert analyze_line(
    1, "Air Fryer: 190°C (375°F) for 40-45 minutes, turning halfway."
).evidence == {"instruction": 1.0, "timing": 1.0}
assert analyze_line(1, "High: 2–3 hours").evidence == {"timing": 1.0}
assert analyze_line(1, "-4 servings (150 g) ham").evidence == {
    "ingredient": 0.8,
    "instruction": 0.2,
}
assert analyze_line(1, "Served in 2 cup glass containers").evidence == {
    "metadata": 1.0
}
assert analyze_line(1, "Storage:").evidence == {
    "heading": 1.0,
    "metadata": 1.0,
}
assert analyze_line(1, "Notes").evidence == {
    "heading": 1.0,
    "metadata": 1.0,
}
assert analyze_line(1, "Storage & Heating ♨️").evidence == {
    "heading": 1.0,
    "metadata": 1.0,
}
assert analyze_line(1, "Instructions").evidence == {
    "heading": 1.0,
    "instruction": 1.0,
}
assert analyze_line(1, "-Refrigerate up to 4 days").evidence == {
    "metadata": 1.0
}
assert analyze_line(1, "Important Tips:").evidence == {
    "heading": 1.0,
    "instruction": 1.0,
}
assert analyze_line(1, "Mix well and cook for 4 minutes.").evidence == {
    "instruction": 1.0
}
assert analyze_line(1, "See the printable recipe for nutrition info.").evidence == {
    "heading": 0.2,
    "nutrition": 0.2,
    "narrative": 1.0,
}
assert analyze_line(1, "#dinner easyrecipe").evidence == {"tag": 1.0}
assert analyze_line(1, "[Garnish]").evidence == {"heading": 1.0}
assert analyze_line(1, "INSTRUCTIONS").evidence == {
    "heading": 1.0,
    "instruction": 1.0,
}

_context_example = parse_recipe_text(
    "Ingredients:\n-1 cup rice\n\nInstructions:\n•Mix the rice.\n\n•Serve warm.\n\n#dinner"
)
assert [
    _dominant_field(candidate) for candidate in _context_example.field_candidates
] == ["ingredients", "steps", "tags"]
assert _context_example.field_candidates[1].line_numbers == [4, 5, 7]
assert _context_example.candidate is not None
assert _context_example.candidate.raw_ingredients == ["1 cup rice"]
assert _context_example.candidate.steps == ["Mix the rice.", "Serve warm."]
assert _context_example.candidate.tags == ["dinner"]

_component_example = build_field_candidates(
    analyze_lines(
        "Chicken dinner\n\n"
        "For the chicken:\nChicken thighs\nGarlic powder\n\n"
        "For serving:\nRice\nLime wedges"
    )
)
assert [
    _dominant_field(candidate) for candidate in _component_example
] == ["name", "ingredients"]

_emoji_component_example = build_field_candidates(
    analyze_lines("Rice 🍚\n250g uncooked rice")
)
assert _emoji_component_example[0].field_scores["ingredients"] == 0.6

_preview_example = parse_recipe_text(
    "Creamy Rice Recipe\n\nIngredients:\n-1 cup rice\n\n"
    "Instructions:\n1. Cook the rice.\n\n#dinner"
)
assert _preview_example.candidate is not None
assert _preview_example.candidate.name == "Creamy Rice"
assert _preview_example.fallback_recommended is False

_same_line_promo_example = parse_recipe_text(
    "SOYMAXX TOAST 🧀 Follow @creator for more\n\n"
    "Ingredients (makes ~4 slices)\n4 slices sourdough\n\n"
    "1. Toast the sourdough."
)
assert _same_line_promo_example.candidate is not None
assert _same_line_promo_example.candidate.name == "SOYMAXX TOAST"
assert _same_line_promo_example.candidate.servings == 4

_series_title_example = parse_recipe_text(
    "Any season is soup season if you believe.\n"
    "Episode 23: super speedy laksa\n\n"
    "Ingredients:\n1 tbsp paste\n\nMethod:\n1. Brown the paste."
)
assert _series_title_example.candidate is not None
assert _series_title_example.candidate.name == "super speedy laksa"

_prefixed_series_title_example = parse_recipe_text(
    "Dinner in twenty minutes!\nBare Minimum Meals, Episode 11: Honey Mustard Chicken"
)
assert _prefixed_series_title_example.candidate is not None
assert _prefixed_series_title_example.candidate.name == "Honey Mustard Chicken"

_described_demonstrative_title_example = parse_recipe_text(
    "I nearly skipped this recipe!\n"
    "This moist, fluffy, not-too-sweet Biscoff Banana Loaf is worth making."
)
assert _described_demonstrative_title_example.candidate is not None
assert _described_demonstrative_title_example.candidate.name == "Biscoff Banana Loaf"

_hashtag_title_example = parse_recipe_text(
    "#SponsorPartner One Pot Chicken Rice\nFull recipe in my bio!"
)
assert _hashtag_title_example.candidate is not None
assert _hashtag_title_example.candidate.name == "One Pot Chicken Rice"
assert _hashtag_title_example.candidate.tags == ["sponsorpartner"]

_series_prefix_example = parse_recipe_text(
    "Meals for Weight-loss: Ep 9\nTandoori Chicken Rice Bowl\n\n"
    "Instructions\n1. Divide the rice evenly between 4 meal prep containers."
)
assert _series_prefix_example.candidate is not None
assert _series_prefix_example.candidate.name == "Tandoori Chicken Rice Bowl"
assert _series_prefix_example.candidate.servings == 4
assert _series_prefix_example.candidate.raw_ingredients == []

_macro_yield_example = parse_recipe_text(
    "Creamy Chicken Pasta\n66g Protein Meal Prep\n\n"
    "(Macros: Per Serving - 6 Total)\n663 Calories\n\n"
    "Ingredients:\n1 cup pasta"
)
assert _macro_yield_example.candidate is not None
assert _macro_yield_example.candidate.name == "Creamy Chicken Pasta"
assert _macro_yield_example.candidate.servings == 6

_section_context_example = parse_recipe_text(
    "Chicken Burritos\n\n(Macros: Per Burrito - 10 Total)\n\n"
    "Ingredients:\nSeason Chicken With: 1 tsp salt, 1 tsp paprika\n"
    "2 chicken breasts\n\nImportant Tips:\n"
    "* Before filling, warm each tortilla."
)
assert _section_context_example.candidate is not None
assert _section_context_example.candidate.servings == 10
assert _section_context_example.candidate.raw_ingredients == [
    "Season Chicken With: 1 tsp salt, 1 tsp paprika",
    "2 chicken breasts",
]
assert _section_context_example.candidate.steps == [
    "Before filling, warm each tortilla."
]

_yield_title_example = parse_recipe_text(
    "🍔 Smash Burger Bowls (makes 4 big bowls)\n\n"
    "Caramelized Onions\n• 2 onions\n• Splash of water as needed to soften"
)
assert _yield_title_example.candidate is not None
assert _yield_title_example.candidate.name == "Smash Burger Bowls"
assert _yield_title_example.candidate.raw_ingredients == [
    "2 onions",
    "Splash of water as needed to soften",
]
assert _yield_title_example.candidate.steps == []

_symbol_subject_example = parse_recipe_text(
    "🔥These Crispy Chicken Tenders Are Insanely Good\n\n"
    "Chicken\n• 1 lb chicken"
)
assert _symbol_subject_example.candidate is not None
assert _symbol_subject_example.candidate.name == "Crispy Chicken Tenders"

_menu_hack_example = parse_recipe_text(
    "👇 BBQ Chicken Mac Hack @menu.app code SAVE20\n\n"
    "✅ 540 Cal • 50g Protein\nSmall Mac & Cheese\n"
    "12-Count Grilled Nuggets\nBBQ Sauce\nLarge Diet Soda\n\n"
    "^ mix all together for Barbecue Chicken Mac & Cheese Bowl"
)
assert _menu_hack_example.candidate is not None
assert _menu_hack_example.candidate.name == "BBQ Chicken Mac Hack"
assert _menu_hack_example.candidate.raw_ingredients == [
    "Small Mac & Cheese",
    "12-Count Grilled Nuggets",
    "BBQ Sauce",
]
assert _menu_hack_example.candidate.steps == [
    "mix all together for Barbecue Chicken Mac & Cheese Bowl"
]

_decorative_recipe_prefix_example = parse_recipe_text(
    "(👇recipe) 300 Calorie Protein Brookie\n\n"
    "🗣️ Are you FOLLOWING @creator\n\nIngredients:\n40g yogurt"
)
assert _decorative_recipe_prefix_example.candidate is not None
assert _decorative_recipe_prefix_example.candidate.name == "300 Calorie Protein Brookie"

_instruction_components_example = parse_recipe_text(
    "Beef Bowl\n\nServings: 4\n\nIngredients\nBeef Coating\n"
    "-1 lb beef\n-1 tsp salt\n\nInstructions:\nBeef:\n"
    "-Coat beef with salt\n-Sear until browned\n\nFinish:\n"
    "Toss with sauce\nGarnish with onions\n\nStorage:\nFridge: 3 days"
)
assert _instruction_components_example.candidate is not None
assert _instruction_components_example.candidate.servings == 4
assert _instruction_components_example.candidate.raw_ingredients == [
    "1 lb beef",
    "1 tsp salt",
]
assert _instruction_components_example.candidate.steps == [
    "Coat beef with salt",
    "Sear until browned",
    "Toss with sauce",
    "Garnish with onions",
]

_post_recipe_guidance_example = parse_recipe_text(
    "Chicken Bowl\n\nIngredients\n-4 servings sliced ham\n-1 cup rice\n\n"
    "Instructions\n-Rinse rice\n-Evenly divide between containers\n\n"
    "Notes\n-When removed, let rest\n\n-Refrigerate up to 4 days\n\n"
    "Reheating:\n-From frozen: thaw overnight"
)
assert _post_recipe_guidance_example.candidate is not None
assert _post_recipe_guidance_example.candidate.raw_ingredients == [
    "4 servings sliced ham",
    "1 cup rice",
]
assert _post_recipe_guidance_example.candidate.steps == [
    "Rinse rice",
    "Evenly divide between containers",
]

_numbered_post_recipe_guidance_example = parse_recipe_text(
    "Snack Pockets\n\nIngredients\n1 cup flour\n\n"
    "Freezing Instructions ❄️:\n1. Wrap each pocket\n2. Freeze for one month\n\n"
    "Reheating Instructions🔥:\n1. Microwave until hot"
)
assert _numbered_post_recipe_guidance_example.candidate is not None
assert _numbered_post_recipe_guidance_example.candidate.steps == []

_component_prefixed_instruction_example = parse_recipe_text(
    "Chilli lime chicken with coconut rice & watermelon salad\n\n"
    "Ingredients for 3 servings:\n1 cup rice\n\n"
    "For the rice, cook to packet instructions."
)
assert _component_prefixed_instruction_example.candidate is not None
assert _component_prefixed_instruction_example.candidate.name == (
    "Chilli lime chicken with coconut rice & watermelon salad"
)
assert _component_prefixed_instruction_example.candidate.steps == [
    "For the rice, cook to packet instructions."
]

_inline_component_heading_example = parse_recipe_text(
    "Skewers\n\nIngredients (serves 2):\nChicken Skewers\n"
    "300g chicken thighs\n1 tsp seasoning\n\n"
    "In a bowl combine the ingredients.\nAir fry until cooked.\n"
    "Divide between two plates.\nFry until browned.\nLay flat.\nToast until crisp.\n"
    "Optional: For extra crunch, soak briefly.\nLift each piece.\nPlace in basket.\n"
    "Melt the butter.\nOnce cooked, add the sauce.\nSpoon over the top.\n"
    "Throw everything into one pan."
)
assert _inline_component_heading_example.candidate is not None
assert _inline_component_heading_example.candidate.raw_ingredients == [
    "300g chicken thighs",
    "1 tsp seasoning",
]
assert _inline_component_heading_example.candidate.steps == [
    "In a bowl combine the ingredients.",
    "Air fry until cooked.",
    "Divide between two plates.",
    "Fry until browned.",
    "Lay flat.",
    "Toast until crisp.",
    "Optional: For extra crunch, soak briefly.",
    "Lift each piece.",
    "Place in basket.",
    "Melt the butter.",
    "Once cooked, add the sauce.",
    "Spoon over the top.",
    "Throw everything into one pan.",
]

_same_line_narrative_example = parse_recipe_text(
    "Jerk Chicken Fried Rice! Meal prep 5 servings for the week.\n\n"
    "Jerk Chicken:\n• 800g chicken"
)
assert _same_line_narrative_example.candidate is not None
assert _same_line_narrative_example.candidate.name == "Jerk Chicken Fried Rice"

_decorated_save_title_example = parse_recipe_text(
    "SAVE THIS ‼️ Jersey Mikes Sub in a Tub 🤯 (recipe 👇🏽)\n\n"
    "Macros per serving (makes x3): 457 calories"
)
assert _decorated_save_title_example.candidate is not None
assert _decorated_save_title_example.candidate.name == "Jersey Mikes Sub in a Tub"
assert _decorated_save_title_example.candidate.servings == 3

_emoji_claim_title_example = parse_recipe_text(
    "Diabetic Friendly Guacamole 🥑 Chicken Salad and it’s Low Carb too! Details follow."
)
assert _emoji_claim_title_example.candidate is not None
assert _emoji_claim_title_example.candidate.name == (
    "Diabetic Friendly Guacamole Chicken Salad"
)
assert _clean_recipe_name("Crispy Chicken Nuggets (recipe 👇🏽)") == (
    "Crispy Chicken Nuggets"
)

_decorated_bullet_yield_title_example = parse_recipe_text(
    "Save time with prep!\n\n🔥Thick Cheeseburger (makes 4):\n\n"
    "Ingredients:\n✅ - 1 lb beef\n✅ - Pickle chips"
)
assert _decorated_bullet_yield_title_example.candidate is not None
assert _decorated_bullet_yield_title_example.candidate.name == "Thick Cheeseburger"
assert _decorated_bullet_yield_title_example.candidate.raw_ingredients == [
    "1 lb beef",
    "Pickle chips",
]

_nutrition_fallback_title_example = parse_recipe_text(
    "Save Time, Money, And Eat Better!\n\n"
    "Macros for Each Pancakes (Recipe Makes 6):\n100 Calories\n\n"
    "Ingredients for 6\n-1 cup flour"
)
assert _nutrition_fallback_title_example.candidate is not None
assert _nutrition_fallback_title_example.candidate.name == "Pancakes"

_all_you_need_context_example = parse_recipe_text(
    "HERB CHICKEN\n(High Protein)\n\nAll you need is:\n"
    "Chicken thighs\nHerbs\nSalt\n\nOptional: You can add lemon.\n\n"
    "Let me know if you try it."
)
assert _all_you_need_context_example.candidate is not None
assert _all_you_need_context_example.candidate.name == "HERB CHICKEN"
assert _all_you_need_context_example.candidate.raw_ingredients == [
    "Chicken thighs",
    "Herbs",
    "Salt",
]
assert _all_you_need_context_example.candidate.steps == [
    "Optional: You can add lemon."
]

_inline_emoji_title_example = parse_recipe_text(
    "FLUFFY LEMON PANCAKE BOWLS 🍋A baked breakfast with berries.\n\n"
    "Macros (1 bowl)\n365 kcal"
)
assert _inline_emoji_title_example.candidate is not None
assert _inline_emoji_title_example.candidate.name == "FLUFFY LEMON PANCAKE BOWLS"
assert _inline_emoji_title_example.candidate.servings == 1

_title_case_emoji_suffix_example = parse_recipe_text(
    "High Protein Chicken Rolls🍗🥓\nEasy meal prep\n\n"
    "Don’t forget to check out my digital recipe book."
)
assert _title_case_emoji_suffix_example.candidate is not None
assert _title_case_emoji_suffix_example.candidate.name == "High Protein Chicken Rolls"

_trailing_method_and_serving_group_example = parse_recipe_text(
    "NOODLE BOWL 🔥 Make this tonight.\n\nMacros (serves 4)\n500 kcal\n\n"
    "Ingredients\n-1 pack noodles\n\nTo serve: Lime wedges, herbs.\n\n"
    "Method:\n1. Cook the noodles.\n\nDivide between bowls."
)
assert _trailing_method_and_serving_group_example.candidate is not None
assert _trailing_method_and_serving_group_example.candidate.name == "NOODLE BOWL"
assert _trailing_method_and_serving_group_example.candidate.raw_ingredients == [
    "1 pack noodles",
    "To serve: Lime wedges, herbs.",
]
assert _trailing_method_and_serving_group_example.candidate.steps == [
    "Cook the noodles.",
    "Divide between bowls.",
]

_labeled_title_and_emoji_ingredient_example = parse_recipe_text(
    "Lunch Series episode 6\n\nRECIPE: Creamy Orzo Salad 😌\n\n"
    "Ingredients:\n✨ 250g orzo\n✨ 1 cucumber\n\n"
    "Meanwhile make the dressing.\nThen simply assemble!\n"
    "Simply mix the filling.\nTake the wrap and fold it."
)
assert _labeled_title_and_emoji_ingredient_example.candidate is not None
assert _labeled_title_and_emoji_ingredient_example.candidate.name == (
    "Creamy Orzo Salad"
)
assert _labeled_title_and_emoji_ingredient_example.candidate.raw_ingredients == [
    "250g orzo",
    "1 cucumber",
]
assert _labeled_title_and_emoji_ingredient_example.candidate.steps == [
    "Meanwhile make the dressing.",
    "Then simply assemble!",
    "Simply mix the filling.",
    "Take the wrap and fold it.",
]

_series_then_title_example = parse_recipe_text(
    "TIRED GIRL DINNERS: episode 6 🫶🏻\n\nSweet Chilli Toastie 🤍\n\n"
    "Serves Two\n\nIngredients:\n1 slice bread\n\n"
    "Then that’s literally it! Simply serve warm."
)
assert _series_then_title_example.candidate is not None
assert _series_then_title_example.candidate.name == "Sweet Chilli Toastie"
assert _series_then_title_example.candidate.servings == 2
assert _series_then_title_example.candidate.steps == [
    "Then that’s literally it! Simply serve warm."
]

_ingredient_heading_yield_and_creami_verbs_example = parse_recipe_text(
    "PROTEIN ICE CREAM\n\nIngredients (1 serve)\n1 cup milk\n\n"
    "Method\nCrush the cookie.\nSpin until smooth.\nDispense into a bowl."
)
assert _ingredient_heading_yield_and_creami_verbs_example.candidate is not None
assert _ingredient_heading_yield_and_creami_verbs_example.candidate.servings == 1
assert _ingredient_heading_yield_and_creami_verbs_example.candidate.steps == [
    "Crush the cookie.",
    "Spin until smooth.",
    "Dispense into a bowl.",
]

_batch_yield_long_ingredient_and_method_verbs_example = parse_recipe_text(
    "SNACK BITES\n\nIngredients (1 batch)\n\n3 rice cakes (about 27g)\n\n"
    "1 scoop chocolate protein (use any brand you like) (about 30g)\n\n"
    "2 egg whites\n\nMethod\nForm into clusters.\nAllow to cool."
)
assert _batch_yield_long_ingredient_and_method_verbs_example.candidate is not None
assert _batch_yield_long_ingredient_and_method_verbs_example.candidate.servings == 1
assert _batch_yield_long_ingredient_and_method_verbs_example.candidate.raw_ingredients == [
    "3 rice cakes (about 27g)",
    "1 scoop chocolate protein (use any brand you like) (about 30g)",
    "2 egg whites",
]
assert _batch_yield_long_ingredient_and_method_verbs_example.candidate.steps == [
    "Form into clusters.",
    "Allow to cool.",
]

_descriptive_yield_parenthetical_and_method_verbs_example = parse_recipe_text(
    "BAKED OATS\n\nIngredients (1 huge serve)\n\n1 banana\n"
    "1 scoop protein powder\n(Use any brand you like)\n10g peanut butter\n\n"
    "Method\nMash the banana.\nMicrowave until cooked.\n"
    "Refrigerate overnight.\nWake up to breakfast."
)
assert _descriptive_yield_parenthetical_and_method_verbs_example.candidate is not None
assert _descriptive_yield_parenthetical_and_method_verbs_example.candidate.servings == 1
assert (
    _descriptive_yield_parenthetical_and_method_verbs_example.candidate.raw_ingredients
    == [
        "1 banana",
        "1 scoop protein powder (Use any brand you like)",
        "10g peanut butter",
    ]
)
assert _descriptive_yield_parenthetical_and_method_verbs_example.candidate.steps == [
    "Mash the banana.",
    "Microwave until cooked.",
    "Refrigerate overnight.",
    "Wake up to breakfast.",
]

_temporal_instruction_prefix_example = parse_recipe_text(
    "PASTA\n\nIngredients\n1 cup pasta\n\n"
    "Meanwhile, add the sauce and stir.\n"
    "Before draining the pasta, reserve some cooking water."
)
assert _temporal_instruction_prefix_example.candidate is not None
assert _temporal_instruction_prefix_example.candidate.steps == [
    "Meanwhile, add the sauce and stir.",
    "Before draining the pasta, reserve some cooking water.",
]

_plain_title_case_and_method_verbs_example = parse_recipe_text(
    "One Pot Herbed Chicken Rice\n\nServes 4\n\n1 cup rice\n2 chicken thighs\n\n"
    "Pat the chicken dry.\nCover and cook for 20 minutes.\n"
    "Finish with fresh herbs."
)
assert _plain_title_case_and_method_verbs_example.candidate is not None
assert _plain_title_case_and_method_verbs_example.candidate.name == (
    "One Pot Herbed Chicken Rice"
)
assert _plain_title_case_and_method_verbs_example.candidate.steps == [
    "Pat the chicken dry.",
    "Cover and cook for 20 minutes.",
    "Finish with fresh herbs.",
]

_pre_yield_imperative_slogan_example = parse_recipe_text(
    "Sticky Chicken\n\nCook once, eat twice. A useful meal-prep recipe.\n\n"
    "Serves 4\n\n500g chicken\n\nCook the chicken until browned."
)
assert _pre_yield_imperative_slogan_example.candidate is not None
assert _pre_yield_imperative_slogan_example.candidate.steps == [
    "Cook the chicken until browned."
]

_keycap_steps_optional_ingredient_and_variable_yield_example = parse_recipe_text(
    "LAVA CAKE\n\nThe batch can be divided into 2 or 3 servings.\n\n"
    "Ingredients:\n1 cup cottage cheese\n"
    "Optional but highly recommended: a sprinkle of chocolate chips\n\n"
    "1️⃣ Blend until smooth.\n2️⃣ Bake until set."
)
assert (
    _keycap_steps_optional_ingredient_and_variable_yield_example.candidate
    is not None
)
assert (
    _keycap_steps_optional_ingredient_and_variable_yield_example.candidate.servings
    is None
)
assert (
    _keycap_steps_optional_ingredient_and_variable_yield_example.candidate.raw_ingredients
    == [
        "1 cup cottage cheese",
        "Optional but highly recommended: a sprinkle of chocolate chips",
    ]
)
assert _keycap_steps_optional_ingredient_and_variable_yield_example.candidate.steps == [
    "Blend until smooth.",
    "Bake until set.",
]

_compact_numbered_steps_example = parse_recipe_text(
    "ROAST DINNER\n\n1.Preheat the oven.\n2.Add the vegetables."
)
assert _compact_numbered_steps_example.candidate is not None
assert _compact_numbered_steps_example.candidate.steps == [
    "Preheat the oven.",
    "Add the vegetables.",
]
assert not NUMBERED_INSTRUCTION.match("1.5 cups flour")

_second_person_slogan_example = parse_recipe_text(
    "You 🤝 oatmeal (soon)\n\n𝘿𝙚𝙩𝙖𝙞𝙡𝙨:\n\n- 1 cup oats\n\n"
    "𝙏𝙤𝙥𝙥𝙚𝙙 𝙬𝙞𝙩𝙝:\n\n- berries\n\n"
    "𝘿𝙞𝙧𝙚𝙘𝙩𝙞𝙤𝙣𝙨:\n\n1. Mix the oats."
)
assert _second_person_slogan_example.candidate is not None
assert _second_person_slogan_example.candidate.name is None

_long_first_line_title_with_nearby_yield_example = parse_recipe_text(
    "Creamy Lemon Garlic Chicken Bowls with a creamy low calorie mash ✨\n\n"
    "Recipe serves 4 and has 40g protein per serve."
)
assert _long_first_line_title_with_nearby_yield_example.candidate is not None
assert _long_first_line_title_with_nearby_yield_example.candidate.name == (
    "Creamy Lemon Garlic Chicken Bowls with a creamy low calorie mash"
)

_recipe_yield_and_component_step_boundary_example = parse_recipe_text(
    "Chicken Rice Bowls ✨\n\nRecipe (serves 2):\n\nPotato:\n"
    "- 500g potato\n- 1 tsp oil\n1. Boil the potato\n\n"
    "Sauce:\n- 1 cup yogurt\n1. Blend until smooth"
)
assert _recipe_yield_and_component_step_boundary_example.candidate is not None
assert _recipe_yield_and_component_step_boundary_example.candidate.name == (
    "Chicken Rice Bowls"
)
assert _recipe_yield_and_component_step_boundary_example.candidate.raw_ingredients == [
    "500g potato",
    "1 tsp oil",
    "1 cup yogurt",
]
assert _recipe_yield_and_component_step_boundary_example.candidate.steps == [
    "Boil the potato",
    "Blend until smooth",
]

_series_of_name_and_inline_tags_example = parse_recipe_text(
    "Episode 5 of Meals for an Athlete: Chicken Soup! "
    "A quick dinner. #highprotein #easyrecipe"
)
assert _series_of_name_and_inline_tags_example.candidate is not None
assert _series_of_name_and_inline_tags_example.candidate.name == "Chicken Soup"
assert _series_of_name_and_inline_tags_example.candidate.tags == [
    "highprotein",
    "easyrecipe",
]

_demonstrative_action_title_over_macros_example = parse_recipe_text(
    "These Cinnamon Protein Bites taste like dessert.\n\n"
    "Macros (per bite, makes 10): 80 calories\n\nIngredients:\n1 cup yogurt"
)
assert _demonstrative_action_title_over_macros_example.candidate is not None
assert _demonstrative_action_title_over_macros_example.candidate.name == (
    "Cinnamon Protein Bites"
)

_emoji_title_boundary_and_unquantified_ingredient_example = parse_recipe_text(
    "High-Protein Vegetable Rounds 🥒If you need a bread alternative, try these.\n\n"
    "Ingredients:\nMakes 4 rounds\n\n1 cup zucchini\n2 eggs\n"
    "Salt and black pepper, to taste\n\n1️⃣ Bake until golden."
)
assert _emoji_title_boundary_and_unquantified_ingredient_example.candidate is not None
assert _emoji_title_boundary_and_unquantified_ingredient_example.candidate.name == (
    "High-Protein Vegetable Rounds"
)
assert (
    _emoji_title_boundary_and_unquantified_ingredient_example.candidate.raw_ingredients
    == ["1 cup zucchini", "2 eggs", "Salt and black pepper, to taste"]
)
