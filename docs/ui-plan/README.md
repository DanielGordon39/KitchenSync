# KitchenSync UI Design Plan

This folder is the working product-design plan for the KitchenSync UI. It describes navigation, screens, user flows, and reusable components before those decisions become application code.

The plan is intentionally iterative. Sections marked **Current direction** are strong enough to guide the next design discussion. Sections marked **Open question** still need a decision before implementation should depend on them.

## Relationship to Other UI Docs

- `docs/ui-architecture.md` describes the technical platform and browser-to-Python boundary.
- `docs/typescript-ui-tutorial.md` teaches the TypeScript and React concepts used to build the UI.
- This folder describes what the user sees and how the product behaves.

## Current Product Sequence

### Phase 1: Cookbook and Recipes

Start with the shared Global Recipes and Cookbook browser as the first complete UI slice. It uses the recipe database/index for:

- Browsing recipes
- Searching recipes
- Expanding a recipe card into the full-screen Main Recipe View popup
- Adding custom recipes
- Editing recipes
- Exercising the browser, API, Markdown, and SQLite path during base testing

Global Recipes presents the complete catalog. Cookbook presents only recipes with cookbook membership and adds a separate notebook section for favorite, rating, and personal notes. Both tabs open the same canonical recipe in Main Recipe View. V1 assumes one implicit user and allows all recipes to be edited; future creator or approved-editor permission checks should not merge recipe content with account-specific cookbook state.

### Phase 2: Ingredients

Add the ingredient catalog after recipe browsing and editing work. This phase should support inspecting the canonical ingredients created from recipes and then add cleanup or editing workflows deliberately.

### Phase 3: Shopping From the Cookbook

Create shopping lists from selected cookbook recipes. The first version should let the user review and edit generated shopping lines before saving them. Ingredient merging, unit conversion, pantry subtraction, and quantity aggregation remain separate design decisions.

## Planning Order

For each feature, work from the outside inward:

1. User goal
2. Navigation and entry point
3. Screen content and actions
4. Success, loading, empty, and error states
5. User flow between screens
6. Data and API requirements
7. Reusable components revealed by multiple screens
8. Responsive and accessibility behavior

## Plan Index

- `navigation.md` — application shell, tabs, routes, and responsive navigation
- `screens/cookbook.md` — Phase 1 recipe catalog, detail, add, and edit screens
- `screens/ingredients.md` — Phase 2 ingredient catalog and cleanup direction
- `screens/shopping.md` — Phase 3 shopping-list generation from recipes
- `components.md` — component layers, inventory, and reuse rules
- `flows.md` — cross-screen user workflows and failure paths

## Design Vocabulary

- **Page or screen:** A route-level user destination such as Cookbook or Ingredients.
- **Full-screen view:** A focused overlay within the current page, such as Main Recipe View.
- **Feature component:** A substantial part of a workflow, such as Recipe Search or Shopping Preview.
- **Shared product component:** A KitchenSync-specific element reused across features, such as Recipe Card or Ingredient Line.
- **Base component:** A small generic control such as Button, Text Input, Dialog, or Empty State.
- **Server state:** Data owned by the Python API, Markdown, or SQLite.
- **URL state:** Search text, selected filters, sorting, and other state worth linking or restoring.
- **Local UI state:** Temporary presentation state such as an open menu or dialog.
- **Form state:** Unsaved values and validation messages in an editor or review flow.

## Reuse Principle

Do not make a component generic only because it might be reused someday. Extract a shared component when:

- Its purpose is already stable, such as Button or Dialog.
- It appears in at least two real screens.
- Keeping the behavior consistent is more valuable than keeping the markup close to one page.

Prefer a few meaningful variants over a component with many unrelated options.

## Immediate Design Questions

The next iteration should decide:

1. Does adding a custom recipe open a full page, side panel, or dialog?
2. How should Git-backed recipe history, diffs, and recovery appear in the UI?
3. Should editing use the same form as adding a recipe?
4. Which recipe fields are required for a manually created recipe?
5. How should a user select recipes for a shopping list?
