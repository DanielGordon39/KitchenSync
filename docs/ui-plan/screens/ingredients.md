# Ingredient Screens

Phase: 2

Ingredient UI work begins after Cookbook browsing, Main Recipe View, and basic custom recipe editing are usable.

## Ingredient Catalog Screen

Suggested route: `/ingredients`

### Purpose

Inspect the canonical ingredient knowledge produced and used by saved recipes.

### Content

- Ingredient search
- Ingredient count
- Category or storage filters when data exists
- Ingredient list
- Indicators for incomplete metadata or possible cleanup work

### Current Backend Support

- `app.ingredients.list()`

### Required Later Support

- Search and detail operations
- Explicit rename and merge operations
- Alias editing
- Category, storage, packaging, and conversion editing as those fields become useful
- Safe updates to ingredient Markdown and rebuildable indexes

## Ingredient Detail or Editor

Possible route: `/ingredients/:ingredientId`

Candidate sections:

- Name and aliases
- Category and storage area
- Packaging
- Unit conversions
- Matching guidance
- Human notes
- Recipes using this ingredient

Do not expose every possible metadata section in the first ingredient UI. Start with the fields needed to understand and clean up the ingredient catalog created by real recipes.

## Cleanup Workflow

Likely early actions:

- Rename an ingredient
- Merge a duplicate into a canonical ingredient
- Add an alias
- Fill missing category or storage information

These should be explicit reviewed actions rather than silent automatic mutations.

## Open Questions

- Is ingredient detail read-only before cleanup operations are implemented?
- How are merge consequences previewed?
- Which ingredient fields should appear in the default list?
- When should recipe parsing create candidates instead of canonical ingredients directly?
