from __future__ import annotations

import sqlite3
from typing import Any

from .database import rows


class IngredientsAPI:
    def __init__(self, connection: sqlite3.Connection):
        self.connection = connection

    def list(self) -> list[dict[str, Any]]:
        ingredient_rows = self.connection.execute(
            """
            SELECT
                ingredient_id,
                name,
                slug,
                parent_ingredient_id,
                category,
                storage_area,
                default_unit
            FROM ingredient_ingredients
            ORDER BY lower(name)
            """
        ).fetchall()
        ingredients = rows(ingredient_rows)
        aliases_by_ingredient: dict[str, list[str]] = {}
        alias_rows = self.connection.execute(
            """
            SELECT ingredient_id, alias
            FROM ingredient_aliases
            ORDER BY lower(alias)
            """
        ).fetchall()
        for alias_row in alias_rows:
            aliases_by_ingredient.setdefault(alias_row["ingredient_id"], []).append(
                alias_row["alias"]
            )

        for ingredient in ingredients:
            ingredient["aliases"] = aliases_by_ingredient.get(
                ingredient["ingredient_id"], []
            )
        return ingredients
