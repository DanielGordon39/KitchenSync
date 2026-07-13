# Database v1

KitchenSync v1 uses one local SQLite file:

```text
data/library/kitchensync.sqlite
```

This is one physical database with separate logical database areas for recipes, ingredients, cookbook state, pantry state, shopping lists, and review candidates.

## V1 Assumptions

- KitchenSync v1 is a single-user local app.
- V1 does not model accounts, sharing, sync, or separate global and personal databases.
- Recipe, ingredient, cookbook, pantry, shopping, and candidate data are separated by table and API boundaries, not by physical SQLite files.
- These boundaries should remain clear enough that v2 can split data by account, sharing scope, or sync ownership later.

## Logical Databases

Recipe tables answer: what is this recipe?

Ingredient tables answer: what is this ingredient?

Cookbook tables answer: which cookbook entry files exist, and what cookbook-specific metadata can be searched or filtered quickly?

Pantry tables answer: what ingredients are currently on hand?

Shopping tables answer: what planned purchases exist?

Candidate tables answer: what imported or parsed data needs review before becoming durable recipe or ingredient data?

## Physical File Decision

Use one SQLite file for v1. Separate physical SQLite files would make cross-area queries, foreign keys, backups, schema setup, and deletes more complicated before the app needs separate lifecycles.

If v2 needs account ownership, sharing, or independent sync, the logical table boundaries can become separate physical databases then.

## Table Prefixes

Use these prefixes for v1:

```text
recipe_*       recipe catalog, recipe index, recipe search
ingredient_*   ingredient catalog and matching data
cookbook_*     cookbook entry index and searchable cookbook metadata
pantry_*       current inventory
shopping_*     shopping lists and planned purchases
candidate_*    recipe and ingredient review queues
```

## Source Of Truth

Recipe Markdown remains the portable source of truth for recipe content in v1.

Ingredient Markdown remains the portable source of truth for canonical ingredient knowledge in v1.

The database may persist app workflow state that is not represented in recipe or ingredient Markdown.

Rebuildable from recipe Markdown:

- recipe metadata
- recipe ingredients
- recipe steps
- recipe search rows

Rebuildable from ingredient Markdown:

- canonical ingredient rows
- aliases
- packaging
- conversions
- category and storage lookup rows

Rebuildable from cookbook entry Markdown:

- cookbook membership
- cookbook-specific recipe notes, ratings, favorite state, status, and cook history
- cookbook entry search rows

Durable app state:

- pantry inventory
- shopping lists
- candidate review state

## V1 Schema Slice

The first implementation slice creates the core table groups and implements:

- database initialization
- recipe metadata upsert
- recipe metadata search
- cookbook entry indexing
- cookbook entry listing

Recipe content writing, Markdown indexing, ingredient matching, pantry, shopping, and candidate resolution come after this slice.

## Cookbook Boundary

Recipe existence is separate from cookbook membership.

A recipe can exist in `recipe_recipes` without a cookbook entry.

Cookbook entry files live at:

```text
data/library/cookbook/{recipe_slug}.md
```

Cookbook entry Markdown owns:

- favorite
- rating
- status
- personal notes
- cook history
- last cooked date
- tweaks and next-time notes

Recipe-owned fields include:

- title
- slug
- source metadata
- ingredient rows
- step rows
- search text

Cookbook entries may duplicate lookup and display metadata such as `recipe_id`, `recipe_slug`, `recipe_path`, and title. They must not duplicate full recipe content such as ingredients, steps, source metadata, or recipe notes.

The SQLite `cookbook_entries` table indexes cookbook entry files for listing, filtering, sorting, and joining against recipe metadata. If SQLite is deleted, cookbook entries should be rebuildable from `data/library/cookbook/{recipe_slug}.md`.

## Candidate Boundary

Candidate rows are durable review workflow state.

Candidates may represent recipe imports or ingredient observations. V1 may keep recipe and ingredient candidate records in one candidate table with a `candidate_type` column until their fields diverge enough to justify separate tables.

Candidate files under `ingredients/_candidates/` or similar paths are deferred until portability of unresolved review state becomes necessary.
