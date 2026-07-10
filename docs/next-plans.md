# KitchenSync Next Plans

Working direction after the initial recipe parsing scaffold.

## Current State

- `parse_recipe(...)` can route webpage links through `recipe-scrapers`.
- Web parsing now creates structured `RecipeIngredient` objects from raw ingredient lines.
- Scratch probes can show both readable markdown and parsed ingredient fields.
- Recipe markdown should remain the portable source of truth.
- Any database should start as an index/cache/app-state layer unless we intentionally decide otherwise.

## Next Decision: Persistence

Before building UI, define what happens when a parsed recipe is accepted and saved.

TODO:
- Decide where recipe markdown files live.
- Decide whether SQLite is the first local database.
- Define which data is source-of-truth markdown vs rebuildable database index.
- Define recipe identity: filename slug, database id, source URL, or some combination.
- Define how imported recipes preserve raw source fields for review/debugging.
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
- Revisit package/container handling when shopping-list generation starts.

## UI Follow-Ups

Build UI after the save contract is clear.

TODO:
- Create a parsed recipe review screen.
- Show raw ingredient text beside parsed fields.
- Let the user edit ingredient name, quantity, unit, and preparation before saving.
- Add a manual recipe editor for parser failures.
- Add a clear flow from URL input -> parse -> review -> save.

## Open Design Questions

TODO:
- Should the first UI be desktop/local only, web app, or both?
- Should recipe markdown be edited directly, generated from forms, or both?
- How should ingredient catalog corrections feed future parsing?
- When should Obsidian planning notes be updated to match the parsing and persistence direction?
