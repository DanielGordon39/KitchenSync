import tomatoPlaceholder from './assets/recipes/tomato-placeholder.png'
import './App.css'
import type { RecipeCardDto } from './lib/api/recipe-types'
import { useEffect, useState } from 'react'

function RecipeCard({ recipe }: { recipe: RecipeCardDto }) {
  const rating = recipe.cookbook?.rating
  return (
    <article className="recipe-card">
      <img
        className="recipe-card__image"
        src={recipe.image_url ?? tomatoPlaceholder}
        alt=""
      />

      <h2 className="recipe-card__title">{recipe.title}</h2>

      {recipe.cookbook?.favorite && (
        <span
          className="recipe-card__favorite"
          aria-label="Favorite recipe"
        >
          ★
        </span>
      )}

      {recipe.description && (
        <p className="recipe-card__description">
          {recipe.description}
        </p>
      )}

      {rating !== null && rating !== undefined && (
        <span
          className="recipe-card__rating"
          aria-label={`Rated ${rating} out of 5`}
        >
          {rating} / 5
        </span>
      )}
    </article>
  )
}

function App() {
  const [recipes, setRecipes] = useState<RecipeCardDto[] | null>(null)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    async function loadRecipes() {
      try {
        const response = await fetch('/api/recipes')

        if (!response.ok) {
          throw new Error(`Request failed with status ${response.status}`)
        }

        const data: RecipeCardDto[] = await response.json()
        setRecipes(data)
      } catch (caughtError) {
        const message =
          caughtError instanceof Error
            ? caughtError.message
            : 'Unable to load recipes'

        setError(message)
      }
    }

    void loadRecipes()
  }, [])

  if (error) {
    return (
      <main>
        <p role="alert">Could not load recipes: {error}</p>
      </main>
    )
  }

  if (recipes === null) {
    return (
      <main>
        <p role="status">Loading recipes…</p>
      </main>
    )
  }

  return (
    <main>
      <section className="recipe-grid" aria-label="Recipes">
        {recipes.map((recipe) => (
          <RecipeCard key={recipe.recipe_id} recipe={recipe} />
        ))}
      </section>
    </main>
  )
}

export default App
