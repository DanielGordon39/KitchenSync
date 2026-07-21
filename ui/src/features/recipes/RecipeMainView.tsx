import {
  type DragEvent,
  type FormEvent,
  type KeyboardEvent,
  useEffect,
  useRef,
  useState,
} from 'react'

import tomatoPlaceholder from '../../assets/recipes/tomato-placeholder.png'
import {
  addRecipeToCookbook,
  getRecipeDetail,
  updateCookbookEntry,
  updateRecipe,
} from '../../lib/api/recipes'
import type {
  CookbookDetailDto,
  RecipeCardDto,
  RecipeDetailDto,
} from '../../lib/api/recipe-types'
import { RecipeIngredientEditor } from './RecipeIngredientEditor'

type RecipeMainViewProps = {
  recipe: RecipeCardDto
  view: 'global' | 'cookbook'
  onClose: () => void
  onChanged: () => void
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

      {detail.recipe.notes.length > 0 && (
        <section
          className="recipe-main-view__recipe-notes"
          aria-labelledby="recipe-notes-heading"
        >
          <h2 id="recipe-notes-heading">Recipe notes</h2>
          <ul>
            {detail.recipe.notes.map((note, index) => (
              <li key={`${index}-${note}`}>{note}</li>
            ))}
          </ul>
        </section>
      )}
    </>
  )
}

function CookbookPanel({
  recipeId,
  cookbook,
  onSaved,
}: {
  recipeId: string
  cookbook: CookbookDetailDto
  onSaved: (cookbook: CookbookDetailDto) => void
}) {
  const [favorite, setFavorite] = useState(cookbook.favorite)
  const [rating, setRating] = useState(
    cookbook.rating === null ? '' : String(cookbook.rating),
  )
  const [notes, setNotes] = useState(cookbook.notes ?? '')
  const [isSaving, setIsSaving] = useState(false)
  const [error, setError] = useState<string | null>(null)

  async function save(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    setIsSaving(true)
    setError(null)
    try {
      const saved = await updateCookbookEntry(recipeId, {
        favorite,
        rating: rating ? Number(rating) : null,
        notes: notes.trim() || null,
      })
      onSaved(saved)
    } catch (caughtError) {
      setError(
        caughtError instanceof Error
          ? caughtError.message
          : 'Unable to save Cookbook details',
      )
    } finally {
      setIsSaving(false)
    }
  }

  return (
    <form className="cookbook-panel" onSubmit={save}>
      <div className="cookbook-panel__heading">
        <div>
          <p className="recipe-main-view__eyebrow">Cookbook</p>
          <h2>Notebook details</h2>
        </div>
        <button type="submit" disabled={isSaving}>
          {isSaving ? 'Saving…' : 'Save details'}
        </button>
      </div>

      <div className="cookbook-panel__fields">
        <label className="cookbook-panel__favorite">
          <input
            type="checkbox"
            checked={favorite}
            onChange={(event) => setFavorite(event.target.checked)}
          />
          Favorite
        </label>

        <label>
          Rating
          <select value={rating} onChange={(event) => setRating(event.target.value)}>
            <option value="">Not rated</option>
            {[1, 2, 3, 4, 5].map((value) => (
              <option key={value} value={value}>
                {value} / 5
              </option>
            ))}
          </select>
        </label>

        <label className="cookbook-panel__notes">
          Personal notes
          <textarea
            value={notes}
            onChange={(event) => setNotes(event.target.value)}
            rows={3}
            placeholder="Substitutions, tweaks, or what to try next time"
          />
        </label>
      </div>
      {error && <p role="alert">{error}</p>}
    </form>
  )
}

type RecipeEditForm = {
  title: string
  description: string
  servings: string
  time: string
  tags: string
  ingredients: string[]
  steps: string[]
  notes: string
}

function moveItem(items: string[], index: number, direction: -1 | 1) {
  const target = index + direction
  if (target < 0 || target >= items.length) return items
  const moved = [...items]
  ;[moved[index], moved[target]] = [moved[target], moved[index]]
  return moved
}

