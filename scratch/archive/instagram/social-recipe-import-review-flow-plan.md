# Social Recipe Import Review Flow Plan

Status: planning handoff only. No production implementation is authorized by this file.

## Goal

Turn a social-recipe URL into an editable recipe draft, let the user review every
field and ingredient decision, and only then save the accepted recipe through
KitchenSync's existing Markdown plus SQLite boundary.

```text
Social recipe URL
  -> acquire public source description and thumbnail metadata
  -> deterministic recipe draft plus warnings
  -> existing recipe editor in import-review mode
  -> user fixes the recipe and resolves ingredient names
  -> explicit Import Recipe action
  -> app.recipes.save_imported_recipe(...)
  -> recipe Markdown, local image, ingredient Markdown, and SQLite indexes
```

The frozen Instagram corpus remains regression evidence. User corrections made
during import review must not rewrite its case JSON files.

## Current Verified State

As of 2026-07-21:

- `scratch/social_recipe_cases/` contains 96 accepted Instagram-description cases.
- The frozen corpus reports 57/57 complete cases and 39/39 correct fallbacks.
- `scratch/social_import_probe.py --promote ... --save` can reparse selected
  complete cases and save them through the real application boundary into an
  ignored disposable library.
- The five-case canary is under
  `scratch/social_import_probe_output/data/library/` and contains five recipe
  Markdown files, five local images, and a disposable SQLite database.
- The canary proved that recipe cards, images, and recipe details render in the
  existing UI.
- `app.recipes.save_imported_recipe(...)` is the only accepted save boundary.
  Preview must not call it.
- `ui/src/features/recipes/RecipeMainView.tsx` already contains the recipe edit
  form for title, description, servings, time, tags, ingredients, steps, and
  notes.
- `ui/src/features/recipes/RecipeIngredientEditor.tsx` already supports:
  - raw and rich ingredient editing;
  - parsing a raw line into quantity, unit, name, and preparation;
  - catalog and alias autocomplete;
  - a `New ingredient` indicator when no exact name or alias matches;
  - adding, removing, and reordering ingredient rows.
- `POST /api/ingredient-lines/parse` and `GET /api/ingredients` already supply
  the ingredient editor's parsing and catalog data.
- At plan-writing time, the worktree contains unrelated/uncommitted UI edits.
  A new implementation chat must inspect and preserve them before editing.

## What the Import Review Screen Should Do

### 1. URL entry and acquisition

- Accept one Instagram post or reel URL.
- Validate the supported Instagram host before acquisition.
- Show a loading state while the backend obtains public description, author,
  source URL, and thumbnail metadata.
- Do not add another social platform in this vertical slice.
- Do not download durable media during preview.
- Return a clear acquisition or unsupported-source error without creating any
  recipe or ingredient records.

### 2. Reviewable recipe draft

Reuse the existing recipe editor instead of creating a second form system.
Populate it with:

- editable title;
- editable description;
- servings and time when available;
- tags;
- editable ingredient rows;
- editable, removable, reorderable steps;
- parser warnings;
- source URL, author, and thumbnail preview;
- an optional collapsed view of the original source description.

The primary actions should be `Cancel` and `Import Recipe`. Nothing is durable
until `Import Recipe` succeeds.

### 3. Ingredient review

Extend the existing ingredient editor only where needed. Each rich ingredient
row should communicate one of these states:

- `Existing ingredient: Butter` when the name or a known alias matches;
- `New ingredient` when no catalog match exists;
- `Raw review needed` when the line is too complex for safe rich editing.

The user must be able to:

- keep the suggested existing ingredient;
- select a different existing ingredient from the current catalog;
- edit the name and intentionally create a new ingredient;
- split a compound source line by editing it and adding rows;
- remove a garnish or non-ingredient line;
- switch uncertain lines back to raw editing.

For the smallest v1, canonicalize a selected alias to the existing ingredient's
canonical name before submitting. This lets the current save boundary reuse the
existing ingredient by slug without introducing candidate tables or a new
ingredient-resolution subsystem.

The original description remains visible as evidence even when the accepted
recipe line is corrected.

### 4. Completeness and warnings

Keep the parser conservative. The review screen may open for both complete and
fallback candidates, but `Import Recipe` should require:

- a nonblank title;
- at least one nonblank ingredient line;
- at least one nonblank instruction step.

