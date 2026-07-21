import { useEffect, useMemo, useRef, useState } from 'react'
import tomatoPlaceholder from './assets/recipes/tomato-placeholder.png'
import './App.css'
import { RecipeMainView } from './features/recipes/RecipeMainView'
import {
  RecipeSearchControls,
  type RecipeFilters,
} from './features/recipes/RecipeSearchControls'
import { listRecipes, listRecipeTags } from './lib/api/recipes'
import type {
  RecipeCardDto,
  RecipeTagDto,
} from './lib/api/recipe-types'

function RecipeCard({
  recipe,
  view,
  onOpen,
}: {
  recipe: RecipeCardDto
  view: 'global' | 'cookbook'
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
        <p className="recipe-card__description">{recipe.description}</p>
      )}

      {view === 'cookbook' && recipe.cookbook && (
        <div className="recipe-card__cookbook" aria-label="Cookbook details">
          {recipe.cookbook.favorite && (
            <span aria-label="Favorite" title="Favorite">
              ♥
            </span>
          )}
          <span>
            {recipe.cookbook.rating === null
              ? 'Not rated'
              : `★ ${recipe.cookbook.rating}/5`}
          </span>
        </div>
      )}
    </button>
  )
}

function RecipeGrid({
  recipes,
  label,
  view,
  onOpen,
}: {
  recipes: RecipeCardDto[]
  label: string
  view: 'global' | 'cookbook'
  onOpen: (recipe: RecipeCardDto) => void
}) {
  return (
    <section className="recipe-grid" aria-label={label}>
      {recipes.map((recipe) => (
        <RecipeCard
          key={recipe.recipe_id}
          recipe={recipe}
          view={view}
          onOpen={() => onOpen(recipe)}
        />
      ))}
    </section>
  )
}

