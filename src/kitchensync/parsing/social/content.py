"""Ingredient and step extraction from contextual social-text evidence."""

import re

from .analysis import (
    _is_good_ingredient_parse,
    _looks_like_inline_ingredient_group,
    _parse_ingredient,
)
from .grouping import (
    _context_blocks,
    _looks_like_bare_ingredient_list,
    _looks_like_ingredient_component,
    _menu_component_lines,
)
from .models import LineAnalysis, RecipeFieldCandidate
from .patterns import (
    BULLET_ITEM,
    IMPERATIVE_START,
    NUMBERED_INSTRUCTION,
    PROMOTIONAL_TEXT,
    TIP_LINE,
)


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
                or line.line_number in contextual_step_lines
                or line.line_number in contextual_metadata_lines
                or any(
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
                                    (
                                        BULLET_ITEM.match(line.text).group("content")
                                        if BULLET_ITEM.match(line.text)
                                        else line.text
                                    ),
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
                or line.line_number in contextual_metadata_lines
                or PROMOTIONAL_TEXT.search(line.text)
                or line.line_number in contextual_ingredient_lines
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
