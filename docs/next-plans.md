# KitchenSync Next Plans

Working direction after the initial recipe parsing scaffold.

## Current State

- `parse_recipe(...)` can route webpage links through `recipe-scrapers`.
- Web parsing now creates structured `RecipeIngredient` objects from raw ingredient lines.
- Scratch probes can show readable recipe markdown without debug parsed ingredient tables.
- Recipe markdown should remain the portable source of truth.
- Any database should start as an index/cache/app-state layer unless we intentionally decide otherwise.
- Recipe Markdown Schema v1 is documented in `docs/recipe-markdown-schema.md`.

## Next Decision: Persistence

Before building UI, define what happens when a parsed recipe is accepted and saved.

TODO:
- Use `recipes/{slug}.md` as the v1 recipe markdown location.
- Decide whether SQLite is the first local database.
- Define which data is source-of-truth markdown vs rebuildable database index.
- Use stable `recipe_id` as identity, with `slug` as filename and source URL as import metadata.
- Preserve compact raw import fields in recipe frontmatter and large raw artifacts as sidecar files.
- Decide whether the ingredient catalog is global app data or emerges from saved recipes first.

Likely first pass:
- Save recipe markdown as the durable artifact.
- Use SQLite for searchable recipe metadata, ingredient lookup, and app state.
- Treat the database as rebuildable until a feature truly needs durable database-only state.

## Ingredient Parsing Follow-Ups

TODO:
- Add more preparation/cut-form examples: `strips`, `cubes`, `diced`, `minced`, `chopped`, `sliced`, `shredded`.
- Normalize unit display separately from raw source text.
- Decide whether ingredient names should preserve source casing or use canonical casing.
- Keep raw ingredient lines available for manual correction.
- Decide if durable parsed ingredient overrides are needed after v1.
- Revisit package/container handling when shopping-list generation starts.

## UI Follow-Ups

Build UI after the save contract is clear.

TODO:
- Create a parsed recipe review screen.
- Show raw ingredient text beside parser-derived fields.
- Let the user edit accepted ingredient text before saving.
- Add a manual recipe editor for parser failures.
- Add a clear flow from URL input -> parse -> review -> save.

## Open Design Questions

TODO:
- Should the first UI be desktop/local only, web app, or both?
- Should recipe markdown be edited directly, generated from forms, or both?
- How should ingredient catalog corrections feed future parsing?
- When should Obsidian planning notes be updated to match the parsing and persistence direction?
