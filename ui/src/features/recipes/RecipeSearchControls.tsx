import { useMemo, useState } from 'react'
import type { KeyboardEvent } from 'react'
import type { RecipeTagDto } from '../../lib/api/recipe-types'

export type RecipeFilters = {
  meals: string[]
  cuisines: string[]
  diets: string[]
}

type FilterOption = {
  slug: string
  label: string
}

type FilterKey = keyof RecipeFilters

const FILTER_OPTIONS: Record<FilterKey, readonly FilterOption[]> = {
  meals: [
    { slug: 'breakfast', label: 'Breakfast' },
    { slug: 'brunch', label: 'Brunch' },
    { slug: 'lunch', label: 'Lunch' },
    { slug: 'dinner', label: 'Dinner' },
    { slug: 'dessert', label: 'Dessert' },
    { slug: 'snack', label: 'Snack' },
  ],
  cuisines: [
    { slug: 'american', label: 'American' },
    { slug: 'italian', label: 'Italian' },
    { slug: 'french', label: 'French' },
    { slug: 'mexican', label: 'Mexican' },
    { slug: 'indian', label: 'Indian' },
    { slug: 'chinese', label: 'Chinese' },
    { slug: 'japanese', label: 'Japanese' },
    { slug: 'korean', label: 'Korean' },
    { slug: 'thai', label: 'Thai' },
    { slug: 'mediterranean', label: 'Mediterranean' },
    { slug: 'greek', label: 'Greek' },
    { slug: 'spanish', label: 'Spanish' },
    { slug: 'vietnamese', label: 'Vietnamese' },
    { slug: 'middle-eastern', label: 'Middle Eastern' },
    { slug: 'fusion', label: 'Fusion' },
  ],
  diets: [
    { slug: 'vegetarian', label: 'Vegetarian' },
    { slug: 'vegan', label: 'Vegan' },
    { slug: 'gluten-free', label: 'Gluten-free' },
    { slug: 'dairy-free', label: 'Dairy-free' },
    { slug: 'low-carb', label: 'Low-carb' },
    { slug: 'low-calorie', label: 'Low-calorie' },
    { slug: 'low-fat', label: 'Low-fat' },
    { slug: 'high-protein', label: 'High-protein' },
    { slug: 'high-fibre', label: 'High-fibre' },
    { slug: 'keto', label: 'Keto' },
    { slug: 'pescatarian', label: 'Pescatarian' },
  ],
}

const FILTER_LABELS = new Map(
  Object.values(FILTER_OPTIONS)
    .flat()
    .map((option) => [option.slug, option.label]),
)

