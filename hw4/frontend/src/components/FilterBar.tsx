import type { CardProduct } from '../api'

export const CATEGORIES = [
  { value: 'hoodie', label: 'Hoodies' },
  { value: 'sweatshirt', label: 'Sweatshirts' },
  { value: 't-shirt', label: 'Tees' },
  { value: 'quarter-zip', label: 'Quarter-zips' },
  { value: 'jacket', label: 'Jackets' },
  { value: 'long-sleeve shirt', label: 'Long sleeve' },
]
const SIZES = ['XS', 'S', 'M', 'L', 'XL', 'XXL']

export type SortKey = 'featured' | 'price-asc' | 'price-desc' | 'name'

export interface Filters {
  category: string // '' = all
  size: string // '' = any
  inStockOnly: boolean
  sort: SortKey
}

export const EMPTY_FILTERS: Filters = { category: '', size: '', inStockOnly: false, sort: 'featured' }

/** Apply the filter bar to a product list. 'featured' keeps the incoming order. */
export function applyFilters<T extends CardProduct>(items: T[], f: Filters): T[] {
  const out = items.filter(
    (p) =>
      (!f.category || p.category === f.category) &&
      (!f.size || p.sizes_in_stock.includes(f.size)) &&
      (!f.inStockOnly || p.total_stock > 0),
  )
  if (f.sort === 'price-asc') out.sort((a, b) => a.price - b.price || a.name.localeCompare(b.name))
  if (f.sort === 'price-desc') out.sort((a, b) => b.price - a.price || a.name.localeCompare(b.name))
  if (f.sort === 'name') out.sort((a, b) => a.name.localeCompare(b.name))
  return out
}

interface Props {
  items: CardProduct[]
  filters: Filters
  onChange: (f: Filters) => void
}

export default function FilterBar({ items, filters, onChange }: Props) {
  const set = (patch: Partial<Filters>) => onChange({ ...filters, ...patch })
  // Only offer categories that exist in the current list, with counts.
  const counts = new Map<string, number>()
  for (const p of items) counts.set(p.category, (counts.get(p.category) ?? 0) + 1)
  const active =
    filters.category !== '' || filters.size !== '' || filters.inStockOnly || filters.sort !== 'featured'

  return (
    <div className="filter-bar">
      <div className="filter-chips" role="group" aria-label="Category">
        <button
          className={`chip-btn${filters.category === '' ? ' active' : ''}`}
          onClick={() => set({ category: '' })}
        >
          All <span>{items.length}</span>
        </button>
        {CATEGORIES.filter((c) => counts.has(c.value)).map((c) => (
          <button
            key={c.value}
            className={`chip-btn${filters.category === c.value ? ' active' : ''}`}
            onClick={() => set({ category: filters.category === c.value ? '' : c.value })}
          >
            {c.label} <span>{counts.get(c.value)}</span>
          </button>
        ))}
      </div>
      <div className="filter-controls">
        <label>
          Has my size
          <select value={filters.size} onChange={(e) => set({ size: e.target.value })}>
            <option value="">Any size</option>
            {SIZES.map((s) => (
              <option key={s} value={s}>
                {s} in stock
              </option>
            ))}
          </select>
        </label>
        <label className="toggle">
          <input
            type="checkbox"
            checked={filters.inStockOnly}
            onChange={(e) => set({ inStockOnly: e.target.checked })}
          />
          In stock only
        </label>
        <label>
          Sort
          <select value={filters.sort} onChange={(e) => set({ sort: e.target.value as SortKey })}>
            <option value="featured">Featured</option>
            <option value="price-asc">Price: low to high</option>
            <option value="price-desc">Price: high to low</option>
            <option value="name">Name A–Z</option>
          </select>
        </label>
        {active && (
          <button className="link-btn" onClick={() => onChange(EMPTY_FILTERS)}>
            Clear filters
          </button>
        )}
      </div>
    </div>
  )
}
