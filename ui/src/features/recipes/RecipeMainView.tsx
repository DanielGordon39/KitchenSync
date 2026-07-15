import { useEffect, useRef, useState } from 'react'

import tomatoPlaceholder from '../../assets/recipes/tomato-placeholder.png'
import { getRecipeDetail } from '../../lib/api/recipes'
import type {
  RecipeCardDto,
  RecipeDetailDto,
} from '../../lib/api/recipe-types'

type RecipeMainViewProps = {
  recipe: RecipeCardDto
  onClose: () => void
}

function RecipeDetailContent({ detail }: { detail: RecipeDetailDto }) {
  const sourceUrl = detail.recipe.source_url?.startsWith('http')
    ? detail.recipe.source_url
    : null

  return (
    <>
      <div className="recipe-main-view__metadata" aria-label="Recipe details">
        {detail.recipe.servings !== null && (
          <span>{detail.recipe.servings} servings</span>
        )}
        {detail.recipe.time_estimate_minutes !== null && (
          <span>{detail.recipe.time_estimate_minutes} minutes</span>
        )}
        {detail.recipe.author && <span>By {detail.recipe.author}</span>}
        {sourceUrl && (
          <a href={sourceUrl} target="_blank" rel="noreferrer">
            {detail.recipe.source_name ?? 'Original source'}
          </a>
        )}
      </div>

      {detail.recipe.tags.length > 0 && (
        <ul className="recipe-main-view__tags" aria-label="Recipe tags">
          {detail.recipe.tags.map((tag) => (
            <li key={tag}>{tag}</li>
          ))}
        </ul>
      )}

      <div className="recipe-main-view__body">
        <section aria-labelledby="recipe-ingredients-heading">
          <h2 id="recipe-ingredients-heading">Ingredients</h2>
          {detail.ingredients.length > 0 ? (
            <ul className="recipe-main-view__ingredients">
              {detail.ingredients.map((ingredient) => (
                <li key={ingredient.ingredient_order}>
                  {ingredient.raw_text}
                </li>
              ))}
            </ul>
          ) : (
            <p>No ingredients are listed for this recipe.</p>
          )}
        </section>

        <section aria-labelledby="recipe-steps-heading">
          <h2 id="recipe-steps-heading">Steps</h2>
          {detail.steps.length > 0 ? (
            <ol className="recipe-main-view__steps">
              {detail.steps.map((step) => (
                <li key={step.step_order}>{step.text}</li>
              ))}
            </ol>
          ) : (
            <p>No steps are listed for this recipe.</p>
          )}
        </section>
      </div>
    </>
  )
}

function RecipeDetailLoading() {
  return (
    <div className="recipe-main-view__loading" role="status">
      <span>Loading ingredients and steps…</span>
      <div className="recipe-main-view__skeleton" aria-hidden="true" />
      <div className="recipe-main-view__skeleton" aria-hidden="true" />
    </div>
  )
}

export function RecipeMainView({ recipe, onClose }: RecipeMainViewProps) {
  const dialogRef = useRef<HTMLDialogElement>(null)
  const [detail, setDetail] = useState<RecipeDetailDto | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [requestVersion, setRequestVersion] = useState(0)

  useEffect(() => {
    const dialog = dialogRef.current
    if (dialog && !dialog.open) {
      dialog.showModal()
    }

    return () => {
      if (dialog?.open) {
        dialog.close()
      }
    }
  }, [])

  useEffect(() => {
    const controller = new AbortController()
    setDetail(null)
    setError(null)

    getRecipeDetail(recipe.recipe_id, controller.signal)
      .then(setDetail)
      .catch((caughtError: unknown) => {
        if (controller.signal.aborted) {
          return
        }

        setError(
          caughtError instanceof Error
            ? caughtError.message
            : 'Unable to load recipe details',
        )
      })

    return () => controller.abort()
  }, [recipe.recipe_id, requestVersion])

  const title = detail?.recipe.title ?? recipe.title

  return (
    <dialog
      ref={dialogRef}
      className="recipe-main-view"
      aria-labelledby="recipe-main-view-title"
      onCancel={(event) => {
        event.preventDefault()
        onClose()
      }}
      onKeyDown={(event) => {
        if (event.key === 'Escape') {
          event.preventDefault()
          onClose()
        }
      }}
    >
      <div className="recipe-main-view__surface">
        <div className="recipe-main-view__topbar">
          <button
            type="button"
            className="recipe-main-view__close"
            onClick={onClose}
            aria-label="Close recipe"
          >
            <span aria-hidden="true">×</span>
          </button>
        </div>

        <article className="recipe-main-view__content">
          <header className="recipe-main-view__hero">
            <img
              src={recipe.image_url ?? tomatoPlaceholder}
              alt=""
              className="recipe-main-view__image"
            />
            <div>
              <p className="recipe-main-view__eyebrow">Recipe</p>
              <h1 id="recipe-main-view-title">{title}</h1>
              {recipe.description && <p>{recipe.description}</p>}
            </div>
          </header>

          {error ? (
            <div className="recipe-main-view__error" role="alert">
              <p>{error}</p>
              <button
                type="button"
                onClick={() => setRequestVersion((version) => version + 1)}
              >
                Try again
              </button>
            </div>
          ) : detail ? (
            <RecipeDetailContent detail={detail} />
          ) : (
            <RecipeDetailLoading />
          )}
        </article>
      </div>
    </dialog>
  )
}