function parseRecipeSearch(value: string, validTags: Set<string>) {
  const trailingTag = value.match(/(^|\s)#([a-z0-9-]+)$/i)
  const exactTags = new Set<string>()

  for (const match of value.matchAll(/(^|\s)#([a-z0-9-]+)/gi)) {
    const slug = match[2].toLowerCase()
    const isIncompleteTrailingTag =
      trailingTag?.index === match.index && !validTags.has(slug)
    if (!isIncompleteTrailingTag) exactTags.add(slug)
  }

  return {
    query: value
      .replace(/(^|\s)#[a-z0-9-]*/gi, ' ')
      .replace(/\s+/g, ' ')
      .trim(),
    exactTags: [...exactTags],
  }
}

function App() {
  const [activeView, setActiveView] = useState<'global' | 'cookbook'>('global')
  const [recipes, setRecipes] = useState<RecipeCardDto[] | null>(null)
  const [availableTags, setAvailableTags] = useState<RecipeTagDto[]>([])
  const [searchValue, setSearchValue] = useState('')
  const [filters, setFilters] = useState<RecipeFilters>({
    meals: [],
    cuisines: [],
    diets: [],
  })
  const [error, setError] = useState<string | null>(null)
  const [tagError, setTagError] = useState<string | null>(null)
  const [isSearching, setIsSearching] = useState(false)
  const [resolvedExactTagCount, setResolvedExactTagCount] = useState(0)
  const [refreshVersion, setRefreshVersion] = useState(0)
  const [selectedRecipe, setSelectedRecipe] = useState<RecipeCardDto | null>(
    null,
  )
  const lastFocusedElement = useRef<HTMLElement | null>(null)
  const validTags = useMemo(
    () => new Set(availableTags.map((tag) => tag.tag_slug)),
    [availableTags],
  )
  const search = useMemo(
    () => parseRecipeSearch(searchValue, validTags),
    [searchValue, validTags],
  )
  const activeFilterCount = Object.values(filters).flat().length

  useEffect(() => {
    const controller = new AbortController()

    void listRecipeTags(activeView, controller.signal)
      .then((tags) => {
        setAvailableTags(tags)
        setTagError(null)
      })
      .catch((caughtError) => {
        if (controller.signal.aborted) return
        setTagError(
          caughtError instanceof Error
            ? caughtError.message
            : 'Tag suggestions are unavailable.',
        )
      })

    return () => controller.abort()
  }, [activeView, refreshVersion])

  useEffect(() => {
    const controller = new AbortController()
    const delay = searchValue || activeFilterCount ? 200 : 0
    setIsSearching(true)

    const timeout = window.setTimeout(() => {
      void listRecipes({
        query: search.query,
        exactTags: search.exactTags,
        meals: filters.meals,
        cuisines: filters.cuisines,
        diets: filters.diets,
        scope: activeView,
        signal: controller.signal,
      })
        .then((data) => {
          setRecipes(data)
          setResolvedExactTagCount(search.exactTags.length)
          setError(null)
        })
        .catch((caughtError) => {
          if (controller.signal.aborted) return
          setError(
            caughtError instanceof Error
              ? caughtError.message
              : 'Unable to load recipes',
          )
        })
        .finally(() => {
          if (!controller.signal.aborted) setIsSearching(false)
        })
    }, delay)

    return () => {
      window.clearTimeout(timeout)
      controller.abort()
    }
  }, [activeFilterCount, activeView, filters, refreshVersion, search, searchValue])

  function openRecipe(recipe: RecipeCardDto) {
    lastFocusedElement.current = document.activeElement as HTMLElement | null
    setSelectedRecipe(recipe)
  }

  function closeRecipe() {
    const elementToRestore = lastFocusedElement.current
    setSelectedRecipe(null)
    window.requestAnimationFrame(() => elementToRestore?.focus())
  }

  function refreshRecipes() {
    setRefreshVersion((version) => version + 1)
  }

  if (error && recipes === null) {
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

  const allTagMatches = recipes.filter((recipe) => recipe.tag_match !== 'some')
  const someTagMatches = recipes.filter((recipe) => recipe.tag_match === 'some')
  const showTagTiers = resolvedExactTagCount > 1

  return (
    <main>
      <header className="app-header">
        <p className="app-header__brand">KitchenSync</p>
        <nav
          className="app-tabs"
          aria-label="Recipe collections"
          role="tablist"
          onKeyDown={(event) => {
            if (event.key !== 'ArrowLeft' && event.key !== 'ArrowRight') return
            event.preventDefault()
            const nextView =
              event.key === 'ArrowRight'
                ? activeView === 'global'
                  ? 'cookbook'
                  : 'global'
                : activeView === 'cookbook'
                  ? 'global'
                  : 'cookbook'
            setActiveView(nextView)
            const tabs = event.currentTarget.querySelectorAll<HTMLButtonElement>(
              '[role="tab"]',
            )
            tabs[nextView === 'global' ? 0 : 1]?.focus()
          }}
        >
          <button
            type="button"
            id="global-recipes-tab"
            role="tab"
            aria-selected={activeView === 'global'}
            aria-controls="recipe-browser"
            tabIndex={activeView === 'global' ? 0 : -1}
            onClick={() => setActiveView('global')}
          >
            Global Recipes
          </button>
          <button
            type="button"
            id="cookbook-tab"
            role="tab"
            aria-selected={activeView === 'cookbook'}
            aria-controls="recipe-browser"
            tabIndex={activeView === 'cookbook' ? 0 : -1}
            onClick={() => setActiveView('cookbook')}
          >
            Cookbook
          </button>
        </nav>
      </header>

      <section
        id="recipe-browser"
        role="tabpanel"
        aria-labelledby={
          activeView === 'global' ? 'global-recipes-tab' : 'cookbook-tab'
        }
      >
        <RecipeSearchControls
          value={searchValue}
          onChange={setSearchValue}
          tags={availableTags}
          tagError={tagError}
          filters={filters}
          onFiltersChange={setFilters}
        />

        <div className="recipe-results__summary" aria-live="polite">
          {isSearching
            ? 'Updating recipes…'
            : `${recipes.length} ${recipes.length === 1 ? 'recipe' : 'recipes'}`}
        </div>

        {error && <p role="alert">Could not update recipes: {error}</p>}

        {!recipes.length ? (
          <p className="recipe-results__empty">
            {activeView === 'cookbook' && !searchValue && !activeFilterCount
              ? 'Your Cookbook is empty. Add a recipe from Global Recipes.'
              : 'No recipes found. Try another search or clear a filter.'}
          </p>
        ) : showTagTiers ? (
          <div className="recipe-results__groups">
            <section aria-labelledby="all-tag-matches">
              <h2 id="all-tag-matches">Matches all tags</h2>
              {allTagMatches.length ? (
                <RecipeGrid
                  recipes={allTagMatches}
                  label="Recipes matching all tags"
                  view={activeView}
                  onOpen={openRecipe}
                />
              ) : (
                <p>No recipes match every requested tag.</p>
              )}
            </section>

            {someTagMatches.length > 0 && (
              <section aria-labelledby="some-tag-matches">
                <h2 id="some-tag-matches">Matches some tags</h2>
                <RecipeGrid
                  recipes={someTagMatches}
                  label="Recipes matching some tags"
                  view={activeView}
                  onOpen={openRecipe}
                />
              </section>
            )}
          </div>
        ) : (
          <RecipeGrid
            recipes={recipes}
            label={activeView === 'global' ? 'Global Recipes' : 'Cookbook'}
            view={activeView}
            onOpen={openRecipe}
          />
        )}
      </section>

      {selectedRecipe && (
        <RecipeMainView
          recipe={selectedRecipe}
          view={activeView}
          onClose={closeRecipe}
          onChanged={refreshRecipes}
        />
      )}
    </main>
  )
}

export default App
