export type RecipeCardDto = {
  recipe_id: string
  title: string
  image_url: string | null
  description: string | null
  cookbook: {
    favorite: boolean
    rating: number | null
  } | null
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
  tags: string[]
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
}
