import type { RecipeCardDto, RecipeDetailDto } from './recipe-types'

async function requireSuccessfulResponse(
  response: Response,
  fallbackMessage: string,
) {
  if (!response.ok) {
    throw new Error(`${fallbackMessage} (${response.status})`)
  }
}

export async function listRecipes(signal?: AbortSignal) {
  const response = await fetch('/api/recipes', { signal })
  await requireSuccessfulResponse(response, 'Unable to load recipes')
  return (await response.json()) as RecipeCardDto[]
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
