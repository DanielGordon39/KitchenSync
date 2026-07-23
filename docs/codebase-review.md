# KitchenSync Codebase Review

Review date: 2026-07-23

This review evaluates the current repository for long-term readability and maintainability without proposing a redesign. Baseline line counts describe the pre-refactor implementation inspected on this date. The targeted social-parser split and recipe-search extraction described below were completed after the review.

## Executive Assessment

KitchenSync already has a sound architecture for its current size. The strongest design choice is the explicit separation between portable Markdown, a local SQLite index, Python-owned business behavior, and a TypeScript UI. The code also has one accepted recipe-save boundary and a review-first social import flow, which prevent the most damaging form of early architectural drift.

The main maintainability issue was concentration, not a missing architecture. A few files accumulated several stages of otherwise coherent workflows. The completed refactor mechanically split the social parser and narrowly extracted recipe-search internals. Moving every product API into a new `api/` or `services/` package would still add churn without improving the current dependency graph.

## Strengths

- The domain vocabulary is stable and visible: Recipe, Ingredient, Cookbook, tags, Markdown, and database indexes retain distinct meanings.
- `KitchenSyncApp` gives scripts and HTTP routes one product-oriented facade.
- `RecipesAPI.save_imported_recipe(...)` centralizes accepted recipe persistence.
- Preview and cancel are transient; only explicit acceptance persists an Instagram import.
- Pydantic models isolate domain data from the UI and storage formats.
- The HTTP layer delegates parsing and persistence rather than reimplementing them.
- Markdown remains compact and human-readable.
- The SQLite schema uses clear logical table prefixes and foreign keys.
- Search intentionally uses a simple standard-library scorer while the local catalog is small.
- External packages are used at appropriate boundaries: `recipe-scrapers`, `ingredient-parser-nlp`, `yt-dlp`, FastAPI, Pydantic, React, and Vite.
- Tests cover model imports, parser dispatch, ingredient parsing, Markdown output, database behavior, web contracts, import preview, accepted saves, and UI-backend orchestration.
- The deterministic social corpus and disposable canary provide stronger parser evidence than isolated examples alone.

## Weaknesses

### Concentrated implementation files

At the review baseline, `parsing/social.py` contained the entire deterministic parser from regex vocabulary through fallback recommendation. `recipe_api.py` combined accepted-save orchestration, filesystem work, SQL writes, detail reads, tag enumeration, and fuzzy search. The targeted refactor resolved the clearest boundaries without changing their public APIs.

### Documentation is distributed

The repository has good focused documents, but there was no single current implementation map. Some older Obsidian notes still describe persistence and HTTP choices as open, while the code has implemented them. `README.md` was empty, making the existing docs difficult to discover.

### Recovery is not complete

The design says recipe, ingredient, and Cookbook indexes are rebuildable from Markdown. The serializers are implemented, but a general Markdown parser and full rebuild command are not. Recipe detail recovery reads only description and notes from Markdown. Until rebuild tooling exists, deleting SQLite would lose the working index even though the durable content files remain.

### Filesystem and SQLite writes are not atomic together

The accepted-save boundary centralizes writes, but filesystem changes happen before the SQLite commit and cannot roll back with it. A failure between these operations can leave repairable divergence. This is acceptable for the local v1 scale, but recovery tooling becomes more important as the library grows.

### DTOs are duplicated by hand

Pydantic request/response models and TypeScript types currently mirror one another manually. The surface is small enough for this to remain readable, but drift risk grows with every endpoint and field.

### Application namespaces are only partially implemented

The schema contains pantry, shopping, and candidate tables, while `KitchenSyncApp` exposes only recipes, ingredients, and cookbook. This is intentional staging, but new contributors can mistake schema presence for finished behavior.

### Module intent is not consistently stated

Most Python modules and public API classes have little or no module-level documentation. The code is readable, but ownership and non-responsibilities often require tracing imports or consulting several docs.

## Architectural Observations

### The architecture is a modular monolith

