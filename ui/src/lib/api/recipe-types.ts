export type RecipeCardDto = {
  recipe_id: string
  title: string
  image_url: string | null
  description: string | null
  cookbook: {
    favorite: boolean
    rating: number | null
  } | null
  tag_match: 'all' | 'some' | null
}

export type RecipeTagDto = {
  tag_slug: string
  recipe_count: number
}

export type IngredientCatalogItemDto = {
  ingredient_id: string
  name: string
  slug: string | null
  aliases: string[]
  default_unit: string | null
}

export type IngredientLineProjectionDto = {
  raw_text: string
  safe_for_rich: boolean
  quantity_text: string | null
  unit: string | null
  ingredient_name: string | null
  preparation: string | null
  reason: string | null
}

export type CookbookDetailDto = {
  favorite: boolean
  rating: number | null
  notes: string | null
}

export type RecipeDetailRecipeDto = {
  recipe_id: string
  title: string
  slug: string | null
  servings: number | null
  source_name: string | null
  source_url: string | null
  author: string | null
  imported_from: string | null
  time_estimate_minutes: number | null
  image_url: string | null
  tags: string[]
  description: string | null
  notes: string[]
}

export type RecipeIngredientDto = {
  ingredient_order: number
  raw_text: string
  ingredient_id: string | null
  parsed_name: string | null
  quantity_amount: number | null
  quantity_unit: string | null
  preparation: string | null
}

export type RecipeStepDto = {
  step_order: number
  text: string
}

export type RecipeDetailDto = {
  recipe: RecipeDetailRecipeDto
  ingredients: RecipeIngredientDto[]
  steps: RecipeStepDto[]
  cookbook: CookbookDetailDto | null
}

export type RecipeUpdateRequest = {
  title: string
  description: string | null
  servings: number | null
  time_estimate_minutes: number | null
  tags: string[]
  ingredients: string[]
  steps: string[]
  notes: string[]
}

export type CookbookUpdateRequest = {
  favorite: boolean
  rating: number | null
  notes: string | null
}
