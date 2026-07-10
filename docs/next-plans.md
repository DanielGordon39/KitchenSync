# KitchenSync Next Plans

Working direction after the initial recipe parsing scaffold.

## Current State

- `parse_recipe(...)` can route webpage links through `recipe-scrapers`.
- Web parsing now creates structured `RecipeIngredient` objects from raw ingredient lines.
- Scratch probes can show readable recipe markdown without debug parsed ingredient tables.
- Recipe markdown should remain the portable source of truth.
- Any database should start as an index/cache/app-state layer unless we intentionally decide otherwise.
- Recipe Markdown Schema v1 is documented in `docs/recipe-markdown-schema.md`.
- Ingredient Markdown Schema v1 is documented in `docs/ingredient-markdown-schema.md`.
- Model data flow is documented in `docs/model-data-flow.md`.

## Persistence Decisions

Before building UI, define what happens when a parsed recipe is accepted and saved.

Decided:
- Use `data/library/` as the local v1 development library root.
- Use `recipes/{slug}.md` as the v1 recipe markdown location.
- Use stable `recipe_id` as identity, with `slug` as filename and source URL as import metadata.
- Preserve compact raw import fields in recipe frontmatter and large raw artifacts as sidecar files.
- Treat recipe metadata, recipe ingredient rows, recipe steps, and recipe search tables as rebuildable from Markdown.
- Use ingredient Markdown files as the source of truth for canonical ingredients.
- Treat ingredient aliases, packaging, conversions, categories, and storage rules as rebuildable from ingredient Markdown.
- Send new or uncertain ingredient observations to an ingredient candidate queue instead of auto-promoting them into canonical ingredients.

Remaining:
- Decide the exact database implementation. SQLite remains the likely first local database.
- Define the review workflow for matching, approving, aliasing, rejecting, and ignoring ingredient candidates.
- Decide whether ingredient candidates start database-only or become file-backed under `ingredients/_candidates/`.

Likely first pass:
- Save recipe markdown as the durable artifact.
- Save canonical ingredient markdown as durable app knowledge.
- Use SQLite for searchable recipe metadata, ingredient lookup, matching, and app workflow state.
- Treat recipe and ingredient indexes as rebuildable until a feature truly needs durable database-only state.
- Keep ingredient candidate review state as durable app state until reviewed.

## Ingredient Parsing Follow-Ups

TODO:
- Add more preparation/cut-form examples: `strips`, `cubes`, `diced`, `minced`, `chopped`, `sliced`, `shredded`.
- Normalize unit display separately from raw source text.
- Decide whether ingredient names should preserve source casing or use canonical casing.
- Keep raw ingredient lines available for manual correction.
- Decide if durable parsed ingredient overrides are needed after v1.
- Create ingredient candidates for unmatched or uncertain parsed ingredient lines.
- Revisit package/container handling when shopping-list generation starts.

## UI Follow-Ups

Build UI after the save contract is clear.

TODO:
- Create a parsed recipe review screen.
- Show raw ingredient text beside parser-derived fields.
- Let the user edit accepted ingredient text before saving.
- Add a manual recipe editor for parser failures.
- Add a clear flow from URL input -> parse -> review -> save.
- Add an ingredient review mode for matching, approving, aliasing, rejecting, and enriching candidate ingredients.

## Open Design Questions

TODO:
- Should the first UI be desktop/local only, web app, or both?
- Should recipe markdown be edited directly, generated from forms, or both?
- How should ingredient catalog corrections feed future parsing and matching?
- When should Obsidian planning notes be updated to match the parsing and persistence direction?
