# UI Flow Plan

## Phase 1: Find and Open a Recipe

```text
Open Cookbook
  -> load recipe summaries
  -> search or browse
  -> select recipe
  -> load recipe detail
```

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
  -> open saved recipe detail
```

Failure and exit paths:

- Required information missing
- Save rejected by backend validation
- Markdown or index update fails
- User cancels with unsaved changes

## Phase 1: Edit a Recipe

```text
Open Recipe Detail
  -> choose Edit
  -> load editable recipe
  -> change fields
  -> validate
  -> save Markdown and index together
  -> return to Recipe Detail
```

Important behavior:

- Editing should use the durable recipe representation, not only the search-index row.
- Cancelling should not mutate durable data.
- Save failure should preserve the user's unsaved values.

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
Open Cookbook or Recipe Detail
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

