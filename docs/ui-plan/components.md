# Component Plan

Components should emerge from the screens and flows in this plan. This inventory is a starting hypothesis, not a requirement to build every component before the first page.

## Component Layers

### Base UI

Small generic controls with stable behavior:

- `Button`
- `IconButton`
- `TextInput`
- `TextArea`
- `Select`
- `Checkbox`
- `Dialog`
- `Drawer`
- `LoadingIndicator`
- `ErrorMessage`
- `EmptyState`

### Shared KitchenSync Components

Product-specific elements likely to appear across features:

- `RecipeCard`
- `RecipeSummary`
- `IngredientLine`
- `TagList`
- `SourceLink`
- `QuantityDisplay`
- `PageHeader`
- `SearchField`

### Phase 1 Feature Components

- `RecipeSearchToolbar`
- `RecipeFilterPanel`
- `RecipeGrid`
- `RecipeMainView`
- `RecipeDetailHeader`
- `RecipeIngredientList`
- `RecipeStepList`
- `RecipeForm`
- `RecipeIngredientEditor`
- `RecipeStepEditor`

### Later Feature Components

- `IngredientCatalogList`
- `IngredientMergePreview`
- `RecipeSelectionList`
- `ShoppingPreviewLine`
- `ShoppingListItem`
- `ServingSelector`

## Component Specification Template

```markdown
### Component Name

Purpose:
- What stable job does this component perform?

Content:
- What information does it display?

Actions:
- What interactions does it own?

Variants:
- Which genuinely different presentations are needed?

States:
- Loading, empty, selected, disabled, error, or missing-data states

Accessibility:
- Label, keyboard, focus, and announcement requirements

Responsive behavior:
- What changes at narrow widths?

Used by:
- Which real screens use it?
```

## Reuse Rules

- Pages own route loading and page composition.
- Feature components own a recognizable workflow section.
- Shared product components own repeated KitchenSync presentation or interaction.
- Base components own generic controls and visual consistency.
- API calls belong in API or route-loading modules, not inside visual leaf components.
- Prefer composition over a component with many boolean options.
- Keep feature-specific components near their feature until real reuse appears.

## State Ownership

| State | Preferred owner | Example |
| --- | --- | --- |
| Server state | Route or API data layer | Recipe list and full recipe data |
| URL state | Router/search parameters | Search text, tag filter, sorting |
| Form state | Recipe or ingredient form | Unsaved title and ingredient rows |
| Local UI state | Closest component that needs it | Selected recipe popup or open filter drawer |
| Durable workflow state | Python API and SQLite | Saved shopping list |

## Recipe Card to Main View Boundary

- `RecipeCard` owns the user's open/select action and the visual origin of the expansion.
- `RecipeGrid` owns visible-window rendering and the trigger for loading more summary pages.
- The grid may keep a larger overscan buffer below than above the viewport, but it does not preload full recipe details.
- The Cookbook screen owns the selected recipe ID as local UI state; opening a recipe does not change the URL.
- `RecipeMainView` owns the full-screen dialog composition and its loading, not-found, and error states.
- Recipe data comes from the data or API layer; it should not be copied into long-lived card-local state.
- The grid loads lightweight summaries. Full ingredients, steps, and other detail are fetched only for the selected recipe.
- Closing the popup should release its detail state or leave only a deliberately small cache; it must not accumulate every opened recipe indefinitely.
- `RecipeMainView` adds a Cookbook-only notebook section for favorite, rating, and personal notes. Cook history remains a later expansion.
