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
        return rows(ingredient_rows)
