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
result = parse_recipe("https://example.com/recipe")
saved = app.recipes.save_imported_recipe(result.recipe)

app.recipes.save_metadata(
    recipe_id="61b0d03ab3a03377ee6b1b04a9c8f01",
    title="Blackened Chicken Penne",
    slug="blackened-chicken-penne",
    servings=2,
    source_name="HelloFresh",
    source_url="https://example.com/recipe",
)

results = app.recipes.search("chicken")
recipe = app.recipes.get("recipe_blackened_chicken_penne_61b0d03a")
```

`save_imported_recipe(...)` is the public save boundary for accepted parsed recipes. It should:
- write the recipe Markdown file under `data/library/recipes/{slug}.md`;
- create or reuse canonical ingredient rows and Markdown files for each parsed ingredient name;
- index the same accepted recipe into `recipe_recipes`, `recipe_ingredients`, `recipe_steps`, `recipe_tags`, and `recipe_search`;
- optionally index cookbook membership through the cookbook API when the import flow says the recipe is saved to the cookbook.
- generate plain UUID hex IDs for new recipe rows and reuse existing recipe rows by source URL first, then slug;
- generate plain UUID hex IDs for new ingredient rows and reuse existing ingredient rows by slug in v1.
- store recipe author, imported-from marker, time-estimate minutes, and tags in SQLite when present.

Descriptions remain Markdown-only in v1. A later tag-suggestion pass may use recipe descriptions as model/parser input, but descriptions are not indexed as first-class database fields yet.

All UI, CLI, scratch, and future HTTP API save flows should call this one method or a thin endpoint that delegates to it. They should not call `write_recipe_markdown_files(...)` and `save_metadata(...)` separately, because separate calls can update Markdown without SQLite or SQLite without Markdown.

Search in v1 can use a simple SQLite `LIKE` query over indexed metadata. Full-text search can replace it when search behavior needs ranking or tokenization.

`save_metadata(...)` is the low-level index helper for tests and rebuild tasks. It should not be the recipe-import API.

Read methods for the first UI:

```python
recipes = app.recipes.list()
recipe = app.recipes.get_by_slug("blackened-chicken-penne")
detail = app.recipes.get_detail(recipe["recipe_id"])
```

`list()`, `get(...)`, `get_by_slug(...)`, and `search(...)` return recipe rows with a `tags` list attached. `get_detail(...)` returns a dictionary with `recipe`, `ingredients`, and `steps` keys so the UI can render a detail page without querying SQLite directly.

## Cookbook

The cookbook answers which cookbook entries exist and what cookbook-specific metadata has been indexed for search and UI views.

```python
app.cookbook.index_entry(
    recipe_id="61b0d03ab3a03377ee6b1b04a9c8f01",
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

V1 keeps imported recipe saves simple: parsed ingredient names are assumed good enough to become canonical ingredient records. If a parsed ingredient slug/name already exists, the recipe ingredient links to it. If not, the save flow creates a minimal ingredient Markdown file and indexes it.

Planned API:

```python
app.ingredients.ensure_ingredient("Chicken Breast")
app.ingredients.search("chicken breast")
app.ingredients.get("chicken_breast")
```

Canonical ingredient rows are indexed from ingredient Markdown.

Ingredient cleanup comes after there is enough real recipe data to review. The likely cleanup API is explicit, not automatic:

```python
app.ingredients.merge(source_id="chicken-breast-strips", target_id="chicken-breast")
app.ingredients.rename("roma-tomato", name="Roma Tomato")
```

The first UI can use:

```python
ingredients = app.ingredients.list()
```

This returns indexed ingredient rows ordered by name. It is read-only for now; cleanup actions such as merge and rename should remain explicit later APIs.

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

Candidate review state starts database-only. V1 keeps ingredient import optimistic and does not route normal parsed recipe ingredients through candidates. V2 should flip imported ingredient observations to candidate-first once the starter corpus has enough recipes to show real merge, alias, and cleanup patterns.

## V2 Boundary

V1 does not model accounts, sharing, sync, or separate global and personal databases.

The API keeps recipe, ingredient, cookbook, pantry, shopping, and candidate concepts separate so v2 can split catalog data from account state without rewriting user-facing operations.
