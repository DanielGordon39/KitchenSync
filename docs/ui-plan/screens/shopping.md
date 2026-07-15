# Shopping Screens

Phase: 3

The first shopping workflow starts from cookbook recipes rather than from a blank list.

## Product Goal

Let the user select recipes, choose intended servings, review generated ingredient lines, and save a practical shopping list.

## Entry Points

- Add a recipe from Main Recipe View
- Select multiple recipes from Cookbook
- Open Shopping and create a list from cookbook recipes

## Suggested Flow

```text
Select cookbook recipes
  -> choose serving counts
  -> generate shopping preview
  -> review, edit, combine, or remove lines
  -> save shopping list
  -> check off items while shopping
```

## Shopping Builder Screen

Possible route: `/shopping/new`

### Content

- Selected recipes
- Serving count per recipe
- Generated ingredient lines
- Warnings for unknown quantities or units
- Manual add-item action
- Save List action

### Review Behavior

The generated preview should remain editable before it becomes durable shopping state. The user should be able to:

- Rename a shopping line
- Adjust quantity or unit
- Remove a line
- Add a missing line
- Choose whether apparently similar lines should combine

## Shopping List Screen

Possible route: `/shopping/:shoppingListId`

### Content

- List name
- Active and checked items
- Source recipes, when useful
- Optional category grouping later

### Actions

- Check or uncheck an item
- Add, edit, or remove an item
- Rename or complete the list
- Return to the source recipe when provenance is available

## Backend Requirements

Shopping APIs are planned but not implemented. The UI will eventually require product-level operations for:

- Creating a shopping list
- Generating a preview from selected recipes and servings
- Saving reviewed preview lines
- Updating and checking items
- Listing active and previous shopping lists

## Decisions to Make Before Implementation

- Should identical ingredient IDs combine automatically or only be suggested?
- How should incompatible units be displayed?
- Should pantry inventory be subtracted in the first release or later?
- Should raw recipe ingredient text remain visible in the preview?
- How should optional recipe ingredients be handled?
- Does checking an item update pantry state, or remain shopping-only?
