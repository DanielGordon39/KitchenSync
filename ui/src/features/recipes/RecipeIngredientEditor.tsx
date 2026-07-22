import {
  type DragEvent,
  type KeyboardEvent,
  useEffect,
  useRef,
  useState,
} from 'react'

import { listIngredients, parseIngredientLines } from '../../lib/api/recipes'
import type {
  IngredientCatalogItemDto,
  IngredientLineProjectionDto,
} from '../../lib/api/recipe-types'

type EditorMode = 'rich' | 'raw'
type UnitSystem = 'us' | 'metric'
type UnitKind = 'amount' | 'volume' | 'weight'

type IngredientRow = {
  id: number
  mode: EditorMode
  rawText: string
  quantityText: string
  unit: string
  ingredientName: string
  preparation: string
  dirty: boolean
  reason: string | null
  parsing: boolean
}

const MODE_STORAGE_KEY = 'kitchensync.recipeEditor.ingredientMode'
const UNIT_SYSTEM_STORAGE_KEY = 'kitchensync.recipeEditor.unitSystem'

const AMOUNT_UNITS = [
  'unit',
  'pinch',
  'dash',
  'clove',
  'slice',
  'bunch',
  'can',
  'jar',
  'package',
]

const UNIT_OPTIONS: Record<UnitKind, Record<UnitSystem, string[]>> = {
  amount: { us: AMOUNT_UNITS, metric: AMOUNT_UNITS },
  volume: {
    us: ['tsp', 'tbsp', 'fl oz', 'cup', 'pint', 'quart', 'gallon'],
    metric: ['mL', 'L'],
  },
  weight: {
    us: ['oz', 'lb'],
    metric: ['mg', 'g', 'kg'],
  },
}

let nextRowId = 0

function readModePreference(): EditorMode {
  try {
    return window.localStorage.getItem(MODE_STORAGE_KEY) === 'raw'
      ? 'raw'
      : 'rich'
  } catch {
    return 'rich'
  }
}

function readUnitSystemPreference(): UnitSystem {
  try {
    return window.localStorage.getItem(UNIT_SYSTEM_STORAGE_KEY) === 'metric'
      ? 'metric'
      : 'us'
  } catch {
    return 'us'
  }
}

function rememberPreference(key: string, value: string) {
  // TODO(accounts): move editor preferences to account settings when accounts exist.
  try {
    window.localStorage.setItem(key, value)
  } catch {
    // Raw and Rich editing still work when browser storage is unavailable.
  }
}

function createRow(rawText: string, preferredMode: EditorMode): IngredientRow {
  return {
    id: nextRowId++,
    mode: rawText.trim() ? 'raw' : preferredMode,
    rawText,
    quantityText: '',
    unit: '',
    ingredientName: '',
    preparation: '',
    dirty: false,
    reason: null,
    parsing: false,
  }
}

function applyProjection(
  row: IngredientRow,
  projection: IngredientLineProjectionDto,
): IngredientRow {
  if (!projection.safe_for_rich) {
    return {
      ...row,
      mode: 'raw',
      reason: projection.reason ?? 'This line needs Raw view.',
      parsing: false,
    }
  }

  return {
    ...row,
    mode: 'rich',
    rawText: projection.raw_text,
    quantityText: projection.quantity_text ?? '',
    unit: projection.unit ?? '',
    ingredientName: projection.ingredient_name ?? '',
    preparation: projection.preparation ?? '',
    dirty: false,
    reason: null,
    parsing: false,
  }
}

function formatRichRow(row: IngredientRow) {
  const main = [row.quantityText, row.unit, row.ingredientName]
    .map((part) => part.trim())
    .filter(Boolean)
    .join(' ')
  const preparation = row.preparation.trim()
  return preparation ? `${main}${main ? ', ' : ''}${preparation}` : main
}

function rowText(row: IngredientRow) {
  if (row.mode === 'raw' || !row.dirty) return row.rawText
  return formatRichRow(row)
}

function asRawRow(row: IngredientRow): IngredientRow {
  return {
    ...row,
    mode: 'raw',
    rawText: rowText(row),
    dirty: false,
    reason: null,
    parsing: false,
  }
}

