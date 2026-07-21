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
- The browser UI now loads recipe cards from `GET /api/recipes`.
- `GET /api/recipes/{recipe_id}` and the full-screen Main Recipe View popup provide the recipe detail slice; existing recipes can now be edited through `PUT /api/recipes/{recipe_id}`.
- Web imports now capture the primary recipe image URI, and accepted saves download the main image into the recipe folder for card/detail display.

## Near-Term Feature Priorities

### 1. Recipe Search and Filters

The recipe grid now has a search bar and compact filter menu. Search covers the complete indexed recipe library, not only cards currently visible in the browser.

Rank text matches in this order:
1. **Recipe title:** fuzzy matching with the strongest ranking weight.
2. **Tags:** fuzzy matching during normal text search.
3. **Ingredients:** fuzzy matching over canonical ingredient names, parsed names, and raw recipe ingredient text.

Search behavior:
- A strong title match should normally outrank tag or ingredient-only matches.
- Typing `#` starts autocomplete from normalized tags that exist in the indexed recipe library.
- A completed hashtag is an exact tag request. With multiple hashtags, recipes matching every tag are shown first, followed by recipes matching some tags ranked by the number matched.
- An incomplete trailing hashtag drives autocomplete but does not constrain results until it is completed or selected.
- Use a stable tie-breaker after relevance so results do not jump between requests.
- Search and infinite loading must share one backend result set with paging or a cursor.
- Keep expanding the expected-match corpus with real typos and ambiguous terms before replacing the current standard-library scorer with full-text search or another fuzzy-search implementation.

The filter menu exposes common indexed tags as explicit constraints:
- Meal and cuisine selections use OR within their section.
- Different filter sections combine with AND.
- Diet selections all apply as required constraints.
- Filters should continue to work when the text query is empty.
- Cookbook-only state such as favorites and ratings does not affect recipe text relevance. Cookbook displays that state now; using it as an explicit filter remains later work.
- TODO(accounts): scope recipe results, tag suggestions, and filter counts to recipes visible to the authenticated account without changing the browser request shape.

### 2. Imported Recipe Main Image

Current v1 behavior:

- Extract the main image URI exposed by `recipe-scrapers` when available.
- Map it into the existing `RecipeMetadata.images` / `ImageRef` model during parse.
- Download the main image only when an accepted recipe is saved through `app.recipes.save_imported_recipe(...)`.
- Store recipes as folders: `recipes/{slug}/recipe.md` plus assets such as `recipes/{slug}/images/main.jpg`.
- Index `main_image_path` in SQLite and expose it to the browser as a local `/library/...` URL.
- Show a stable fallback when a source has no usable image or the image download fails.

Remaining:

- Preserve enough source information to distinguish the main recipe image from future step images.
- Decide how imports should handle duplicates and very large files.
- For social imports, initially use the platform thumbnail or first post image as the main-image candidate.
- Add a review-time frame selector that can scrub downloaded video, record a chosen timestamp as import evidence, and extract exactly one frame into the existing `recipes/{slug}/images/main.{ext}` location.
- Keep generated frame previews and downloaded review media temporary; do not add every candidate frame to the durable `Recipe` model.
- Add step images only after real sources expose reliable step-level media.

### 3. Social-Media Recipe Import Research Spike

Treat social-media recipe import as a key KitchenSync feature. Research YouTube Shorts, Instagram, TikTok, and Facebook separately before committing to a shared implementation because their public metadata, caption, transcript, authentication, and rate-limit boundaries may differ.

Target pipeline:

```text
Social media URL
  -> platform adapter
  -> source description/caption + source metadata
  -> existing captions or audio/video transcript
  -> normalized import document
  -> recipe extraction
  -> explicit review
  -> accepted Recipe save boundary
```

The research spike should evaluate:

- Official platform APIs, permissions, and permitted public-post access
- Maintained libraries or tools for post metadata, descriptions, captions, media, and transcripts
- Authentication/session requirements, rate limits, and likely reliability
- Existing caption retrieval versus local or hosted speech-to-text
- Privacy, storage, cost, and failure behavior for downloaded media and transcripts
- A small observed URL corpus for YouTube Shorts, Instagram, TikTok, and Facebook

