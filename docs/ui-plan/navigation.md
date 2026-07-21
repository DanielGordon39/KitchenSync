# Navigation Plan

## Current Direction

Use a persistent application shell with the product areas introduced in phases.

| Area | Suggested route | Phase | Primary purpose |
| --- | --- | --- | --- |
| Global Recipes | `/recipes` | 1 | Browse, search, open, and edit the complete recipe catalog |
| Cookbook | `/cookbook` | 1 | Browse the notebook subset and manage favorite, rating, and notes |
| Ingredients | `/ingredients` | 2 | Inspect and maintain canonical ingredient knowledge |
| Shopping | `/shopping` | 3 | Build and manage shopping lists from cookbook recipes |
| Settings | `/settings` | Later | Configure library, API, display, and platform behavior |

Route names are suggestions, not locked API contracts.

## Default Destination

Open the first browser implementation on Global Recipes. Global Recipes and Cookbook are accessible tabs over one shared browser; Cookbook starts empty until recipes are added from the global catalog.

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

The first implementation uses a top tab bar for Global Recipes and Cookbook. It keeps the selected tab in local UI state; add routes only when direct links, browser history, or more product areas make routing useful.

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
- The selected Global Recipes/Cookbook tab is local state in the first implementation. Future top-level product areas should come from routes.
- Temporary menus and dialogs remain local UI state, including the recipe selected for the Main Recipe View popup.

## Open Questions

- Bottom navigation or menu navigation on mobile?
- Should Add Recipe be global or Cookbook-only?
- Should an active shopping list display a badge or item count in navigation?