function findIngredient(
  catalog: IngredientCatalogItemDto[],
  value: string,
) {
  const normalized = value.trim().toLocaleLowerCase()
  if (!normalized) return null
  return (
    catalog.find(
      (ingredient) =>
        ingredient.name.toLocaleLowerCase() === normalized ||
        ingredient.aliases.some(
          (alias) => alias.toLocaleLowerCase() === normalized,
        ),
    ) ?? null
  )
}

function ingredientOptions(catalog: IngredientCatalogItemDto[]) {
  const seen = new Set<string>()
  const options: { value: string; label?: string }[] = []
  for (const ingredient of catalog) {
    for (const [value, label] of [
      [ingredient.name, undefined],
      ...ingredient.aliases.map(
        (alias) => [alias, `${ingredient.name} alias`] as const,
      ),
    ] as const) {
      const key = value.toLocaleLowerCase()
      if (seen.has(key)) continue
      seen.add(key)
      options.push({ value, label })
    }
  }
  return options
}

function rowTextForSave(
  row: IngredientRow,
  catalog: IngredientCatalogItemDto[],
) {
  if (row.mode === 'raw') return row.rawText
  const match = findIngredient(catalog, row.ingredientName)
  if (
    match &&
    match.name.toLocaleLowerCase() !==
      row.ingredientName.trim().toLocaleLowerCase()
  ) {
    return formatRichRow({ ...row, ingredientName: match.name })
  }
  return rowText(row)
}

