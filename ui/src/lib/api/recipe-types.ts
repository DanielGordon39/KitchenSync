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
