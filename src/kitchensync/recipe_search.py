"""In-memory filtering and relevance ranking for the local recipe catalog."""

from difflib import SequenceMatcher
import re
import sqlite3
from typing import Any

from .database import row_dict
from .markdown import slugify


MIN_SEARCH_SCORE = 0.45


def search_recipes(
    connection: sqlite3.Connection,
    query: str,
    *,
    exact_tags: list[str] | None = None,
    meal_tags: list[str] | None = None,
    cuisine_tags: list[str] | None = None,
    diet_tags: list[str] | None = None,
    recipe_ids: set[str] | None = None,
) -> list[dict[str, Any]]:
    """Filter and rank indexed recipes for browser search."""

    query = query.strip()
    exact_tag_set = _tag_set(exact_tags)
    meal_tag_set = _tag_set(meal_tags)
    cuisine_tag_set = _tag_set(cuisine_tags)
    diet_tag_set = _tag_set(diet_tags)

    recipe_rows = connection.execute("SELECT * FROM recipe_recipes").fetchall()
    tag_rows = connection.execute(
        "SELECT recipe_id, tag_slug FROM recipe_tags ORDER BY tag_order"
    ).fetchall()
    ingredient_rows = connection.execute(
        """
        SELECT recipe_id, parsed_name, raw_text
        FROM recipe_ingredients
        ORDER BY ingredient_order
        """
    ).fetchall()

    tags_by_recipe: dict[str, list[str]] = {}
    for row in tag_rows:
        tags_by_recipe.setdefault(row["recipe_id"], []).append(row["tag_slug"])

    ingredients_by_recipe: dict[str, list[str]] = {}
    for row in ingredient_rows:
        values = ingredients_by_recipe.setdefault(row["recipe_id"], [])
        if row["parsed_name"]:
            values.append(row["parsed_name"])
        values.append(row["raw_text"])

    ranked: list[tuple[int, int, float, str, str, dict[str, Any]]] = []
    for row in recipe_rows:
        recipe = row_dict(row)
        if recipe is None:
            continue

        recipe_id = recipe["recipe_id"]
        if recipe_ids is not None and recipe_id not in recipe_ids:
            continue
        tags = tags_by_recipe.get(recipe_id, [])
        tag_set = set(tags)

        if meal_tag_set and not tag_set.intersection(meal_tag_set):
            continue
        if cuisine_tag_set and not tag_set.intersection(cuisine_tag_set):
            continue
        if diet_tag_set and not diet_tag_set.issubset(tag_set):
            continue

        matched_tag_count = len(tag_set.intersection(exact_tag_set))
        tag_match: str | None = None
        tag_group = 0
        if exact_tag_set:
            if matched_tag_count == 0:
                continue
            tag_match = "all" if matched_tag_count == len(exact_tag_set) else "some"
            tag_group = 0 if tag_match == "all" else 1

        relevance = _recipe_search_score(
            query,
            recipe,
            tags,
            ingredients_by_recipe.get(recipe_id, []),
        )
        if query and relevance < MIN_SEARCH_SCORE:
            continue

        recipe["tags"] = tags
        recipe["tag_match"] = tag_match
        ranked.append(
            (
                tag_group,
                -matched_tag_count,
                -relevance,
                recipe["title"].casefold(),
                recipe_id,
                recipe,
            )
        )

    # ponytail: score the local catalog in memory; add FTS/paging when its
    # size makes this measurably slow.
    ranked.sort(key=lambda item: item[:-1])
    return [item[-1] for item in ranked]


def list_recipe_tags(
    connection: sqlite3.Connection,
    recipe_ids: set[str] | None = None,
) -> list[dict[str, Any]]:
    """Return normalized tag counts for a catalog or Cookbook scope."""

    tag_rows = connection.execute(
        """
        SELECT recipe_id, tag_slug
        FROM recipe_tags
        ORDER BY tag_slug, recipe_id
        """
    ).fetchall()
    counts: dict[str, int] = {}
    for row in tag_rows:
        if recipe_ids is not None and row["recipe_id"] not in recipe_ids:
            continue
        counts[row["tag_slug"]] = counts.get(row["tag_slug"], 0) + 1
    return [
        {"tag_slug": tag_slug, "recipe_count": count}
        for tag_slug, count in sorted(counts.items())
    ]


def _tag_set(values: list[str] | None) -> set[str]:
    return {
        slugify(value.lstrip("#"))
        for value in values or []
        if value.strip().lstrip("#")
    }


def _search_text(value: str | None) -> str:
    return re.sub(r"[^a-z0-9]+", " ", (value or "").casefold()).strip()


def _fuzzy_score(query: str, candidate: str | None) -> float:
    normalized_query = _search_text(query)
    normalized_candidate = _search_text(candidate)
    if not normalized_query or not normalized_candidate:
        return 0.0
    if normalized_query == normalized_candidate:
        return 1.0
    if normalized_candidate.startswith(normalized_query):
        return 0.98
    if normalized_query in normalized_candidate:
        return 0.95

    score = SequenceMatcher(None, normalized_query, normalized_candidate).ratio()
    if " " not in normalized_query:
        score = max(
            score,
            *(
                SequenceMatcher(None, normalized_query, token).ratio()
                for token in normalized_candidate.split()
            ),
        )
    return score


def _best_fuzzy_score(query: str, values: list[str | None]) -> float:
    return max((_fuzzy_score(query, value) for value in values), default=0.0)


def _recipe_search_score(
    query: str,
    recipe: dict[str, Any],
    tags: list[str],
    ingredients: list[str],
) -> float:
    if not query:
        return 0.0

    title_score = _fuzzy_score(query, recipe["title"])
    tag_score = _best_fuzzy_score(query, tags) * 0.82
    ingredient_score = _best_fuzzy_score(query, ingredients) * 0.68
    metadata_score = _best_fuzzy_score(
        query,
        [
            recipe.get("slug"),
            recipe.get("source_name"),
            recipe.get("source_url"),
            recipe.get("author"),
            recipe.get("imported_from"),
        ],
    ) * 0.5
    return max(title_score, tag_score, ingredient_score, metadata_score)
