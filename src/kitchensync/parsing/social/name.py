"""Recipe-name extraction and cleanup heuristics."""

import re
import unicodedata

from .models import LineAnalysis, RecipeFieldCandidate
from .patterns import BULLET_ITEM, PROMOTIONAL_TEXT, SAVE_RECIPE_NAME


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
                and name.casefold()
                not in {
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