KitchenSync is one Python package and one browser client. The backend modules share one SQLite connection and local library root. This is the right shape for a local-first personal application. Separate services, message buses, repository interfaces, or dependency-injection frameworks would add operational and conceptual cost without solving a current problem.

### APIs are product namespaces, not transport APIs

`RecipesAPI`, `IngredientsAPI`, and `CookbookAPI` are application-facing namespaces used by both HTTP endpoints and scripts. They are not merely FastAPI routers. Keeping them near `KitchenSyncApp` makes this distinction visible.

### Parsing has two orchestration paths

The generic parser returns a `ParseResult` and is used by the website batch importer. The Instagram browser path separates acquisition, deterministic text parsing, transient review, and accepted save. These paths should share domain and persistence boundaries without being forced into one artificial importer abstraction.

### Markdown is durable but SQLite is currently operationally required

The format boundary is correct, but the recovery story is ahead of the tooling. Documentation should say “rebuildable by design” rather than imply a working one-command rebuild today.

### The browser remains thin at the persistence boundary

The UI has substantial interaction code, but persistence decisions still live in Python. The UI submits raw editable content and displays backend results; it does not derive file paths, IDs, or database rows.

## Technical Debt

| Debt | Current impact | Recommended trigger |
| --- | --- | --- |
| No full Markdown reader/index rebuild | SQLite cannot yet be recreated automatically | Implement before treating database deletion as a supported recovery operation |
| Manual filesystem-plus-database consistency | Interrupted saves may require repair | Add a repair/reindex command before multi-user or unattended imports |
| Hand-maintained Python/TypeScript DTO parity | Endpoint changes can drift | Generate types after the HTTP schema stabilizes and manual drift becomes recurring |
| Additive migrations embedded in `database.py` | Fine for the small schema, less auditable over time | Introduce numbered migrations only when multiple deployed database versions need support |
| Best-effort image download silently falls back | Missing images are not surfaced as structured diagnostics | Add save diagnostics when users need to resolve image failures |
| Social heuristic vocabulary is centralized and dense | Safe behavior changes require broad file navigation | Split by parser stage while preserving the frozen corpus |
| `unclassified_lines` is rarely informative because analysis assigns a default narrative concept | Diagnostic name overpromises current behavior | Revisit only when fallback orchestration consumes truly unclassified evidence |
| Web request-to-`Recipe` mapping is repeated for import and update | Small maintenance duplication | Extract one mapper when a third write route needs the same conversion |
| Root `main.py` is a placeholder | Misleading entrypoint | Replace or remove when a supported CLI is defined |
| Local data layout docs mention a `.kitchensync/` folder while the current database lives at `data/library/kitchensync.sqlite` | Minor onboarding ambiguity | Align the data README in the next persistence-doc pass |

## Large Files

### Production Python

| File | Lines | Why it grew | Keep together? | Proposed decomposition |
| --- | ---: | --- | --- | --- |
| `src/kitchensync/parsing/social.py` | 1,620 | Regex vocabulary, intermediate models, normalization, line evidence, grouping, title extraction, field extraction, warnings, and pipeline orchestration accumulated through corpus-driven parser work | No. These are sequential but independently understandable parser stages. | Convert to a `parsing/social/` package with a compatibility-preserving `__init__.py`; split models/patterns, normalization, analysis, grouping, candidate metadata, ingredient/step content, and fallback decisions. |
| `src/kitchensync/recipe_api.py` | 788 | The recipe namespace owns accepted saves, images, Markdown, ingredient setup, index writes, detail reads, tags, filters, and fuzzy ranking | Mostly. Save and read operations share one consistency boundary, but search ranking is independently cohesive. | Keep `recipe_api.py` and `RecipesAPI` stable; extract internal search/filter/ranking work to `recipe_search.py`. Defer a storage package until rebuild/import behavior creates another clear boundary. |
| `src/kitchensync/web.py` | 570 | DTOs and endpoints for recipe lists, tags, ingredients, import review/save, recipe detail/update, and Cookbook state share one adapter | Yes for now. It is one small transport layer and splitting it would require router composition before the app has many resource families. | Defer. Split DTOs and routers only when another substantial resource family makes route discovery difficult. |
| `src/kitchensync/parsing/ingredients.py` | 203 | Lossless editor projection and domain parsing share the same third-party parse shape and unit helpers | Yes. Both paths must agree on what the parser can represent. | Keep together. Split only if catalog matching or conversion logic arrives. |
| `src/kitchensync/cookbook_api.py` | 200 | Markdown formatting and index synchronization are the complete Cookbook-entry save boundary | Yes. | Keep together until cook-history operations or rebuild logic become substantial. |
| `src/kitchensync/database.py` | 196 | One compact schema string plus a few connection/migration helpers | Yes at the current schema size. | Move to numbered migrations only when deployed schema evolution requires it. |

