# TypeScript UI Tutorial for KitchenSync

This guide is a learning path for building KitchenSync's browser UI. It assumes no previous TypeScript experience. It uses KitchenSync-shaped examples, but none of the snippets are currently application code.

Read this alongside `docs/ui-architecture.md`.

## 1. The Mental Model

TypeScript is JavaScript plus a static type checker.

```ts
const title: string = "Tomato Soup";
const servings: number = 4;
const favorite: boolean = true;
```

The browser still runs JavaScript. TypeScript checks code before it runs and is removed from the built output.

Two consequences matter immediately:

1. Good TypeScript catches many mistakes in the editor or build.
2. A TypeScript type does not validate JSON received at runtime.

## 2. Files You Will See

- `.ts` contains TypeScript without JSX markup.
- `.tsx` contains TypeScript plus JSX markup used by React components.
- `tsconfig.json` controls TypeScript checking.
- `vite.config.ts` configures Vite.
- `package.json` lists JavaScript packages and commands.

Use strict TypeScript. Strict errors can feel noisy at first, but they teach where the program is making an unsafe assumption.

## 3. Variables and Type Inference

Prefer `const` unless the variable itself must be reassigned.

```ts
const recipeTitle = "Tomato Soup";
let searchText = "";

searchText = "tomato";
```

TypeScript infers both variables as strings. Do not annotate every obvious local variable.

```ts
const servingCount = 4; // inferred as number
const tags = ["soup", "weeknight"]; // inferred as string[]
```

Use an explicit type when it communicates intent or inference does not have enough information:

```ts
const selectedRecipeIds: string[] = [];
```

Without `: string[]`, an empty array may not carry the intent you want in every context.

## 4. Object Shapes With `type`

KitchenSync API data is mostly JSON objects. A type alias names an expected shape:

```ts
type RecipeSummaryDto = {
  recipe_id: string;
  title: string;
  slug: string | null;
  servings: number | null;
  source_name: string | null;
  source_url: string | null;
  author: string | null;
  imported_from: string | null;
  time_estimate_minutes: number | null;
  markdown_path: string | null;
  created_at: string;
  updated_at: string;
  tags: string[];
};
```

The `Dto` suffix means data transfer object: the shape crossing the HTTP/JSON boundary. It is not necessarily the same as the Python domain `Recipe` model.

The current Python read API returns snake_case keys, so the first TypeScript DTOs should use the same keys. Avoid adding a snake_case-to-camelCase conversion layer until it solves a real readability problem.

## 5. `type` Versus `interface`

Both can describe objects:

```ts
type RecipeCardProps = {
  title: string;
};

interface RecipeCardPropsAlternative {
  title: string;
}
```

A practical KitchenSync convention can be:

- Use `type` for API DTOs, unions, and composed types.
- Use either `type` or `interface` for component props, then stay consistent.

Do not spend much time on this choice initially. The important skill is describing the data shape accurately.

## 6. Arrays and Nested Objects

The current detail read returns a recipe, ingredients, and steps:

```ts
type RecipeIngredientDto = {
  ingredient_order: number;
  raw_text: string;
  ingredient_id: string | null;
  parsed_name: string | null;
  quantity_amount: number | null;
  quantity_unit: string | null;
  preparation: string | null;
};

type RecipeStepDto = {
  step_order: number;
  text: string;
};

type RecipeDetailDto = {
  recipe: RecipeSummaryDto;
  ingredients: RecipeIngredientDto[];
  steps: RecipeStepDto[];
};
```

`RecipeIngredientDto[]` means an array whose elements must match `RecipeIngredientDto`.

The generic spelling means the same thing:

```ts
const ingredients: Array<RecipeIngredientDto> = [];
```

Use `Thing[]` for simple arrays and `Array<Thing>` when nested generic syntax is easier to read.

## 7. Optional, `undefined`, and `null`

These are related but different:

```ts
type Example = {
  nickname?: string;
  description: string | null;
};
```

- `nickname?: string` means the property may be absent. Reading it produces `string | undefined`.
- `description: string | null` means the property exists, but its value may explicitly be `null`.

JSON supports `null` but not `undefined`. Python `None` becomes JSON `null`.

For API DTOs, prefer required properties with nullable values when the API consistently includes the key. Use optional properties only when the server may omit the key.

Narrow before using a nullable value:

```ts
function formatServings(servings: number | null): string {
  if (servings === null) {
    return "Servings not provided";
  }

  return `${servings} servings`;
}
```

## 8. Functions

Parameter types follow the parameter name. Return types follow the closing parenthesis.

```ts
function formatMinutes(minutes: number | null): string {
  if (minutes === null) {
    return "Time not provided";
  }

  return `${minutes} min`;
}
```

Arrow functions are common for short callbacks:

```ts
const recipeTitles = recipes.map((recipe) => recipe.title);
```

TypeScript infers `recipe` from the array element type.

Use named functions for important operations and arrow functions for small callbacks. This is a readability preference, not a TypeScript requirement.

## 9. Literal Unions and Narrowing

A union says a value may be one of several types. Literal unions restrict it to exact values:

```ts
type ImportStatus = "idle" | "loading" | "success" | "error";
```

For UI workflows, a discriminated union is safer than several booleans:

```ts
type ImportState =
  | { kind: "idle" }
  | { kind: "loading"; sourceUrl: string }
  | { kind: "success"; recipe: RecipeDetailDto }
  | { kind: "error"; message: string };
```

TypeScript narrows the shape after checking `kind`:

```ts
function ImportMessage({ state }: { state: ImportState }) {
  switch (state.kind) {
    case "idle":
      return <p>Enter a recipe URL.</p>;
    case "loading":
      return <p>Parsing {state.sourceUrl}...</p>;
    case "success":
      return <p>Found {state.recipe.recipe.title}.</p>;
    case "error":
      return <p role="alert">{state.message}</p>;
  }
}
```

Inside each case, only the fields belonging to that state are available. This prevents impossible states such as `isLoading === true` and `error !== null` unless the model intentionally allows them.

## 10. Modules and Type-Only Imports

Export values and types from one file:

```ts
export type RecipeSummaryDto = {
  recipe_id: string;
  title: string;
};

export function recipePath(recipe: RecipeSummaryDto): string {
  return `/recipes/${recipe.recipe_id}`;
}
```

Import them elsewhere:

```ts
import { recipePath } from "./recipes";
import type { RecipeSummaryDto } from "./recipes";
```

`import type` tells TypeScript that the import is only needed while checking types and should not become a runtime JavaScript import.

## 11. Generics

Generics let a function preserve information about a type supplied by its caller.

```ts
type ApiPage<T> = {
  items: T[];
  total: number;
};

type RecipePage = ApiPage<RecipeSummaryDto>;
```

Read `ApiPage<RecipeSummaryDto>` as “an API page whose item type is `RecipeSummaryDto`.”

Do not reach for generics simply because they look reusable. Introduce them when two or more real shapes share the same behavior.

## 12. Async Functions and `Promise`

Browser HTTP calls are asynchronous:

```ts
async function loadRecipes(): Promise<RecipeSummaryDto[]> {
  const response = await fetch("/api/recipes");

  if (!response.ok) {
    throw new Error(`Could not load recipes (${response.status})`);
  }

  return response.json();
}
```

Breakdown:

1. `async` means the function always returns a promise.
2. `Promise<RecipeSummaryDto[]>` describes the eventual successful value.
3. `await` pauses this function until the fetch finishes without freezing the browser.
4. `response.ok` must be checked because `fetch` does not reject merely because the server returned an HTTP error status.
5. This example trusts the JSON too much; the next section fixes that.

## 13. `unknown` Instead of `any`

`any` turns off useful checking:

```ts
const unsafeData: any = await response.json();
unsafeData.this.does.not.exist(); // TypeScript allows this.
```

`unknown` forces proof before use:

```ts
const untrustedData: unknown = await response.json();
```

Use `unknown` at untrusted boundaries such as HTTP responses, local storage, pasted JSON, or messages from a native wrapper.

## 14. Runtime Validation With Zod

TypeScript cannot inspect runtime JSON, so validate API responses. Zod is one option:

```ts
import { z } from "zod";

const RecipeSummarySchema = z.object({
  recipe_id: z.string(),
  title: z.string(),
  slug: z.string().nullable(),
  servings: z.number().int().nullable(),
  source_name: z.string().nullable(),
  source_url: z.string().nullable(),
  author: z.string().nullable(),
  imported_from: z.string().nullable(),
  time_estimate_minutes: z.number().int().nullable(),
  markdown_path: z.string().nullable(),
  created_at: z.string(),
  updated_at: z.string(),
  tags: z.array(z.string()),
});

type RecipeSummaryDto = z.infer<typeof RecipeSummarySchema>;
```

The schema does two jobs:

- `RecipeSummarySchema.parse(value)` checks a runtime value.
- `z.infer<typeof RecipeSummarySchema>` derives the matching static TypeScript type.

Now the fetch function can validate:

```ts
const RecipeListSchema = z.array(RecipeSummarySchema);

async function loadRecipes(): Promise<RecipeSummaryDto[]> {
  const response = await fetch("/api/recipes");

  if (!response.ok) {
    throw new Error(`Could not load recipes (${response.status})`);
  }

  const body: unknown = await response.json();
  return RecipeListSchema.parse(body);
}
```

If the server returns `servings: "four"`, validation fails at the boundary instead of letting bad data travel through many components.

## 15. React Components and Props

A React component is usually a function that returns JSX:

```tsx
import type { RecipeSummaryDto } from "../lib/api/recipe-types";

type RecipeCardProps = {
  recipe: RecipeSummaryDto;
  onOpen: (recipeId: string) => void;
};

export function RecipeCard({ recipe, onOpen }: RecipeCardProps) {
  return (
    <article>
      <h2>{recipe.title}</h2>
      <p>{recipe.servings ?? "Unknown"} servings</p>
      <button type="button" onClick={() => onOpen(recipe.recipe_id)}>
        View recipe
      </button>
    </article>
  );
}
```

Breakdown:

- The file is `.tsx` because it contains JSX.
- `RecipeCardProps` describes inputs from the parent component.
- `{ recipe, onOpen }` destructures the props object.
- `(recipeId: string) => void` means a function accepts a string and has no meaningful return value.
- `??` uses the right side only when the left side is `null` or `undefined`.
- The arrow function delays `onOpen` until the button is clicked.

## 16. Rendering Arrays

Use `map` to turn data into elements:

```tsx
type RecipeListProps = {
  recipes: RecipeSummaryDto[];
};

export function RecipeList({ recipes }: RecipeListProps) {
  return (
    <section aria-labelledby="recipe-list-heading">
      <h1 id="recipe-list-heading">Recipes</h1>
      {recipes.map((recipe) => (
        <RecipeCard
          key={recipe.recipe_id}
          recipe={recipe}
          onOpen={(recipeId) => console.log(recipeId)}
        />
      ))}
    </section>
  );
}
```

`key` gives React stable identity for list items. Use the recipe ID, not the array index, because list order may change.

## 17. State With `useState`

State is data that changes and causes the component to render again:

```tsx
import { useState } from "react";

export function RecipeSearch() {
  const [query, setQuery] = useState("");

  return (
    <label>
      Search recipes
      <input
        value={query}
        onChange={(event) => setQuery(event.currentTarget.value)}
      />
    </label>
  );
}
```

TypeScript infers `query` as `string` from the initial value.

Use an explicit generic when the initial value is not enough:

```ts
const [selectedRecipe, setSelectedRecipe] =
  useState<RecipeSummaryDto | null>(null);
```

Do not put every variable in state. Derived values can be calculated during rendering:

```ts
const normalizedQuery = query.trim().toLocaleLowerCase();
const visibleRecipes = recipes.filter((recipe) =>
  recipe.title.toLocaleLowerCase().includes(normalizedQuery),
);
```

## 18. Event Types

Inline event handlers are usually inferred. Extracted handlers may need an explicit type:

```tsx
import type { ChangeEvent } from "react";

function handleSearchChange(event: ChangeEvent<HTMLInputElement>) {
  console.log(event.currentTarget.value);
}
```

Useful form event types include:

- `ChangeEvent<HTMLInputElement>` for an input change.
- `FormEvent<HTMLFormElement>` for form submission.
- `MouseEvent<HTMLButtonElement>` for a button-specific mouse handler.

Prefer `currentTarget` when you want the element that owns the handler.

## 19. A Small Typed Form

Start with native form behavior and React state:

```tsx
import { useState } from "react";
import type { FormEvent } from "react";

type RecipeUrlFormProps = {
  onPreview: (sourceUrl: string) => Promise<void>;
};

export function RecipeUrlForm({ onPreview }: RecipeUrlFormProps) {
  const [sourceUrl, setSourceUrl] = useState("");
  const [isSubmitting, setIsSubmitting] = useState(false);

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setIsSubmitting(true);

    try {
      await onPreview(sourceUrl);
    } finally {
      setIsSubmitting(false);
    }
  }

  return (
    <form onSubmit={handleSubmit}>
      <label htmlFor="recipe-url">Recipe URL</label>
      <input
        id="recipe-url"
        type="url"
        required
        value={sourceUrl}
        onChange={(event) => setSourceUrl(event.currentTarget.value)}
      />
      <button type="submit" disabled={isSubmitting}>
        {isSubmitting ? "Loading..." : "Preview recipe"}
      </button>
    </form>
  );
}
```

Notice that the component does not know how parsing works. It owns the form UI and calls an injected operation.

## 20. Error Handling

JavaScript allows any value to be thrown, so caught errors are safest as `unknown`:

```ts
function errorMessage(error: unknown): string {
  if (error instanceof Error) {
    return error.message;
  }

  return "An unexpected error occurred";
}
```

Then use it in a catch block:

```ts
try {
  await loadRecipes();
} catch (error: unknown) {
  setMessage(errorMessage(error));
}
```

Avoid assertions such as `error as Error` unless the code has actually proved the value is an `Error`.

## 21. Type Assertions: Use Carefully

This compiles but does not validate anything:

```ts
const recipe = (await response.json()) as RecipeSummaryDto;
```

`as RecipeSummaryDto` means “trust me.” It does not convert or inspect the JSON.

Prefer:

```ts
const body: unknown = await response.json();
const recipe = RecipeSummarySchema.parse(body);
```

Assertions are still useful when TypeScript lacks information that the browser or a library guarantees, but they should be narrow and justified.

## 22. API Types Versus Domain Types

Do not copy the Python `Recipe` Pydantic model blindly into TypeScript.

The first UI reads indexed rows shaped like:

- `RecipeSummaryDto`
- `RecipeIngredientDto`
- `RecipeStepDto`
- `RecipeDetailDto`

The import-review endpoint may later return a different shape closer to the parsed Python `Recipe`. Name those types after their boundary, for example:

```ts
type ParsedRecipePreviewDto = {
  name: string;
  servings: number | null;
  ingredients: ParsedIngredientPreviewDto[];
  steps: ParsedStepPreviewDto[];
};
```

This prevents one oversized “Recipe” type from pretending every screen receives the same data.

## 23. Common Python-to-TypeScript Differences

