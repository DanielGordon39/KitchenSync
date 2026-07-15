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

Current browser HTTP support:

- `GET /api/recipes`
- `GET /api/recipes/{recipe_id}`

Still required before browser implementation:

- Paged and searchable recipe-summary endpoints for the eventual infinite grid
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

### Search and Filter Direction

Place one free-text search field above the recipe grid. Search the complete backend result set, not only the recipe cards already loaded in the browser.

Rank matches by:

1. Fuzzy recipe-title match
2. Exact or spelling-corrected tag match
3. Fuzzy ingredient match

Title matches receive the strongest weight. Tag matching should prefer known normalized tags and visibly suggest a corrected tag rather than silently rewriting the query. Ingredient matching can use canonical ingredient names, parsed names, and raw ingredient text.

Provide explicit tag and ingredient filters in addition to free-text search. Filters act as constraints on the result set and should remain usable with an empty text query. Search, filters, sorting, and infinite loading must use the same stable backend ordering and paging contract.

Before implementation, create representative examples for:

- Misspelled recipe titles
- Misspelled or partial tags
- Ingredient synonyms and partial ingredient names
- Queries that match a title, tag, and ingredient at different strengths
- Multiple active filters with and without text search

### Eventual Infinite Scroll Direction

The target Cookbook grid is an infinite, virtualized list of recipe summaries. Keep these concerns separate:

- **Infinite loading** fetches additional pages of recipe-card summaries.
- **Virtualization** keeps only the visible cards and a nearby overscan window rendered in the document.
- **Detail loading** fetches ingredients, steps, and the rest of one recipe for Main Recipe View.

Use this loading order:

1. Load enough summary cards to fill the initial viewport plus a small buffer.
2. Render visible rows and overscan beyond both edges of the viewport.
3. Bias the overscan and next-page trigger toward rows below the viewport because downward scrolling is the common path.
4. Keep a smaller buffer above for quick reverse scrolling.
5. Fetch the next summary page before the user reaches the end of the loaded range.

A two-below to one-above bias is a reasonable starting heuristic, but it is not a durable product contract. Prefer measuring the buffer in viewport distance or responsive row counts instead of always loading ten rows: ten rows may represent ten cards on mobile and forty or more cards on a wide grid.

Do not preload full recipe details for every card in the overscan window. Detail payloads are larger and would make infinite scrolling steadily consume network and memory. Fetch detail when a recipe is selected; a later optimization may prefetch one likely recipe on clear user intent such as keyboard focus or sustained pointer hover. Keep any detail cache small and bounded.

Additional behavior:

- Lazy-load card images near the visible or forward-overscan range.
- Preserve already fetched summary pages long enough for smooth reverse scrolling.
- Reset paging and the visible anchor when search, sort, or filters change.
- Show distinct initial-loading, loading-more, retry, and end-of-results states.
- Add a paged or cursor-based recipe-summary API with a stable sort order before the library needs true infinite loading.

## Recipe Card

Current candidate information:

- Recipe title
- Image when available
- Time estimate
- Servings
- Tags
- Source name

The first card does not need every field. Choose the smallest set that helps the user identify and compare recipes.

### Open Behavior

Selecting any recipe card opens that recipe's **Main Recipe View** as a full-screen popup over the Cookbook. The interaction should feel as if the selected card expands out of the grid and takes over the full application viewport:

- The Cookbook grid, search, and filters remain mounted beneath the popup but become visually and interactively inactive.
- The selected recipe ID is local UI state. Opening and closing the popup does not change the `/cookbook` URL.
- The transition may visually grow from the selected card, but opening the recipe must not depend on animation support.
- Close or Escape reveals the same Cookbook view with its search, filters, and scroll position intact.
- Keyboard focus moves into the opened recipe view and returns to the originating card when it closes. Reduced-motion preferences should replace the expansion with a simple transition.

This is an application-level full-screen dialog, not use of the browser fullscreen API and not a separate route. Refreshing the browser closes the popup, and an open recipe is not directly linkable in this first version. Revisit URL-backed selection only if sharing or restoring an open recipe becomes important.

## Main Recipe View

Location: full-screen popup within `/cookbook`

### Purpose

Give the selected recipe the full screen so the user can read all recipe content without the Cookbook catalog competing for space. It is also the future starting point for editing or shopping-list creation.

