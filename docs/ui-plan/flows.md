# UI Flow Plan

## Phase 1: Find and Open a Recipe

```text
Open Cookbook
  -> load recipe summaries
  -> search or browse
  -> select recipe
  -> store the selected recipe ID in local UI state
  -> expand the selected card into the Main Recipe View popup
  -> load full detail for only the selected recipe
```

Close or Escape clears the selection and reveals the still-mounted Cookbook at its prior search, filters, and scroll position. The URL remains `/cookbook`; the expansion is a visual transition, not the owner of recipe data or navigation state.

Failure paths:

- API unavailable
- Empty recipe library
- No matching recipes
- Recipe removed before detail loads

## Phase 1: Add a Custom Recipe

```text
Open Cookbook
  -> choose Add Recipe
  -> enter recipe fields
  -> validate
  -> save through Python API
  -> open the saved recipe in Main Recipe View
```

Failure and exit paths:

- Required information missing
- Save rejected by backend validation
- Markdown or index update fails
- User cancels with unsaved changes

## Phase 1 TODO: Edit a Recipe

The Edit action can begin from Main Recipe View, but the edit-mode shape and its user-facing history or recovery behavior are not decided yet.

```text
Open Main Recipe View
  -> choose Edit
  -> enter the future edit mode
  -> change fields
  -> validate
  -> save Markdown and index together
  -> return to Main Recipe View
```

Important behavior:

- Editing should use the durable recipe representation, not only the search-index row.
- Cancelling should not mutate durable data.
- Save failure should preserve the user's unsaved values.
- Git can provide Markdown history, diffs, and rollback, but the UI workflow over that history is a separate design decision.

## Phase 2: Review an Ingredient

```text
Open Ingredients
  -> search or browse
  -> open ingredient
  -> inspect aliases and metadata
  -> perform an explicit cleanup action
  -> review result
```

## Phase 3: Build Shopping List From Recipes

```text
Open Cookbook or Main Recipe View
  -> select recipe or recipes
  -> choose servings
  -> generate shopping preview
  -> review and edit ingredient lines
  -> save list
  -> check items while shopping
```

## Flow Documentation Checklist

For each new workflow, record:

- Trigger
- Ordered user steps
- Data read and written
- Success destination
- Validation failures
- API failures
- Cancel and back behavior
- Unsaved-change behavior
- Mobile-specific interaction differences