Show parser warnings near the affected section. A fallback becomes importable
after the user supplies the missing content; it does not need a separate
workflow.

### 5. Duplicate behavior

Before saving, show whether the source URL or resulting slug matches an existing
recipe. Do not silently overwrite an existing recipe from the review screen.

- New source and slug: label the action `Import Recipe`.
- Existing source or slug: identify the existing recipe and require an explicit
  `Update Existing Recipe` action.

The final write should still delegate to `save_imported_recipe(...)`; duplicate
awareness belongs in preview/review, not in a second persistence path.

### 6. Accepted save

On explicit acceptance:

- construct the final `Recipe` from the edited draft;
- retain source URL, author, Instagram source name, and import method;
- pass the thumbnail as the main-image candidate;
- call `app.recipes.save_imported_recipe(...)` exactly once;
- return the normal recipe-detail response so the UI can show the saved recipe;
- let the existing save boundary download the local image and create/reuse
  ingredient Markdown and SQLite rows.

If image download fails, save the recipe with the existing fallback-image
behavior and show a non-blocking warning.

## Canary Findings the Review Flow Must Handle

Use these frozen cases as manual acceptance examples without changing them:

- Case 014: clean baseline; should be reviewable and importable without edits.
- Case 028: `250g @allthingsdairy__ butter` should be correctable to existing
  `Butter`; `bruised lemongrass` needs a human name/preparation decision.
- Case 044: source typo `lotatoes` should be visibly editable before it creates
  a canonical ingredient.
- Case 075: the compound chicken/oyster/soy line must be splittable; the final
  instruction ending in `fresh lim` must be warned about and editable.
- Case 097: the optional coating line can be split or retained after review.

Also verify that source-style lowercase or uppercase titles can be normalized by
the user before saving.

## Minimal Backend Shape

Names may change to match repository conventions, but keep the boundary small.

### Preview

`POST /api/recipe-imports/preview`

Request:

```json
{
  "source_url": "https://www.instagram.com/..."
}
```

Response should contain only what the review UI needs:

- editable recipe fields using the existing recipe update shape where possible;
- raw source description;
- author, source name, source URL, and thumbnail URI;
- parser warnings and completeness state;
- existing-recipe match information when applicable.

Preview must be read-only with respect to the recipe library.

### Save

`POST /api/recipe-imports`

Accept the edited draft plus source metadata and an explicit duplicate action.
Construct a normal `Recipe`, call `save_imported_recipe(...)`, and return the
saved `RecipeDetailDto`.

Do not add a persistent import-candidate table in this first pass. The draft may
live in React state and be resubmitted on final acceptance. Add durable drafts
only after a real resume-across-sessions requirement appears.

## Parser and Acquisition Promotion

The proven parser and Instagram acquisition currently live under `scratch/`.
Production code must not import scratch modules.

When implementing:

1. Identify the smallest parser surface needed to convert one frozen description
   into a review draft.
2. Promote that stable, creator-independent logic into
   `src/kitchensync/parsing/` while keeping the scratch corpus runner as the
   regression oracle.
3. Keep Instagram acquisition separate from description parsing.
4. Move `yt-dlp` from development-only to runtime dependencies if the FastAPI
   process performs live acquisition.
5. Do not add transcription, video download, job queues, or another platform in
   this slice.

No production rule may depend on a creator, handle, shortcode, URL, exact dish
name, or exact ingredient phrase.

## Reuse Targets

Prefer extending these current surfaces:

- `ui/src/features/recipes/RecipeMainView.tsx`
  - extract or parameterize the existing recipe form only as much as needed for
    both edit and import-review modes;
- `ui/src/features/recipes/RecipeIngredientEditor.tsx`
  - retain raw/rich behavior, catalog autocomplete, new-ingredient detection,
    and row controls;
- `ui/src/lib/api/recipe-types.ts`
  - reuse the recipe-edit field shape inside preview/save DTOs where practical;
- `ui/src/lib/api/recipes.ts`
  - add the two thin import calls;
- `src/kitchensync/web.py`
  - add thin HTTP endpoints that delegate parsing/acquisition and the public save
    boundary;
- `src/kitchensync/parsing/`
  - hold promoted, platform-independent parser behavior and a small Instagram
    acquisition adapter;