Post-refactor production counts:

| File | Lines | Result |
| --- | ---: | --- |
| `src/kitchensync/recipe_api.py` | 652 | Stable facade and persistence/read boundary; search delegates to a cohesive internal module |
| `src/kitchensync/web.py` | 572 | Unchanged apart from its module docstring |
| `src/kitchensync/parsing/social/name.py` | 414 | Recipe-name heuristics are isolated from other parser stages |
| `src/kitchensync/parsing/social/content.py` | 413 | Ingredient and step extraction is isolated |
| `src/kitchensync/parsing/social/grouping.py` | 266 | Context grouping and field association |
| `src/kitchensync/parsing/social/analysis.py` | 224 | Independent line evidence and ingredient-parser support |
| `src/kitchensync/recipe_search.py` | 198 | Filtering, tag counts, and fuzzy ranking extracted from `RecipesAPI` |

### Large non-production Python

| File | Lines | Assessment |
| --- | ---: | --- |
| `tests/test_app_database.py` | 818 | Covers several product namespaces and is the strongest test-splitting candidate. Split by recipe persistence, search, ingredients, and Cookbook when the next database feature is added; a mechanical split now has little value. |
| `tests/test_web.py` | 457 | Multiple route contracts share similar fake-app setup. Keep until a second backend resource family makes focused route files easier to navigate. |
| `scratch/social_import_probe.py` | 447 | Broad by design: it is an exploratory acquisition and report tool, not a reusable runtime module. Keep stable while the research loop is active. |
| `scripts/import_recipe_urls.py` | 364 | Batch orchestration, reporting, and CLI parsing are cohesive enough for one operational script. Reusable behavior already lives in the package. |
| `scratch/archive/instagram/run_social_recipe_review_canary.py` | 325 | Archived end-to-end verification; keep separate from production and split only if it becomes an active reusable tool again. |

Large frontend files also deserve monitoring: `RecipeMainView.tsx` is 931 lines, `RecipeIngredientEditor.tsx` is 759, and `App.css` is 1,228. They still map to recognizable UI responsibilities, but import review and ordinary recipe editing now share one file. A future UI-only refactor could extract `RecipeEditor` and `RecipeImportReview` after the current import flow settles.

## Targeted Refactor Outcome

### Social parser: completed

Preserve these import surfaces:

```python
from kitchensync.parsing import parse_recipe_text
from kitchensync.parsing.social import (
    LineAnalysis,
    RecipeFieldCandidate,
    RecipeTextParseResult,
    SocialRecipeCandidate,
    analyze_lines,
    build_field_candidates,
    build_social_recipe_candidate,
    normalize_lines,
    parse_recipe_text,
)
```

Implemented package:

```text
src/kitchensync/parsing/social/
  __init__.py
  models.py
  patterns.py
  normalize.py
  analysis.py
  grouping.py
  name.py
  candidate.py
  content.py
  fallback.py
```

Responsibilities:

