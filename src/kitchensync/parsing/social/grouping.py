"""Context grouping and Recipe-field association for line evidence."""

import re

from .analysis import _is_good_ingredient_parse, _parse_ingredient
from .models import LineAnalysis, RecipeFieldCandidate
from .patterns import (
    BULLET_ITEM,
    IMPERATIVE_START,
    RECIPE_WORD,
    SERVINGS_CUE,
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
                (
                    match.group("content").strip()
                    if (match := BULLET_ITEM.match(line.text))
                    else line.text
                )
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
