import type {
  CookbookDetailDto,
  CookbookUpdateRequest,
  IngredientCatalogItemDto,
  IngredientLineProjectionDto,
  RecipeCardDto,
  RecipeDetailDto,
  RecipeTagDto,
  RecipeUpdateRequest,
} from './recipe-types'

export type RecipeSearchRequest = {
  query?: string
  exactTags?: string[]
  meals?: string[]
  cuisines?: string[]
  diets?: string[]
  scope?: 'global' | 'cookbook'
  signal?: AbortSignal
}

async function requireSuccessfulResponse(
  response: Response,
  fallbackMessage: string,
) {
  if (!response.ok) {
    throw new Error(`${fallbackMessage} (${response.status})`)
  }
}

export async function listRecipes({
  query = '',
  exactTags = [],
  meals = [],
  cuisines = [],
  diets = [],
  scope = 'global',
  signal,
}: RecipeSearchRequest = {}) {
  const params = new URLSearchParams()
  if (query) params.set('q', query)
  for (const tag of exactTags) params.append('tag', tag)
  for (const meal of meals) params.append('meal', meal)
  for (const cuisine of cuisines) params.append('cuisine', cuisine)
  for (const diet of diets) params.append('diet', diet)
  if (scope === 'cookbook') params.set('scope', scope)

  const search = params.size ? `?${params}` : ''
  const response = await fetch(`/api/recipes${search}`, { signal })
  await requireSuccessfulResponse(response, 'Unable to load recipes')
  return (await response.json()) as RecipeCardDto[]
}

export async function listRecipeTags(
  scope: 'global' | 'cookbook' = 'global',
  signal?: AbortSignal,
) {
  const search = scope === 'cookbook' ? '?scope=cookbook' : ''
  const response = await fetch(`/api/recipe-tags${search}`, { signal })
  await requireSuccessfulResponse(response, 'Unable to load recipe tags')
  return (await response.json()) as RecipeTagDto[]
}

export async function listIngredients(signal?: AbortSignal) {
  const response = await fetch('/api/ingredients', { signal })
  await requireSuccessfulResponse(response, 'Unable to load ingredients')
  return (await response.json()) as IngredientCatalogItemDto[]
}

export async function parseIngredientLines(
  lines: string[],
  signal?: AbortSignal,
) {
  const response = await fetch('/api/ingredient-lines/parse', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ lines }),
    signal,
  })
  await requireSuccessfulResponse(response, 'Unable to parse ingredient lines')
  return (await response.json()) as IngredientLineProjectionDto[]
}

export async function getRecipeDetail(
  recipeId: string,
  signal?: AbortSignal,
) {
  const response = await fetch(
    `/api/recipes/${encodeURIComponent(recipeId)}`,
    { signal },
  )

  if (response.status === 404) {
    throw new Error('This recipe is no longer available.')
  }

  await requireSuccessfulResponse(response, 'Unable to load recipe details')
  return (await response.json()) as RecipeDetailDto
}

export async function updateRecipe(
  recipeId: string,
  request: RecipeUpdateRequest,
) {
  const response = await fetch(
    `/api/recipes/${encodeURIComponent(recipeId)}`,
    {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(request),
    },
  )
  await requireSuccessfulResponse(response, 'Unable to save recipe')
  return (await response.json()) as RecipeDetailDto
}

export async function addRecipeToCookbook(recipeId: string) {
  const response = await fetch(
    `/api/recipes/${encodeURIComponent(recipeId)}/cookbook`,
    { method: 'POST' },
  )
  await requireSuccessfulResponse(response, 'Unable to add recipe to Cookbook')
  return (await response.json()) as CookbookDetailDto
}

export async function updateCookbookEntry(
  recipeId: string,
  request: CookbookUpdateRequest,
) {
  const response = await fetch(
    `/api/recipes/${encodeURIComponent(recipeId)}/cookbook`,
    {
      method: 'PATCH',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(request),
    },
  )
  await requireSuccessfulResponse(response, 'Unable to save Cookbook details')
  return (await response.json()) as CookbookDetailDto
}