| Python | TypeScript |
| --- | --- |
| `str` | `string` |
| `int` and `float` | `number` |
| `bool` | `boolean` |
| `None` | `null` in JSON |
| `list[T]` | `T[]` or `Array<T>` |
| `dict[str, T]` | `Record<string, T>` |
| `T | None` | `T | null` at a JSON boundary |
| Pydantic runtime validation | TypeScript does not provide runtime validation; use a schema library or generated client plus validation. |

Other differences to remember:

- JavaScript `number` does not distinguish integer and floating-point types.
- Browser dates arrive as strings unless code explicitly parses them.
- Object equality compares references, not field-by-field value equality.
- Empty strings, zero, `false`, `null`, and `undefined` behave differently in truthiness checks.
- TypeScript object types are structural: matching shape matters more than the declared class name.

## 24. Suggested Learning Milestones

### Milestone 1: Static Recipe Card

Learn:

- Vite file structure
- `.tsx`
- Props
- JSX
- Basic CSS

Build a card from a hard-coded `RecipeSummaryDto`.

### Milestone 2: Recipe List

Learn:

- Arrays
- `map`
- Stable keys
- Component composition
- Responsive Grid or Flexbox

Render several hard-coded recipes.

### Milestone 3: Search and UI State

Learn:

- `useState`
- Input events
- Derived values
- Conditional rendering

Filter the hard-coded list in the browser.

### Milestone 4: Routes

Learn:

- URL paths
- Route parameters
- Layout routes
- Navigation links
- Loading and error elements

Create list and detail routes.

### Milestone 5: Real API Reads

Learn:

- `async` and `await`
- `fetch`
- HTTP status handling
- `unknown`
- Zod validation

Replace hard-coded data with the Python HTTP API.

### Milestone 6: Import Review Form

Learn:

- Form submission
- Discriminated unions
- Editable arrays
- Validation messages
- Mutation and navigation flow

Implement URL -> preview -> review -> save after the API contract exists.

### Milestone 7: Tests

Learn:

- Unit tests for pure formatters
- Component tests through labels, roles, and visible text
- HTTP mocking at the network layer
- End-to-end browser tests for the import workflow

## 25. Beginner Guardrails

- Prefer inference for local values, explicit types for public boundaries.
- Prefer `unknown` over `any`.
- Prefer literal unions over TypeScript `enum` for small JSON status sets.
- Prefer one component responsibility over a single giant screen component.
- Keep API calls in `lib/api` or feature API modules, not scattered through visual components.
- Keep server data out of global client stores unless a real client-owned state problem appears.
- Do not use `!` to silence a nullable error until you understand why the value is safe.
- Read compiler errors from the final line upward: the useful mismatch is often near the bottom.
- Let the editor show inferred types by hovering before adding annotations.
- Run type checking separately from tests; fast transpilers such as Vite and Vitest do not replace full type checking.

## 26. Boilerplate I Can Help With Later

When requested, safe starter boilerplate can include:

- The Vite React TypeScript scaffold under `ui/`.
- A strict `tsconfig` review.
- Empty route and feature folders.
- A typed API wrapper with mocked data.
- Example DTO and Zod schema files.
- Vitest and React Testing Library setup.
- A responsive application shell with placeholder routes.

That boilerplate should stay behavior-light so the user can write and understand the first real components.

## Official Learning References

- [TypeScript for the New Programmer](https://www.typescriptlang.org/docs/handbook/typescript-from-scratch.html)
- [TypeScript Everyday Types](https://www.typescriptlang.org/docs/handbook/2/everyday-types.html)
- [TypeScript Narrowing](https://www.typescriptlang.org/docs/handbook/2/narrowing.html)
- [React Quick Start](https://react.dev/learn)
- [React: Using TypeScript](https://react.dev/learn/typescript)
- [Vite Getting Started](https://vite.dev/guide/)
- [React Router Data Mode](https://reactrouter.com/start/modes)
- [Zod basics](https://zod.dev/basics)