- `__init__.py`: public compatibility facade and `parse_recipe_text(...)` orchestration;
- `models.py`: parser intermediate Pydantic models;
- `patterns.py`: shared compiled regex vocabulary and fixed headings;
- `normalize.py`: source-line normalization;
- `analysis.py`: ingredient support and independent line evidence;
- `grouping.py`: contextual blocks and field candidates;
- `name.py`: recipe-name extraction and cleanup heuristics;
- `candidate.py`: candidate assembly plus description, servings, tags, and notes;
- `content.py`: ingredient and step extraction from contextual evidence;
- `fallback.py`: concrete warnings and fallback recommendation.

A separate `scoring.py` was not added. Evidence scoring remains with line analysis and grouping, where the rules are interpreted.

### Recipe API: narrow extraction completed

Keep:

```python
from kitchensync.recipe_api import RecipesAPI
```

`RecipesAPI.search(...)` and `RecipesAPI.list_tags(...)` signatures remain unchanged. Query normalization, fuzzy scoring, filter/ranking assembly, and tag counting now live in `src/kitchensync/recipe_search.py`. The public class remains the product namespace and delegates internally.

Save orchestration remains together; repositories, storage services, and mixins were not added. Those methods intentionally coordinate files and index rows at one boundary.

### API/service folder move: defer

Do not move:

```text
recipe_api.py
ingredient_api.py
cookbook_api.py
```

into `api/` or `services/` now.

Reasons:

- the flat package is still small and highly discoverable;
- the modules are already named by product concept;
- `KitchenSyncApp` is the canonical discovery surface;
- a move would require compatibility shims without changing ownership;
- `services/` would blur the fact that these are stable application namespaces, not generic service objects.

Reconsider an `api/` package when at least pantry, shopping, and candidate APIs are implemented and the package root becomes difficult to scan.

## Future Scaling Concerns

### Library size

Recipe search loads recipe, tag, and ingredient rows into memory and scores them with `difflib`. This is appropriate for the current local catalog. Add SQLite FTS and paging only after measurements show interactive latency or memory problems.

### Import volume

Batch imports write and commit one recipe at a time. That isolates failures and keeps reports meaningful. High-volume unattended ingestion would need explicit transaction, retry, image, and repair policies rather than a transparent bulk optimization.

### Multi-user or sync behavior

The current architecture assumes one local implicit user. Account ownership, permissions, merge behavior, and sync conflict resolution would change persistence semantics. Do not pre-build those abstractions into v1 APIs.

### Schema evolution

The current `CREATE TABLE IF NOT EXISTS` schema plus additive columns is sufficient for one local app. Multiple released clients opening older databases will require ordered, testable migrations.

### UI contract growth

Manual TypeScript DTOs and a single FastAPI module remain simple now. If endpoints expand across pantry, shopping, and candidate workflows, split routers by product namespace and generate TypeScript types from the stable OpenAPI schema.

### Parser change safety

Social parsing is rule- and corpus-driven. Refactors should be mechanical. Behavior changes should remain one narrow rule at a time and run against the frozen social corpus before merging.

## Documentation Drift to Review

The new architecture guide records current repository behavior. The following planning context is older than the implementation:

- the Obsidian project hub still lists persistence and the UI-to-Python boundary as open decisions;
- the Obsidian Recipe Engine note says Markdown generation is not implemented;
- the Obsidian Parsing Pipeline note predates Instagram acquisition and deterministic social parsing;
- `docs/ui-architecture.md` describes import preview/save endpoints as future, but they are implemented;
- `data/README.md` shows a `.kitchensync/` database directory that is not the current v1 path.

These differences do not require code changes. The Obsidian notes should be updated only through an explicit documentation-alignment pass.

## Deferred Opportunities

- Full Markdown parse and index rebuild.
- Save repair/reconciliation command.
- Structured import/image diagnostics.
- Generated TypeScript API types.
- Route/DTO package split after more product namespaces exist.
- UI extraction of shared recipe editor and import-review components.
- Test-file split when the next database or web resource family lands.
- Pantry, shopping, and candidate APIs only when those workflows are ready.
