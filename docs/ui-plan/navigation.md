# Navigation Plan

## Current Direction

Use a persistent application shell with the product areas introduced in phases.

| Area | Suggested route | Phase | Primary purpose |
| --- | --- | --- | --- |
| Cookbook | `/cookbook` | 1 | Browse, search, open, add, and edit recipes |
| Ingredients | `/ingredients` | 2 | Inspect and maintain canonical ingredient knowledge |
| Shopping | `/shopping` | 3 | Build and manage shopping lists from cookbook recipes |
| Settings | `/settings` | Later | Configure library, API, display, and platform behavior |

Route names are suggestions, not locked API contracts.

## Default Destination

Open the application on the Cookbook because it is the first useful product area and the source for later ingredient and shopping workflows.

## Desktop Shell

Suggested layout:

```text
+-------------------------------------------------------+
| KitchenSync                         Global actions     |
+----------------+--------------------------------------+
| Cookbook       |                                      |
| Ingredients    |            Current page              |
| Shopping       |                                      |
| Settings       |                                      |
+----------------+--------------------------------------+
```

The first implementation may use a top navigation bar instead of a side rail. Choose based on the number of stable top-level areas and available width; do not build both patterns initially.

## Mobile Shell

Use the same route structure with navigation adapted for narrow screens. Likely options are:

- Bottom navigation for the three primary areas
- A top app bar plus menu for less-frequent destinations such as Settings

Avoid hiding the primary Cookbook action behind several menu levels.

## Page-Level Actions

Primary actions belong near the page title or in an obvious mobile action area:

- Cookbook: Add Recipe
- Ingredients: Add or Review Ingredient, when those behaviors exist
- Shopping: New Shopping List

## Navigation State

- Search and filters should use URL query parameters when restoring or sharing the view is useful.
- Unsaved editor values should remain form state, not URL state.
- The selected top-level area comes from the current route.
- Temporary menus and dialogs remain local UI state, including the recipe selected for the Main Recipe View popup.

## Open Questions

- Side navigation or top navigation on desktop?
- Bottom navigation or menu navigation on mobile?
- Should Add Recipe be global or Cookbook-only?
- Should an active shopping list display a badge or item count in navigation?
