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

In v1, normal recipe imports do not use candidates for parsed ingredients. The first implementation auto-creates or reuses canonical ingredient records from parsed ingredient names so the recipe corpus can grow quickly. Candidate-first ingredient import is deferred to v2.

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

SQLite row IDs are internal database identities. New recipe and ingredient rows use plain UUID hex strings. These IDs are not stored in Markdown and may be regenerated if the SQLite database is rebuilt. Slugs remain the human-readable file identity and lookup key for Markdown-backed records.

Rebuildable from recipe Markdown:

- recipe metadata
- recipe main image path
- recipe ingredients
- recipe steps
- recipe tags
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
- candidate review state, when a workflow explicitly creates candidates

## Current V1 Schema Slice

The implemented slice now includes:

- database initialization and additive schema migration;
- accepted recipe saves through `app.recipes.save_imported_recipe(...)`;
- recipe and ingredient Markdown writes;
- local main-image persistence;
- recipe metadata, ingredient, step, tag, and search indexing;
- recipe list/detail reads for the browser UI;
- optimistic ingredient creation and reuse by slug;
- cookbook entry indexing and listing.

Pantry, shopping, candidate resolution, ingredient merge/rename helpers, and full Markdown-to-index rebuild commands remain future work. Candidate-first ingredient import stays deferred until roughly 30-50 saved recipes expose practical duplicate and alias patterns.

Repeated imports should reuse an existing recipe row by source URL first, then slug as a fallback. New ingredient rows should use UUID IDs and reuse existing ingredients by slug in v1.

Recipe metadata indexing includes title, slug, servings, source name, source URL, author, imported-from marker, simple time estimate minutes, Markdown path, and main image path. Recipe tags are indexed in `recipe_tags`. Recipe search includes title, slug, source fields, author, imported-from marker, tags, ingredient names, and raw ingredient lines; step text is stored in `recipe_steps` but not included in search text for v1.

Recipe search ranks normal fuzzy text by title, then tags, then ingredients, with source metadata retained as a lower-priority fallback. Completed `#tag` tokens are exact tag requests. When several are present, recipes matching every requested tag form the first result group and recipes matching some requested tags form a second group ranked by match count. Common meal, cuisine, and diet filters use the same normalized `recipe_tags` rows and remain separate from cookbook relationship state.

## Cookbook Boundary

Recipe existence is separate from cookbook membership.

A recipe can exist in `recipe_recipes` without a cookbook entry.

V1 assumes one implicit local user and allows every recipe to be edited. A cookbook entry points to that same canonical recipe; adding a recipe to the Cookbook does not clone or fork its content. The entry adds notebook state such as favorite, rating, and personal notes. Later account-aware versions may restrict global recipe editing to the creator or approved editors without changing this recipe-versus-cookbook ownership boundary.

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
- main image path
- ingredient rows
- step rows
- search text

Cookbook entries may duplicate lookup and display metadata such as `recipe_id`, `recipe_slug`, `recipe_path`, and title. They must not duplicate full recipe content such as ingredients, steps, source metadata, or recipe notes.

The SQLite `cookbook_entries` table indexes cookbook entry files for listing, filtering, sorting, and joining against recipe metadata. If SQLite is deleted, cookbook entries should be rebuildable from `data/library/cookbook/{recipe_slug}.md`.

## Candidate Boundary

Candidate rows are durable review workflow state.

V1 keeps the candidate table available, but normal parsed recipe imports should not create ingredient candidates. They should auto-create or reuse canonical ingredients and preserve raw recipe ingredient text for later cleanup.

V2 should use candidates for imported ingredient observations before they become canonical ingredients. It may keep recipe and ingredient candidate records in one candidate table with a `candidate_type` column until their fields diverge enough to justify separate tables.

Candidate files under `ingredients/_candidates/` or similar paths are deferred until portability of unresolved review state becomes necessary.
