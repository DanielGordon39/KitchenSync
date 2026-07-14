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
- `app.recipes.save_imported_recipe(...)` now implements the accepted recipe save boundary and keeps Markdown and SQLite indexing together.
- Browser-first UI architecture is documented in `docs/ui-architecture.md`.
- The KitchenSync-specific TypeScript learning path is documented in `docs/typescript-ui-tutorial.md`.
- The iterative navigation, screen, flow, and component plan is documented under `docs/ui-plan/`.

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
- For v1, assume parsed imported recipe ingredients are good enough to auto-create or reuse canonical ingredient entries.
- Keep raw recipe ingredient text and parsed fields in the recipe index so ingredient cleanup is possible after importing a starter corpus.
- Index recipe author, imported-from marker, time-estimate minutes, and tags in SQLite.
- Keep recipe descriptions Markdown-first for now; use descriptions as possible input for generated tag suggestions later.
- Use one local SQLite file at `data/library/kitchensync.sqlite` for v1.
- Keep recipe, ingredient, cookbook, pantry, shopping, and candidate data as separate logical database areas inside that SQLite file.
- Use `data/library/cookbook/{recipe_slug}.md` as the durable source for cookbook entry metadata.
- Treat cookbook membership and cookbook-specific recipe metadata as rebuildable from cookbook entry Markdown.
- Treat pantry inventory, shopping lists, and candidate review state as durable app state.
- Keep recipe existence separate from cookbook membership, even though v1 starts with one app-wide cookbook.
- Route accepted parsed recipe saves through one public API boundary, `app.recipes.save_imported_recipe(...)`, so Markdown writes and SQLite indexing happen from the same accepted recipe object.
- Defer ingredient-candidate-first imports to v2, after roughly 30-50 saved recipes reveal practical merge and alias patterns.

Remaining:
- Expose `app.recipes.save_imported_recipe(...)` through a thin browser-facing HTTP endpoint without duplicating its behavior.
- Implement simple ingredient cleanup helpers after the starter corpus exists, likely merge and rename first.
- Define the v2 review workflow for matching, approving, aliasing, rejecting, and ignoring ingredient candidates.

Likely first pass:
- Save recipe markdown as the durable artifact.
- Save canonical ingredient markdown as durable app knowledge by auto-creating minimal ingredient records from parsed recipe ingredients.
- Save cookbook entry markdown as durable cookbook-specific recipe metadata.
- Use SQLite for searchable recipe metadata, ingredient lookup, matching, cookbook state, pantry state, shopping lists, and app workflow state.
- Treat recipe, ingredient, and cookbook indexes as rebuildable until a feature truly needs durable database-only state.
- Keep candidate review state as durable database state when a workflow explicitly creates candidates.

## Ingredient Parsing Follow-Ups

TODO:
- Add more preparation/cut-form examples: `strips`, `cubes`, `diced`, `minced`, `chopped`, `sliced`, `shredded`.
- Normalize unit display separately from raw source text.
- Decide whether ingredient names should preserve source casing or use canonical casing.
- Keep raw ingredient lines available for manual correction.
- Decide if durable parsed ingredient overrides are needed after v1.
- After importing roughly 30-50 recipes, review ingredient duplicates and decide which candidate-first rules belong in v2.
- Revisit package/container handling when shopping-list generation starts.
- Explore automatic ingredient category suggestions for newly created canonical ingredients, with review before treating categories as trusted app knowledge.

## UI Follow-Ups

The save contract is clear. The next prerequisite for real browser data is a thin HTTP API over `KitchenSyncApp`.

Recommended starting direction:
- Use a browser-first React and TypeScript UI built with Vite.
- Keep the UI responsive for desktop and mobile browsers.
- Keep Python business and persistence behavior behind an HTTP/JSON boundary.
- Build the Cookbook and recipe create/edit slice first, then Ingredients, then Shopping generated from cookbook recipes.
- Reuse the static web UI later through Tauri for desktop and evaluate Capacitor for Android/iOS.
- Defer PWA service-worker behavior, Tauri packaging, and Capacitor projects until the browser workflow is stable.
- No UI scaffold or browser-facing Python HTTP API exists yet.

TODO:
- Define and implement the thin HTTP API that delegates to `KitchenSyncApp`.
- Create a parsed recipe review screen.
- Show raw ingredient text beside parser-derived fields.
- Let the user edit accepted ingredient text before saving.
- Add a manual recipe editor for parser failures.
- Add a clear flow from URL input -> parse -> review -> save.
- Add an ingredient cleanup/review mode for merging, renaming, aliasing, and enriching ingredients after the starter corpus exists.

## Open Design Questions

TODO:
- Should recipe markdown be edited directly, generated from forms, or both?
- How should ingredient catalog corrections feed future parsing and matching?
- Which imported ingredient observations should become v2 candidates instead of auto-created canonical ingredients?
- How should mobile browsers and future mobile apps reach a user's local-first KitchenSync data?
- When does offline behavior justify adding a PWA service worker rather than only a web app manifest?
- When should Obsidian planning notes be updated to match the parsing and persistence direction?