Expected direction:

- A custom KitchenSync orchestration layer is likely even if maintained libraries handle individual platform or transcription steps.
- Keep platform adapters separate instead of building one large social-media scraper.
- Preserve the source description and transcript as import evidence so extraction can be reviewed or rerun.
- Preserve platform thumbnails, post images, and selected video-frame timestamps as image-candidate evidence until review chooses the durable main image.
- Do not save uncertain social-media extraction directly as canonical recipe content without an explicit review step.
- The first successful boundary is a reviewable recipe candidate or a clear unsupported/failure result, not perfect automatic parsing.

Research deliverable:

- A platform-by-platform capability matrix
- Recommended library/API path and fallback for each platform
- A minimal shared adapter contract
- A transcription recommendation
- Risks that require user authentication, browser automation, or custom extraction
- A proposed YouTube Shorts vertical slice before expanding to the other platforms

## Persistence Decisions

Before building UI, define what happens when a parsed recipe is accepted and saved.

Decided:
- Use `data/library/` as the local v1 development library root.
- Use `recipes/{slug}/recipe.md` as the v1 recipe markdown location.
- Keep recipe-owned assets such as downloaded images under the same `recipes/{slug}/` folder.
- Keep recipe Markdown human-first without required technical frontmatter.
- Derive database identity during indexing, with `slug` from the filename and source URL as import metadata.
- Preserve compact import fields as readable recipe fact bullets and large raw artifacts as sidecar files.
- Treat recipe metadata, recipe ingredient rows, recipe steps, and recipe search tables as rebuildable from Markdown.
- Use ingredient Markdown files as the source of truth for canonical ingredients.
- Treat ingredient aliases, packaging, conversions, categories, and storage rules as rebuildable from ingredient Markdown.
- For v1, assume parsed imported recipe ingredients are good enough to auto-create or reuse canonical ingredient entries.
- Keep raw recipe ingredient text and parsed fields in the recipe index so ingredient cleanup is possible after importing a starter corpus.
- Index recipe author, imported-from marker, time-estimate minutes, and tags in SQLite.
- Index the local main image path in SQLite for recipe card and detail display.
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

The save contract is clear, and the first browser slice now loads the recipe grid and Main Recipe View through thin HTTP endpoints over `KitchenSyncApp`.

The browser now also has Global Recipes and Cookbook tabs over the shared search/filter grid. Cookbook membership adds favorite, rating, and personal notes without copying the recipe. Main Recipe View supports explicit editing of existing recipes through the canonical Markdown plus SQLite update boundary. Ingredient rows provide lossless per-line Raw/Rich editing, catalog autocomplete, and filtered unit suggestions while continuing to save canonical raw lines. V1 assumes one implicit user and allows every recipe to be edited; creator and approved-editor permissions and account-backed editor preferences are deferred to the account-aware version.

Recommended starting direction:
- Use a browser-first React and TypeScript UI built with Vite.
- Use npm as the v1 package manager and keep `package-lock.json` as the single UI lockfile.
- Keep the UI responsive for desktop and mobile browsers.
- Keep Python business and persistence behavior behind an HTTP/JSON boundary.
- Build the Cookbook and recipe create/edit slice first, then Ingredients, then Shopping generated from cookbook recipes.
- Reuse the static web UI later through Tauri for desktop and evaluate Capacitor for Android/iOS.
- Defer PWA service-worker behavior, Tauri packaging, and Capacitor projects until the browser workflow is stable.
- Reconsider a deliberate migration from npm to Bun after the browser workflow is stable and only when it provides a concrete speed or tooling benefit.
- The Vite UI scaffold, scoped recipe-card endpoint, recipe-detail endpoint, full-screen popup, Cookbook metadata controls, and existing-recipe editor now exist.

TODO:
- Add paged or cursor-based recipe summaries for eventual infinite scrolling.
- Expand the thin HTTP API only through product-level methods that delegate to `KitchenSyncApp`.
- Create a parsed recipe review screen.
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
