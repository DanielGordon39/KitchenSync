import tomatoPlaceholder from './assets/recipes/tomato-placeholder.png'
import './App.css'
import { RecipeMainView } from './features/recipes/RecipeMainView'
import { listRecipes } from './lib/api/recipes'
import type { RecipeCardDto } from './lib/api/recipe-types'
import { useEffect, useRef, useState } from 'react'

function RecipeCard({
  recipe,
  onOpen,
}: {
  recipe: RecipeCardDto
  onOpen: () => void
}) {
  return (
    <button type="button" className="recipe-card" onClick={onOpen}>
      <img
        className="recipe-card__image"
        src={recipe.image_url ?? tomatoPlaceholder}
        alt=""
      />

      <h2 className="recipe-card__title">{recipe.title}</h2>

      {recipe.description && (
        <p className="recipe-card__description">
          {recipe.description}
        </p>
      )}
    </button>
  )
}

function App() {
  const [recipes, setRecipes] = useState<RecipeCardDto[] | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [selectedRecipe, setSelectedRecipe] = useState<RecipeCardDto | null>(
    null,
  )
  const lastFocusedElement = useRef<HTMLElement | null>(null)

  useEffect(() => {
    const controller = new AbortController()

    async function loadRecipes() {
      try {
        const data = await listRecipes(controller.signal)
        setRecipes(data)
      } catch (caughtError) {
        if (controller.signal.aborted) {
          return
        }

        const message =
          caughtError instanceof Error
            ? caughtError.message
            : 'Unable to load recipes'

        setError(message)
      }
    }

    void loadRecipes()

    return () => controller.abort()
  }, [])

  function openRecipe(recipe: RecipeCardDto) {
    lastFocusedElement.current = document.activeElement as HTMLElement | null
    setSelectedRecipe(recipe)
  }

  function closeRecipe() {
    const elementToRestore = lastFocusedElement.current
    setSelectedRecipe(null)
    window.requestAnimationFrame(() => elementToRestore?.focus())
  }

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
          <RecipeCard
            key={recipe.recipe_id}
            recipe={recipe}
            onOpen={() => openRecipe(recipe)}
          />
        ))}
      </section>

      {selectedRecipe && (
        <RecipeMainView recipe={selectedRecipe} onClose={closeRecipe} />
      )}
    </main>
  )
}

export default App
