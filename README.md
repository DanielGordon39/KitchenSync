# KitchenSync

KitchenSync is a local-first recipe application with a Python/FastAPI backend, a React/TypeScript UI, human-readable Markdown storage, and a rebuildable SQLite index.

Start with:

- [Architecture guide](docs/architecture-guide.md)
- [Codebase review](docs/codebase-review.md)
- [Intended Python API](docs/intended-api.md)
- [UI architecture](docs/ui-architecture.md)
- [Database v1](docs/database-v1.md)

The current backend entry point is `kitchensync.web:app`. Repeatable website imports use `scripts/import_recipe_urls.py`.