### Content

- Title and description
- Servings and time
- Source information
- Ingredients in recipe order
- Steps in recipe order
- Notes
- Tags and images when available

### Detail Content Source TODO

The current detail endpoint can return indexed recipe metadata, tags, ingredients, steps, and the local main image URL. Recipe descriptions and recipe notes are not currently part of `app.recipes.get_detail(...)` because they are not indexed in SQLite.

Before Main Recipe View promises those fields, decide whether the detail read should:

- Parse the canonical recipe Markdown and combine it with indexed data
- Promote selected display fields into the rebuildable SQLite index
- Use another explicit read model derived from recipe Markdown

The decision must preserve Markdown as the canonical recipe source and define how the UI avoids stale or conflicting detail data. Do not add placeholder fields to the endpoint contract until this source boundary is settled.

### Actions

- Close the popup and return focus to the Cookbook
- Edit recipe, after edit mode and history behavior are defined
- Add recipe to shopping workflow, in Phase 3
- Adjust displayed serving count, after scaling behavior is defined

### Recipe-Only Boundary

The first Main Recipe View displays recipe content only. It does not include cookbook-specific state such as:

- Favorite state
- Personal or family rating
- Personal notes
- Cook history or last-cooked information

When KitchenSync begins using the cookbook database in the UI, this view can gain a separate cookbook section for that relationship data. Keep that as an explicit later expansion; do not make those fields part of the first Main Recipe View contract now.

### Data and Memory Boundary

- The Cookbook grid loads summary data only, not every recipe's ingredients and steps.
- Opening the popup fetches full detail for the selected recipe.
- Closing the popup may discard that detail or retain a small bounded cache for quick reopening.
- Recipe images should use lazy loading so the browser does not decode every off-screen image immediately.
- The card grid follows the infinite-loading and virtualization direction above. Its summary buffer remains independent of the selected recipe popup.

### Frictionless Open Behavior

- Respond to the click immediately by opening the popup shell with title, image, and other summary data already held by the selected card.
- Start the detail request at the same time as the expansion; do not wait for it before opening the popup.
- If ingredients and steps arrive during the transition, place them directly into the view.
- If detail takes longer, show stable skeleton regions for ingredients and steps instead of a blank popup or blocking spinner.
- Let recipe text become usable without waiting for a large image to download or decode.
- Keep the most recently opened recipe, or another deliberately small bounded set, available for instant reopening.
- Measure click-to-popup and click-to-usable-detail separately so database, HTTP, image, and rendering delays remain distinguishable.

### Responsive Behavior

- Fill the available dynamic viewport on phones, tablets, and desktop screens.
- Let the popup own vertical scrolling so long ingredients and steps remain usable without moving the background Cookbook.
- Use one readable content column at narrow widths.
- On wider screens, constrain line length and introduce additional columns only when ingredients and steps remain easy to follow.
- Keep Close and future Edit actions reachable in a persistent header, including around mobile safe areas and browser controls.

### Edit Mode TODO

An Edit action may switch the Main Recipe View into a dedicated edit mode, but the edit interaction is not yet settled. Before implementing it, decide:

- Whether editing replaces the reading layout inside the popup or opens a separate editor
- How unsaved changes, Save, Cancel, and stale recipe data behave
- How the UI exposes version history or recovery

Recipe Markdown is already Git-friendly, and Git can own file history, diffs, and rollback. The UI still needs a deliberate product workflow over that capability; do not create a second recipe-history system as part of the first detail view.

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

Status: TODO pending the Main Recipe View edit-mode and history decisions.

If a separate editor remains the chosen direction, reuse the same form structure as Add Custom Recipe when practical. Add and Edit may share field components and validation, but they remain separate behaviors:

- Add starts from empty defaults.
- Edit loads an existing durable recipe.
- Edit needs missing-recipe and stale-data handling.
- Saving an edit must update Markdown and rebuild or update indexed rows together.

## Phase 1 Base-Test Slice

The minimum useful implementation order is:

1. Render a static Cookbook layout.
2. Load recipe summaries from the API.
3. Search recipes.
4. Open a recipe in Main Recipe View.
5. Add a simple custom recipe.
6. Edit the same recipe.
7. Confirm the recipe remains correct after restarting the Python API and rebuilding indexes.