function moveItemTo(items: string[], source: number, target: number) {
  if (source === target || source < 0 || target < 0) return items
  if (source >= items.length || target >= items.length) return items
  const moved = [...items]
  const [item] = moved.splice(source, 1)
  moved.splice(target, 0, item)
  return moved
}

function RecipeEditor({
  detail,
  onCancel,
  onSaved,
}: {
  detail: RecipeDetailDto
  onCancel: () => void
  onSaved: (detail: RecipeDetailDto) => void
}) {
  const [form, setForm] = useState<RecipeEditForm>({
    title: detail.recipe.title,
    description: detail.recipe.description ?? '',
    servings:
      detail.recipe.servings === null ? '' : String(detail.recipe.servings),
    time:
      detail.recipe.time_estimate_minutes === null
        ? ''
        : String(detail.recipe.time_estimate_minutes),
    tags: detail.recipe.tags.join(', '),
    ingredients: detail.ingredients.map((ingredient) => ingredient.raw_text),
    steps: detail.steps.map((step) => step.text),
    notes: detail.recipe.notes.join('\n'),
  })
  const [isSaving, setIsSaving] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [draggedStepIndex, setDraggedStepIndex] = useState<number | null>(null)
  const [dropTargetStepIndex, setDropTargetStepIndex] = useState<number | null>(
    null,
  )

  function updateStep(index: number, value: string) {
    setForm((current) => ({
      ...current,
      steps: current.steps.map((step, stepIndex) =>
        stepIndex === index ? value : step,
      ),
    }))
  }

  function startStepDragging(
    event: DragEvent<HTMLButtonElement>,
    index: number,
  ) {
    event.dataTransfer.effectAllowed = 'move'
    event.dataTransfer.setData('text/plain', String(index))
    setDraggedStepIndex(index)
  }

  function dropStep(event: DragEvent<HTMLElement>, target: number) {
    event.preventDefault()
    const transferredIndex = event.dataTransfer.getData('text/plain')
    const source =
      draggedStepIndex ??
      (transferredIndex ? Number(transferredIndex) : null)
    if (source !== null) {
      setForm((current) => ({
        ...current,
        steps: moveItemTo(current.steps, source, target),
      }))
    }
    setDraggedStepIndex(null)
    setDropTargetStepIndex(null)
  }

  function reorderStepWithKeyboard(
    event: KeyboardEvent<HTMLButtonElement>,
    index: number,
  ) {
    if (event.key !== 'ArrowUp' && event.key !== 'ArrowDown') return
    event.preventDefault()
    setForm((current) => ({
      ...current,
      steps: moveItem(
        current.steps,
        index,
        event.key === 'ArrowUp' ? -1 : 1,
      ),
    }))
  }

  async function save(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    setIsSaving(true)
    setError(null)
    try {
      const saved = await updateRecipe(detail.recipe.recipe_id, {
        title: form.title,
        description: form.description.trim() || null,
        servings: form.servings ? Number(form.servings) : null,
        time_estimate_minutes: form.time ? Number(form.time) : null,
        tags: form.tags.split(/[\s,]+/).filter(Boolean),
        ingredients: form.ingredients.map((line) => line.trim()).filter(Boolean),
        steps: form.steps.map((step) => step.trim()).filter(Boolean),
        notes: form.notes
          .split('\n')
          .map((line) => line.trim())
          .filter(Boolean),
      })
      onSaved(saved)
    } catch (caughtError) {
      setError(
        caughtError instanceof Error
          ? caughtError.message
          : 'Unable to save recipe',
      )
    } finally {
      setIsSaving(false)
    }
  }

  return (
    <form className="recipe-editor" onSubmit={save}>
      <div className="recipe-editor__heading">
        <div>
          <p className="recipe-main-view__eyebrow">Editing recipe</p>
          <h1 id="recipe-main-view-title">Edit {detail.recipe.title}</h1>
        </div>
        <div className="recipe-editor__actions">
          <button type="button" onClick={onCancel} disabled={isSaving}>
            Cancel
          </button>
          <button type="submit" disabled={isSaving}>
            {isSaving ? 'Saving…' : 'Save recipe'}
          </button>
        </div>
      </div>

      {error && <p role="alert">{error}</p>}

      <div className="recipe-editor__fields">
        <label>
          Title
          <input
            required
            maxLength={200}
            value={form.title}
            onChange={(event) =>
              setForm((current) => ({ ...current, title: event.target.value }))
            }
          />
        </label>

        <label className="recipe-editor__wide">
          Description
          <textarea
            rows={3}
            value={form.description}
            onChange={(event) =>
              setForm((current) => ({
                ...current,
                description: event.target.value,
              }))
            }
          />
        </label>

        <label>
          Servings
          <input
            type="number"
            min="1"
            value={form.servings}
            onChange={(event) =>
              setForm((current) => ({ ...current, servings: event.target.value }))
            }
          />
        </label>

        <label>
          Total time (minutes)
          <input
            type="number"
            min="1"
            value={form.time}
            onChange={(event) =>
              setForm((current) => ({ ...current, time: event.target.value }))
            }
          />
        </label>

        <label className="recipe-editor__wide">
          Tags
          <input
            value={form.tags}
            onChange={(event) =>
              setForm((current) => ({ ...current, tags: event.target.value }))
            }
            placeholder="dinner, italian, vegetarian"
          />
        </label>

        <RecipeIngredientEditor
          initialLines={detail.ingredients.map(
            (ingredient) => ingredient.raw_text,
          )}
          onChange={(ingredients) =>
            setForm((current) => ({ ...current, ingredients }))
          }
        />

        <fieldset className="recipe-editor__steps recipe-editor__wide">
          <legend>Steps</legend>
          <ol className="recipe-editor__step-list">
            {form.steps.map((step, index) => (
              <li
                className={`recipe-editor__step${
                  dropTargetStepIndex === index ? ' is-drop-target' : ''
                }${draggedStepIndex === index ? ' is-dragging' : ''}`}
                key={index}
                onDragOver={(event) => {
                  event.preventDefault()
                  event.dataTransfer.dropEffect = 'move'
                  if (draggedStepIndex !== index) setDropTargetStepIndex(index)
                }}
                onDrop={(event) => dropStep(event, index)}
              >
                <button
                  type="button"
                  className="recipe-editor__step-drag-handle"
                  draggable
                  aria-label={`Drag step ${index + 1}; use arrow keys to reorder`}
                  title="Drag to reorder; arrow keys also work"
                  onDragStart={(event) => startStepDragging(event, index)}
                  onDragEnd={() => {
                    setDraggedStepIndex(null)
                    setDropTargetStepIndex(null)
                  }}
                  onKeyDown={(event) => reorderStepWithKeyboard(event, index)}
                >
                  <span aria-hidden="true">☰</span>
                </button>

                <textarea
                  rows={3}
                  aria-label={`Step ${index + 1}`}
                  value={step}
                  onChange={(event) => updateStep(index, event.target.value)}
                />

                <div className="recipe-editor__step-controls">
                  <button
                    type="button"
                    aria-label={`Remove step ${index + 1}`}
                    onClick={() =>
                      setForm((current) => ({
                        ...current,
                        steps: current.steps.filter(
                          (_, stepIndex) => stepIndex !== index,
                        ),
                      }))
                    }
                  >
                    Remove
                  </button>
                </div>
              </li>
            ))}
          </ol>
          <button
            type="button"
            onClick={() =>
              setForm((current) => ({
                ...current,
                steps: [...current.steps, ''],
              }))
            }
          >
            Add step
          </button>
        </fieldset>

        <label className="recipe-editor__wide">
          Recipe notes
          <textarea
            rows={4}
            value={form.notes}
            onChange={(event) =>
              setForm((current) => ({ ...current, notes: event.target.value }))
            }
          />
          <small>Use one note per line.</small>
        </label>
      </div>
    </form>
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

export function RecipeMainView({
  recipe,
  view,
  onClose,
  onChanged,
}: RecipeMainViewProps) {
  const dialogRef = useRef<HTMLDialogElement>(null)
  const [detail, setDetail] = useState<RecipeDetailDto | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [requestVersion, setRequestVersion] = useState(0)
  const [isEditing, setIsEditing] = useState(false)
  const [isAdding, setIsAdding] = useState(false)

  useEffect(() => {
    const dialog = dialogRef.current
    if (dialog && !dialog.open) dialog.showModal()
    return () => {
      if (dialog?.open) dialog.close()
    }
  }, [])

  useEffect(() => {
    const controller = new AbortController()
    setDetail(null)
    setError(null)

    getRecipeDetail(recipe.recipe_id, controller.signal)
      .then(setDetail)
      .catch((caughtError: unknown) => {
        if (controller.signal.aborted) return
        setError(
          caughtError instanceof Error
            ? caughtError.message
            : 'Unable to load recipe details',
        )
      })

    return () => controller.abort()
  }, [recipe.recipe_id, requestVersion])

  function requestClose() {
    if (isEditing && !window.confirm('Discard your unsaved recipe changes?')) return
    onClose()
  }

  async function addToCookbook() {
    setIsAdding(true)
    setError(null)
    try {
      const cookbook = await addRecipeToCookbook(recipe.recipe_id)
      setDetail((current) => (current ? { ...current, cookbook } : current))
      onChanged()
    } catch (caughtError) {
      setError(
        caughtError instanceof Error
          ? caughtError.message
          : 'Unable to add recipe to Cookbook',
      )
    } finally {
      setIsAdding(false)
    }
  }

  const title = detail?.recipe.title ?? recipe.title
  const description = detail?.recipe.description ?? recipe.description

  return (
    <dialog
      ref={dialogRef}
      className="recipe-main-view"
      aria-labelledby="recipe-main-view-title"
      onCancel={(event) => {
        event.preventDefault()
        requestClose()
      }}
    >
      <div className="recipe-main-view__surface">
        <div className="recipe-main-view__topbar">
          {detail && !isEditing && (
            <>
              {view === 'global' && detail.cookbook === null && (
                <button
                  type="button"
                  className="recipe-main-view__action"
                  onClick={addToCookbook}
                  disabled={isAdding}
                >
                  {isAdding ? 'Adding…' : 'Add to Cookbook'}
                </button>
              )}
              <button
                type="button"
                className="recipe-main-view__action"
                onClick={() => setIsEditing(true)}
              >
                Edit recipe
              </button>
            </>
          )}
          <button
            type="button"
            className="recipe-main-view__close"
            onClick={requestClose}
            aria-label="Close recipe"
          >
            <span aria-hidden="true">×</span>
          </button>
        </div>

        <article className="recipe-main-view__content">
          {detail && isEditing ? (
            <RecipeEditor
              detail={detail}
              onCancel={() => setIsEditing(false)}
              onSaved={(saved) => {
                setDetail(saved)
                setIsEditing(false)
                onChanged()
              }}
            />
          ) : (
            <>
              <header className="recipe-main-view__hero">
                <img
                  src={detail?.recipe.image_url ?? recipe.image_url ?? tomatoPlaceholder}
                  alt=""
                  className="recipe-main-view__image"
                />
                <div>
                  <p className="recipe-main-view__eyebrow">Recipe</p>
                  <h1 id="recipe-main-view-title">{title}</h1>
                  {description && <p>{description}</p>}
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
                <>
                  {view === 'cookbook' && detail.cookbook && (
                    <CookbookPanel
                      recipeId={recipe.recipe_id}
                      cookbook={detail.cookbook}
                      onSaved={(cookbook) => {
                        setDetail((current) =>
                          current ? { ...current, cookbook } : current,
                        )
                        onChanged()
                      }}
                    />
                  )}
                  <RecipeDetailContent detail={detail} />
                </>
              ) : (
                <RecipeDetailLoading />
              )}
            </>
          )}
        </article>
      </div>
    </dialog>
  )
}
