# Cookbook and Recipe Screens

Phase: 1

The Cookbook is the first complete UI slice. It uses recipe index data for browsing and search while preserving room for separate cookbook-specific metadata such as favorites and ratings.

## Cookbook Screen

Suggested route: `/cookbook`

### Purpose

Help the user find, open, and manage saved recipes.

### Entry Points

- Default application destination
- Return destination after saving or cancelling a recipe
- Destination after selecting Cookbook in navigation

### Content

- Page title
- Add Recipe action
- Search field
- Sort and filter controls
- Recipe count or result summary
- Recipe card or list results

### Primary Actions

- Search recipes
- Open a recipe
- Add a custom recipe
- Edit an existing recipe
- Clear search or filters

### Data

Current backend support:

- `app.recipes.list()`
- `app.recipes.search(query)`
- `app.recipes.get(recipe_id)`
- `app.recipes.get_detail(recipe_id)`

Still required before browser implementation:

- HTTP endpoints over those methods
- A product-level manual create operation
- A product-level edit operation that keeps Markdown and SQLite synchronized

The UI must not call `save_metadata(...)` directly as a substitute for a complete create or edit operation.

### States

- Initial loading
- Recipes loaded
- Empty library
- No search results
- API unavailable
- Search or filter error

### Responsive Behavior

- Use a multi-column recipe grid when space permits.
- Collapse to one column on narrow screens.
- Keep search and Add Recipe easy to reach.
- Move secondary filters into a drawer or expandable section only if they no longer fit clearly.

## Recipe Card

Current candidate information:

- Recipe title
- Image when available
- Time estimate
- Servings
- Tags
- Source name
- Favorite state when cookbook metadata is added

The first card does not need every field. Choose the smallest set that helps the user identify and compare recipes.

## Recipe Detail Screen

Suggested route: `/recipes/:recipeId`

### Purpose

Display the complete recipe and provide the starting point for editing or shopping-list creation.

### Content

- Title and descriptive metadata
- Servings and time
- Source information
- Ingredients in recipe order
- Steps in recipe order
- Notes
- Tags and images when available

### Actions

- Edit recipe
- Return to Cookbook
- Add recipe to shopping workflow, in Phase 3
- Adjust displayed serving count, after scaling behavior is defined

### States

- Loading
- Recipe loaded
- Recipe not found
- Recipe data incomplete
- API error

## Add Custom Recipe Screen

Suggested route: `/recipes/new`

### Purpose

Create a recipe manually when no import source is used or parsing fails.

### Candidate Fields

- Title
- Description
- Servings
- Time estimate
- Ingredient lines
- Ordered steps
- Notes
- Source information, optional
- Tags and images, optional when supported

### Behavior

- Add, remove, and reorder ingredient lines.
- Add, remove, and reorder steps.
- Preserve unsaved values while validation messages are shown.
- Save through one Python operation that writes Markdown and updates the index.
- Cancel without mutating durable recipe data.

### Open Questions

- Which fields are required besides title?
- Should the editor show raw ingredient text only or parsed fields too?
- Should the recipe Markdown preview be visible?
- Should autosave exist, or should the first version use explicit Save only?

## Edit Recipe Screen

Suggested route: `/recipes/:recipeId/edit`

Reuse the same form structure as Add Custom Recipe when practical. Add and Edit may share field components and validation, but they remain separate page behaviors:

- Add starts from empty defaults.
- Edit loads an existing durable recipe.
- Edit needs missing-recipe and stale-data handling.
- Saving an edit must update Markdown and rebuild or update indexed rows together.

## Phase 1 Base-Test Slice

The minimum useful implementation order is:

1. Render a static Cookbook layout.
2. Load recipe summaries from the API.
3. Search recipes.
4. Open recipe details.
5. Add a simple custom recipe.
6. Edit the same recipe.
7. Confirm the recipe remains correct after restarting the Python API and rebuilding indexes.

