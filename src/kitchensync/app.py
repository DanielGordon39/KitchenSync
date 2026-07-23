"""Application facade and lifecycle for one local KitchenSync library."""

from __future__ import annotations

import sqlite3
from pathlib import Path

from .cookbook_api import CookbookAPI
from .database import SCHEMA_SQL, connect, migrate_schema
from .ingredient_api import IngredientsAPI
from .recipe_api import RecipesAPI


DEFAULT_DATABASE_PATH = Path("data/library/kitchensync.sqlite")


class KitchenSyncApp:
    """Expose product namespaces over one configured SQLite connection."""

    def __init__(self, connection: sqlite3.Connection, database_path: Path):
        self.connection = connection
        self.database_path = database_path
        self.library_root = database_path.parent
        self.recipes = RecipesAPI(connection, self.library_root)
        self.ingredients = IngredientsAPI(connection)
        self.cookbook = CookbookAPI(connection, self.library_root)

    @classmethod
    def open(cls, database_path: str | Path = DEFAULT_DATABASE_PATH) -> KitchenSyncApp:
        """Open a library database and initialize its current schema."""

        database_path = Path(database_path)
        connection = connect(database_path)
        connection.executescript(SCHEMA_SQL)
        migrate_schema(connection)
        connection.commit()
        return cls(connection, database_path)

    def close(self) -> None:
        self.connection.close()

    def __enter__(self) -> KitchenSyncApp:
        return self

    def __exit__(self, *exc_info: object) -> None:
        self.close()