function activeTagPrefix(value: string) {
  return value.match(/(^|\s)#([a-z0-9-]*)$/i)?.[2].toLowerCase() ?? null
}

function completeActiveTag(value: string, tag: string) {
  const match = value.match(/(^|\s)#([a-z0-9-]*)$/i)
  if (!match || match.index === undefined) return value

  const tagStart = match.index + match[1].length
  return `${value.slice(0, tagStart)}#${tag} `
}

function FilterGroup({
  title,
  hint,
  filterKey,
  options,
  selected,
  tagCounts,
  onToggle,
}: {
  title: string
  hint: string
  filterKey: FilterKey
  options: readonly FilterOption[]
  selected: string[]
  tagCounts: Map<string, number>
  onToggle: (filterKey: FilterKey, slug: string) => void
}) {
  const availableOptions = options.filter((option) => tagCounts.has(option.slug))
  if (!availableOptions.length) return null

  return (
    <fieldset className="recipe-filter-group">
      <legend>{title}</legend>
      <p>{hint}</p>
      {availableOptions.map((option) => (
        <label key={option.slug}>
          <input
            type="checkbox"
            checked={selected.includes(option.slug)}
            onChange={() => onToggle(filterKey, option.slug)}
          />
          <span>{option.label}</span>
          <small>{tagCounts.get(option.slug)}</small>
        </label>
      ))}
    </fieldset>
  )
}

export function RecipeSearchControls({
  value,
  onChange,
  tags,
  tagError,
  filters,
  onFiltersChange,
}: {
  value: string
  onChange: (value: string) => void
  tags: RecipeTagDto[]
  tagError: string | null
  filters: RecipeFilters
  onFiltersChange: (filters: RecipeFilters) => void
}) {
  const [suggestionsOpen, setSuggestionsOpen] = useState(false)
  const [activeSuggestionIndex, setActiveSuggestionIndex] = useState(0)
  const prefix = activeTagPrefix(value)
  const tagCounts = useMemo(
    () => new Map(tags.map((tag) => [tag.tag_slug, tag.recipe_count])),
    [tags],
  )
  const suggestions = useMemo(() => {
    if (prefix === null) return []

    return tags
      .filter((tag) => tag.tag_slug.startsWith(prefix))
      .sort(
        (left, right) =>
          Number(right.tag_slug === prefix) - Number(left.tag_slug === prefix) ||
          right.recipe_count - left.recipe_count ||
          left.tag_slug.localeCompare(right.tag_slug),
      )
      .slice(0, 8)
  }, [prefix, tags])
  const showSuggestions = suggestionsOpen && suggestions.length > 0
  const activeIndex = Math.min(activeSuggestionIndex, suggestions.length - 1)
  const activeSuggestion = suggestions[activeIndex]
  const activeFilterCount = Object.values(filters).flat().length

  function updateValue(nextValue: string) {
    setActiveSuggestionIndex(0)
    setSuggestionsOpen(true)
    onChange(nextValue)
  }

  function chooseSuggestion(tag: string) {
    onChange(completeActiveTag(value, tag))
    setSuggestionsOpen(false)
    setActiveSuggestionIndex(0)
  }

  function handleSearchKeyDown(event: KeyboardEvent<HTMLInputElement>) {
    if (!showSuggestions) return

    if (event.key === 'ArrowDown') {
      event.preventDefault()
      setActiveSuggestionIndex((index) => (index + 1) % suggestions.length)
    } else if (event.key === 'ArrowUp') {
      event.preventDefault()
      setActiveSuggestionIndex(
        (index) => (index - 1 + suggestions.length) % suggestions.length,
      )
    } else if (event.key === 'Enter' && activeSuggestion) {
      event.preventDefault()
      chooseSuggestion(activeSuggestion.tag_slug)
    } else if (event.key === 'Escape') {
      setSuggestionsOpen(false)
    }
  }

  function toggleFilter(filterKey: FilterKey, slug: string) {
    const selected = filters[filterKey]
    const nextSelected = selected.includes(slug)
      ? selected.filter((value) => value !== slug)
      : [...selected, slug]
    onFiltersChange({ ...filters, [filterKey]: nextSelected })
  }

  function removeFilter(filterKey: FilterKey, slug: string) {
    onFiltersChange({
      ...filters,
      [filterKey]: filters[filterKey].filter((value) => value !== slug),
    })
  }

  return (
    <section className="recipe-search" aria-label="Find recipes">
      <div className="recipe-search__toolbar">
        <div
          className="recipe-search__input-wrap"
          onBlur={(event) => {
            if (!event.currentTarget.contains(event.relatedTarget as Node | null)) {
              setSuggestionsOpen(false)
            }
          }}
        >
          <label className="visually-hidden" htmlFor="recipe-search-input">
            Search recipes
          </label>
          <input
            id="recipe-search-input"
            type="search"
            role="combobox"
            autoComplete="off"
            placeholder="Search recipes or type # for tags"
            value={value}
            aria-autocomplete="list"
            aria-expanded={showSuggestions}
            aria-controls="recipe-tag-suggestions"
            aria-activedescendant={
              showSuggestions && activeSuggestion
                ? `recipe-tag-${activeSuggestion.tag_slug}`
                : undefined
            }
            onChange={(event) => updateValue(event.target.value)}
            onFocus={() => setSuggestionsOpen(true)}
            onKeyDown={handleSearchKeyDown}
          />
          {value && (
            <button
              type="button"
              className="recipe-search__clear"
              aria-label="Clear search"
              onClick={() => updateValue('')}
            >
              ×
            </button>
          )}

          {showSuggestions && (
            <ul
              id="recipe-tag-suggestions"
              className="recipe-search__suggestions"
              role="listbox"
              aria-label="Recipe tags"
            >
              {suggestions.map((tag, index) => (
                <li
                  id={`recipe-tag-${tag.tag_slug}`}
                  key={tag.tag_slug}
                  role="option"
                  aria-selected={index === activeIndex}
                >
                  <button
                    type="button"
                    tabIndex={-1}
                    onMouseDown={(event) => event.preventDefault()}
                    onClick={() => chooseSuggestion(tag.tag_slug)}
                  >
                    <span>#{tag.tag_slug}</span>
                    <small>{tag.recipe_count}</small>
                  </button>
                </li>
              ))}
            </ul>
          )}
        </div>

        <details className="recipe-filters">
          <summary>
            Filters
            {activeFilterCount > 0 && <span>{activeFilterCount}</span>}
          </summary>
          <div className="recipe-filters__menu">
            <div className="recipe-filters__heading">
              <strong>Filter recipes</strong>
              {activeFilterCount > 0 && (
                <button
                  type="button"
                  onClick={() =>
                    onFiltersChange({ meals: [], cuisines: [], diets: [] })
                  }
                >
                  Clear all
                </button>
              )}
            </div>
            <FilterGroup
              title="Meal"
              hint="Match any selected"
              filterKey="meals"
              options={FILTER_OPTIONS.meals}
              selected={filters.meals}
              tagCounts={tagCounts}
              onToggle={toggleFilter}
            />
            <FilterGroup
              title="Cuisine and style"
              hint="Match any selected"
              filterKey="cuisines"
              options={FILTER_OPTIONS.cuisines}
              selected={filters.cuisines}
              tagCounts={tagCounts}
              onToggle={toggleFilter}
            />
            <FilterGroup
              title="Diet"
              hint="Match every selected"
              filterKey="diets"
              options={FILTER_OPTIONS.diets}
              selected={filters.diets}
              tagCounts={tagCounts}
              onToggle={toggleFilter}
            />
            <p className="recipe-filters__tag-help">
              Type <code>#</code> in search for any tag.
            </p>
          </div>
        </details>
      </div>

      {tagError && <p className="recipe-search__tag-error">{tagError}</p>}

      {activeFilterCount > 0 && (
        <div className="recipe-search__chips" aria-label="Active filters">
          {(Object.keys(filters) as FilterKey[]).flatMap((filterKey) =>
            filters[filterKey].map((slug) => (
              <button
                key={`${filterKey}-${slug}`}
                type="button"
                aria-label={`Remove ${FILTER_LABELS.get(slug) ?? slug} filter`}
                onClick={() => removeFilter(filterKey, slug)}
              >
                {FILTER_LABELS.get(slug) ?? slug} <span>×</span>
              </button>
            )),
          )}
        </div>
      )}
    </section>
  )
}
