# Scripts

Repeatable KitchenSync maintenance and import entrypoints.

## Website Recipe Import

`import_recipe_urls.py` reads newline-separated recipe webpage URLs, parses them through the public KitchenSync parsing API, optionally saves accepted recipes through `app.recipes.save_imported_recipe(...)`, and writes CSV, JSONL, and Markdown reports.

From the repository root:

```powershell
uv run python scripts/import_recipe_urls.py --dry-run
uv run python scripts/import_recipe_urls.py
```

The default input corpus is `scripts/recipe_urls.txt`. Generated reports are written under `data/imports/web_recipe_reports/` and are gitignored.

Keep scripts thin: reusable parsing, persistence, and application behavior belongs under `src/kitchensync/`.
