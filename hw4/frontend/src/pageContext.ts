import type { CatalogueQuery, PageContext } from './api'

const NUMBER_KEYS = ['min_price', 'max_price'] as const
const TEXT_KEYS = ['query', 'category', 'color', 'size'] as const

/** Describe the current route for the chat agent. */
export function pageContextFor(pathname: string, search: string): PageContext {
  const path = pathname + search
  const product = pathname.match(/^\/products\/([^/]+)\/?$/)
  if (product) {
    return { path, page_type: 'product', product_id: decodeURIComponent(product[1]) }
  }
  if (pathname === '/products') {
    const params = new URLSearchParams(search)
    if (!params.has('title')) return { path, page_type: 'products' }
    // Chat results on the Products page: send the search so the backend can rebuild the list.
    const results: CatalogueQuery = { in_stock_only: params.get('in_stock_only') === 'true' }
    for (const key of TEXT_KEYS) {
      const value = params.get(key)
      if (value) results[key] = value
    }
    for (const key of NUMBER_KEYS) {
      const value = params.get(key)
      if (value) results[key] = Number(value)
    }
    return {
      path,
      page_type: 'products',
      results_title: params.get('title') ?? undefined,
      results_search: results,
    }
  }
  const named: Record<string, PageContext['page_type']> = {
    '/': 'home',
    '/about': 'about',
    '/login': 'login',
    '/create-account': 'create-account',
  }
  return { path, page_type: named[pathname] ?? 'other' }
}