- `src/kitchensync/recipe_api.py`
  - reuse existing lookup and save behavior; add only a focused source-URL lookup
    if preview duplicate detection needs it.

Avoid a second recipe editor, a generic workflow engine, a candidate repository,
or duplicate Markdown/database write logic.

## Implementation Phases

### Phase 1: Production parser boundary

- Promote the deterministic description parser behind a small production API.
- Preserve the scratch corpus unchanged and keep its runner green.
- Add focused production tests for one complete and one fallback description.

Gate:

- The promoted parser matches the same fields for the selected frozen examples.
- No creator-specific rules enter production code.

### Phase 2: Read-only preview endpoint

- Add Instagram URL validation and acquisition.
- Return the recipe draft, source evidence, thumbnail, warnings, and duplicate
  information.
- Mock acquisition in tests; do not make live Instagram calls in pytest.

Gate:

- Preview creates no database rows, Markdown, ingredient files, or images.
- Acquisition and parsing failures return reviewable error responses.

### Phase 3: Reused review UI

- Add an import entry point and URL field.
- Open the existing recipe editor populated from preview.
- Show source evidence, thumbnail, parser warnings, and ingredient match states.
- Keep the draft entirely client-side until acceptance.

Gate:

- The five canary cases can be opened and edited.
- Ingredient rows can be corrected, split, removed, reordered, and matched.
- Cancel leaves the library unchanged.

### Phase 4: Accepted save endpoint

- Add explicit import/update submission.
- Construct `Recipe` and delegate once to `save_imported_recipe(...)`.
- Return the saved recipe detail and open it in the normal Main Recipe View.

Gate:

- A reviewed recipe produces one Markdown file, local image when available,
  correct indexes, and only the approved new canonical ingredients.
- Duplicate updates require explicit review action.

### Phase 5: Canary validation

- Exercise cases 014, 028, 044, 075, and 097 against a disposable scratch
  database first.
- Confirm the exact corrections made for each case.
- Inspect generated Markdown, ingredient catalog, local images, recipe cards, and
  recipe details.
- Only then ask whether to import reviewed recipes into the real library.

## Verification

Run after each phase, in proportion to the change:

```powershell
uv run python scratch/run_social_recipe_corpus.py
uv run pytest
npm --prefix ui run build
npm --prefix ui run lint
git diff --check
```

Focused tests should cover:

- complete and fallback preview responses;
- no writes during preview or cancel;
- supported-host validation;
- ingredient existing/new state and alias canonicalization;
- explicit duplicate behavior;
- final save delegation and Markdown/SQLite parity;
- image download success and graceful failure;
- UI loading, error, edit, cancel, and import states.

Do not add tests that silently decide unresolved product behavior; record the
decision first or ask the user.

## Out of Scope for This Vertical Slice

- TikTok, YouTube, Facebook, or another platform;
- video/audio transcription;
- frame selection or durable review video;
- automatic correction of source typos;
- fuzzy ingredient matching that makes decisions without review;
- persistent import drafts or candidate database tables;
- bulk import into the real library;
- rewriting frozen corpus expectations as user-facing corrections.

## New Chat Kickoff Prompt

Copy this into a new KitchenSync chat when ready to implement:

```text
Read AGENTS.md and every required policy/design source it names. Then read
scratch/social-recipe-import-review-flow-plan.md completely.

Inspect the current worktree before editing. Preserve existing or concurrent UI
changes, especially RecipeIngredientEditor.tsx and App.css. Treat current code
and tests as implementation truth.

Implement the Social Recipe Import Review Flow plan sequentially, starting with
Phase 1. Reuse the existing RecipeMainView recipe editor,
RecipeIngredientEditor, ingredient catalog/parse endpoints, and
app.recipes.save_imported_recipe(...) boundary. Keep the frozen corpus unchanged.
Do not add another platform, candidate database, job queue, or creator-specific
parser rules.

I authorize the non-trivial code, dependency, configuration, and focused test
changes required under src/, ui/, tests/, scripts/, pyproject.toml, uv.lock, and
scratch/ for this plan. Do not modify unrelated files, rewrite design notes, or
commit without asking.

Continue through ordinary implementation failures until the current phase gate
passes or you encounter an explicit blocker. Report material canary review
findings before writing to data/library/.
```

If the next chat should remain plan-only, omit the authorization paragraph and
say which phase or design question to evaluate without editing code.
