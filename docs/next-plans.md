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
- Database v1 is documented in `docs/database-v1.md`.
- Intended Python API v1 is documented in `docs/intended-api.md`.

## Persistence Decisions

Before building UI, define what happens when a parsed recipe is accepted and saved.

Decided:
- Use `data/library/` as the local v1 development library root.
- Use `recipes/{slug}.md` as the v1 recipe markdown location.
- Keep recipe Markdown human-first without required technical frontmatter.
- Derive database identity during indexing, with `slug` from the filename and source URL as import metadata.
- Preserve compact import fields as readable recipe fact bullets and large raw artifacts as sidecar files.
- Treat recipe metadata, recipe ingredient rows, recipe steps, and recipe search tables as rebuildable from Markdown.
- Use ingredient Markdown files as the source of truth for canonical ingredients.
- Treat ingredient aliases, packaging, conversions, categories, and storage rules as rebuildable from ingredient Markdown.
- Send new or uncertain ingredient observations to an ingredient candidate queue instead of auto-promoting them into canonical ingredients.
- Use one local SQLite file at `data/library/kitchensync.sqlite` for v1.
- Keep recipe, ingredient, cookbook, pantry, shopping, and candidate data as separate logical database areas inside that SQLite file.
- Use `data/library/cookbook/{recipe_slug}.md` as the durable source for cookbook entry metadata.
- Treat cookbook membership and cookbook-specific recipe metadata as rebuildable from cookbook entry Markdown.
- Treat pantry inventory, shopping lists, and candidate review state as durable app state.
- Keep recipe existence separate from cookbook membership, even though v1 starts with one app-wide cookbook.

Remaining:
- Define the review workflow for matching, approving, aliasing, rejecting, and ignoring ingredient candidates.

Likely first pass:
- Save recipe markdown as the durable artifact.
- Save canonical ingredient markdown as durable app knowledge.
- Save cookbook entry markdown as durable cookbook-specific recipe metadata.
- Use SQLite for searchable recipe metadata, ingredient lookup, matching, cookbook state, pantry state, shopping lists, and app workflow state.
- Treat recipe, ingredient, and cookbook indexes as rebuildable until a feature truly needs durable database-only state.
- Keep candidate review state as durable database state until reviewed.

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
