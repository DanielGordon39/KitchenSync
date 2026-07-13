# Intended API v1

KitchenSync v1 exposes one app facade over one local SQLite database.

The public API should name product concepts, not storage implementation details.

## Open The App

```python
from kitchensync.app import KitchenSyncApp

app = KitchenSyncApp.open("data/library/kitchensync.sqlite")
```

Opening the app initializes the SQLite schema if needed.

## Namespaces

The facade is organized around logical database areas:

```python
app.recipes
app.ingredients
app.cookbook
app.pantry
app.shopping
app.candidates
```

V1 implements only the first recipe/cookbook slice. Other namespaces exist in the intended API so later work has a stable place to land.

## Recipes

Recipes answer what a recipe is.

```python
app.recipes.save_metadata(
    recipe_id="recipe_blackened_chicken_penne_61b0d03a",
    title="Blackened Chicken Penne",
    slug="blackened-chicken-penne",
    servings=2,
    source_name="HelloFresh",
    source_url="https://example.com/recipe",
)

results = app.recipes.search("chicken")
recipe = app.recipes.get("recipe_blackened_chicken_penne_61b0d03a")
```

Search in v1 can use a simple SQLite `LIKE` query over indexed metadata. Full-text search can replace it when search behavior needs ranking or tokenization.

## Cookbook

The cookbook answers which cookbook entries exist and what cookbook-specific metadata has been indexed for search and UI views.

```python
app.cookbook.index_entry(
    recipe_id="recipe_blackened_chicken_penne_61b0d03a",
    recipe_slug="blackened-chicken-penne",
    title="Blackened Chicken Penne",
    cookbook_path="cookbook/blackened-chicken-penne.md",
    favorite=True,
    rating=4,
)
entries = app.cookbook.list_entries()
```

Recipe existence is separate from cookbook entry existence. Cookbook entry Markdown lives under `data/library/cookbook/{recipe_slug}.md` and is the durable source for cookbook-specific metadata.

## Ingredients

Ingredients answer what an ingredient is.

Planned API:

```python
app.ingredients.search("chicken breast")
app.ingredients.get("chicken_breast")
```

Canonical ingredient rows are indexed from ingredient Markdown.

## Pantry

Pantry answers what ingredients are currently on hand.

Planned API:

```python
app.pantry.list_items()
app.pantry.update_item("chicken_breast", amount=10, unit="ounce")
```

Pantry state is durable app state and is not canonical ingredient data.

## Shopping

Shopping answers what planned purchases exist.

Planned API:

```python
shopping_list = app.shopping.create_list("This week")
app.shopping.add_item(shopping_list.id, "chicken_breast", amount=20, unit="ounce")
```

Shopping list state is durable app state.

## Candidates

Candidates answer what parsed or imported data needs review.

Planned API:

```python
app.candidates.list_pending(candidate_type="ingredient")
app.candidates.resolve(candidate_id, action="approved_alias")
```

Candidate review state starts database-only in v1. It can become file-backed later if unresolved review state needs portable diffs.

## V2 Boundary

V1 does not model accounts, sharing, sync, or separate global and personal databases.

The API keeps recipe, ingredient, cookbook, pantry, shopping, and candidate concepts separate so v2 can split catalog data from account state without rewriting user-facing operations.