export function RecipeIngredientEditor({
  initialLines,
  onChange,
}: {
  initialLines: string[]
  onChange: (lines: string[]) => void
}) {
  const initialMode = useRef(readModePreference()).current
  const initialText = initialLines.join('\n')
  const [defaultMode, setDefaultMode] = useState<EditorMode>(initialMode)
  const [unitSystem, setUnitSystem] = useState<UnitSystem>(
    readUnitSystemPreference,
  )
  const [unitKind, setUnitKind] = useState<UnitKind>('volume')
  const [rows, setRows] = useState<IngredientRow[]>(() =>
    (initialLines.length ? initialLines : ['']).map((line) =>
      createRow(line, initialMode),
    ),
  )
  const [bulkRawText, setBulkRawText] = useState(initialText)
  const [catalog, setCatalog] = useState<IngredientCatalogItemDto[]>([])
  const [catalogLoaded, setCatalogLoaded] = useState(false)
  const [catalogError, setCatalogError] = useState<string | null>(null)
  const [parseError, setParseError] = useState<string | null>(null)
  const [toolbarMessage, setToolbarMessage] = useState<string | null>(null)
  const [isParsingAll, setIsParsingAll] = useState(false)
  const [draggedRowId, setDraggedRowId] = useState<number | null>(null)
  const [dropTargetRowId, setDropTargetRowId] = useState<number | null>(null)
  const onChangeRef = useRef(onChange)

  useEffect(() => {
    onChangeRef.current = onChange
  }, [onChange])

  useEffect(() => {
    onChangeRef.current(
      defaultMode === 'raw'
        ? bulkRawText.split('\n')
        : rows.map((row) => rowTextForSave(row, catalog)),
    )
  }, [bulkRawText, catalog, defaultMode, rows])

  useEffect(() => {
    const controller = new AbortController()

    listIngredients(controller.signal)
      .then((items) => {
        setCatalog(items)
        setCatalogLoaded(true)
      })
      .catch((caughtError: unknown) => {
        if (controller.signal.aborted) return
        setCatalogError(
          caughtError instanceof Error
            ? caughtError.message
            : 'Ingredient autocomplete is unavailable.',
        )
      })

    if (initialMode === 'rich') {
      const lines = initialText ? initialText.split('\n') : ['']
      setIsParsingAll(true)
      parseIngredientLines(lines, controller.signal)
        .then((projections) => {
          setRows((current) =>
            current.map((row, index) => {
              const projection = projections[index]
              if (!projection || row.rawText !== projection.raw_text) return row
              return applyProjection(row, projection)
            }),
          )
        })
        .catch((caughtError: unknown) => {
          if (controller.signal.aborted) return
          setParseError(
            caughtError instanceof Error
              ? caughtError.message
              : 'Rich parsing is unavailable. Raw editing still works.',
          )
        })
        .finally(() => {
          if (!controller.signal.aborted) setIsParsingAll(false)
        })
    }

    return () => controller.abort()
  }, [initialMode, initialText])

  function updateDefaultMode(mode: EditorMode) {
    if (mode === defaultMode) return
    setToolbarMessage(null)
    setParseError(null)

    if (mode === 'raw') {
      setBulkRawText(rows.map(rowText).join('\n'))
      setDefaultMode('raw')
      rememberPreference(MODE_STORAGE_KEY, 'raw')
      return
    }

    const lines = bulkRawText.split('\n')
    const nextRows = lines.map((line) => createRow(line, 'raw'))
    setIsParsingAll(true)
    parseIngredientLines(lines)
      .then((projections) => {
        setRows(
          nextRows.map((row, index) =>
            projections[index] ? applyProjection(row, projections[index]) : row,
          ),
        )
        setDefaultMode('rich')
        rememberPreference(MODE_STORAGE_KEY, 'rich')
        const exceptions = projections.filter(
          (projection) => !projection.safe_for_rich,
        ).length
        if (exceptions) {
          setToolbarMessage(
            `${exceptions} complex ingredient ${exceptions === 1 ? 'line stayed' : 'lines stayed'} in Raw view.`,
          )
        }
      })
      .catch((caughtError: unknown) => {
        setParseError(
          caughtError instanceof Error
            ? caughtError.message
            : 'Rich parsing is unavailable. Raw editing still works.',
        )
      })
      .finally(() => setIsParsingAll(false))
  }

  async function updateRowMode(row: IngredientRow, mode: EditorMode) {
    if (mode === row.mode) return
    if (mode === 'raw') {
      setRows((current) =>
        current.map((item) => (item.id === row.id ? asRawRow(item) : item)),
      )
      return
    }

    const rawText = row.rawText
    setRows((current) =>
      current.map((item) =>
        item.id === row.id ? { ...item, parsing: true, reason: null } : item,
      ),
    )
    try {
      const [projection] = await parseIngredientLines([rawText])
      setRows((current) =>
        current.map((item) => {
          if (item.id !== row.id || item.rawText !== rawText) return item
          return projection
            ? applyProjection(item, projection)
            : { ...item, parsing: false }
        }),
      )
    } catch (caughtError) {
      setRows((current) =>
        current.map((item) =>
          item.id === row.id
            ? {
                ...item,
                parsing: false,
                reason:
                  caughtError instanceof Error
                    ? caughtError.message
                    : 'Rich parsing is unavailable.',
              }
            : item,
        ),
      )
    }
  }

  function updateRichField(
    rowId: number,
    field: 'quantityText' | 'unit' | 'ingredientName' | 'preparation',
    value: string,
  ) {
    setRows((current) =>
      current.map((row) => {
        if (row.id !== rowId) return row
        const updated = {
          ...row,
          [field]: value,
          dirty: true,
          reason: null,
        } as IngredientRow
        if (field === 'ingredientName' && !updated.unit.trim()) {
          const match = findIngredient(catalog, value)
          if (match?.default_unit) updated.unit = match.default_unit
        }
        return updated
      }),
    )
  }

  function moveRow(index: number, direction: -1 | 1) {
    setRows((current) => {
      const target = index + direction
      if (target < 0 || target >= current.length) return current
      const moved = [...current]
      ;[moved[index], moved[target]] = [moved[target], moved[index]]
      return moved
    })
  }

  function moveRowTo(sourceId: number, targetId: number) {
    if (sourceId === targetId) return
    setRows((current) => {
      const sourceIndex = current.findIndex((row) => row.id === sourceId)
      const targetIndex = current.findIndex((row) => row.id === targetId)
      if (sourceIndex < 0 || targetIndex < 0) return current
      const reordered = [...current]
      const [moved] = reordered.splice(sourceIndex, 1)
      reordered.splice(targetIndex, 0, moved)
      return reordered
    })
  }

  function startDragging(event: DragEvent<HTMLButtonElement>, rowId: number) {
    event.dataTransfer.effectAllowed = 'move'
    event.dataTransfer.setData('text/plain', String(rowId))
    setDraggedRowId(rowId)
  }

  function dropRow(event: DragEvent<HTMLElement>, targetId: number) {
    event.preventDefault()
    const transferredId = event.dataTransfer.getData('text/plain')
    const sourceId = draggedRowId ?? (transferredId ? Number(transferredId) : null)
    if (sourceId !== null) moveRowTo(sourceId, targetId)
    setDraggedRowId(null)
    setDropTargetRowId(null)
  }

  function reorderWithKeyboard(
    event: KeyboardEvent<HTMLButtonElement>,
    index: number,
  ) {
    if (event.key !== 'ArrowUp' && event.key !== 'ArrowDown') return
    event.preventDefault()
    moveRow(index, event.key === 'ArrowUp' ? -1 : 1)
  }

  const catalogOptions = ingredientOptions(catalog)
  const unitOptions = UNIT_OPTIONS[unitKind][unitSystem]

  return (
    <fieldset className="recipe-ingredient-editor recipe-editor__wide">
      <legend>Ingredients</legend>
      <div className="recipe-ingredient-editor__toolbar">
        <div>
          <small>Default view</small>
          <div role="group" aria-label="Default ingredient view">
            {(['rich', 'raw'] as const).map((mode) => (
              <button
                type="button"
                key={mode}
                aria-pressed={defaultMode === mode}
                disabled={isParsingAll}
                onClick={() => updateDefaultMode(mode)}
              >
                {mode === 'rich' ? 'Rich' : 'Raw'}
              </button>
            ))}
          </div>
        </div>

        {defaultMode === 'rich' && (
          <>
            <div>
              <small>Unit system</small>
              <div role="group" aria-label="Unit suggestion system">
                {(['us', 'metric'] as const).map((system) => (
                  <button
                    type="button"
                    key={system}
                    aria-pressed={unitSystem === system}
                    onClick={() => {
                      setUnitSystem(system)
                      rememberPreference(UNIT_SYSTEM_STORAGE_KEY, system)
                    }}
                  >
                    {system === 'us' ? 'US' : 'Metric'}
                  </button>
                ))}
              </div>
            </div>

            <div>
              <small>Unit suggestions</small>
              <div role="group" aria-label="Unit suggestion category">
                {(['amount', 'volume', 'weight'] as const).map((kind) => (
                  <button
                    type="button"
                    key={kind}
                    aria-pressed={unitKind === kind}
                    onClick={() => setUnitKind(kind)}
                  >
                    {kind[0].toUpperCase() + kind.slice(1)}
                  </button>
                ))}
              </div>
            </div>
          </>
        )}
      </div>

      {toolbarMessage && <p role="status">{toolbarMessage}</p>}
      {catalogError && <p role="alert">{catalogError}</p>}
      {parseError && <p role="alert">{parseError}</p>}

      <datalist id="recipe-ingredient-options">
        {catalogOptions.map((option) => (
          <option
            key={option.value.toLocaleLowerCase()}
            value={option.value}
            label={option.label}
          />
        ))}
      </datalist>
      <datalist id="recipe-unit-options">
        {unitOptions.map((unit) => (
          <option key={unit} value={unit} />
        ))}
      </datalist>

      {defaultMode === 'raw' ? (
        <label className="recipe-ingredient-editor__bulk-raw">
          Raw ingredient text
          <textarea
            rows={Math.max(8, bulkRawText.split('\n').length)}
            value={bulkRawText}
            onChange={(event) => setBulkRawText(event.target.value)}
          />
          <small>
            One ingredient per line. This fast editor skips structure; switching
            back to Rich reparses the lines and leaves anything uncertain in Raw
            for review.
          </small>
        </label>
      ) : (
        <>
          <div
            className="recipe-ingredient-editor__column-headings"
            aria-hidden="true"
          >
            <span />
            <span />
            <div className="recipe-ingredient-editor__rich-fields">
              <span>Quantity</span>
              <span>Unit</span>
              <span>Ingredient</span>
              <span>Preparation</span>
            </div>
            <span />
          </div>
          <ol className="recipe-ingredient-editor__rows">
          {rows.map((row, index) => {
            const ingredientMatch = findIngredient(catalog, row.ingredientName)
            const hasRichValue = Boolean(
              row.quantityText.trim() ||
                row.unit.trim() ||
                row.ingredientName.trim() ||
                row.preparation.trim(),
            )
            const isNewIngredient =
              catalogLoaded &&
              Boolean(row.ingredientName.trim()) &&
              ingredientMatch === null

            return (
              <li
                className={`recipe-ingredient-editor__row${
                  dropTargetRowId === row.id ? ' is-drop-target' : ''
                }${draggedRowId === row.id ? ' is-dragging' : ''}`}
                key={row.id}
                onDragOver={(event) => {
                  event.preventDefault()
                  event.dataTransfer.dropEffect = 'move'
                  if (draggedRowId !== row.id) setDropTargetRowId(row.id)
                }}
                onDrop={(event) => dropRow(event, row.id)}
              >
                <button
                  type="button"
                  className="recipe-ingredient-editor__drag-handle"
                  draggable
                  aria-label={`Drag ingredient ${index + 1}; use arrow keys to reorder`}
                  title="Drag to reorder; arrow keys also work"
                  onDragStart={(event) => startDragging(event, row.id)}
                  onDragEnd={() => {
                    setDraggedRowId(null)
                    setDropTargetRowId(null)
                  }}
                  onKeyDown={(event) => reorderWithKeyboard(event, index)}
                >
                  <span aria-hidden="true">☰</span>
                </button>

                <div className="recipe-ingredient-editor__row-content">
                  {row.mode === 'raw' ? (
                    <label>
                      <textarea
                        aria-label={`Ingredient ${index + 1} raw text`}
                        rows={2}
                        value={row.rawText}
                        onChange={(event) =>
                          setRows((current) =>
                            current.map((item) =>
                              item.id === row.id
                                ? {
                                    ...item,
                                    rawText: event.target.value,
                                    reason: null,
                                  }
                                : item,
                            ),
                          )
                        }
                      />
                    </label>
                  ) : (
                    <div className="recipe-ingredient-editor__rich-fields">
                      <label>
                        <input
                          aria-label={`Ingredient ${index + 1} quantity`}
                          value={row.quantityText}
                          placeholder="1/2 or about 2"
                          onChange={(event) =>
                            updateRichField(
                              row.id,
                              'quantityText',
                              event.target.value,
                            )
                          }
                        />
                      </label>
                      <label>
                        <input
                          aria-label={`Ingredient ${index + 1} unit`}
                          list="recipe-unit-options"
                          value={row.unit}
                          placeholder="cup"
                          onChange={(event) =>
                            updateRichField(row.id, 'unit', event.target.value)
                          }
                        />
                      </label>
                      <label>
                        <input
                          aria-label={`Ingredient ${index + 1} name`}
                          list="recipe-ingredient-options"
                          required={hasRichValue}
                          value={row.ingredientName}
                          placeholder="Start typing an ingredient"
                          onChange={(event) =>
                            updateRichField(
                              row.id,
                              'ingredientName',
                              event.target.value,
                            )
                          }
                        />
                        {isNewIngredient && (
                          <span className="recipe-ingredient-editor__new">
                            New ingredient
                          </span>
                        )}
                        {ingredientMatch && (
                          <span className="recipe-ingredient-editor__existing">
                            Existing ingredient: {ingredientMatch.name}
                          </span>
                        )}
                      </label>
                      <label>
                        <input
                          aria-label={`Ingredient ${index + 1} preparation`}
                          value={row.preparation}
                          placeholder="diced"
                          onChange={(event) =>
                            updateRichField(
                              row.id,
                              'preparation',
                              event.target.value,
                            )
                          }
                        />
                      </label>
                    </div>
                  )}

                  {row.parsing && (
                    <small role="status">Checking this line…</small>
                  )}
                  {row.mode === 'raw' && row.rawText.trim() && (
                    <small className="recipe-ingredient-editor__review">
                      Raw review needed
                    </small>
                  )}
                  {row.reason && <small>{row.reason}</small>}
                </div>

                <div className="recipe-ingredient-editor__row-controls">
                  <button
                    type="button"
                    disabled={row.parsing}
                    onClick={() =>
                      updateRowMode(row, row.mode === 'rich' ? 'raw' : 'rich')
                    }
                  >
                    {row.mode === 'rich' ? 'Raw' : 'Rich'}
                  </button>
                  <button
                    type="button"
                    aria-label={`Remove ingredient ${index + 1}`}
                    onClick={() =>
                      setRows((current) =>
                        current.filter((item) => item.id !== row.id),
                      )
                    }
                  >
                    Remove
                  </button>
                </div>
              </li>
            )
          })}
          </ol>
        </>
      )}

      {defaultMode === 'rich' && (
        <>
          <button
            type="button"
            onClick={() =>
              setRows((current) => [...current, createRow('', 'rich')])
            }
          >
            Add ingredient
          </button>
          <small>
            Rich fields save back to one readable line. Custom names and units
            are allowed.
          </small>
        </>
      )}
    </fieldset>
  )
}
