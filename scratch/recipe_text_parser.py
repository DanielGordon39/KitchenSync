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

from ingredient_parser import parse_ingredient
from pydantic import BaseModel, Field


NUMBERED_INSTRUCTION = re.compile(r"^\d+[.)]\s+")
RECIPE_WORD = re.compile(r"\brecipe\b", re.IGNORECASE)
NUTRITION_HEADING = re.compile(
    r"^(?:macros?|nutrition(?:\s+(?:facts|info|information))?)"
    r"(?:\s+per\s+[^:]+)?\s*:?$",
    re.IGNORECASE,
)
NUTRITION_VALUE = re.compile(
    r"^(protein|carb(?:ohydrate)?s?|fat|calories?|fiber|fibre|sugar|sodium)"
    r"\s*:?\s*\d",
    re.IGNORECASE,
)
BULLET_ITEM = re.compile(r"^(?P<marker>[-*•])\s*(?P<content>.*)$")
IMPERATIVE_START = re.compile(
    r"^(?:add|bake|blend|boil|brown|chop|combine|cook|fold|heat|mix|pour|"
    r"preheat|roast|season|serve|simmer|slice|stir|top|whisk)\b",
    re.IGNORECASE,
)
INSTRUCTION_HEADINGS = ("directions", "how to", "instructions", "method", "steps")
SERVINGS_CUE = re.compile(
    r"\b(?:makes?|serves?)\s+\d+\b|\b\d+\s+servings?\b",
    re.IGNORECASE,
)
SERVINGS_VALUE = re.compile(
    r"\b(?:makes?|serves?)\s+(?P<first>\d+)\b|"
    r"\b(?P<second>\d+)\s+servings?\b",
    re.IGNORECASE,
)
SAVE_RECIPE_NAME = re.compile(
    r"\bsave\s+this\s+(?P<name>.+?)\s+recipe\b",
    re.IGNORECASE,
)
HASHTAG = re.compile(r"#(?P<tag>[\w-]+)")
PROMOTIONAL_TEXT = re.compile(
    r"\b(?:comment|follow|like\s*&\s*share|link(?:ed)?\s+in\s+(?:my\s+)?bio|"
    r"save\s+this|do\s+not\s+authorize|creator|"
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
    is_nutrition_value = bool(NUTRITION_VALUE.match(text))
    mentions_nutrition = "nutrition" in folded or "macro" in folded
    is_heading = is_nutrition_heading or text.endswith(":") or (
        len(text) <= 40
        and bool(RECIPE_WORD.search(text))
        and not text.endswith((".", "!", "?"))
    )
    is_instruction = bool(NUMBERED_INSTRUCTION.match(text))

    if is_heading:
        evidence["heading"] = 1.0
    elif mentions_nutrition:
        evidence["heading"] = 0.2
    if "ingredient" in folded and is_heading:
        evidence["ingredient"] = 1.0
    if is_instruction or (
        is_heading and any(heading in folded for heading in INSTRUCTION_HEADINGS)
    ):
        evidence["instruction"] = 1.0
    if is_nutrition_heading or is_nutrition_value:
        evidence["nutrition"] = 1.0
    elif mentions_nutrition:
        evidence["nutrition"] = 0.2
        evidence["narrative"] = 1.0
    if text.startswith("#"):
        evidence["tag"] = 1.0

    ingredient_text = bullet_content if bullet_content is not None else text
    semantic_evidence = {"divider", "heading", "instruction", "nutrition", "tag"}
    if not semantic_evidence.intersection(evidence):
        parsed_ingredient = _parse_ingredient(ingredient_text)
        if bullet_match:
            if _is_good_ingredient_parse(parsed_ingredient, ingredient_text):
                evidence["ingredient"] = 0.8
                evidence["instruction"] = 0.2
            else:
                evidence["ingredient"] = 0.2
                evidence["instruction"] = 0.8
        elif parsed_ingredient is not None and parsed_ingredient.amount:
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
    if IMPERATIVE_START.match(text) and text.rstrip().endswith((".", "!", "?")):
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
    if block[0].evidence.get("heading", 0.0) < 0.8 or len(block) < 3:
        return False
    if any(
        block[0].evidence.get(concept, 0.0)
        for concept in ("ingredient", "instruction", "nutrition", "tag")
    ):
        return False

    body = block[1:]
    ingredient_like = sum(
        len(line.text) <= 80
        and _is_good_ingredient_parse(_parse_ingredient(line.text), line.text)
        for line in body
    )
    return ingredient_like / len(body) >= 0.6


def _dominant_field(candidate: RecipeFieldCandidate) -> str:
    return max(candidate.field_scores, key=candidate.field_scores.get)


def build_social_recipe_candidate(
    line_analyses: list[LineAnalysis],
    field_candidates: list[RecipeFieldCandidate],
) -> SocialRecipeCandidate:
    """Build review-only recipe content from contextual field candidates."""
    return SocialRecipeCandidate(
        name=_recipe_name(line_analyses),
        description=_recipe_description(line_analyses, field_candidates),
        servings=_recipe_servings(line_analyses),
        raw_ingredients=_field_content(
            line_analyses,
            field_candidates,
            field="ingredients",
        ),
        steps=_field_content(line_analyses, field_candidates, field="steps"),
        tags=_recipe_tags(field_candidates),
        notes=_recipe_notes(line_analyses, field_candidates),
    )


def _recipe_name(line_analyses: list[LineAnalysis]) -> str | None:
    for line in line_analyses:
        match = SAVE_RECIPE_NAME.search(line.text)
        if match:
            return _clean_recipe_name(match.group("name"))

    first_content = next((line.text for line in line_analyses if line.text), None)
    if first_content is None:
        return None
    name = _clean_recipe_name(first_content)
    if name.casefold() in {
        "directions",
        "full",
        "full recipe",
        "ingredient",
        "ingredients",
        "instructions",
        "method",
        "recipe",
        "steps",
    }:
        return None
    return name or None


def _clean_recipe_name(text: str) -> str:
    text = re.sub(r"\s+recipe\b.*$", "", text.strip(), flags=re.IGNORECASE)
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
    for line in line_analyses:
        match = SERVINGS_VALUE.search(line.text)
        if match:
            return int(match.group("first") or match.group("second"))
    return None


def _field_content(
    line_analyses: list[LineAnalysis],
    field_candidates: list[RecipeFieldCandidate],
    *,
    field: str,
) -> list[str]:
    line_numbers = {
        line_number
        for candidate in field_candidates
        if candidate.field_scores.get(field, 0.0) >= 0.5
        for line_number in candidate.line_numbers
    }
    values = []
    for line in line_analyses:
        if line.line_number not in line_numbers:
            continue
        if line.evidence.get("heading", 0.0) >= 0.8:
            continue
        text = line.text
        bullet_match = BULLET_ITEM.match(text)
        if bullet_match:
            text = bullet_match.group("content").strip()
        if field == "steps":
            text = NUMBERED_INSTRUCTION.sub("", text).strip()
        if text:
            values.append(text)
    return values


def _recipe_tags(field_candidates: list[RecipeFieldCandidate]) -> list[str]:
    tags = []
    for candidate in field_candidates:
        if candidate.field_scores.get("tags", 0.0) < 0.5:
            continue
        for line in candidate.lines:
            for match in HASHTAG.finditer(line):
                tag = match.group("tag").casefold()
                if tag not in tags:
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
    "ingredient": 0.2,
    "instruction": 0.8,
}
assert analyze_line(1, "•Add pasta cooking water, cream and stir.").evidence == {
    "ingredient": 0.2,
    "instruction": 0.8,
}
assert analyze_line(1, "-").evidence == {"divider": 1.0}
assert analyze_line(1, "Macros per serving:").evidence == {
    "heading": 1.0,
    "nutrition": 1.0,
}
assert analyze_line(1, "Protein: 46g").evidence == {"nutrition": 1.0}
assert analyze_line(1, "See the printable recipe for nutrition info.").evidence == {
    "heading": 0.2,
    "nutrition": 0.2,
    "narrative": 1.0,
}
assert analyze_line(1, "#dinner easyrecipe").evidence == {"tag": 1.0}

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

_preview_example = parse_recipe_text(
    "Creamy Rice Recipe\n\nIngredients:\n-1 cup rice\n\n"
    "Instructions:\n1. Cook the rice.\n\n#dinner"
)
assert _preview_example.candidate is not None
assert _preview_example.candidate.name == "Creamy Rice"
assert _preview_example.fallback_recommended is False
