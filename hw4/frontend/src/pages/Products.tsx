import { useEffect, useMemo, useState } from 'react'
import { Link, useLocation, useSearchParams } from 'react-router-dom'
import { fetchPageResults, fetchProducts, type CardProduct, type PageResults, type Product } from '../api'
import FilterBar, { applyFilters, EMPTY_FILTERS, type Filters } from '../components/FilterBar'
import ProductCard from '../components/ProductCard'

// Set by the chat widget when it navigates here, so results show instantly
// without a second request. A reload or shared link falls back to /api/search.
interface ChatNavState {
  pageResults?: PageResults
  resultsKey?: string
}

export default function Products() {
  const [params] = useSearchParams()
  const location = useLocation()
  const navState = location.state as ChatNavState | null
  const resultsKey = params.toString()
  const fromChat = params.has('title')

  const [allProducts, setAllProducts] = useState<Product[] | null>(null)
  const [chatResults, setChatResults] = useState<PageResults | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [filter, setFilter] = useState('')
  // Home page category tiles link to /products?category=hoodie (no title = not chat results).
  const initialFilters = (): Filters => ({
    ...EMPTY_FILTERS,
    category: fromChat ? '' : params.get('category') ?? '',
  })
  const [filters, setFilters] = useState<Filters>(initialFilters)

  // Full catalogue (default view).
  useEffect(() => {
    if (fromChat || allProducts) return
    fetchProducts()
      .then(setAllProducts)
      .catch((e: Error) => setError(e.message))
  }, [fromChat, allProducts])

  // Chat search results: use what the chat passed along, or re-run the search from the URL.
  useEffect(() => {
    setFilters(initialFilters())
    setFilter('')
    if (!fromChat) {
      setChatResults(null)
      return
    }
    if (navState?.pageResults && navState.resultsKey === resultsKey) {
      setChatResults(navState.pageResults)
      return
    }
    setChatResults(null)
    fetchPageResults(params)
      .then(setChatResults)
      .catch((e: Error) => setError(e.message))
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [resultsKey])

  const source: CardProduct[] | null = fromChat ? chatResults?.products ?? null : allProducts

  const visible = useMemo(() => {
    if (!source) return []
    const q = filter.trim().toLowerCase()
    const matching = !q
      ? source
      : source.filter((p) => {
          const { colors = [], search_tags = [] } = p as Partial<Product>
          return [p.name, p.description, ...colors, ...search_tags].join(' ').toLowerCase().includes(q)
        })
    return applyFilters(matching, filters)
  }, [source, filter, filters])

  return (
    <section className="section">
      {fromChat && (
        <div className="chat-results-banner" key={`banner-${resultsKey}`}>
          <span className="chat-results-icon">💬</span>
          <div>
            <small>Results from the chat</small>
            <strong>{chatResults?.title ?? params.get('title')}</strong>
          </div>
          <Link to="/products" className="btn btn-small btn-outline">
            Show all products
          </Link>
        </div>
      )}
      <div className="section-head">
        <div>
          <h1>{fromChat ? chatResults?.title ?? params.get('title') : 'Products'}</h1>
          {source && (
            <p className="muted">
              {visible.length} {visible.length === 1 ? 'item' : 'items'}
            </p>
          )}
        </div>
        <input
          className="search"
          type="search"
          placeholder={fromChat ? 'Filter these results…' : 'Search hoodies, colleges, colors…'}
          value={filter}
          onChange={(e) => setFilter(e.target.value)}
        />
      </div>
      {source && <FilterBar items={source} filters={filters} onChange={setFilters} />}
      {error && <p className="error">Couldn't load products: {error}</p>}
      {!source && !error && <p className="muted">Loading products…</p>}
      {source && visible.length === 0 && (
        <p className="muted">
          No products match these filters.{' '}
          <button className="link-btn" onClick={() => { setFilters(EMPTY_FILTERS); setFilter('') }}>
            Clear filters
          </button>
        </p>
      )}
      <div className={`product-grid${fromChat ? ' product-grid-chat' : ''}`} key={`grid-${resultsKey}`}>
        {visible.map((p) => (
          <ProductCard key={p.product_id} product={p} />
        ))}
      </div>
    </section>
  )
}
